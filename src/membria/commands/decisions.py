"""Decision management commands."""

import typer
from rich.console import Console
from rich.table import Table

decisions_app = typer.Typer(help="Manage decisions in the Reasoning Graph")
console = Console()


@decisions_app.command("list")
def list_decisions(
    status: str = typer.Option(None, help="Filter by status"),
    module: str = typer.Option(None, help="Filter by module"),
) -> None:
    """List decisions."""
    console.print("[bold]Recent Decisions[/bold]\n")
    console.print("[dim]No decisions recorded yet[/dim]")
    console.print("\n[dim]Decisions will appear here after you start using Membria with Claude Code[/dim]")


@decisions_app.command("show")
def show(decision_id: str) -> None:
    """Show decision details."""
    console.print(f"[bold]Decision: {decision_id}[/bold]\n")
    console.print("[dim]Not found[/dim]")


@decisions_app.command("record")
def record() -> None:
    """Record a new decision interactively."""
    console.print("[bold]Record Decision[/bold]\n")
    console.print("[dim]Interactive wizard coming soon[/dim]")
