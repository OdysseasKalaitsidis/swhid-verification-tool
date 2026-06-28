# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import json
import pytest
from swhid_tool.project_detector import ProjectDetector

def test_project_detector_extracts_dependencies(tmp_path):
    # 1. Setup mock package.json
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({
        "dependencies": {
            "lodash": "^4.17.21"
        },
        "devDependencies": {
            "typescript": "~5.0.4"
        }
    }))

    # 2. Setup mock .csproj
    csproj = tmp_path / "test_project.csproj"
    csproj.write_text("""
    <Project Sdk="Microsoft.NET.Sdk">
      <ItemGroup>
        <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
        <PackageReference Include="Microsoft.Extensions.Logging">
          <Version>8.0.0</Version>
        </PackageReference>
      </ItemGroup>
    </Project>
    """)

    # 3. Setup mock requirements.txt
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("""
    six==1.17.0
    requests==2.31.0
    """)

    # 4. Run detector
    detector = ProjectDetector(str(tmp_path))
    purls = detector.detect_and_extract()

    # 5. Verify results
    assert "pkg:npm/lodash@4.17.21" in purls
    assert "pkg:npm/typescript@5.0.4" in purls
    assert "pkg:nuget/Newtonsoft.Json@13.0.3" in purls
    assert "pkg:nuget/Microsoft.Extensions.Logging@8.0.0" in purls
    assert "pkg:pypi/six@1.17.0" in purls
    assert "pkg:pypi/requests@2.31.0" in purls
    assert len(purls) == 6
