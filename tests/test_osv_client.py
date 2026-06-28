# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch
from swhid_tool.osv_client import OSVClient

@patch("requests.Session.post")
def test_query_vulnerabilities_hybrid(mock_post):
    # Mock OSV.dev response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            # First query: PURL query for pkg:pypi/six@1.17.0
            {
                "vulns": [
                    {"id": "GHSA-1111-2222-3333", "summary": "Vuln A"},
                    {"id": "GHSA-dup-id", "summary": "Duplicate Vuln"}
                ]
            },
            # Second query: Commit query for commit-sha-1
            {
                "vulns": [
                    {"id": "GHSA-dup-id", "summary": "Duplicate Vuln"},
                    {"id": "GHSA-4444-5555-6666", "summary": "Vuln B"}
                ]
            }
        ]
    }
    mock_post.return_value = mock_resp

    client = OSVClient()
    items = [
        {
            "purl": "pkg:pypi/six@1.17.0",
            "swhid": "swh:1:rev:commit-sha-1"
        }
    ]

    vuln_map = client.query_vulnerabilities_hybrid(items)

    # Verify mock_post call
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert len(payload["queries"]) == 2
    assert payload["queries"][0] == {"package": {"purl": "pkg:pypi/six@1.17.0"}}
    assert payload["queries"][1] == {"commit": "commit-sha-1"}

    # Verify combined and deduplicated results
    assert "pkg:pypi/six@1.17.0" in vuln_map
    vulns = vuln_map["pkg:pypi/six@1.17.0"]
    
    # Total unique vulns: GHSA-1111-2222-3333, GHSA-dup-id, GHSA-4444-5555-6666 (3 unique)
    assert len(vulns) == 3
    vuln_ids = {v["id"] for v in vulns}
    assert vuln_ids == {"GHSA-1111-2222-3333", "GHSA-dup-id", "GHSA-4444-5555-6666"}

@patch("requests.Session.post")
def test_query_vulnerabilities_hybrid_empty(mock_post):
    client = OSVClient()
    assert client.query_vulnerabilities_hybrid([]) == {}
    mock_post.assert_not_called()
