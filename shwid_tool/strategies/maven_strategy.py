import io
import re
import zipfile
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from shwid_tool.strategies.base import VerificationStrategy
from shwid_tool.core import SWHClient

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
        findings = {"purl": purl}

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
                
            return findings
        except Exception as e:
            return {"status": "Error", "reason": str(e)}

    def _fetch_pom(self, base_url: str) -> str:
        resp = requests.get(base_url + ".pom")
        resp.raise_for_status()
        return resp.text

    def _parse_scm(self, pom_text: str) -> Dict[str, str]:
        root = ET.fromstring(pom_text)
        def find(element, tag):
            node = element.find(f"{{{self.NS}}}{tag}")
            if node is None: node = element.find(tag)
            return node
        
        scm = find(root, "scm")
        if scm is None: return {}
        
        def text(tag):
            node = find(scm, tag)
            return (node.text or "").strip() if node is not None else ""
        
        return {"url": text("url"), "tag": text("tag")}

    def _inspect_sources_jar(self, base_url: str, scm: Dict[str, str]) -> Dict[str, Any]:
        # Similar logic to sources_inspector.py
        # Download, strip META-INF, match .java files
        try:
            resp = requests.get(base_url + "-sources.jar")
            if resp.status_code != 200:
                return {"status": "Skipped", "reason": "No sources.jar found"}
            
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                # Inventory and verify
                # (Simplified for now)
                return {"status": "Inferred", "jar_entries": len(zf.namelist())}
        except:
            return {"status": "Failed", "reason": "Error inspecting sources.jar"}
