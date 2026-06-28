# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from swhid_tool.core import SWHClient
from swhid_tool.strategies.nuget_strategy import NugetStrategy

@patch("requests.get")
def test_nuget_strategy_metadata_verified(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = NugetStrategy(client)

    # 1. Mock NuGet registration API response
    mock_registry_resp = MagicMock()
    mock_registry_resp.status_code = 200
    mock_registry_resp.json.return_value = {
        "catalogEntry": {
            "repository": {
                "type": "git",
                "url": "https://github.com/JamesNK/Newtonsoft.Json.git"
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
            "refs/tags/13.0.3": {
                "target_type": "revision",
                "target": "dummymatchingrevision123"
            }
        }
    }

    mock_get.return_value = mock_registry_resp
    client.session.get.side_effect = [mock_swh_visit_resp, mock_swh_snap_resp]

    result = strategy.resolve("Newtonsoft.Json", "13.0.3", {})

    assert result["status"] == "Verified"
    assert result["swhid"] == "swh:1:rev:dummymatchingrevision123"
    assert result["confidence"] == "Verified"
    assert result["repo_url"] == "https://github.com/JamesNK/Newtonsoft.Json"
    assert result["tag_matched"] == "13.0.3"


@patch("requests.get")
def test_nuget_strategy_project_url_fallback(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = NugetStrategy(client)

    # Mock NuGet registration API response with projectUrl fallback
    mock_registry_resp = MagicMock()
    mock_registry_resp.status_code = 200
    mock_registry_resp.json.return_value = {
        "catalogEntry": {
            "projectUrl": "https://github.com/JamesNK/Newtonsoft.Json"
        }
    }

    # Mock SWH visit/latest response (not archived)
    mock_swh_visit_resp = MagicMock()
    mock_swh_visit_resp.status_code = 404

    mock_get.return_value = mock_registry_resp
    client.session.get.return_value = mock_swh_visit_resp

    result = strategy.resolve("Newtonsoft.Json", "13.0.3", {})

    assert result["status"] == "Partial"
    assert result["confidence"] == "Partial"
    assert result["repo_url"] == "https://github.com/JamesNK/Newtonsoft.Json"
    client.trigger_save_code_now.assert_called_with("https://github.com/JamesNK/Newtonsoft.Json")
