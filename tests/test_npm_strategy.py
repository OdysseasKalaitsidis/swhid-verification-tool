# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from swhid_tool.core import SWHClient
from swhid_tool.strategies.npm_strategy import NpmStrategy

@patch("requests.get")
def test_npm_strategy_metadata_verified(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = NpmStrategy(client)

    # 1. Mock npm registry package metadata
    mock_registry_resp = MagicMock()
    mock_registry_resp.status_code = 200
    mock_registry_resp.json.return_value = {
        "versions": {
            "4.17.21": {
                "repository": {
                    "type": "git",
                    "url": "git+https://github.com/lodash/lodash.git"
                }
            }
        }
    }

    # 2. Mock SWH visit/latest response
    mock_swh_visit_resp = MagicMock()
    mock_swh_visit_resp.status_code = 200
    mock_swh_visit_resp.json.return_value = {
        "snapshot": "dummysnapshotid123"
    }

    # 3. Mock SWH snapshot response with matching tag
    mock_swh_snap_resp = MagicMock()
    mock_swh_snap_resp.status_code = 200
    mock_swh_snap_resp.json.return_value = {
        "branches": {
            "refs/tags/4.17.21": {
                "target_type": "revision",
                "target": "dummymatchingrevision123"
            }
        }
    }

    # Sequence of requests.get and client.session.get
    mock_get.return_value = mock_registry_resp
    client.session.get.side_effect = [mock_swh_visit_resp, mock_swh_snap_resp]

    result = strategy.resolve("lodash", "4.17.21", {})

    assert result["status"] == "Verified"
    assert result["swhid"] == "swh:1:rev:dummymatchingrevision123"
    assert result["confidence"] == "Verified"
    assert result["repo_url"] == "https://github.com/lodash/lodash"
    assert result["tag_matched"] == "4.17.21"


@patch("requests.get")
def test_npm_strategy_scoped_package(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = NpmStrategy(client)

    # Mock package not found to terminate early and inspect URL called
    mock_registry_resp = MagicMock()
    mock_registry_resp.status_code = 404
    mock_get.return_value = mock_registry_resp

    result = strategy.resolve("@babel:core", "7.20.0", {})

    # Verify that the URL requested has the correct escaped scoped package name
    mock_get.assert_called_with("https://registry.npmjs.org/@babel%2Fcore")
    assert result["status"] == "Error"
    assert "Package not found in npm registry" in result["reason"]
