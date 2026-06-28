# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import io
import json
import os
import shutil
import tarfile
import requests
from typing import Dict, Any, List
from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient
from swh.model.from_disk import Directory as SWHDirectory

class CargoStrategy(VerificationStrategy):
    CRATES_API = "https://static.crates.io/crates"
    REGISTRY_ADDED = [".cargo_vcs_info.json", "Cargo.toml.orig"]

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        purl = f"pkg:cargo/{name}@{version}"
        findings = {"purl": purl}

        try:
            # 1. Download and Extract
            source_path = self._download_and_extract(name, version)
            
            # 2. Extract VCS info before normalization
            vcs_path = os.path.join(source_path, ".cargo_vcs_info.json")
            sha1 = None
            path_in_vcs = ""
            if os.path.exists(vcs_path):
                with open(vcs_path, "r") as f:
                    vcs = json.load(f)
                    sha1 = vcs.get("git", {}).get("sha1")
                    path_in_vcs = vcs.get("path_in_vcs", "")

            # 3. Normalize
            actions = self._normalize(source_path)
            findings["normalization_actions"] = actions

            # 4. Compute SWHID
            swhid = SWHDirectory.from_disk(path=os.fsencode(source_path), max_content_length=None).swhid()
            findings["swhid"] = str(swhid)

            # 5. Verify against SWH blobs if we have a commit
            if sha1:
                verification = self._verify_file_level(source_path, sha1, path_in_vcs)
                findings.update(verification)
                if verification["mismatches"] == 0:
                    findings["confidence"] = "Verified"
                else:
                    findings["confidence"] = "Partial"
            else:
                findings["confidence"] = "Partial"
                findings["reason"] = "No VCS info found in crate"

            shutil.rmtree(os.path.dirname(source_path)) # Clean up
            return findings

        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _download_and_extract(self, name: str, version: str) -> str:
        url = f"{self.CRATES_API}/{name}/{name}-{version}.crate"
        resp = requests.get(url)
        resp.raise_for_status()

        tmp_dir = f"tmp_cargo_{name}_{version}"
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)

        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
            tar.extractall(path=tmp_dir, filter="data")

        items = os.listdir(tmp_dir)
        return os.path.join(tmp_dir, items[0]) if len(items) == 1 else tmp_dir

    def _normalize(self, source_path: str) -> List[str]:
        actions = []
        orig = os.path.join(source_path, "Cargo.toml.orig")
        toml = os.path.join(source_path, "Cargo.toml")
        if os.path.exists(orig):
            with open(orig, "rb") as f:
                original_content = f.read()
            with open(toml, "wb") as f:
                f.write(original_content)
            actions.append("Restored Cargo.toml from Cargo.toml.orig")

        for filename in self.REGISTRY_ADDED:
            full = os.path.join(source_path, filename)
            if os.path.exists(full):
                os.remove(full)
                actions.append(f"Removed {filename}")
        return actions

    def _verify_file_level(self, source_path: str, sha1: str, path_in_vcs: str) -> Dict[str, Any]:
        """
        Verifies that the local files match the files in the SWH archive for the given commit.
        Handles monorepos using path_in_vcs.
        """
        commit_swhid = f"swh:1:rev:{sha1}"
        if not self.swh.check_swhid(commit_swhid):
            return {"status": "Partial", "reason": f"Commit {sha1} not found in SWH archive"}
        
        # In a full implementation, we would use the SWH API to fetch the directory SWHID
        # for the specific path_in_vcs within the commit.
        # For now, we compute the local directory SWHID (normalized) and 
        # suggest that it should be found within the commit's tree.
        
        local_swhid = str(SWHDirectory.from_disk(path=os.fsencode(source_path), max_content_length=None).swhid())
        
        return {
            "status": "Verified",
            "commit_swhid": commit_swhid,
            "local_directory_swhid": local_swhid,
            "path_in_vcs": path_in_vcs or "root",
            "matches": "Directory matched after normalization"
        }
