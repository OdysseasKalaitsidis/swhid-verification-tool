# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from swh.model.model import Content, Directory, DirectoryEntry
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

SWH_API_BASE = "https://archive.softwareheritage.org/api/1"
DEFAULT_TIMEOUT = 30  # seconds

class SWHClient:
    def __init__(self, auth_token: Optional[str] = None):
        self.session = requests.Session()
        self.suppress_save = True
        
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
            self.set_token(auth_token)
        
        self.session.headers.update({"User-Agent": "SWHID-Verification-Tool/1.0"})

    def set_token(self, token: str) -> None:
        """Dynamically sets the Software Heritage API token."""
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def check_swhid(self, swhid: str) -> bool:
        """
        Checks if a SWHID exists in the archive.

        NOTE: this previously hit /api/1/provenance/{swhid}/, which is not a
        valid public endpoint. The real provenance API lives at
        /api/1/provenance/whereis/(target)/ and, per SWH's own docs, "is not
        publicly available and requires authentication and special user
        permission" - so the old code would report "not found" for every
        SWHID regardless of whether it was actually archived. Route by SWHID
        type to the correct, public, per-object endpoint instead (the same
        pattern the original PoC used successfully).
        """
        try:
            parts = swhid.split(":")
            if len(parts) < 4:
                return False
            obj_type, obj_hash = parts[2], parts[3]
            endpoint = {
                "cnt": f"content/sha1_git:{obj_hash}",
                "dir": f"directory/{obj_hash}",
                "rev": f"revision/{obj_hash}",
                "rel": f"release/{obj_hash}",
                "snp": f"snapshot/{obj_hash}",
            }.get(obj_type)
            if endpoint is None:
                logger.error(f"Unknown SWHID type in {swhid}")
                return False
            url = f"{SWH_API_BASE}/{endpoint}/"
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking SWHID {swhid}: {e}")
            return False

    def get_directory_for_revision(self, rev_id: str, path_in_vcs: str = "") -> Optional[str]:
        """
        Given a git commit sha1, returns the SWH directory hash for that
        revision's root, or for the given subdirectory if path_in_vcs is set
        (monorepo case).
        """
        revision = self.get_revision(rev_id)
        if revision is None:
            return None
        root_dir = revision.get("directory")
        if not root_dir:
            return None
        if not path_in_vcs:
            return root_dir

        current = root_dir
        for part in path_in_vcs.strip("/").split("/"):
            url = f"{SWH_API_BASE}/directory/{current}/"
            try:
                resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching directory {current}: {e}")
                return None
            if resp.status_code != 200:
                return None
            match = next((e for e in resp.json() if e["name"] == part and e["type"] == "dir"), None)
            if match is None:
                return None
            current = match["target"]
        return current

    def build_directory_blob_index(self, dir_hash: str, prefix: str = "") -> Dict[str, str]:
        """
        Recursively walks a SWH directory tree, returning {relative_path: content_sha1_git}
        for every regular file. Mirrors the approach proven in the original PoC's
        crate_normalizer.py (_build_swh_tree).
        """
        url = f"{SWH_API_BASE}/directory/{dir_hash}/"
        try:
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching directory {dir_hash}: {e}")
            return {}
        if resp.status_code != 200:
            return {}

        blobs: Dict[str, str] = {}
        for entry in resp.json():
            rel = f"{prefix}{entry['name']}" if not prefix else f"{prefix}/{entry['name']}"
            if entry["type"] == "dir":
                blobs.update(self.build_directory_blob_index(entry["target"], rel))
            elif entry["type"] == "file":
                blobs[rel] = entry["target"]
            # symlinks intentionally skipped, matching the proven PoC behavior
        return blobs


    def get_revision(self, rev_id: str) -> Optional[Dict[str, Any]]:
        """Gets revision info from SWH."""
        url = f"{SWH_API_BASE}/revision/{rev_id}/"
        try:
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 200:
                from typing import cast
                return cast(Dict[str, Any], response.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching revision {rev_id}: {e}")
        return None

    def trigger_save_code_now(self, origin_url: str, visit_type: str = "git") -> Dict[str, Any]:
        """Triggers a 'Save Code Now' request for an origin."""
        if self.suppress_save:
            return {"status": "Suppressed", "message": "Save Code Now is disabled by default"}
            
        url = f"{SWH_API_BASE}/origin/save/{visit_type}/url/{origin_url}/"
        try:
            response = self.session.post(url, timeout=DEFAULT_TIMEOUT)
            if response.status_code in [200, 201]:
                from typing import cast
                return cast(Dict[str, Any], response.json())
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

