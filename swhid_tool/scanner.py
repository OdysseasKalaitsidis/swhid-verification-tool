# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
from typing import Dict, List, TypedDict
from swhid_tool.core import compute_content_swhid, SWHClient
from rich.console import Console
from rich.table import Table
from swh.model.from_disk import Directory as SWHDirectory

class ScanResults(TypedDict):
    total_files: int
    verified_files: int
    mismatches: List[Dict[str, str]]
    missing: List[str]

console = Console()

class InstallationScanner:
    def __init__(self, swh_client: SWHClient):
        self.swh = swh_client

    def scan_directory(self, path: str, expected_swhids: Dict[str, str]) -> ScanResults:
        """
        Scans a directory and compares file/directory hashes against expected SWHIDs.
        expected_swhids: { "rel_path": "swh:1:..." }
        """
        results: ScanResults = {
            "total_files": 0,
            "verified_files": 0,
            "mismatches": [],
            "missing": []
        }
        
        for rel_path, expected_swhid in expected_swhids.items():
            results["total_files"] += 1
            full_path = os.path.join(path, rel_path)
            
            if not os.path.exists(full_path):
                results["missing"].append(rel_path)
                continue
            
            try:
                if os.path.isdir(full_path):
                    # Resolve revision to directory if needed
                    target_expected = expected_swhid
                    if expected_swhid.startswith("swh:1:rev:"):
                        rev_id = expected_swhid.split(":")[-1]
                        rev_info = self.swh.get_revision(rev_id)
                        if rev_info and "directory" in rev_info:
                            target_expected = f"swh:1:dir:{rev_info['directory']}"
                    
                    # Compute directory SWHID recursively
                    swhid_obj = SWHDirectory.from_disk(path=os.fsencode(full_path), max_content_length=None).swhid()
                    actual_swhid = str(swhid_obj)
                    
                    if actual_swhid == target_expected:
                        results["verified_files"] += 1
                    else:
                        results["mismatches"].append({
                            "path": rel_path,
                            "expected": target_expected,
                            "actual": actual_swhid
                        })
                else:
                    with open(full_path, "rb") as f:
                        content = f.read()
                        actual_swhid = compute_content_swhid(content)
                    
                    if actual_swhid == expected_swhid:
                        results["verified_files"] += 1
                    else:
                        results["mismatches"].append({
                            "path": rel_path,
                            "expected": expected_swhid,
                            "actual": actual_swhid
                        })
            except Exception as e:
                results["mismatches"].append({
                    "path": rel_path,
                    "expected": expected_swhid,
                    "actual": f"Error: {str(e)}"
                })
        
        return results

    def report(self, results: ScanResults) -> None:
        table = Table(title="Installation Verification Results")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Files Checked", str(results["total_files"]))
        table.add_row("Verified Files", str(results["verified_files"]))
        table.add_row("Mismatches", str(len(results["mismatches"])))
        table.add_row("Missing Files", str(len(results["missing"])))
        
        console.print(table)
        
        if results["mismatches"]:
            console.print("\n[red]Mismatches found:[/red]")
            for m in results["mismatches"]:
                console.print(f"- {m['path']}: Expected {m['expected']}, Actual {m['actual']}")
        
        if results["missing"]:
            console.print("\n[yellow]Missing files:[/yellow]")
            for missing_file in results["missing"]:
                console.print(f"- {missing_file}")
