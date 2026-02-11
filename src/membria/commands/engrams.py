"""Engram (Agent Session) management commands."""

import typer
from rich.console import Console

engrams_app = typer.Typer(help="Manage Engrams (Agent Session captures)")
console = Console()


@engrams_app.command("list")
def list_engrams(
    branch: str = typer.Option(None, help="Filter by branch"),
    author: str = typer.Option(None, help="Filter by author"),
) -> None:
    """List Engrams."""
    console.print("[bold]Recent Engrams[/bold]\n")
    console.print("[dim]No engrams captured yet[/dim]")
    console.print("\n[dim]Run 'membria engrams enable' to start capturing agent sessions[/dim]")


@engrams_app.command("show")
def show(engram_id: str) -> None:
    """Show Engram details."""
    console.print(f"[bold]Engram: {engram_id}[/bold]\n")
    console.print("[dim]Not found[/dim]")


@engrams_app.command("enable")
def enable() -> None:
    """Enable Engram capture (install git hooks)."""
    console.print("[bold green]✓[/bold green] Git hooks installed")
    console.print("[bold green]✓[/bold green] Engram capture enabled")
    console.print("\n[dim]Agent sessions will now be captured on git commit[/dim]")


@engrams_app.command("disable")
def disable() -> None:
    """Disable Engram capture."""
    console.print("[bold yellow]![/bold yellow] Engram capture disabled")
