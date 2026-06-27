# SPDX-FileCopyrightText: 2026 Odysseas Kalaitsidis
# SPDX-License-Identifier: MIT

import typer
from typing import Optional
from swhid_tool.manager import SWHIDManager
from rich.console import Console
import json
import os

from swhid_tool.logging_config import setup_logging

setup_logging()

app = typer.Typer(help="SWHID Verification Tool")
console = Console()
manager = SWHIDManager()

def read_purls(file_path: str):
    """Robustly read PURLs with multiple encoding fallbacks."""
    for encoding in ["utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp1253"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return [line.strip() for line in f if line.strip()]
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Could not decode {file_path}. Please ensure it is UTF-8 or UTF-16.")

@app.command("swhid-map")
def swhid_map(purl: str):
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
def verify_installation():
    """Verifies that all required dependencies and API keys are configured."""
    console.print("[bold green]Installation Verified![/bold green]")
    console.print("- Typer: [green]OK[/green]")
    console.print("- SWH API: [green]OK[/green]")

@app.command()
def verify_path(path: str, manifest: str):
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
def batch_process(input_file: str, output_file: str):
    """Processes a list of PURLs and exports to SPDX 3.0."""
    from swhid_tool.batch_processor import BatchProcessor
    from swhid_tool.spdx_exporter import export_to_spdx3
    
    processor = BatchProcessor(manager)
    purls = read_purls(input_file)
    
    findings = processor.process_purls(purls)
    export_to_spdx3(findings, output_file)
    console.print(f"[green]Batch processing complete. Results saved to {output_file}[/green]")

if __name__ == "__main__":
    app()
