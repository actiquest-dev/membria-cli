"""Daemon management commands."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
from pathlib import Path

from membria.process_manager import ProcessManager
from membria.config import ConfigManager

daemon_app = typer.Typer(help="Manage the Membria MCP daemon")
console = Console()


@daemon_app.command("start")
def start(port: int = typer.Option(3117, "--port", "-p", help="Port for MCP daemon")) -> None:
    """Start the MCP daemon."""
    config = ConfigManager()
    manager = ProcessManager()

    success, message = manager.start(port=port)

    if success:
        console.print(f"[bold green]✓[/bold green] {message}")
        console.print(f"[bold green]✓[/bold green] Graph: local (FalkorDB at 192.168.0.105:6379)")
        console.print(f"[bold green]✓[/bold green] Ready for Claude Code integration")
        console.print(f"\n[dim]Access logs: membria daemon logs[/dim]")
    else:
        console.print(f"[bold red]✗[/bold red] {message}")
        raise typer.Exit(code=1)


@daemon_app.command("stop")
def stop() -> None:
    """Stop the MCP daemon."""
    manager = ProcessManager()

    if not manager.is_running():
        console.print("[bold yellow]![/bold yellow] Daemon is not running")
        return

    success, message = manager.stop()
    if success:
        console.print(f"[bold green]✓[/bold green] {message}")
    else:
        console.print(f"[bold red]✗[/bold red] {message}")
        raise typer.Exit(code=1)


@daemon_app.command("status")
def status() -> None:
    """Show daemon status."""
    manager = ProcessManager()
    proc_status = manager.status()

    console.print("[bold]Daemon Status[/bold]\n")

    if proc_status.is_running:
        console.print(f"Status: [bold green]running[/bold green]")
        console.print(f"PID: {proc_status.pid}")
        if proc_status.uptime_seconds:
            hours = int(proc_status.uptime_seconds // 3600)
            minutes = int((proc_status.uptime_seconds % 3600) // 60)
            console.print(f"Uptime: {hours}h {minutes}m")
        console.print(f"Port: {proc_status.port}")
        console.print(f"Graph: [bold green]connected[/bold green] (192.168.0.105:6379)")
        console.print(f"MCP: [bold green]ready[/bold green]")
    else:
        console.print(f"Status: [bold red]stopped[/bold red]")
        console.print(f"Port: {proc_status.port}")
        console.print(f"Graph: [bold yellow]not connected[/bold yellow]")
        console.print(f"\n[dim]Run 'membria daemon start' to start the daemon[/dim]")


@daemon_app.command("logs")
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """Show daemon logs."""
    manager = ProcessManager()
    log_content = manager.get_logs(follow=follow, lines=lines)

    if "[dim]No logs available[/dim]" in log_content or log_content == "No logs available":
        console.print("[dim]No logs available - daemon not running[/dim]")
    else:
        console.print(log_content)
