import os
import re
import io
import shutil
import tarfile
import zipfile
import requests
from typing import Dict, Any, Optional, List
from shwid_tool.strategies.base import VerificationStrategy
from shwid_tool.core import SWHClient, compute_directory_swhid
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
        # Implementation for Sigstore verification
        # For now, a placeholder logic similar to existing script but structured
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

            # TODO: Use sigstore library for real verification
            # Extract commit SHA (dummy logic for now, using existing regex)
            import base64
            prov_data = prov_resp.json()
            cert_b64 = prov_data["attestation_bundles"][0]["attestations"][0]["verification_material"]["certificate"]
            cert_bytes = base64.b64decode(cert_b64)
            matches = re.findall(r"[0-9a-f]{40}", cert_bytes.decode("latin-1"))
            if not matches:
                return {"status": "Failed", "reason": "Commit SHA not found in cert"}
            
            commit_sha = matches[0]
            swhid = f"swh:1:rev:{commit_sha}"
            if self.swh.check_swhid(swhid):
                return {"status": "Verified", "swhid": swhid, "strategy": "A"}
            return {"status": "Partial", "reason": "Commit not in SWH", "swhid": swhid}
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _strategy_b_metadata(self, name: str, version: str) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.PYPI_API}/{name}/{version}/json")
            resp.raise_for_status()
            info = resp.json().get("info", {})
            project_urls = info.get("project_urls", {})
            
            repo_url = None
            for key in ["Source", "GitHub", "Repository", "Homepage"]:
                url = project_urls.get(key, "")
                if "github.com" in url or "gitlab.com" in url:
                    repo_url = url
                    break
            
            if not repo_url:
                return {"status": "Failed", "reason": "No repository URL in metadata"}

            # Fuzzy matching for tags (e.g., v1.0.0, release-1.0.0)
            # In a real impl, we'd fetch tags from the repo.
            # For now, let's assume we found a tag match if we can.
            return {"status": "Inferred", "repo_url": repo_url, "strategy": "B"}
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _strategy_c_file_level(self, name: str, version: str) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.PYPI_API}/{name}/{version}/json")
            resp.raise_for_status()
            urls = resp.json()["urls"]
            
            # Prefer sdist, then wheel
            artifact = next((f for f in urls if f["packagetype"] == "sdist"), None)
            if not artifact:
                artifact = next((f for f in urls if f["packagetype"] == "bdist_wheel"), None)
            
            if not artifact:
                return {"status": "Failed", "reason": "No artifact found"}

            # Download and compute SWHID
            resp = requests.get(artifact["url"])
            resp.raise_for_status()
            
            # Temporary extraction
            tmp_dir = "tmp_pypi_extract"
            if os.path.exists(tmp_dir): shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)
            
            if artifact["filename"].endswith(".tar.gz"):
                with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                    tar.extractall(path=tmp_dir)
            elif artifact["filename"].endswith(".whl") or artifact["filename"].endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zip_ref:
                    zip_ref.extractall(tmp_dir)
            
            # Compute SWHID of the directory
            # Usually there is an inner directory in sdist
            source_path = tmp_dir
            items = os.listdir(tmp_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(tmp_dir, items[0])):
                source_path = os.path.join(tmp_dir, items[0])

            swhid = SWHDirectory.from_disk(path=os.fsencode(source_path)).swhid()
            shutil.rmtree(tmp_dir)

            found = self.swh.check_swhid(str(swhid))
            return {
                "status": "Verified" if found else "Partial",
                "swhid": str(swhid),
                "strategy": "C",
                "confidence": "Verified" if found else "Partial"
            }
        except Exception as e:
            return {"status": "Error", "reason": str(e)}
