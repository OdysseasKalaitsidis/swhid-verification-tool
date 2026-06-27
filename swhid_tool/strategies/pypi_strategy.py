# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import re
import io
import shutil
import tarfile
import zipfile
import requests
import urllib.parse
from typing import Dict, Any, Optional, List
from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient, compute_directory_swhid
from swh.model.from_disk import Directory as SWHDirectory

class PyPIStrategy(VerificationStrategy):
    PYPI_API = "https://pypi.org/pypi"
    PYPI_INTEGRITY = "https://pypi.org/integrity"

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        purl = f"pkg:pypi/{name}@{version}"
        findings = {"purl": purl, "strategies_tried": []}

        # 1. Strategy A: Attestation
        attestation_result = self._strategy_a_attestation(name, version)
        findings["strategies_tried"].append({"name": "A: Attestation", "result": attestation_result})
        if attestation_result.get("status") == "Verified":
            findings.update(attestation_result)
            findings["confidence"] = "Verified"
            return findings

        # 2. Strategy B: Metadata
        metadata_result = self._strategy_b_metadata(name, version)
        findings["strategies_tried"].append({"name": "B: Metadata", "result": metadata_result})
        if metadata_result.get("status") == "Inferred":
            findings.update(metadata_result)
            findings["confidence"] = "Inferred"
            # We don't return yet, maybe Strategy C can get more "Verified" status?
            # Actually, the instructions say "three-tiered fallback", so if A fails, try B, if B fails, try C.
            # But B only gives a commit. We might want to verify that commit.
            return findings

        # 3. Strategy C: File-level
        file_level_result = self._strategy_c_file_level(name, version)
        findings["strategies_tried"].append({"name": "C: File-level", "result": file_level_result})
        findings.update(file_level_result)
        findings["confidence"] = file_level_result.get("confidence", "None")

        return findings

    def _strategy_a_attestation(self, name: str, version: str) -> Dict[str, Any]:
        """
        Strategy A: Sigstore/PEP 740 verification.
        Extracts commit SHA from Fulcio certificate extensions.
        """
        try:
            resp = requests.get(f"{self.PYPI_API}/{name}/{version}/json")
            resp.raise_for_status()
            urls = resp.json()["urls"]
            sdist = next((f for f in urls if f["packagetype"] == "sdist"), None)
            if not sdist:
                return {"status": "Skipped", "reason": "No sdist found"}

            filename = sdist["filename"]
            prov_resp = requests.get(f"{self.PYPI_INTEGRITY}/{name}/{version}/{filename}/provenance")
            if prov_resp.status_code == 404:
                return {"status": "Failed", "reason": "No PEP 740 attestation"}

            import base64
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            prov_data = prov_resp.json()
            # In PEP 740, the cert is in the attestation bundle
            cert_b64 = prov_data["attestation_bundles"][0]["attestations"][0]["verification_material"]["certificate"]
            cert_bytes = base64.b64decode(cert_b64)
            
            # Load as X.509 certificate
            # Check if it's DER or PEM
            try:
                cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
            except Exception:
                cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())

            # Fulcio OID for Source Repository Digest (Commit SHA)
            # 1.3.6.1.4.1.57264.1.13
            COMMIT_SHA_OID = "1.3.6.1.4.1.57264.1.13"
            commit_sha = None
            
            for ext in cert.extensions:
                if ext.oid.dotted_string == COMMIT_SHA_OID:
                    commit_sha = ext.value.value.decode("utf-8")
                    break
            
            # Fallback to SAN if OID not found (common in older sigstore)
            if not commit_sha:
                for ext in cert.extensions:
                    if ext.oid == x509.OID_SUBJECT_ALTERNATIVE_NAME:
                        san_values = ext.value.get_values_for_type(x509.UniformResourceIdentifier)
                        for val in san_values:
                            if "@" in val:
                                commit_sha = val.split("@")[-1]
                                break
            
            if not commit_sha:
                return {"status": "Failed", "reason": "Commit SHA not found in Fulcio certificate"}
            
            swhid = f"swh:1:rev:{commit_sha}"
            if self.swh.check_swhid(swhid):
                return {"status": "Verified", "swhid": swhid, "strategy": "A", "commit_sha": commit_sha}
            return {"status": "Partial", "reason": "Commit not in SWH", "swhid": swhid, "commit_sha": commit_sha}
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _strategy_b_metadata(self, name: str, version: str) -> Dict[str, Any]:
        """
        Strategy B: Metadata/Git tag matching.
        Uses PyPI project_urls and fuzzy tag matching.
        """
        try:
            resp = requests.get(f"{self.PYPI_API}/{name}/{version}/json")
            resp.raise_for_status()
            info = resp.json().get("info", {})
            project_urls = info.get("project_urls", {})
            
            repo_url = None
            for key in ["Source", "GitHub", "Repository", "Homepage"]:
                url = project_urls.get(key, "")
                if url and ("github.com" in url or "gitlab.com" in url):
                    repo_url = url.rstrip("/")
                    if repo_url.endswith(".git"): repo_url = repo_url[:-4]
                    break
            
            if not repo_url:
                return {"status": "Failed", "reason": "No repository URL in metadata"}

            # Fuzzy matching for tags
            possible_tags = [version, f"v{version}", f"release-{version}", f"{name}-{version}"]
            
            # Check if SWH has archived this repo
            encoded_url = urllib.parse.quote_plus(repo_url)
            swh_url = f"https://archive.softwareheritage.org/api/1/origin/{encoded_url}/visit/latest/"
            swh_resp = self.swh.session.get(swh_url, timeout=30)
            
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
                                "strategy": "B",
                                "confidence": "Verified",
                                "repo_url": repo_url,
                                "tag_matched": matched_tag_name
                            }
                
                return {
                    "status": "Inferred",
                    "repo_url": repo_url,
                    "strategy": "B",
                    "confidence": "Inferred",
                    "reason": "Origin archived but no exact tag match found in SWH snapshot"
                }
            else:
                # Trigger Save Code Now
                self.swh.trigger_save_code_now(repo_url)
                return {
                    "status": "Partial",
                    "repo_url": repo_url,
                    "strategy": "B",
                    "confidence": "Partial",
                    "reason": "Origin not archived in SWH; triggered Save Code Now"
                }
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _strategy_c_file_level(self, name: str, version: str) -> Dict[str, Any]:
        """
        Strategy C: File-level matching.
        Unpacks artifacts, strips non-source files, and computes SWHID.
        """
        try:
            resp = requests.get(f"{self.PYPI_API}/{name}/{version}/json")
            resp.raise_for_status()
            urls = resp.json()["urls"]
            
            # Prefer sdist
            artifact = next((f for f in urls if f["packagetype"] == "sdist"), None)
            is_wheel = False
            if not artifact:
                artifact = next((f for f in urls if f["packagetype"] == "bdist_wheel"), None)
                is_wheel = True
            
            if not artifact:
                return {"status": "Failed", "reason": "No artifact found"}

            resp = requests.get(artifact["url"])
            resp.raise_for_status()
            
            tmp_dir = f"tmp_pypi_{name}_{version}"
            if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)
            
            if artifact["filename"].endswith(".tar.gz"):
                with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                    tar.extractall(path=tmp_dir, filter="data")
            elif artifact["filename"].endswith(".whl") or artifact["filename"].endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zip_ref:
                    zip_ref.extractall(tmp_dir)
            
            # Normalization: Strip compiled extensions and metadata
            source_files = {}
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith(".py"): # Only pure Python
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, tmp_dir)
                        # Strip inner directory if sdist
                        if "/" in rel_path:
                            rel_path = "/".join(rel_path.split("/")[1:])
                        
                        with open(full_path, "rb") as f_obj:
                            source_files[rel_path] = f_obj.read()

            if not source_files:
                shutil.rmtree(tmp_dir)
                return {"status": "Failed", "reason": "No .py files found in artifact"}

            swhid = compute_directory_swhid(source_files)
            shutil.rmtree(tmp_dir)

            found = self.swh.check_swhid(swhid)
            return {
                "status": "Verified" if found else "Partial",
                "swhid": swhid,
                "strategy": "C",
                "confidence": "Verified" if found else "Partial",
                "file_count": len(source_files)
            }
        except Exception as e:
            return {"status": "Error", "reason": str(e)}
