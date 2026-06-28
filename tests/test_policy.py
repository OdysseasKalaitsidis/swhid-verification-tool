# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

from swhid_tool.policy import PolicyEngine

def test_default_policy():
    engine = PolicyEngine()
    assert engine.config["policy"]["fail_on_mismatch"] is True
    assert engine.config["policy"]["minimum_confidence_level"] == "Inferred"
    assert engine.config["policy"]["fail_on_vulnerability"] is False

def test_load_policy_from_file(tmp_path):
    policy_file = tmp_path / "swhid-policy.toml"
    policy_file.write_text("""
[policy]
fail_on_mismatch = false
minimum_confidence_level = "Verified"
fail_on_vulnerability = true
allowlist = [
  "pkg:npm/ignored-package@*",
  "pkg:pypi/another-one@1.0.0"
]
ignored_vulnerabilities = [
  "CVE-2026-1234"
]
""")
    engine = PolicyEngine(str(policy_file))
    assert engine.config["policy"]["fail_on_mismatch"] is False
    assert engine.config["policy"]["minimum_confidence_level"] == "Verified"
    assert engine.config["policy"]["fail_on_vulnerability"] is True
    assert engine.config["policy"]["allowlist"] == ["pkg:npm/ignored-package@*", "pkg:pypi/another-one@1.0.0"]
    assert engine.config["policy"]["ignored_vulnerabilities"] == ["CVE-2026-1234"]

def test_evaluate_confidence_violations():
    engine = PolicyEngine()
    engine.config["policy"]["minimum_confidence_level"] = "Verified"
    
    findings = [
        {"purl": "pkg:pypi/six@1.17.0", "status": "Verified"},
        {"purl": "pkg:pypi/requests@2.31.0", "status": "Inferred"},
        {"purl": "pkg:pypi/bad-one@1.0.0", "status": "Partial"}
    ]
    
    violations = engine.evaluate_findings(findings)
    assert len(violations) == 2
    assert violations[0]["purl"] == "pkg:pypi/requests@2.31.0"
    assert violations[0]["type"] == "confidence_violation"
    assert violations[1]["purl"] == "pkg:pypi/bad-one@1.0.0"

def test_evaluate_vulnerability_violations():
    engine = PolicyEngine()
    engine.config["policy"]["fail_on_vulnerability"] = True
    engine.config["policy"]["ignored_vulnerabilities"] = ["CVE-ignored"]
    
    findings = [
        {
            "purl": "pkg:pypi/six@1.17.0",
            "status": "Verified",
            "vulnerabilities": [
                {"id": "CVE-ignored", "summary": "Ignored vuln"},
                {"id": "CVE-bad", "summary": "Active vuln"}
            ]
        }
    ]
    
    violations = engine.evaluate_findings(findings)
    assert len(violations) == 1
    assert violations[0]["purl"] == "pkg:pypi/six@1.17.0"
    assert violations[0]["type"] == "vulnerability_violation"
    assert "CVE-bad" in violations[0]["message"]

def test_allowlist_matching():
    engine = PolicyEngine()
    engine.config["policy"]["minimum_confidence_level"] = "Verified"
    engine.config["policy"]["allowlist"] = [
        "pkg:pypi/ignored-*",
        "pkg:npm/scoped/*"
    ]
    
    findings = [
        {"purl": "pkg:pypi/ignored-pkg@1.0", "status": "Partial"},
        {"purl": "pkg:npm/scoped/package@2.0", "status": "Partial"},
        {"purl": "pkg:pypi/normal-pkg@1.0", "status": "Partial"}
    ]
    
    violations = engine.evaluate_findings(findings)
    assert len(violations) == 1
    assert violations[0]["purl"] == "pkg:pypi/normal-pkg@1.0"

def test_evaluate_scan_mismatches():
    engine = PolicyEngine()
    engine.config["policy"]["fail_on_mismatch"] = True
    
    scan_results = {
        "total_files": 3,
        "verified_files": 2,
        "mismatches": [
            {"path": "lib/bad_file.py", "expected": "swh:1:cnt:123", "actual": "swh:1:cnt:456"}
        ],
        "missing": []
    }
    
    violations = engine.evaluate_scan_results(scan_results, "mypackage")
    assert len(violations) == 1
    assert violations[0]["purl"] == "local:mypackage"
    assert violations[0]["type"] == "mismatch_violation"
    assert "lib/bad_file.py" in violations[0]["message"]
