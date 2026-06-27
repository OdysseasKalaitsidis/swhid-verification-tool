# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from swhid_tool.core import SWHClient
from swhid_tool.strategies.cargo_strategy import CargoStrategy
from swhid_tool.strategies.maven_strategy import MavenStrategy
from swhid_tool.strategies.pypi_strategy import PyPIStrategy

def test_cargo_strategy_normalize(tmp_path):
    # Setup temp cargo files
    source_dir = tmp_path / "cargo_project"
    source_dir.mkdir()
    
    cargo_toml = source_dir / "Cargo.toml"
    cargo_toml_orig = source_dir / "Cargo.toml.orig"
    vcs_info = source_dir / ".cargo_vcs_info.json"
    
    cargo_toml.write_text("modified toml")
    cargo_toml_orig.write_text("original toml")
    vcs_info.write_text("{}")
    
    client = MagicMock(spec=SWHClient)
    strategy = CargoStrategy(client)
    
    actions = strategy._normalize(str(source_dir))
    
    # Assert Cargo.toml is restored to original content
    assert cargo_toml.read_text() == "original toml"
    # Assert temporary files are removed
    assert not vcs_info.exists()
    assert not cargo_toml_orig.exists()
    
    assert "Restored Cargo.toml from Cargo.toml.orig" in actions
    assert "Removed .cargo_vcs_info.json" in actions

def test_maven_strategy_parse_scm():
    pom_xml = """<project xmlns="http://maven.apache.org/POM/4.0.0">
        <scm>
            <url>https://github.com/owner/repo</url>
            <tag>v1.2.3</tag>
        </scm>
    </project>"""
    
    client = MagicMock(spec=SWHClient)
    strategy = MavenStrategy(client)
    
    scm_info = strategy._parse_scm(pom_xml)
    assert scm_info.get("url") == "https://github.com/owner/repo"
    assert scm_info.get("tag") == "v1.2.3"

@patch("requests.get")
def test_pypi_strategy_a_attestation_404(mock_get):
    client = MagicMock(spec=SWHClient)
    strategy = PyPIStrategy(client)
    
    # Mock PyPI JSON API response returning URLs
    mock_resp_json = MagicMock()
    mock_resp_json.status_code = 200
    mock_resp_json.json.return_value = {
        "urls": [{"packagetype": "sdist", "filename": "six-1.17.0.tar.gz"}]
    }
    
    # Mock PyPI Integrity API returning 404
    mock_resp_integrity = MagicMock()
    mock_resp_integrity.status_code = 404
    
    mock_get.side_effect = [mock_resp_json, mock_resp_integrity]
    
    result = strategy._strategy_a_attestation("six", "1.17.0")
    assert result["status"] == "Failed"
    assert result["reason"] == "No PEP 740 attestation"

@patch("requests.get")
def test_pypi_strategy_b_metadata_repo_url(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = PyPIStrategy(client)
    
    # Mock PyPI JSON response with GitHub URL
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "info": {
            "project_urls": {
                "Source": "https://github.com/owner/repo.git"
            }
        }
    }
    mock_get.return_value = mock_resp
    
    # Mock SWH API response returning 404 (triggered Save Code Now)
    mock_swh_resp = MagicMock()
    mock_swh_resp.status_code = 404
    client.session.get.return_value = mock_swh_resp
    
    result = strategy._strategy_b_metadata("six", "1.17.0")
    
    # Verify that it finds repo_url correctly (stripped .git)
    assert result["repo_url"] == "https://github.com/owner/repo"
    assert result["status"] == "Partial"
    client.trigger_save_code_now.assert_called_with("https://github.com/owner/repo")
