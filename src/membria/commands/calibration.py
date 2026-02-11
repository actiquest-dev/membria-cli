"""Calibration and confidence analysis commands."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List, Dict
import json
from statistics import mean

from membria.config import ConfigManager
from membria.graph import GraphClient

calibration_app = typer.Typer(help="Analyze decision confidence calibration")
console = Console()


def get_confidence_bucket(confidence: float) -> str:
    """Get bucket label for confidence value."""
    value = int(confidence * 10)
    if value >= 10:
        value = 9
    return f"{value * 0.1:.1f}-{(value + 1) * 0.1:.1f}"


@calibration_app.command("show")
def show(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by module/domain"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json)"),
) -> None:
    """Show calibration metrics."""
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

        # Filter by domain/module
        if domain:
            decisions = [d for d in decisions if d.get('module') == domain]

        # Only analyze resolved decisions (with outcome)
        resolved = [d for d in decisions if d.get('outcome') in ('success', 'failure')]

        if not resolved:
            console.print("[dim]No resolved decisions to analyze[/dim]")
            graph.disconnect()
            return

        # Group by confidence buckets
        buckets: Dict[str, List[dict]] = {}
        for d in resolved:
            confidence = float(d.get('confidence', 0.5))
            bucket = get_confidence_bucket(confidence)

            if bucket not in buckets:
                buckets[bucket] = []
            buckets[bucket].append(d)

        # Calculate metrics per bucket
        bucket_stats = []
        for bucket in sorted(buckets.keys()):
            decisions_in_bucket = buckets[bucket]
            success_count = len([d for d in decisions_in_bucket if d.get('outcome') == 'success'])
            total = len(decisions_in_bucket)
            success_rate = success_count / total if total > 0 else 0

            # Expected confidence (mid-point of bucket)
            bucket_parts = bucket.split('-')
            expected_confidence = float(bucket_parts[0])  # Lower bound

            bucket_stats.append({
                'bucket': bucket,
                'expected_confidence': expected_confidence,
                'total': total,
                'success': success_count,
                'actual_success_rate': success_rate,
                'overconfidence_gap': expected_confidence - success_rate,
            })

        # Overall calibration
        overall_confidence = mean([float(d.get('confidence', 0.5)) for d in resolved])
        overall_success_rate = len([d for d in resolved if d.get('outcome') == 'success']) / len(
            resolved
        )
        overall_gap = overall_confidence - overall_success_rate

        # Output
        if format == "json":
            output = {
                "overall": {
                    "avg_confidence": round(overall_confidence, 3),
                    "success_rate": round(overall_success_rate, 3),
                    "overconfidence_gap": round(overall_gap, 3),
                    "sample_size": len(resolved),
                    "calibration": "good" if abs(overall_gap) < 0.1 else "overconfident"
                    if overall_gap > 0
                    else "underconfident",
                },
                "by_bucket": [
                    {
                        "bucket": b['bucket'],
                        "count": b['total'],
                        "success_rate": round(b['actual_success_rate'], 3),
                        "overconfidence_gap": round(b['overconfidence_gap'], 3),
                    }
                    for b in bucket_stats
                ],
            }
            console.print(json.dumps(output, indent=2))
        else:
            # Table format
            console.print("[bold]Calibration Analysis[/bold]\n")

            # Overall metrics
            calibration_status = "📊 Well calibrated"
            if overall_gap > 0.15:
                calibration_status = "⚠️  Overconfident"
            elif overall_gap < -0.15:
                calibration_status = "⚠️  Underconfident"

            overall_table = Table(title="Overall Calibration")
            overall_table.add_column("Metric", style="cyan")
            overall_table.add_column("Value", style="white")
            overall_table.add_row("Average Confidence", f"{overall_confidence:.2f}")
            overall_table.add_row("Actual Success Rate", f"{overall_success_rate:.2f} ({overall_success_rate*100:.1f}%)")
            overall_table.add_row("Overconfidence Gap", f"{overall_gap:+.3f}")
            overall_table.add_row("Status", calibration_status)
            overall_table.add_row("Sample Size", str(len(resolved)))

            console.print(overall_table)

            # By bucket
            console.print("\n[bold]Confidence Buckets[/bold]\n")
            bucket_table = Table()
            bucket_table.add_column("Confidence", style="cyan")
            bucket_table.add_column("Count", style="white")
            bucket_table.add_column("Success Rate", style="green")
            bucket_table.add_column("Gap", style="yellow")
            bucket_table.add_column("Status", style="magenta")

            for b in bucket_stats:
                gap = b['overconfidence_gap']
                status = "✓" if abs(gap) < 0.1 else ("Over" if gap > 0 else "Under")
                bucket_table.add_row(
                    b['bucket'],
                    str(b['total']),
                    f"{b['actual_success_rate']*100:.1f}%",
                    f"{gap:+.3f}",
                    status,
                )

            console.print(bucket_table)

            # Recommendations
            console.print("\n[bold]Recommendations[/bold]")
            if overall_gap > 0.15:
                console.print(f"[yellow]⚠️  You're overconfident by {abs(overall_gap)*100:.1f}%[/yellow]")
                console.print(f"[dim]• Consider more conservative confidence estimates[/dim]")
                console.print(f"[dim]• Review failure cases to understand blind spots[/dim]")
            elif overall_gap < -0.15:
                console.print(f"[yellow]⚠️  You're underconfident by {abs(overall_gap)*100:.1f}%[/yellow]")
                console.print(f"[dim]• You're better than you think! Trust your decisions more[/dim]")
            else:
                console.print(f"[green]✓ Well calibrated! Keep doing what you're doing[/green]")

            # Domain-specific analysis
            if domain:
                console.print(f"\n[dim]Analysis for module: {domain}[/dim]")

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)
