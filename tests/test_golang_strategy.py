# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from swhid_tool.core import SWHClient
from swhid_tool.strategies.golang_strategy import GoLangStrategy

def test_golang_strategy_case_encode():
    client = MagicMock(spec=SWHClient)
    strategy = GoLangStrategy(client)
    
    assert strategy._case_encode("GitHub.com/Sirupsen/logrus") == "github.com/!sirupsen/logrus"
    assert strategy._case_encode("golang.org/x/Text") == "golang.org/x/!text"


def test_golang_strategy_resolve_github_shortcut():
    client = MagicMock(spec=SWHClient)
    strategy = GoLangStrategy(client)
    
    repo_url = strategy._resolve_go_import("github.com/gin-gonic/gin")
    assert repo_url == "https://github.com/gin-gonic/gin"


@patch("requests.get")
def test_golang_strategy_resolve_go_import_vanity(mock_get):
    client = MagicMock(spec=SWHClient)
    strategy = GoLangStrategy(client)

    # Mock HTML response for vanity import
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
        <head>
            <meta name="go-import" content="golang.org/x/text git https://go.googlesource.com/text">
        </head>
    </html>
    """
    mock_get.return_value = mock_resp

    repo_url = strategy._resolve_go_import("golang.org/x/text")
    assert repo_url == "https://go.googlesource.com/text"
    mock_get.assert_called_with("https://golang.org/x/text?go-get=1", timeout=15)


@patch("requests.get")
def test_golang_strategy_metadata_verified(mock_get):
    client = MagicMock(spec=SWHClient)
    client.session = MagicMock()
    strategy = GoLangStrategy(client)

    # Mock SWH visit/latest response
    mock_swh_visit_resp = MagicMock()
    mock_swh_visit_resp.status_code = 200
    mock_swh_visit_resp.json.return_value = {
        "snapshot": "dummysnapshotid123"
    }

    # Mock SWH snapshot response with matching tag
    mock_swh_snap_resp = MagicMock()
    mock_swh_snap_resp.status_code = 200
    mock_swh_snap_resp.json.return_value = {
        "branches": {
            "refs/tags/v1.9.0": {
                "target_type": "revision",
                "target": "dummymatchingrevision123"
            }
        }
    }

    client.session.get.side_effect = [mock_swh_visit_resp, mock_swh_snap_resp]

    # Resolve github.com/gin-gonic/gin@v1.9.0
    result = strategy.resolve("github.com/gin-gonic/gin", "v1.9.0", {})

    assert result["status"] == "Verified"
    assert result["swhid"] == "swh:1:rev:dummymatchingrevision123"
    assert result["confidence"] == "Verified"
    assert result["repo_url"] == "https://github.com/gin-gonic/gin"
    assert result["tag_matched"] == "v1.9.0"
