# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock
from swhid_tool.core import SWHClient, compute_content_swhid
from swhid_tool.scanner import InstallationScanner

def test_consistent_swhid_computation():
    content = b"import sys\nprint('hello')\n"
    swhid1 = compute_content_swhid(content)
    swhid2 = compute_content_swhid(content)
    assert swhid1 == swhid2
    assert swhid1.startswith("swh:1:cnt:")

def test_scan_directory(tmp_path):
    # Setup temp files
    file1 = tmp_path / "app.py"
    file2 = tmp_path / "utils.py"
    tmp_path / "missing.py" # Will not be created
    
    file1.write_bytes(b"print('app')")
    file2.write_bytes(b"print('utils')")
    
    swhid1 = compute_content_swhid(b"print('app')")
    swhid2 = compute_content_swhid(b"print('utils')")
    swhid_wrong = "swh:1:cnt:0000000000000000000000000000000000000000"
    
    expected_swhids = {
        "app.py": swhid1,       # Should match
        "utils.py": swhid_wrong, # Should mismatch
        "missing.py": swhid2     # Should be missing
    }
    
    client = MagicMock(spec=SWHClient)
    scanner = InstallationScanner(client)
    
    results = scanner.scan_directory(str(tmp_path), expected_swhids)
    
    assert results["total_files"] == 3
    assert results["verified_files"] == 1
    
    assert len(results["mismatches"]) == 1
    assert results["mismatches"][0]["path"] == "utils.py"
    assert results["mismatches"][0]["expected"] == swhid_wrong
    assert results["mismatches"][0]["actual"] == swhid2
    
    assert len(results["missing"]) == 1
    assert results["missing"][0] == "missing.py"
