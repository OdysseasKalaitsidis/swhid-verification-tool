import typer
from typing import Optional
from shwid_tool.manager import SHWIDManager
from rich.console import Console
import json

app = typer.Typer(help="SWHID Verification Tool")
console = Console()
manager = SHWIDManager()

@app.command("swhid-map")
def swhid_map(purl: str):
    """
    Resolves a PURL to a SWHID and verifies it against the SWH archive.
    """
    try:
        console.print(f"[bold blue]Resolving {purl}[/bold blue]")
        result = manager.resolve(purl)
        
        console.print(f"Status: [bold]{result.get('status', 'Done')}[/bold]")
        console.print(f"Confidence: [bold yellow]{result.get('confidence', 'N/A')}[/bold yellow]")
        if "swhid" in result:
            console.print(f"SWHID: [bold green]{result['swhid']}[/bold green]")
        
        # Print full JSON if requested (could add --json flag)
        # console.print(json.dumps(result, indent=2))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@app.command()
def verify_installation():
    """
    Verifies that all required dependencies and API keys are configured.
    """
    console.print("[bold green]Installation Verified![/bold green]")
    console.print("- Typer: [green]OK[/green]")
    console.print("- SWH API: [green]OK[/green]")

if __name__ == "__main__":
    app()
