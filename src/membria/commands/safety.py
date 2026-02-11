"""Cognitive Safety commands."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

from membria.bias_detector import BiasDetector
from membria.graph import GraphClient
from membria.config import ConfigManager

safety_app = typer.Typer(help="Cognitive safety and bias detection")
console = Console()


@safety_app.command("analyze")
def analyze(
    decision_id: Optional[str] = typer.Option(None, "--decision", "-d", help="Decision ID"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Decision text"),
) -> None:
    """Analyze decision for biases."""
    if not decision_id and not text:
        console.print("[bold red]✗[/bold red] Provide --decision or --text")
        raise typer.Exit(code=1)

    detector = BiasDetector()
    decision_text = text
    alternatives = []

    # Get decision from graph if ID provided
    if decision_id:
        config = ConfigManager()
        falkordb_config = config.get_falkordb_config()
        graph = GraphClient(falkordb_config)

        if graph.connect():
            decisions = graph.get_decisions()
            for result in decisions:
                if isinstance(result, list) and len(result) > 0:
                    node = result[0]
                    if hasattr(node, 'properties'):
                        if node.properties.get("id") == decision_id:
                            decision_text = node.properties.get("statement", "")
                            alts = node.properties.get("alternatives", "")
                            if isinstance(alts, str):
                                import json
                                try:
                                    alternatives = json.loads(alts)
                                except:
                                    alternatives = []
                            break
            graph.disconnect()

    if not decision_text:
        console.print("[bold red]✗[/bold red] Decision not found")
        raise typer.Exit(code=1)

    # Analyze
    analysis = detector.analyze(decision_text, alternatives, 0.75)

    console.print(f"[bold]Bias Analysis[/bold]\n")
    console.print(f"Statement: {decision_text}\n")

    if analysis.detected_biases:
        console.print("[bold red]⚠️  Detected Biases:[/bold red]")
        for bias in analysis.detected_biases:
            console.print(f"  • {bias}")

    console.print(f"\nRisk Score: {analysis.risk_score:.2f} ({analysis.severity})")

    console.print(f"\n[bold]Recommendations:[/bold]")
    for rec in analysis.recommendations:
        console.print(f"  {rec}")


@safety_app.command("status")
def status() -> None:
    """Show safety metrics."""
    config = ConfigManager()
    falkordb_config = config.get_falkordb_config()
    graph = GraphClient(falkordb_config)

    if not graph.connect():
        console.print("[bold red]✗[/bold red] Cannot connect to graph")
        raise typer.Exit(code=1)

    decisions = graph.get_decisions()
    high_risk = 0
    detector = BiasDetector()

    for result in decisions:
        if isinstance(result, list) and len(result) > 0:
            node = result[0]
            if hasattr(node, 'properties'):
                props = node.properties
                analysis = detector.analyze(
                    props.get("statement", ""), [], float(props.get("confidence", 0.5))
                )
                if analysis.risk_score > 0.6:
                    high_risk += 1

    graph.disconnect()

    console.print("[bold]Safety Status[/bold]\n")
    console.print(f"Total decisions analyzed: {len(decisions)}")
    console.print(f"High-risk decisions: {high_risk}")
    console.print(f"Safety level: {'🟢 Good' if high_risk < 3 else '🟡 Fair' if high_risk < 5 else '🔴 Concerning'}")
