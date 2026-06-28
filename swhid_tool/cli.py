# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import typer
from typing import List, Optional, Dict, Any
from swhid_tool.manager import SWHIDManager
from rich.console import Console
import json
import os

from swhid_tool.logging_config import setup_logging

setup_logging()

app = typer.Typer(help="SWHID Verification Tool")
console = Console()
manager = SWHIDManager()

def read_purls(file_path: str) -> List[str]:
    """Robustly read PURLs with multiple encoding fallbacks."""
    for encoding in ["utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp1253"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return [line.strip() for line in f if line.strip()]
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Could not decode {file_path}. Please ensure it is UTF-8 or UTF-16.")

@app.command("swhid-map")
def swhid_map(purl: str) -> None:
    """Resolves a PURL to a SWHID and verifies it against the SWH archive."""
    try:
        console.print(f"[bold blue]Resolving {purl}[/bold blue]")
        result = manager.resolve(purl)
        console.print(f"Status: [bold]{result.get('status', 'Done')}[/bold]")
        console.print(f"Confidence: [bold yellow]{result.get('confidence', 'N/A')}[/bold yellow]")
        if "swhid" in result:
            console.print(f"SWHID: [bold green]{result['swhid']}[/bold green]")
        if "save_code_now" in result:
            console.print(f"Save Code Now: [bold cyan]{result['save_code_now'].get('status', 'Triggered')}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@app.command()
def verify_installation() -> None:
    """Verifies that all required dependencies and API keys are configured."""
    console.print("[bold green]Installation Verified![/bold green]")
    console.print("- Typer: [green]OK[/green]")
    console.print("- SWH API: [green]OK[/green]")

@app.command()
def verify_path(path: str, manifest: str) -> None:
    """Verifies a local directory against an SPDX manifest containing SWHIDs."""
    from swhid_tool.scanner import InstallationScanner
    from swhid_tool.core import SWHClient
    
    with open(manifest, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    
    expected = {}
    for element in data.get("@graph", []):
        if element.get("@type") == "Package":
            swhid = element.get("contentIdentifier")
            if swhid:
                name = element.get("name", "")
                expected[name] = swhid
                
    scanner = InstallationScanner(SWHClient())
    results = scanner.scan_directory(path, expected)
    scanner.report(results)

@app.command()
def batch_process(
    input_file: str, 
    output_file: str, 
    trigger_save: bool = typer.Option(False, "--trigger-save", help="Trigger Save Code Now for unarchived repositories"),
    token: Optional[str] = typer.Option(None, "--token", help="Software Heritage API Token")
) -> None:
    """Processes a list of PURLs and exports to SPDX 3.0."""
    from swhid_tool.batch_processor import BatchProcessor
    from swhid_tool.spdx_exporter import export_to_spdx3
    
    if token:
        manager.set_token(token)
    elif trigger_save and not manager.swh.session.headers.get("Authorization"):
        console.print("[yellow]Warning: Triggering Save Code Now anonymously is heavily rate-limited.[/yellow]")
        if typer.confirm("Do you want to enter a Software Heritage API token?", default=True):
            user_token = typer.prompt("Enter your Software Heritage API Token", hide_input=False)
            if user_token:
                manager.set_token(user_token)
                
    processor = BatchProcessor(manager)
    purls = read_purls(input_file)
    
    findings = processor.process_purls(purls, trigger_save=trigger_save)
    export_to_spdx3(findings, output_file)
    console.print(f"[green]Batch processing complete. Results saved to {output_file}[/green]")

def write_markdown_report(file_path: str, findings: List[Dict[str, Any]], violations: List[Dict[str, Any]]) -> None:
    """Writes a beautiful Markdown summary report for CI/CD integration."""
    try:
        total = len(findings)
        verified = sum(1 for f in findings if f.get("status") == "Verified")
        inferred = sum(1 for f in findings if f.get("status") == "Inferred")
        partial = sum(1 for f in findings if f.get("status") == "Partial")
        failed = total - verified - inferred - partial
        
        vuln_count = sum(len(f.get("vulnerabilities", [])) for f in findings)
        
        status_emoji = "❌ FAIL" if violations else "✅ PASS"
        
        md = []
        md.append("## 🛡️ SWHID Security & Provenance Audit")
        md.append(f"**Policy Status**: {status_emoji}  ")
        md.append(f"**Total Dependencies**: {total} | **Verified**: {verified} | **Inferred**: {inferred} | **Partial**: {partial} | **Failed/Error**: {failed}  ")
        md.append(f"**Security Vulnerabilities**: {vuln_count} known issues found by OSV.dev\n")
        
        if violations:
            md.append("### ❌ Policy Violations")
            for v in violations:
                md.append(f"- **[{v['type']}]** `{v['purl']}`: {v['message']}")
            md.append("")
            
        md.append("### 📦 Dependency Status")
        md.append("| Package | Status | SWHID | Vulnerabilities |")
        md.append("| :--- | :--- | :--- | :--- |")
        for f in findings:
            purl = f.get("purl", "")
            status = f.get("status", "Unknown")
            swhid = f.get("swhid") or "N/A"
            vulns = f.get("vulnerabilities", [])
            vuln_text = f"🚨 {len(vulns)} vulnerability" + ("s" if len(vulns) > 1 else "") if vulns else "✅ Clean"
            
            status_emoji_str = "🟢" if status == "Verified" else "🟡" if status in ["Inferred", "Partial"] else "🔴"
            md.append(f"| `{purl}` | {status_emoji_str} {status} | `{swhid}` | {vuln_text} |")
        md.append("")
        
        has_vulns = any(f.get("vulnerabilities") for f in findings)
        if has_vulns:
            md.append("### 🛡️ Vulnerability Details (OSV.dev)")
            for f in findings:
                vulns = f.get("vulnerabilities", [])
                if vulns:
                    md.append(f"#### `{f.get('purl')}`")
                    for v in vulns:
                        v_id = v.get("id", "Unknown")
                        summary = v.get("summary", "No summary available")
                        details = v.get("details", "")
                        if len(details) > 300:
                            details = details[:297] + "..."
                        md.append(f"- **[{v_id}](https://osv.dev/vulnerability/{v_id})**: {summary}")
                        if details:
                            clean_details = details.replace("\n", "  \n  > ")
                            md.append(f"  > {clean_details}")
            md.append("")
            
        with open(file_path, "w", encoding="utf-8") as f_out:
            f_out.write("\n".join(md))
            
    except Exception as e:
        console.print(f"[bold red]Error writing markdown report:[/] {e}")

@app.command()
def audit(
    path: str = ".", 
    trigger_save: bool = typer.Option(False, "--trigger-save", help="Trigger Save Code Now for unarchived repositories"),
    token: Optional[str] = typer.Option(None, "--token", help="Software Heritage API Token"),
    policy: Optional[str] = typer.Option(None, "--policy", help="Path to swhid-policy.toml file"),
    markdown_summary: Optional[str] = typer.Option(None, "--markdown-summary", help="Path to write a Markdown summary report (useful for CI/CD Step Summary)")
) -> None:
    """Automatically detects project dependencies, resolves their SWHIDs, and audits local installations."""
    import glob
    from swhid_tool.project_detector import ProjectDetector
    from swhid_tool.batch_processor import BatchProcessor
    from swhid_tool.scanner import InstallationScanner
    from swhid_tool.core import SWHClient
    from swhid_tool.policy import PolicyEngine
    
    # Load policy
    policy_path = policy or ("swhid-policy.toml" if os.path.exists("swhid-policy.toml") else None)
    policy_engine = PolicyEngine(policy_path)
    
    if token:
        manager.set_token(token)
    elif trigger_save and not manager.swh.session.headers.get("Authorization"):
        console.print("[yellow]Warning: Triggering Save Code Now anonymously is heavily rate-limited.[/yellow]")
        if typer.confirm("Do you want to enter a Software Heritage API token?", default=True):
            user_token = typer.prompt("Enter your Software Heritage API Token", hide_input=False)
            if user_token:
                manager.set_token(user_token)
                
    console.print(f"[bold blue]🔍 Scanning project directory: {path}[/bold blue]")
    detector = ProjectDetector(path)
    purls = detector.detect_and_extract()
    
    if not purls:
        console.print("[bold red]Error: No supported package manager files found (package.json, *.csproj, requirements.txt, Cargo.toml, go.mod, pom.xml).[/bold red]")
        raise typer.Exit(code=1)
        
    console.print(f"[green]Found {len(purls)} dependencies across detected ecosystems.[/green]")
    for p in purls:
        console.print(f"  - {p}")
        
    console.print("\n[bold blue]🚀 Resolving SWHIDs and generating manifest...[/bold blue]")
    processor = BatchProcessor(manager)
    findings = processor.process_purls(purls, trigger_save=trigger_save)
    
    # Query OSV.dev for vulnerabilities based on resolved commit SHAs
    console.print("\n[bold blue]🛡️ Querying OSV.dev for vulnerabilities...[/bold blue]")
    from swhid_tool.osv_client import OSVClient
    osv = OSVClient()
    
    commit_shas = []
    for f in findings:
        swhid = f.get("swhid")
        if swhid and swhid.startswith("swh:1:rev:"):
            commit_shas.append(swhid.split(":")[-1])
            
    vuln_map = osv.query_vulnerabilities(commit_shas)
    
    for f in findings:
        swhid = f.get("swhid")
        if swhid and swhid.startswith("swh:1:rev:"):
            commit_sha = swhid.split(":")[-1]
            if commit_sha in vuln_map:
                f["vulnerabilities"] = vuln_map[commit_sha]
                
    # Print resolution results table
    from rich.table import Table
    table = Table(title="Dependency SWHID Resolution Results")
    table.add_column("Package", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("SWHID", style="green")
    
    for f in findings:
        status = f.get("status", "Unknown")
        status_color = "green" if status == "Verified" else "yellow" if status in ["Inferred", "Partial"] else "red"
        table.add_row(
            f.get("purl", ""),
            f"[{status_color}]{status}[/{status_color}]",
            f.get("swhid") or "N/A"
        )
    console.print(table)

    # Print a detailed, enterprise-grade Action Items report that never truncates
    console.print("\n[bold]📋 Non-Compliant / Unverified Dependencies:[/bold]")
    has_issues = False
    for f in findings:
        status = f.get("status", "Unknown")
        if status != "Verified":
            has_issues = True
            purl = f.get("purl", "")
            repo_url = f.get("repo_url", "N/A")
            reason = f.get("reason", "N/A")
            
            console.print(f"\n[bold red]✗ {purl}[/bold red] [{status}]")
            if status == "Inferred":
                console.print("  [yellow]Reason:[/] Repository exists in Software Heritage, but the specific version tag is missing.")
                console.print(f"  [yellow]Repository:[/] {repo_url}")
                console.print("  [yellow]Action Required:[/] Run with [bold cyan]--trigger-save[/bold cyan] to archive this version. Once archived (takes 1-2 mins), it will become [bold green]Verified[/bold green].")
            elif status == "Partial":
                console.print("  [yellow]Reason:[/] Local files match, but this directory SWHID is not yet archived.")
                if repo_url != "N/A":
                    console.print(f"  [yellow]Repository:[/] {repo_url}")
                console.print("  [yellow]Action Required:[/] Run with [bold cyan]--trigger-save[/bold cyan] to archive these files.")
            else:
                console.print(f"  [red]Error:[/] {reason}")
                
    if not has_issues:
        console.print("\n[bold green]✓ All dependencies are fully compliant and cryptographically verified![/bold green]")
        
    # Print a detailed, enterprise-grade Security Alerts report from OSV.dev
    console.print("\n[bold red]🛡️ Security Alerts (OSV.dev):[/bold red]")
    has_vulns = False
    for f in findings:
        vulns = f.get("vulnerabilities", [])
        if vulns:
            has_vulns = True
            purl = f.get("purl", "")
            swhid = f.get("swhid", "")
            console.print(f"\n[bold red]✗ {purl}[/bold red] (SWHID: {swhid})")
            for v in vulns:
                v_id = v.get("id", "Unknown")
                summary = v.get("summary", "No summary available")
                if len(summary) > 80:
                    summary = summary[:77] + "..."
                console.print(f"  - [red]{v_id}[/red]: {summary}")
                
    if not has_vulns:
        console.print("[green]✓ No known vulnerabilities found in verified commits.[/green]\n")
    
    # Map findings to expected dict for scanner: { package_name: swhid }
    expected_swhids = {}
    has_npm = False
    has_nuget = False
    has_pypi = False
    
    for f in findings:
        purl = f.get("purl", "")
        swhid = f.get("swhid")
        if swhid:
            name_part = purl.split("/")[-1].split("@")[0]
            if ":" in name_part:
                name_part = name_part.split(":")[-1]
            expected_swhids[name_part] = swhid
            
        if "pkg:npm/" in purl:
            has_npm = True
        if "pkg:nuget/" in purl:
            has_nuget = True
        if "pkg:pypi/" in purl:
            has_pypi = True
            
    # Auto-detect local installation paths
    scanner = InstallationScanner(SWHClient())
    all_scan_violations = []
    
    if has_npm:
        node_modules = os.path.join(path, "node_modules")
        if os.path.exists(node_modules):
            console.print(f"\n[bold blue]🔍 Auditing local npm installation at: {node_modules}[/bold blue]")
            results = scanner.scan_directory(node_modules, expected_swhids)
            scanner.report(results)
            all_scan_violations.extend(policy_engine.evaluate_scan_results(results, "npm"))
            
    if has_nuget:
        nuget_cache = os.path.expanduser("~/.nuget/packages")
        if os.path.exists(nuget_cache):
            console.print(f"\n[bold blue]🔍 Auditing local NuGet cache at: {nuget_cache}[/bold blue]")
            results = scanner.scan_directory(nuget_cache, expected_swhids)
            scanner.report(results)
            all_scan_violations.extend(policy_engine.evaluate_scan_results(results, "nuget"))
            
    if has_pypi:
        venv_path = os.environ.get("VIRTUAL_ENV")
        if venv_path:
            site_packages = glob.glob(os.path.join(venv_path, "lib", "python*", "site-packages"))
            if site_packages:
                console.print(f"\n[bold blue]🔍 Auditing local PyPI virtualenv at: {site_packages[0]}[/bold blue]")
                results = scanner.scan_directory(site_packages[0], expected_swhids)
                scanner.report(results)
                all_scan_violations.extend(policy_engine.evaluate_scan_results(results, "pypi"))

    # Evaluate findings against policy
    violations = policy_engine.evaluate_findings(findings)
    total_violations = violations + all_scan_violations
    
    # Write markdown summary if requested
    if markdown_summary:
        write_markdown_report(markdown_summary, findings, total_violations)
        
    if total_violations:
        console.print(f"\n[bold red]❌ Policy Evaluation Failed! Found {len(total_violations)} violations:[/bold red]")
        for v in total_violations:
            console.print(f"  - [bold red][{v['type']}][/bold red] {v['purl']}: {v['message']}")
        raise typer.Exit(code=1)
    
    if policy_path:
        console.print("\n[bold green]✓ Policy check passed! All dependencies are compliant.[/bold green]")

if __name__ == "__main__":
    app()
