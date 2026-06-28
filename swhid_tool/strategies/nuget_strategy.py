# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import io
import shutil
import zipfile
import requests
import urllib.parse
from typing import Dict, Any, Optional

from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient
from swh.model.from_disk import Directory as SWHDirectory

class NugetStrategy(VerificationStrategy):
    REGISTRATION_API = "https://api.nuget.org/v3/registration5-semver1"

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        # NuGet names are case-insensitive, but API endpoints expect lowercase
        lower_name = name.lower()
        purl = f"pkg:nuget/{name}@{version}"
        findings: Dict[str, Any] = {"purl": purl, "strategies_tried": []}

        try:
            # Fetch package version metadata from NuGet registration API
            url = f"{self.REGISTRATION_API}/{lower_name}/{version}.json"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return {"purl": purl, "status": "Error", "reason": f"Package version not found in NuGet registry: {resp.status_code}"}

            version_data = resp.json()

            # 1. Strategy A: Metadata & Tag Matching
            metadata_result = self._strategy_a_metadata(name, version, version_data)
            findings["strategies_tried"].append({"name": "A: Metadata", "result": metadata_result})
            if metadata_result.get("status") == "Verified":
                findings.update(metadata_result)
                findings["confidence"] = "Verified"
                return findings
            elif metadata_result.get("status") in ["Inferred", "Partial"]:
                findings.update(metadata_result)
                findings["confidence"] = metadata_result.get("status")

            # 2. Strategy B: File-level / Nupkg Matching
            file_level_result = self._strategy_b_file_level(name, version, version_data)
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

    def _strategy_a_metadata(self, name: str, version: str, version_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strategy A: Extract Git repo URL from catalog entry, and match version tag in SWH.
        """
        try:
            catalog_entry = version_data.get("catalogEntry", {})
            if isinstance(catalog_entry, str):
                # Fetch the catalog entry JSON from the URL
                catalog_resp = requests.get(catalog_entry, timeout=15)
                if catalog_resp.status_code == 200:
                    catalog_entry = catalog_resp.json()
                else:
                    catalog_entry = {}
            
            # Find repository URL
            repo_url = ""
            repo_info = catalog_entry.get("repository")
            if isinstance(repo_info, dict):
                repo_url = repo_info.get("url", "")
            
            # Fallback to projectUrl if repository is not specified
            if not repo_url:
                project_url = catalog_entry.get("projectUrl", "")
                if project_url and ("github.com" in project_url or "gitlab.com" in project_url):
                    repo_url = project_url

            if not repo_url:
                return {"status": "Failed", "reason": "Repository URL not found in NuGet metadata"}

            # Normalize Git URL
            repo_url = repo_url.replace("git+", "").replace("git://", "https://")
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]

            # Check if SWH has archived this repo
            encoded_url = urllib.parse.quote_plus(repo_url)
            swh_url = f"https://archive.softwareheritage.org/api/1/origin/{encoded_url}/visit/latest/"
            swh_resp = self.swh.session.get(swh_url, timeout=30)

            possible_tags = [version, f"v{version}", f"release-{version}"]

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

                return {
                    "status": "Inferred",
                    "repo_url": repo_url,
                    "strategy": "A",
                    "confidence": "Inferred",
                    "reason": "Origin archived but no exact tag match found in SWH snapshot"
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

    def _strategy_b_file_level(self, name: str, version: str, version_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strategy B: Download .nupkg file, extract, and compute SWHID.
        """
        try:
            nupkg_url = version_data.get("packageContent")
            if not nupkg_url:
                return {"status": "Failed", "reason": "No packageContent URL found in NuGet metadata"}

            resp = requests.get(nupkg_url)
            resp.raise_for_status()

            # Create temp directory
            tmp_dir = f"tmp_nuget_{name}_{version}"
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)

            # Unpack nupkg (which is a standard zip file)
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Normalization: Remove NuGet-specific packaging files
            # These are generated by the NuGet packaging process and not part of the source.
            for root, dirs, files in os.walk(tmp_dir, topdown=False):
                for f in files:
                    if f.endswith(".nuspec") or f == "[Content_Types].xml" or f.endswith(".psmdcp"):
                        os.remove(os.path.join(root, f))
                
                # Remove metadata directories
                for d in dirs:
                    if d in ["_rels", "package"]:
                        shutil.rmtree(os.path.join(root, d))

            # Compute directory SWHID using SWHDirectory.from_disk
            swhid_obj = SWHDirectory.from_disk(path=os.fsencode(tmp_dir), max_content_length=None).swhid()
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
