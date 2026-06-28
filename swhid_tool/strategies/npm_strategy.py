# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import io
import re
import shutil
import tarfile
import requests
import urllib.parse
from typing import Dict, Any, Optional

from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient
from swh.model.from_disk import Directory as SWHDirectory

class NpmStrategy(VerificationStrategy):
    NPM_REGISTRY = "https://registry.npmjs.org"

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        # Handle scoped packages (e.g. @babel:core -> @babel/core)
        npm_name = name.replace(":", "/")
        purl = f"pkg:npm/{npm_name}@{version}"
        findings = {"purl": purl, "strategies_tried": []}

        try:
            # Fetch registry metadata for the package
            # Scoped package names can be used directly in the URL
            resp = requests.get(f"{self.NPM_REGISTRY}/{urllib.parse.quote(npm_name, safe='@')}")
            if resp.status_code != 200:
                return {"purl": purl, "status": "Error", "reason": f"Package not found in npm registry: {resp.status_code}"}

            package_data = resp.json()
            version_data = package_data.get("versions", {}).get(version)
            if not version_data:
                return {"purl": purl, "status": "Error", "reason": f"Version {version} not found in npm registry"}

            # 1. Strategy A: Metadata & Tag Matching
            metadata_result = self._strategy_a_metadata(npm_name, version, version_data, package_data)
            findings["strategies_tried"].append({"name": "A: Metadata", "result": metadata_result})
            if metadata_result.get("status") == "Verified":
                findings.update(metadata_result)
                findings["confidence"] = "Verified"
                return findings
            elif metadata_result.get("status") == "Inferred":
                findings.update(metadata_result)
                findings["confidence"] = "Inferred"

            # 2. Strategy B: File-level / Tarball Matching
            file_level_result = self._strategy_b_file_level(npm_name, version, version_data)
            findings["strategies_tried"].append({"name": "B: File-level", "result": file_level_result})
            
            if file_level_result.get("status") == "Verified" or findings.get("status") != "Inferred":
                findings.update(file_level_result)
                findings["confidence"] = file_level_result.get("confidence", "None")

            return findings

        except Exception as e:
            return {"purl": purl, "status": "Error", "reason": str(e)}

    def _strategy_a_metadata(self, name: str, version: str, version_data: Dict[str, Any], package_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strategy A: Metadata/Git tag matching.
        Extracts repository URL and directory, and finds a matching tag in SWH.
        """
        try:
            # Extract repository URL (from version metadata or fallback to top-level metadata)
            repo_info = version_data.get("repository") or package_data.get("repository")
            if not repo_info:
                return {"status": "Failed", "reason": "No repository field in metadata"}

            repo_url = ""
            if isinstance(repo_info, dict):
                repo_url = repo_info.get("url", "")
            elif isinstance(repo_info, str):
                repo_url = repo_info

            if not repo_url:
                return {"status": "Failed", "reason": "Repository URL not found in repository field"}

            # Normalize Git URL (e.g. git+https://github.com/user/repo.git -> https://github.com/user/repo)
            repo_url = repo_url.replace("git+", "").replace("git://", "https://")
            if repo_url.startswith("git@github.com:"):
                repo_url = repo_url.replace("git@github.com:", "https://github.com/")
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            
            # Clean ssh://git@ or other prefixes
            repo_url = re.sub(r'^ssh://git@', 'https://', repo_url)

            # Extract repository directory (for monorepos)
            repo_dir = ""
            if isinstance(repo_info, dict):
                repo_dir = repo_info.get("directory", "")

            # Check if SWH has archived this repo
            encoded_url = urllib.parse.quote_plus(repo_url)
            swh_url = f"https://archive.softwareheritage.org/api/1/origin/{encoded_url}/visit/latest/"
            swh_resp = self.swh.session.get(swh_url, timeout=30)

            possible_tags = [version, f"v{version}", f"release-{version}", f"{name.split('/')[-1]}-{version}"]

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
                                "tag_matched": matched_tag_name,
                                "directory": repo_dir
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
        Strategy B: Tarball/File-level matching.
        Downloads the published tgz, unpacks it, and computes the directory SWHID.
        """
        try:
            dist_info = version_data.get("dist", {})
            tarball_url = dist_info.get("tarball")
            if not tarball_url:
                return {"status": "Failed", "reason": "No tarball URL found in registry"}

            resp = requests.get(tarball_url)
            resp.raise_for_status()

            # Clean name for safe directory path
            safe_name = name.replace("/", "_").replace("@", "")
            tmp_dir = f"tmp_npm_{safe_name}_{version}"
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)

            # Unpack tarball
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                tar.extractall(path=tmp_dir, filter="data")

            # npm tarballs always unpack into a single 'package' directory
            package_dir = os.path.join(tmp_dir, "package")
            if not os.path.exists(package_dir):
                # Fallback if package structure is different
                items = os.listdir(tmp_dir)
                if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                    package_dir = os.path.join(tmp_dir, items[0])
                else:
                    package_dir = tmp_dir

            # Compute directory SWHID using SWHDirectory.from_disk
            swhid_obj = SWHDirectory.from_disk(path=os.fsencode(package_dir), max_content_length=None).swhid()
            swhid = str(swhid_obj)

            # Clean up
            shutil.rmtree(tmp_dir)

            found = self.swh.check_swhid(swhid)
            return {
                "status": "Verified" if found else "Partial",
                "swhid": swhid,
                "strategy": "B",
                "confidence": "Verified" if found else "Partial",
            }

        except Exception as e:
            return {"status": "Error", "reason": str(e)}
