# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import os
import sys
import fnmatch
import logging
from typing import Dict, List, Any, Optional
from swhid_tool.scanner import ScanResults

# Use standard library tomllib (Python 3.11+) with tomli fallback
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        raise ImportError(
            "The 'tomli' package is required for Python < 3.11. "
            "Install it with: pip install tomli"
        )

logger = logging.getLogger(__name__)

class PolicyEngine:
    """
    Evaluates resolved package findings and local installation scans against a policy.
    Supports loading from a TOML configuration file.
    """
    def __init__(self, policy_path: Optional[str] = None):
        self.policy_path = policy_path
        self.config = self._load_default_config()
        if policy_path and os.path.exists(policy_path):
            self.load_policy(policy_path)

    def _load_default_config(self) -> Dict[str, Any]:
        return {
            "policy": {
                "fail_on_mismatch": True,
                "minimum_confidence_level": "Inferred",
                "fail_on_vulnerability": False,
                "max_severity": "MEDIUM",
                "allowlist": [],
                "ignored_vulnerabilities": []
            }
        }

    def load_policy(self, path: str) -> None:
        try:
            with open(path, "rb") as f:
                parsed = tomllib.load(f)
            if "policy" in parsed:
                self.config["policy"].update(parsed["policy"])
            logger.info(f"Loaded policy from {path}: {self.config['policy']}")
        except Exception as e:
            logger.error(f"Failed to load policy file {path}: {e}")

    def is_allowlisted(self, purl: str) -> bool:
        allowlist = self.config["policy"].get("allowlist", [])
        for pattern in allowlist:
            if fnmatch.fnmatch(purl, pattern):
                return True
        return False

    def evaluate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates the findings against the policy.
        Returns a list of policy violations.
        Each violation is a dict: { "purl": str, "type": str, "message": str }
        """
        violations = []
        policy = self.config["policy"]
        min_confidence = policy.get("minimum_confidence_level", "Inferred")
        fail_on_vuln = policy.get("fail_on_vulnerability", False)
        max_severity = policy.get("max_severity", "MEDIUM")
        ignored_vulns = policy.get("ignored_vulnerabilities", [])

        # Map confidence names to numeric scores for comparison
        confidence_scores = {
            "Verified": 3,
            "Inferred": 2,
            "Partial": 1,
            "Error": 0,
            "Failed": 0,
            "Unknown": 0
        }
        min_score = confidence_scores.get(min_confidence, 2)

        for f in findings:
            purl = f.get("purl", "")
            if self.is_allowlisted(purl):
                continue

            status = f.get("status", "Unknown")
            status_score = confidence_scores.get(status, 0)
            if status_score < min_score:
                violations.append({
                    "purl": purl,
                    "type": "confidence_violation",
                    "message": f"Package status '{status}' is below the required '{min_confidence}'."
                })

            vulns = f.get("vulnerabilities", [])
            for v in vulns:
                v_id = v.get("id", "Unknown")
                if v_id in ignored_vulns:
                    continue

                severity = self.parse_severity(v)
                severity_score = self.get_severity_score(severity)
                max_severity_score = self.get_severity_score(max_severity)

                if fail_on_vuln:
                    violations.append({
                        "purl": purl,
                        "type": "vulnerability_violation",
                        "message": f"Package has known vulnerability {v_id} [{severity}]: {v.get('summary', 'No summary')}"
                    })
                elif max_severity_score > 0 and severity_score >= max_severity_score:
                    violations.append({
                        "purl": purl,
                        "type": "vulnerability_violation",
                        "message": f"Package has known {severity} severity vulnerability {v_id} (threshold: {max_severity}): {v.get('summary', 'No summary')}"
                    })

        return violations

    def parse_severity(self, v: Dict[str, Any]) -> str:
        """Parses the qualitative severity level from an OSV vulnerability entry."""
        db_specific = v.get("database_specific") or {}
        cvss_info = db_specific.get("cvss") or {}
        
        severity = db_specific.get("severity") or cvss_info.get("severity")
        if severity:
            return severity.upper()
            
        severity_list = v.get("severity") or []
        for sev in severity_list:
            score_str = sev.get("score", "")
            try:
                score = float(score_str)
                if score >= 9.0:
                    return "CRITICAL"
                elif score >= 7.0:
                    return "HIGH"
                elif score >= 4.0:
                    return "MEDIUM"
                elif score > 0:
                    return "LOW"
            except ValueError:
                pass
                
        return "UNKNOWN"

    def get_severity_score(self, severity: str) -> int:
        """Maps a qualitative severity string to a numeric score for comparison."""
        levels = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "UNKNOWN": 0,
            "NONE": 0
        }
        return levels.get(severity.upper(), 0)

    def evaluate_scan_results(self, scan_results: ScanResults, package_name: str) -> List[Dict[str, Any]]:
        """
        Evaluates local installation scan results against the policy.
        """
        violations = []
        policy = self.config["policy"]
        fail_on_mismatch = policy.get("fail_on_mismatch", True)

        if fail_on_mismatch:
            mismatches = scan_results.get("mismatches", [])
            for m in mismatches:
                violations.append({
                    "purl": f"local:{package_name}",
                    "type": "mismatch_violation",
                    "message": f"Local file/directory '{m['path']}' has a cryptographic mismatch. Expected {m['expected']}, but got {m['actual']}."
                })
        return violations
