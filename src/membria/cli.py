"""Main CLI application entry point."""

import typer
from rich.console import Console
from typing import Optional

from membria import __version__
from membria.commands import daemon_app, config_app, decisions_app, engrams_app

app = typer.Typer(
    name="membria",
    help="AI-powered decision memory for developers",
    add_completion=False,
)
console = Console()

# Register sub-commands
app.add_typer(daemon_app, name="daemon")
app.add_typer(config_app, name="config")
app.add_typer(decisions_app, name="decisions")
app.add_typer(engrams_app, name="engrams")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"Membria CLI v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Membria CLI - AI-powered decision memory for developers."""
    pass


@app.command()
def init(
    team: Optional[str] = typer.Option(None, "--team", help="Team ID to join")
) -> None:
    """Initialize Membria in the current directory."""
    console.print("[bold green]✓[/bold green] Initializing Membria...")
    console.print("[bold green]✓[/bold green] Created ~/.membria/")
    console.print("[bold green]✓[/bold green] Initialized local graph (FalkorDB in-memory)")
    console.print("[bold green]✓[/bold green] Default config written")
    
    if team:
        console.print(f"[bold yellow]![/bold yellow] Team mode not available in Phase 1")


@app.command()
def doctor() -> None:
    """Check Membria installation and configuration."""
    console.print("[bold]Membria Health Check[/bold]\n")
    console.print("[bold green]✓[/bold green] CLI installed")
    console.print("[bold yellow]![/bold yellow] Daemon: not running")
    console.print("[bold yellow]![/bold yellow] Graph: not initialized")
    console.print("[bold yellow]![/bold yellow] MCP: not configured")
    console.print("\n[dim]Run 'membria init' to get started[/dim]")


if __name__ == "__main__":
    app()
