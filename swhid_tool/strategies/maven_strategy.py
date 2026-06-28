# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import io
import re
import zipfile
import requests
import xml.etree.ElementTree as ET
import hashlib
from typing import Dict, Any, Optional, Tuple
from swhid_tool.strategies.base import VerificationStrategy
from swhid_tool.core import SWHClient

class MavenStrategy(VerificationStrategy):
    MAVEN_CENTRAL = "https://repo1.maven.org/maven2"
    NS = "http://maven.apache.org/POM/4.0.0"

    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def resolve(self, name: str, version: str, qualifiers: Dict[str, str]) -> Dict[str, Any]:
        # Maven name is group:artifact
        if ":" not in name:
            return {"status": "Error", "reason": "Maven name must be group:artifact"}
        
        group_id, artifact_id = name.split(":")
        purl = f"pkg:maven/{group_id}/{artifact_id}@{version}"
        findings: Dict[str, Any] = {"purl": purl}

        try:
            group_path = group_id.replace(".", "/")
            base_url = f"{self.MAVEN_CENTRAL}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}"
            
            # 1. Strategy A: SCM Block
            pom_text = self._fetch_pom(base_url)
            scm = self._parse_scm(pom_text)
            findings["scm"] = scm
            
            # 2. Strategy B: Sources JAR
            sources_jar_result = self._inspect_sources_jar(base_url, scm)
            findings.update(sources_jar_result)
            
            if sources_jar_result.get("status") == "Verified":
                findings["confidence"] = "Verified"
            else:
                findings["confidence"] = "Partial"
            
            if "first_verified_swhid" in sources_jar_result:
                findings["swhid"] = sources_jar_result["first_verified_swhid"]
                del findings["first_verified_swhid"]

            return findings

        except Exception as e:
            return {"purl": purl, "status": "Error", "reason": str(e)}

    def _fetch_pom(self, base_url: str) -> str:
        resp = requests.get(base_url + ".pom")
        resp.raise_for_status()
        return resp.text

    def _parse_scm(self, pom_text: str) -> Dict[str, str]:
        root = ET.fromstring(pom_text)
        def find(element: ET.Element, tag: str) -> Optional[ET.Element]:
            node = element.find(f"{{{self.NS}}}{tag}")
            if node is None:
                node = element.find(tag)
            return node
        
        scm = find(root, "scm")
        if scm is None:
            return {}
        
        def text(tag: str) -> str:
            node = find(scm, tag)
            return (node.text or "").strip() if node is not None else ""
        
        return {"url": text("url"), "tag": text("tag")}

    def _extract_github_owner_repo(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        if not url:
            return None, None
        m = re.search(r"github\.com/([^/]+)/([^/\s]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _fetch_git_tree(self, owner: str, repo: str, tag: str) -> Optional[Dict[str, str]]:
        headers = {"Accept": "application/vnd.github+json"}
        for ref in [tag, f"v{tag}"]:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
            try:
                resp = self.swh.session.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    return {e["path"]: e["sha"] for e in data.get("tree", []) if e["type"] == "blob"}
            except Exception:
                pass
        return None

    def _git_blob_sha1(self, data: bytes) -> str:
        header = f"blob {len(data)}\0".encode()
        return hashlib.sha1(header + data).hexdigest()

    def _strip_src_prefix(self, path: str) -> str:
        for prefix in ["src/main/java/", "src/test/java/", "src/main/resources/", "src/test/resources/"]:
            if path.startswith(prefix):
                return path[len(prefix):]
        return path

    def _inspect_sources_jar(self, base_url: str, scm: Dict[str, str]) -> Dict[str, Any]:
        try:
            resp = self.swh.session.get(base_url + "-sources.jar", timeout=30)
            if resp.status_code != 200:
                return {"status": "Skipped", "reason": "No sources.jar found"}
            
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                jar_files = zf.namelist()
                jar_java_files = [f for f in jar_files if not f.endswith("/") and (f.endswith(".java") or f.endswith(".py"))]
                
                owner, repo = self._extract_github_owner_repo(scm.get("url", ""))
                tag = scm.get("tag", "")
                
                if not owner or not repo or not tag:
                    return {
                        "status": "Inferred",
                        "reason": "Could not extract GitHub owner/repo or tag from SCM info",
                        "total_files": len(jar_java_files),
                        "verified_files": 0,
                        "mismatches": 0,
                    }
                
                git_tree = self._fetch_git_tree(owner, repo, tag)
                if git_tree is None:
                    return {
                        "status": "Inferred",
                        "reason": "Could not fetch git tree from GitHub",
                        "total_files": len(jar_java_files),
                        "verified_files": 0,
                        "mismatches": 0,
                    }
                
                git_java_shas = {
                    self._strip_src_prefix(p): sha
                    for p, sha in git_tree.items()
                    if p.endswith(".java") or p.endswith(".py")
                }
                
                verified_files = 0
                mismatches = 0
                first_verified_sha = None
                
                for path in jar_java_files:
                    stripped_path = self._strip_src_prefix(path)
                    if stripped_path in git_java_shas:
                        jar_bytes = zf.read(path)
                        jar_sha = self._git_blob_sha1(jar_bytes)
                        git_sha = git_java_shas[stripped_path]
                        
                        if jar_sha == git_sha or self._git_blob_sha1(jar_bytes.replace(b"\r\n", b"\n")) == git_sha:
                            verified_files += 1
                            if not first_verified_sha:
                                first_verified_sha = jar_sha
                        else:
                            mismatches += 1
                
                status = "Inferred"
                if verified_files > 0:
                    status = "Verified" if mismatches == 0 else "Partial"
                
                verified_swh = False
                if first_verified_sha:
                    swhid = f"swh:1:cnt:{first_verified_sha}"
                    if self.swh.check_swhid(swhid):
                        verified_swh = True
                
                res = {
                    "status": status,
                    "verified_files": verified_files,
                    "total_files": len(jar_java_files),
                    "mismatches": mismatches,
                }
                if verified_swh and first_verified_sha:
                    res["first_verified_swhid"] = f"swh:1:cnt:{first_verified_sha}"
                
                return res
        except Exception as e:
            return {"status": "Failed", "reason": f"Error inspecting sources.jar: {e}"}
