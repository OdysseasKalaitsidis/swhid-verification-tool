import os
import requests
from swh.model.swhids import CoreSWHID, ObjectType
from swh.model.model import Content, Directory, DirectoryEntry
from swh.model.from_disk import Directory as DiskDirectory, Content as DiskContent
from typing import Dict, List, Optional, Any

SWH_API_BASE = "https://archive.softwareheritage.org/api/1"

class SWHClient:
    def __init__(self, auth_token: Optional[str] = None):
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})

    def check_swhid(self, swhid: str) -> bool:
        """Checks if a SWHID exists in the archive."""
        # Note: swhids in API usually omit the swh:1: prefix if using specific endpoints
        # But /provenance/ takes the full swhid
        url = f"{SWH_API_BASE}/provenance/{swhid}/"
        response = self.session.get(url)
        if response.status_code == 200:
            return True
        return False

    def get_revision(self, rev_id: str) -> Optional[Dict[str, Any]]:
        """Gets revision info from SWH."""
        url = f"{SWH_API_BASE}/revision/{rev_id}/"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    def trigger_save_code_now(self, origin_url: str, visit_type: str = "git") -> Dict[str, Any]:
        """Triggers a 'Save Code Now' request for an origin."""
        url = f"{SWH_API_BASE}/origin/save/{visit_type}/url/{origin_url}/"
        response = self.session.post(url)
        if response.status_code in [200, 201]:
            return response.json()
        return {"status": "Error", "message": response.text, "code": response.status_code}

def compute_content_swhid(content: bytes) -> str:
    """Computes swh:1:cnt for a file."""
    cnt = Content.from_dict({"data": content})
    return str(cnt.swhid())

def compute_directory_swhid(files: Dict[str, bytes]) -> str:
    """
    Computes swh:1:dir for a flat dictionary of filename -> content.
    """
    entries = []
    for name, content in files.items():
        cnt = Content.from_dict({"data": content})
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
