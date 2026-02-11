"""Statistics and analytics commands."""

import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime, timedelta
from typing import Optional
import json

from membria.config import ConfigManager
from membria.graph import GraphClient

stats_app = typer.Typer(help="View decision statistics and analytics")
console = Console()


@stats_app.command("show")
def show(
    period: Optional[str] = typer.Option(None, "--period", "-p", help="Time period (7d, 30d, 90d, all)"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Filter by module"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
) -> None:
    """Show decision statistics."""
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        # Get decisions
        decisions_raw = graph.get_decisions()

        # Convert to dictionaries
        decisions = []
        for result in decisions_raw:
            if isinstance(result, list) and len(result) > 0:
                node = result[0]
                if hasattr(node, 'properties'):
                    decisions.append(node.properties)
            elif isinstance(result, dict):
                decisions.append(result)

        # Filter by period
        if period and period != "all":
            days = int(period.rstrip('d'))
            cutoff_time = datetime.now().timestamp() - (days * 86400)
            decisions = [
                d for d in decisions
                if d.get('created_at', 0) >= cutoff_time
            ]

        # Filter by module
        if module:
            decisions = [d for d in decisions if d.get('module') == module]

        # Calculate statistics
        total = len(decisions)
        if total == 0:
            console.print("[dim]No decisions recorded[/dim]")
            graph.disconnect()
            return

        success = len([d for d in decisions if d.get('outcome') == 'success'])
        failure = len([d for d in decisions if d.get('outcome') == 'failure'])
        pending = len([d for d in decisions if d.get('outcome') == 'pending'])
        resolved = success + failure

        success_rate = (success / resolved * 100) if resolved > 0 else 0

        # Statistics by module
        modules = {}
        for d in decisions:
            mod = d.get('module', 'general')
            if mod not in modules:
                modules[mod] = {'total': 0, 'success': 0, 'failure': 0}
            modules[mod]['total'] += 1
            if d.get('outcome') == 'success':
                modules[mod]['success'] += 1
            elif d.get('outcome') == 'failure':
                modules[mod]['failure'] += 1

        # Output
        if format == "json":
            stats_data = {
                "total": total,
                "resolved": resolved,
                "pending": pending,
                "success": success,
                "failure": failure,
                "success_rate_percent": round(success_rate, 2),
                "by_module": {
                    mod: {
                        "total": stats['total'],
                        "success": stats['success'],
                        "success_rate": round(
                            stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0, 2
                        ),
                    }
                    for mod, stats in modules.items()
                },
            }
            console.print(json.dumps(stats_data, indent=2))
        else:
            # Table format
            console.print("[bold]Decision Statistics[/bold]\n")

            # Overall stats
            table = Table(title="Overall")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="white")
            table.add_row("Total Decisions", str(total))
            table.add_row("Resolved", str(resolved))
            table.add_row("Success", f"[green]{success}[/green]")
            table.add_row("Failure", f"[red]{failure}[/red]")
            table.add_row("Pending", f"[yellow]{pending}[/yellow]")
            table.add_row("Success Rate", f"[bold green]{success_rate:.1f}%[/bold green]")

            console.print(table)

            # By module
            if modules:
                console.print("\n[bold]By Module[/bold]\n")
                module_table = Table()
                module_table.add_column("Module", style="cyan")
                module_table.add_column("Total", style="white")
                module_table.add_column("Success", style="green")
                module_table.add_column("Rate", style="yellow")

                for mod, stats in sorted(modules.items()):
                    rate = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
                    module_table.add_row(
                        mod,
                        str(stats['total']),
                        str(stats['success']),
                        f"{rate:.1f}%",
                    )

                console.print(module_table)

            # Period info
            if period:
                console.print(f"\n[dim]Period: {period}[/dim]")

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)
