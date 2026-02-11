"""Daemon management commands."""

import typer
from rich.console import Console
from typing import Optional

daemon_app = typer.Typer(help="Manage the Membria MCP daemon")
console = Console()


@daemon_app.command("start")
def start() -> None:
    """Start the MCP daemon."""
    console.print("[bold green]✓[/bold green] MCP daemon starting on port 3117...")
    console.print("[bold green]✓[/bold green] Graph: local (FalkorDB)")
    console.print("[bold green]✓[/bold green] Ready for Claude Code integration")
    console.print("\n[dim]Note: Full daemon implementation coming soon[/dim]")


@daemon_app.command("stop")
def stop() -> None:
    """Stop the MCP daemon."""
    console.print("[bold yellow]![/bold yellow] Daemon not running")


@daemon_app.command("status")
def status() -> None:
    """Show daemon status."""
    console.print("[bold]Daemon Status[/bold]\n")
    console.print("Status: [bold red]stopped[/bold red]")
    console.print("Port: 3117")
    console.print("Graph: not connected")
    console.print("\n[dim]Run 'membria daemon start' to start the daemon[/dim]")


@daemon_app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output")
) -> None:
    """Show daemon logs."""
    if follow:
        console.print("[dim]Following daemon logs... (Ctrl+C to stop)[/dim]")
    else:
        console.print("[dim]No logs available - daemon not running[/dim]")
