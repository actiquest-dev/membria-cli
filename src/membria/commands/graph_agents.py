"""Graph agent commands: Monitor and analyze the decision graph."""

import typer
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from membria.graph import GraphClient
from membria.graph_agents import GraphAnalyzer, HealthStatus
from membria.config import ConfigManager

app = typer.Typer(help="Monitor and analyze the decision graph")
console = Console()


@app.command()
def health() -> None:
    """Check graph health status.

    Example:
        membria graph health
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)
        health = analyzer.health_agent.check_health()

        # Display status
        status_color = {
            HealthStatus.HEALTHY: "green",
            HealthStatus.DEGRADED: "yellow",
            HealthStatus.UNHEALTHY: "red",
        }

        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
        }

        console.print(
            f"\n{status_emoji[health.status]} "
            f"[bold {status_color[health.status]}]"
            f"{health.status.value.upper()}[/bold]\n"
        )

        # Metrics table
        table = Table(title="Health Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Decisions", str(health.total_decisions))
        table.add_row("Success Rate", f"{health.success_rate:.1%}")
        table.add_row("Avg Confidence", f"{health.avg_confidence:.1%}")
        table.add_row("Rework Rate", f"{health.rework_rate:.1%}")
        table.add_row("Calibration Quality", f"{health.calibration_quality:.1%}")
        table.add_row("Last Check", health.last_check or "Never")

        console.print(table)

        # Issues and warnings
        if health.issues:
            console.print("\n[bold red]ISSUES:[/bold red]")
            for issue in health.issues:
                console.print(f"  ❌ {issue}")

        if health.warnings:
            console.print("\n[bold yellow]WARNINGS:[/bold yellow]")
            for warning in health.warnings:
                console.print(f"  ⚠️  {warning}")

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def analyze(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Analyze specific domain"),
    full: bool = typer.Option(False, "--full", "-f", help="Full analysis report"),
) -> None:
    """Analyze graph state and detect anomalies.

    Example:
        membria graph analyze
        membria graph analyze --domain "framework_choice"
        membria graph analyze --full
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)

        if full:
            # Full analysis
            analysis = analyzer.run_full_analysis()
            console.print(json.dumps(analysis, indent=2))
        else:
            # Calibration analysis
            calibrations = analyzer.calibration_agent.analyze_calibration(domain)

            if not calibrations:
                console.print("[dim]No calibration data available[/dim]")
                graph.disconnect()
                return

            console.print("\n[bold]Calibration Analysis[/bold]\n")

            for cal in calibrations:
                # Determine status
                if abs(cal.overconfidence) > 0.15:
                    status = (
                        "OVERCONFIDENT"
                        if cal.overconfidence > 0
                        else "UNDERCONFIDENT"
                    )
                    emoji = "📈" if cal.overconfidence > 0 else "📉"
                else:
                    status = "WELL-CALIBRATED"
                    emoji = "✅"

                console.print(f"{emoji} [bold]{cal.domain}[/bold]")
                console.print(f"   Confidence: {cal.avg_confidence:.0%}")
                console.print(f"   Success Rate: {cal.actual_success_rate:.0%}")
                console.print(f"   Sample Size: {cal.sample_size}")
                console.print(f"   Status: {status}")

                if cal.recommendations:
                    console.print("   Recommendations:")
                    for rec in cal.recommendations:
                        console.print(f"     • {rec}")

                console.print()

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def anomalies() -> None:
    """Detect anomalies in the graph.

    Example:
        membria graph anomalies
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)
        anomalies = analyzer.anomaly_agent.detect_anomalies()

        if not anomalies:
            console.print("[green]✓ No anomalies detected[/green]\n")
            graph.disconnect()
            return

        console.print(f"\n[bold]Detected Anomalies: {len(anomalies)}[/bold]\n")

        # Group by severity
        critical = [a for a in anomalies if a.severity == "critical"]
        high = [a for a in anomalies if a.severity == "high"]
        medium = [a for a in anomalies if a.severity == "medium"]
        low = [a for a in anomalies if a.severity == "low"]

        for severity, items, emoji, color in [
            ("CRITICAL", critical, "🔴", "red"),
            ("HIGH", high, "🟠", "orange1"),
            ("MEDIUM", medium, "🟡", "yellow"),
            ("LOW", low, "🔵", "blue"),
        ]:
            if not items:
                continue

            console.print(f"[bold {color}]{emoji} {severity}[/bold {color}]")
            for anomaly in items:
                console.print(f"  • {anomaly.anomaly_type}")
                console.print(f"    {anomaly.description}")
                console.print(f"    Affected: {anomaly.affected_items} items")
                console.print(f"    → {anomaly.recommendation}")
            console.print()

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def report() -> None:
    """Generate comprehensive graph report.

    Example:
        membria graph report
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)

        # Generate all analyses
        analyzer.health_agent.check_health()
        analyzer.calibration_agent.analyze_calibration()
        analyzer.anomaly_agent.detect_anomalies()

        # Display summary
        summary = analyzer.get_summary()
        console.print(summary)

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def stats(
    output: str = typer.Option("text", "--output", "-o", help="Output format (text, json)"),
) -> None:
    """Get graph statistics.

    Example:
        membria graph stats
        membria graph stats --output json
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)
        analysis = analyzer.run_full_analysis()

        if output == "json":
            console.print(json.dumps(analysis, indent=2))
        else:
            # Format as text
            health = analysis["health"]

            console.print("\n[bold blue]Graph Statistics[/bold blue]\n")

            table = Table()
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Status", health["status"].upper())
            table.add_row("Total Decisions", str(health["total_decisions"]))
            table.add_row("Success Rate", f"{health['success_rate']:.1%}")
            table.add_row("Average Confidence", f"{health['avg_confidence']:.1%}")
            table.add_row("Rework Rate", f"{health['rework_rate']:.1%}")
            table.add_row("Prevention Rate", f"{health['prevention_rate']:.1%}")
            table.add_row("Calibration", f"{health['calibration_quality']:.1%}")

            console.print(table)

            # Anomalies summary
            if analysis["anomalies"]:
                console.print(f"\n[bold yellow]Anomalies: {len(analysis['anomalies'])}[/bold yellow]")
                for anom in analysis["anomalies"]:
                    icon = "🔴" if anom["severity"] == "critical" else "🟠" if anom["severity"] == "high" else "🟡"
                    console.print(f"  {icon} {anom['type']}: {anom['description']}")

            console.print()

        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def prevention() -> None:
    """Analyze prevention cycle effectiveness.

    Shows how well negative knowledge prevents future decisions.

    Example:
        membria graph prevention
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)
        prevention = analyzer.causal_agent.analyze_prevention_effectiveness()

        console.print("\n[bold cyan]Prevention Cycle Analysis[/bold cyan]\n")

        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Failures", str(prevention.total_failures))
        table.add_row("Lessons Learned", str(prevention.lessons_learned))
        table.add_row("Decisions Prevented", str(prevention.prevented_decisions))
        table.add_row("Prevention Rate", f"{prevention.prevention_rate:.1%}")

        console.print(table)

        if prevention.active_preventions:
            console.print("\n[bold]Active Preventions:[/bold]")
            for nk_id in prevention.active_preventions:
                console.print(f"  ✅ {nk_id}")

        console.print()
        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@app.command()
def causal(
    decision_id: str = typer.Argument(..., help="Decision ID to trace (e.g., dec_abc123)")
) -> None:
    """Show full causal chain for a decision.

    Traces: Decision → CodeChange → Outcome → NegativeKnowledge → Prevention

    Example:
        membria graph causal dec_auth_jwt
    """
    try:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if not graph.connect():
            console.print("[bold red]✗[/bold red] Cannot connect to graph")
            raise typer.Exit(code=1)

        analyzer = GraphAnalyzer(graph)
        chains = analyzer.causal_agent.analyze_causal_chains()

        console.print(f"\n[bold cyan]Causal Chain: {decision_id}[/bold cyan]\n")

        # Filter chains for this decision
        matching_chains = [c for c in chains if c.decision_id == decision_id]

        if not matching_chains:
            console.print(f"[dim]No causal chain found for {decision_id}[/dim]")
            graph.disconnect()
            return

        for chain in matching_chains:
            console.print(f"[bold]Decision:[/bold] {chain.decision_statement}")
            console.print(f"  Confidence: {chain.decision_confidence:.0%}")

            if chain.code_change_sha:
                console.print(f"\n[bold]→ Implemented in:[/bold] {chain.code_change_sha}")

            if chain.outcome_status:
                console.print(f"\n[bold]→ Outcome:[/bold] {chain.outcome_status}")
                if chain.outcome_evidence:
                    console.print(f"  {chain.outcome_evidence}")

            if chain.learned_lesson:
                console.print(f"\n[bold]→ Learned:[/bold] {chain.learned_lesson}")
                if chain.recommendation:
                    console.print(f"  💡 {chain.recommendation}")

            if chain.prevented_future_decisions:
                console.print(f"\n[bold]→ Prevented:[/bold]")
                for future_id in chain.prevented_future_decisions:
                    console.print(f"  ✅ {future_id}")

        console.print()
        graph.disconnect()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)
