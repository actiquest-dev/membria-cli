"""Decision management commands."""

import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime
from typing import Optional
import uuid

from membria.config import ConfigManager
from membria.graph import GraphClient
from membria.models import Decision

decisions_app = typer.Typer(help="Manage decisions in the Reasoning Graph")
console = Console()


@decisions_app.command("list")
def list_decisions(
    status: Optional[str] = typer.Option(None, help="Filter by status (pending/success/failure)"),
    module: Optional[str] = typer.Option(None, help="Filter by module"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of decisions to show"),
) -> None:
    """List decisions from the reasoning graph."""
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        # Get decisions (returns list of [Node] tuples)
        decisions_raw = graph.get_decisions()

        if not decisions_raw:
            console.print("[bold]Recent Decisions[/bold]\n")
            console.print("[dim]No decisions recorded yet[/dim]")
            console.print("\n[dim]Decisions will appear here after you start using Membria with Claude Code[/dim]")
            graph.disconnect()
            return

        # Convert Node objects to dictionaries
        decisions = []
        for result in decisions_raw:
            if isinstance(result, list) and len(result) > 0:
                node = result[0]
                if hasattr(node, 'properties'):
                    decisions.append(node.properties)
            elif isinstance(result, dict):
                decisions.append(result)

        # Apply filters
        filtered = decisions
        if status:
            filtered = [d for d in filtered if d.get("outcome") == status]
        if module:
            filtered = [d for d in filtered if d.get("module") == module]

        # Limit results
        filtered = filtered[:limit]

        # Create table
        table = Table(title="Recent Decisions")
        table.add_column("ID", style="cyan")
        table.add_column("Statement", style="white")
        table.add_column("Module", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Outcome", style="magenta")

        for d in filtered:
            outcome_color = "green" if d.get("outcome") == "success" else "red" if d.get("outcome") == "failure" else "yellow"
            table.add_row(
                str(d.get("id", "?"))[:12],
                d.get("statement", "")[:50],
                d.get("module", "general"),
                f"{float(d.get('confidence', 0)):.2f}",
                f"[{outcome_color}]{d.get('outcome', 'pending')}[/{outcome_color}]",
            )

        console.print("[bold]Recent Decisions[/bold]\n")
        console.print(table)

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@decisions_app.command("show")
def show(decision_id: str) -> None:
    """Show decision details."""
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        # Get all decisions and find the one
        decisions_raw = graph.get_decisions()
        decision = None

        for result in decisions_raw:
            d = None
            if isinstance(result, list) and len(result) > 0:
                node = result[0]
                if hasattr(node, 'properties'):
                    d = node.properties
            elif isinstance(result, dict):
                d = result

            if d and (d.get("id") == decision_id or str(d.get("id", "")).startswith(decision_id)):
                decision = d
                break

        if not decision:
            console.print(f"[bold red]✗[/bold red] Decision not found: {decision_id}")
            graph.disconnect()
            raise typer.Exit(code=1)

        # Display decision details
        console.print(f"[bold]Decision: {decision.get('id')}[/bold]\n")
        console.print(f"Statement: {decision.get('statement', 'N/A')}")
        console.print(f"Module: {decision.get('module', 'general')}")
        console.print(f"Confidence: {float(decision.get('confidence', 0)):.2f}")
        console.print(f"Status: {decision.get('outcome', 'pending')}")

        # Handle alternatives - might be a JSON string or list
        alternatives = decision.get("alternatives", [])
        if isinstance(alternatives, str):
            import json
            try:
                alternatives = json.loads(alternatives)
            except:
                alternatives = []

        if alternatives:
            console.print(f"\nAlternatives considered:")
            for alt in alternatives:
                console.print(f"  - {alt}")

        console.print(f"\nCreated: {decision.get('created_at', 'N/A')}")
        if decision.get("resolved_at"):
            console.print(f"Resolved: {decision.get('resolved_at')}")

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@decisions_app.command("record")
def record(
    statement: Optional[str] = typer.Option(None, "--statement", "-s", help="Decision statement"),
    alternatives: Optional[str] = typer.Option(None, "--alternatives", "-a", help="Comma-separated alternatives"),
    confidence: float = typer.Option(0.5, "--confidence", "-c", help="Confidence level (0-1)"),
    module: str = typer.Option("general", "--module", "-m", help="Module name"),
) -> None:
    """Record a new decision interactively."""
    try:
        # Interactive input if not provided via options
        if not statement:
            statement = typer.prompt("Decision statement")

        if not alternatives:
            alternatives_str = typer.prompt("Alternatives (comma-separated)")
            alternatives = [a.strip() for a in alternatives_str.split(",")]
        else:
            alternatives = [a.strip() for a in alternatives.split(",")]

        if confidence < 0 or confidence > 1:
            confidence = float(typer.prompt("Confidence (0-1)"))

        # Create decision
        decision = Decision(
            decision_id=f"dec_{uuid.uuid4().hex[:12]}",
            statement=statement,
            alternatives=alternatives,
            confidence=confidence,
            module=module,
        )

        # Save to graph
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        if graph.add_decision(decision):
            console.print(f"\n[bold green]✓[/bold green] Decision recorded: {decision.decision_id}")
            console.print(f"Statement: {statement}")
            console.print(f"Confidence: {confidence:.2f}")
        else:
            console.print("[bold red]✗[/bold red] Failed to record decision")
            raise typer.Exit(code=1)

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)
