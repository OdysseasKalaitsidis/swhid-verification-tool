# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import io
import re
import shutil
import zipfile
import requests
import urllib.parse
from typing import Dict, Any, Optional

from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient
from swh.model.from_disk import Directory as SWHDirectory

class GoLangStrategy(VerificationStrategy):
    GO_PROXY = "https://proxy.golang.org"

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        # Go module name is the import path (e.g. github.com/gin-gonic/gin)
        # Note: purl_parser might have joined namespace if present, but for golang,
        # namespace is the domain + org (e.g. namespace="github.com/gin-gonic", name="gin")
        # Let's rebuild the full module path
        module_path = name.replace(":", "/")
        purl = f"pkg:golang/{module_path}@{version}"
        findings: Dict[str, Any] = {"purl": purl, "strategies_tried": []}

        try:
            # 1. Strategy A: Metadata & Tag Matching
            metadata_result = self._strategy_a_metadata(module_path, version)
            findings["strategies_tried"].append({"name": "A: Metadata", "result": metadata_result})
            if metadata_result.get("status") == "Verified":
                findings.update(metadata_result)
                findings["confidence"] = "Verified"
                return findings
            elif metadata_result.get("status") in ["Inferred", "Partial"]:
                findings.update(metadata_result)
                findings["confidence"] = metadata_result.get("status")

            # 2. Strategy B: Go Proxy Zip Matching
            file_level_result = self._strategy_b_file_level(module_path, version)
            findings["strategies_tried"].append({"name": "B: File-level", "result": file_level_result})
            
            # Confidence scoring: Verified (3) > Inferred (2) > Partial (1) > Failed/Error (0)
            def get_score(status: Optional[str]) -> int:
                return {"Verified": 3, "Inferred": 2, "Partial": 1}.get(status or "", 0)
                
            if get_score(file_level_result.get("status")) >= get_score(findings.get("status")):
                findings.update(file_level_result)
                findings["confidence"] = file_level_result.get("confidence", "None")

            return findings

        except Exception as e:
            return {"purl": purl, "status": "Error", "reason": str(e)}

    def _case_encode(self, path: str) -> str:
        """
        Go proxy requires case-encoding where uppercase letters are replaced by '!' followed by lowercase.
        E.g. github.com/Sirupsen/logrus -> github.com/!sirupsen/logrus
        The domain name (first element) is always lowercase.
        """
        parts = path.split("/")
        if len(parts) > 0:
            parts[0] = parts[0].lower()
            
        encoded_parts = []
        for part in parts:
            encoded_chars = []
            for char in part:
                if char.isupper():
                    encoded_chars.append("!" + char.lower())
                else:
                    encoded_chars.append(char)
            encoded_parts.append("".join(encoded_chars))
        return "/".join(encoded_parts)

    def _resolve_go_import(self, module_path: str) -> Optional[str]:
        """
        Resolves the VCS repository URL for a Go module using the go-get protocol.
        """
        # If it's github.com, we can shortcut
        if module_path.startswith("github.com/"):
            parts = module_path.split("/")
            if len(parts) >= 3:
                return f"https://{parts[0]}/{parts[1]}/{parts[2]}"

        try:
            # Request with ?go-get=1
            url = f"https://{module_path}?go-get=1"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                # Find <meta name="go-import" content="prefix type repo">
                match = re.search(r'<meta\s+name="go-import"\s+content="([^"]+)"', resp.text)
                if match:
                    parts = match.group(1).split()
                    if len(parts) >= 3 and parts[1] == "git":
                        return parts[2]
        except Exception:
            pass
        return None

    def _strategy_a_metadata(self, module_path: str, version: str) -> Dict[str, Any]:
        """
        Strategy A: Resolve repo URL via go-get, and match version tag in SWH.
        """
        try:
            repo_url = self._resolve_go_import(module_path)
            if not repo_url:
                return {"status": "Failed", "reason": f"Could not resolve repository URL for {module_path}"}

            # Normalize repo URL
            repo_url = repo_url.replace("git+", "").replace("git://", "https://")
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]

            # Check if SWH has archived this repo
            encoded_url = urllib.parse.quote_plus(repo_url)
            swh_url = f"https://archive.softwareheritage.org/api/1/origin/{encoded_url}/visit/latest/"
            swh_resp = self.swh.session.get(swh_url, timeout=30)

            possible_tags = [version, f"v{version}"]

            if swh_resp.status_code == 200:
                snapshot_id = swh_resp.json().get("snapshot")
                if snapshot_id:
                    snapshot_url = f"https://archive.softwareheritage.org/api/1/snapshot/{snapshot_id}/"
                    snap_resp = self.swh.session.get(snapshot_url, timeout=30)
                    if snap_resp.status_code == 200:
                        branches = snap_resp.json().get("branches", {})
                        matching_revision = None
                        matched_tag_name = None
                        for ref_name, branch_data in branches.items():
                            if not branch_data:
                                continue
                            short_name = ref_name.replace("refs/tags/", "").replace("refs/heads/", "")
                            if short_name in possible_tags:
                                if branch_data.get("target_type") == "revision" and branch_data.get("target"):
                                    matching_revision = branch_data.get("target")
                                    matched_tag_name = short_name
                                    break

                        if matching_revision:
                            swhid = f"swh:1:rev:{matching_revision}"
                            return {
                                "status": "Verified",
                                "swhid": swhid,
                                "strategy": "A",
                                "confidence": "Verified",
                                "repo_url": repo_url,
                                "tag_matched": matched_tag_name
                            }

                self.swh.trigger_save_code_now(repo_url)
                return {
                    "status": "Inferred",
                    "repo_url": repo_url,
                    "strategy": "A",
                    "confidence": "Inferred",
                    "reason": "Origin archived but no exact tag match found in SWH snapshot; triggered Save Code Now to update"
                }
            else:
                # Trigger Save Code Now
                self.swh.trigger_save_code_now(repo_url)
                return {
                    "status": "Partial",
                    "repo_url": repo_url,
                    "strategy": "A",
                    "confidence": "Partial",
                    "reason": "Origin not archived in SWH; triggered Save Code Now"
                }

        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _strategy_b_file_level(self, module_path: str, version: str) -> Dict[str, Any]:
        """
        Strategy B: Download the module source zip from proxy.golang.org and compute SWHID.
        """
        try:
            encoded_module = self._case_encode(module_path)
            encoded_version = self._case_encode(version)
            
            zip_url = f"{self.GO_PROXY}/{encoded_module}/@v/{encoded_version}.zip"
            resp = requests.get(zip_url)
            if resp.status_code != 200:
                return {"status": "Failed", "reason": f"Could not download zip from Go Proxy: {resp.status_code}"}

            # Create temp directory
            safe_name = module_path.replace("/", "_").replace(".", "_")
            tmp_dir = f"tmp_go_{safe_name}_{version}"
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)

            # Unpack zip
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Go proxy zips always unpack into a single directory named '{module}@{version}'
            # Since the zip path contains the case-encoded module path, the directory name matches.
            items = os.listdir(tmp_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                unpack_dir = os.path.join(tmp_dir, items[0])
            else:
                unpack_dir = tmp_dir

            # Compute directory SWHID using SWHDirectory.from_disk
            swhid_obj = SWHDirectory.from_disk(path=os.fsencode(unpack_dir), max_content_length=None).swhid()
            swhid = str(swhid_obj)

            # Clean up
            shutil.rmtree(tmp_dir)

            found = self.swh.check_swhid(swhid)
            return {
                "status": "Verified" if found else "Partial",
                "swhid": swhid,
                "strategy": "B",
                "confidence": "Verified" if found else "Partial"
            }

        except Exception as e:
            return {"status": "Error", "reason": str(e)}
