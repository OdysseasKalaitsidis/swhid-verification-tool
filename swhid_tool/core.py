# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from swh.model.swhids import CoreSWHID, ObjectType
from swh.model.model import Content, Directory, DirectoryEntry
from swh.model.from_disk import Directory as DiskDirectory, Content as DiskContent
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

SWH_API_BASE = "https://archive.softwareheritage.org/api/1"
DEFAULT_TIMEOUT = 30  # seconds

class SWHClient:
    def __init__(self, auth_token: Optional[str] = None):
        self.session = requests.Session()
        
        # Configure robust retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,  # 2, 4, 8, 16, 32 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})
        
        self.session.headers.update({"User-Agent": "SWHID-Verification-Tool/1.0 (GSoC 2026)"})

    def check_swhid(self, swhid: str) -> bool:
        """Checks if a SWHID exists in the archive."""
        url = f"{SWH_API_BASE}/provenance/{swhid}/"
        try:
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking SWHID {swhid}: {e}")
            return False

    def get_revision(self, rev_id: str) -> Optional[Dict[str, Any]]:
        """Gets revision info from SWH."""
        url = f"{SWH_API_BASE}/revision/{rev_id}/"
        try:
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching revision {rev_id}: {e}")
        return None

    def trigger_save_code_now(self, origin_url: str, visit_type: str = "git") -> Dict[str, Any]:
        """Triggers a 'Save Code Now' request for an origin."""
        url = f"{SWH_API_BASE}/origin/save/{visit_type}/url/{origin_url}/"
        try:
            response = self.session.post(url, timeout=DEFAULT_TIMEOUT)
            if response.status_code in [200, 201]:
                return response.json()
            return {"status": "Error", "message": response.text, "code": response.status_code}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering Save Code Now for {origin_url}: {e}")
            return {"status": "Error", "message": str(e)}

def compute_content_swhid(content: bytes) -> str:
    """Computes swh:1:cnt for a file."""
    cnt = Content.from_data(data=content)
    return str(cnt.swhid())

def compute_directory_swhid(files: Dict[str, bytes]) -> str:
    """
    Computes swh:1:dir for a flat dictionary of filename -> content.
    """
    entries = []
    for name, content in files.items():
        cnt = Content.from_data(data=content)
        entries.append(
            DirectoryEntry(
                name=name.encode("utf-8"),
                type="file",
                target=cnt.swhid().object_id,
                perms=0o100644,
            )
        )
    
    entries.sort(key=lambda x: x.name)
    dir_obj = Directory(entries=tuple(entries))
    return str(dir_obj.swhid())

