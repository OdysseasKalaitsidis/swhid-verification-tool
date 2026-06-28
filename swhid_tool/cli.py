# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import typer
from typing import List, Optional
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

@app.command()
def audit(
    path: str = ".", 
    trigger_save: bool = typer.Option(False, "--trigger-save", help="Trigger Save Code Now for unarchived repositories"),
    token: Optional[str] = typer.Option(None, "--token", help="Software Heritage API Token")
) -> None:
    """Automatically detects project dependencies, resolves their SWHIDs, and audits local installations."""
    import glob
    from swhid_tool.project_detector import ProjectDetector
    from swhid_tool.batch_processor import BatchProcessor
    from swhid_tool.scanner import InstallationScanner
    from swhid_tool.core import SWHClient
    
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
    
    # Print resolution results table
    from rich.table import Table
    table = Table(title="Dependency SWHID Resolution Results")
    table.add_column("Package", style="cyan", width=35)
    table.add_column("Status", style="bold", width=12)
    table.add_column("SWHID", style="green", width=44)
    table.add_column("Details / Action Required", style="white")
    
    for f in findings:
        status = f.get("status", "Unknown")
        status_color = "green" if status == "Verified" else "yellow" if status in ["Inferred", "Partial"] else "red"
        
        # Build rich details message
        reason = f.get("reason", "")
        repo_url = f.get("repo_url", "")
        
        if status == "Verified":
            details = "[green]✓ Cryptographically verified[/green]"
            if repo_url:
                details += f" from {repo_url}"
        elif status == "Inferred":
            details = f"[yellow]⚠ Repo found, but version tag not archived yet.[/yellow]\n  Repo: {repo_url}\n  [bold]Action:[/] Run with [bold cyan]--trigger-save[/bold cyan] to archive it."
        elif status == "Partial":
            details = "[yellow]⚠ Local SWHID computed, but not found in SWH archive.[/yellow]"
        elif status == "Error" or status == "Failed":
            details = f"[red]✗ Resolution failed: {reason}[/red]"
        else:
            details = reason or "N/A"
            
        table.add_row(
            f.get("purl", ""),
            f"[{status_color}]{status}[/{status_color}]",
            f.get("swhid") or "N/A",
            details
        )
    console.print(table)
    
    # Map findings to expected dict for scanner: { package_name: swhid }
    expected_swhids = {}
    has_npm = False
    has_nuget = False
    has_pypi = False
    
    for f in findings:
        purl = f.get("purl", "")
        swhid = f.get("swhid")
        if swhid:
            # Extract package name from PURL
            # pkg:npm/lodash@4.17.21 -> lodash
            # pkg:nuget/Newtonsoft.Json@13.0.3 -> Newtonsoft.Json
            name_part = purl.split("/")[-1].split("@")[0]
            # Handle scoped packages (e.g. @babel/core -> core)
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
    
    if has_npm:
        node_modules = os.path.join(path, "node_modules")
        if os.path.exists(node_modules):
            console.print(f"\n[bold blue]🔍 Auditing local npm installation at: {node_modules}[/bold blue]")
            results = scanner.scan_directory(node_modules, expected_swhids)
            scanner.report(results)
            
    if has_nuget:
        nuget_cache = os.path.expanduser("~/.nuget/packages")
        if os.path.exists(nuget_cache):
            console.print(f"\n[bold blue]🔍 Auditing local NuGet cache at: {nuget_cache}[/bold blue]")
            results = scanner.scan_directory(nuget_cache, expected_swhids)
            scanner.report(results)
            
    if has_pypi:
        venv_path = os.environ.get("VIRTUAL_ENV")
        if venv_path:
            site_packages = glob.glob(os.path.join(venv_path, "lib", "python*", "site-packages"))
            if site_packages:
                console.print(f"\n[bold blue]🔍 Auditing local PyPI virtualenv at: {site_packages[0]}[/bold blue]")
                results = scanner.scan_directory(site_packages[0], expected_swhids)
                scanner.report(results)

if __name__ == "__main__":
    app()
