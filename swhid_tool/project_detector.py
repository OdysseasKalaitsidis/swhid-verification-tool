# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import re
import json
import glob
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

class ProjectDetector:
    """
    Automatically detects package manager files in a directory and extracts PURLs.
    """
    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)

    def detect_and_extract(self) -> List[str]:
        purls = []
        
        # 1. npm (package.json)
        package_json_path = os.path.join(self.project_path, "package.json")
        if os.path.exists(package_json_path):
            purls.extend(self._extract_npm(package_json_path))

        # 2. .NET (csproj files)
        csproj_files = glob.glob(os.path.join(self.project_path, "*.csproj"))
        for csproj in csproj_files:
            purls.extend(self._extract_nuget(csproj))

        # 3. Python (requirements.txt)
        req_txt_path = os.path.join(self.project_path, "requirements.txt")
        if os.path.exists(req_txt_path):
            purls.extend(self._extract_pypi(req_txt_path))

        # 4. Rust (Cargo.toml)
        cargo_toml_path = os.path.join(self.project_path, "Cargo.toml")
        if os.path.exists(cargo_toml_path):
            purls.extend(self._extract_cargo(cargo_toml_path))

        # 5. Go (go.mod)
        go_mod_path = os.path.join(self.project_path, "go.mod")
        if os.path.exists(go_mod_path):
            purls.extend(self._extract_go(go_mod_path))

        # 6. Maven (pom.xml)
        pom_xml_path = os.path.join(self.project_path, "pom.xml")
        if os.path.exists(pom_xml_path):
            purls.extend(self._extract_maven(pom_xml_path))

        # Deduplicate PURLs
        return list(set(purls))

    def _extract_npm(self, file_path: str) -> List[str]:
        purls = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Combine dependencies and devDependencies
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            all_deps = {**deps, **dev_deps}
            
            for name, ver_spec in all_deps.items():
                # Clean version specifier (e.g. ^1.2.3 or ~1.2.3 -> 1.2.3)
                version = re.sub(r'^[~^>=<*]+', '', ver_spec).strip()
                # Split on space if multiple ranges, take first
                version = version.split()[0] if version else ""
                if version and not version.startswith("http") and not version.startswith("git"):
                    purls.append(f"pkg:npm/{name}@{version}")
        except Exception:
            pass
        return purls

    def _extract_nuget(self, file_path: str) -> List[str]:
        purls = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Look for <PackageReference Include="Name" Version="Version" />
            for item_group in root.findall(".//ItemGroup"):
                for package_ref in item_group.findall("PackageReference"):
                    name = package_ref.get("Include")
                    version = package_ref.get("Version")
                    # Version can also be in a child element <Version>1.0.0</Version>
                    if not version:
                        ver_el = package_ref.find("Version")
                        if ver_el is not None:
                            version = ver_el.text
                            
                    if name and version:
                        purls.append(f"pkg:nuget/{name.strip()}@{version.strip()}")
        except Exception:
            # Fallback to regex if XML parsing fails due to MSBuild quirks
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                matches = re.findall(r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"', content)
                for name, version in matches:
                    purls.append(f"pkg:nuget/{name.strip()}@{version.strip()}")
            except Exception:
                pass
        return purls

    def _extract_pypi(self, file_path: str) -> List[str]:
        purls = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Match name==version
                    match = re.match(r'^([a-zA-Z0-9_\-]+)\s*==\s*([a-zA-Z0-9\.\-_]+)', line)
                    if match:
                        purls.append(f"pkg:pypi/{match.group(1)}@{match.group(2)}")
        except Exception:
            pass
        return purls

    def _extract_cargo(self, file_path: str) -> List[str]:
        purls = []
        try:
            # Simple TOML parser to avoid adding tomli dependency
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Look for dependencies block
            deps_match = re.search(r'\[dependencies\](.*?)(\n\[|$)', content, re.DOTALL)
            if deps_match:
                deps_block = deps_match.group(1)
                # Match name = "version" or name = { version = "version" }
                matches = re.findall(r'^([a-zA-Z0-9_\-]+)\s*=\s*(?:"([^"]+)"|\{\s*version\s*=\s*"([^"]+)"[^*]*\})', deps_block, re.MULTILINE)
                for name, ver1, ver2 in matches:
                    version = ver1 or ver2
                    if version:
                        # Clean version specifiers
                        version = re.sub(r'^[~^>=<*]+', '', version).strip()
                        purls.append(f"pkg:cargo/{name}@{version}")
        except Exception:
            pass
        return purls

    def _extract_go(self, file_path: str) -> List[str]:
        purls = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Match: require github.com/name/repo v1.2.3
                    # or inside require (...) block: github.com/name/repo v1.2.3
                    match = re.search(r'(?:require\s+)?([a-zA-Z0-9\.\-_/]+)\s+(v[0-9\.]+)', line)
                    if match:
                        purls.append(f"pkg:golang/{match.group(1)}@{match.group(2)}")
        except Exception:
            pass
        return purls

    def _extract_maven(self, file_path: str) -> List[str]:
        purls = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            
            # Find dependencies
            deps = root.findall(".//m:dependency", ns)
            if not deps: # Fallback if no namespace
                deps = root.findall(".//dependency")
                
            for dep in deps:
                group_id = dep.find("groupId") if dep.find("groupId") is not None else dep.find("m:groupId", ns)
                artifact_id = dep.find("artifactId") if dep.find("artifactId") is not None else dep.find("m:artifactId", ns)
                version = dep.find("version") if dep.find("version") is not None else dep.find("m:version", ns)
                
                if group_id is not None and artifact_id is not None and version is not None:
                    g = group_id.text.strip() if group_id.text else ""
                    a = artifact_id.text.strip() if artifact_id.text else ""
                    v = version.text.strip() if version.text else ""
                    if g and a and v:
                        purls.append(f"pkg:maven/{g}/{a}@{v}")
        except Exception:
            pass
        return purls
