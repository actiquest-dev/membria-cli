"""Cognitive Safety commands."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List

from membria.bias_detector import BiasDetector
from membria.graph import GraphClient
from membria.config import ConfigManager
from membria.firewall import Firewall, FirewallDecision
from membria.red_flags import RedFlagSeverity

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


@safety_app.command("firewall")
def firewall_check(
    statement: str = typer.Argument(..., help="Decision statement to evaluate"),
    confidence: Optional[float] = typer.Option(0.75, "--confidence", "-c", help="Confidence level (0.0-1.0)"),
    alternatives: Optional[str] = typer.Option(None, "--alternatives", "-a", help="Alternatives (comma-separated)"),
    time_pressure: bool = typer.Option(False, "--rush", help="Under time pressure?"),
) -> None:
    """Evaluate decision through firewall.

    Checks for red flags and risky patterns.

    Args:
        statement: Decision statement
        confidence: Confidence level (0.0-1.0)
        alternatives: Comma-separated alternatives considered
        time_pressure: Mark if under time pressure

    Examples:
        membria safety firewall "Use custom JWT" --confidence 0.7
        membria safety firewall "Implement caching" -c 0.85 -a "Redis,Memcached"
    """
    try:
        # Parse alternatives
        alts = []
        if alternatives:
            alts = [a.strip() for a in alternatives.split(",")]

        # Create firewall and evaluate
        fw = Firewall()
        result = fw.evaluate(
            decision_statement=statement,
            confidence=confidence,
            alternatives=alts if alts else None,
            antipatterns=None,
            time_pressure=time_pressure,
        )

        # Display result
        console.print(fw.format_for_display(result))

        # Exit code based on decision
        if result.decision == FirewallDecision.BLOCK:
            raise typer.Exit(code=2)  # Blocked
        elif result.decision == FirewallDecision.WARN:
            raise typer.Exit(code=1)  # Warning
        else:
            raise typer.Exit(code=0)  # OK

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


@safety_app.command("red-flags")
def show_red_flags(
    statement: str = typer.Argument(..., help="Decision statement to check"),
    confidence: float = typer.Option(0.75, "--confidence", help="Confidence level"),
) -> None:
    """Show all red flags for a decision.

    Detailed analysis of potential issues.

    Args:
        statement: Decision statement
        confidence: Confidence level

    Example:
        membria safety red-flags "Custom authentication" --confidence 0.6
    """
    try:
        from membria.red_flags import RedFlagDetector

        detector = RedFlagDetector()
        flags = detector.detect(
            decision_statement=statement,
            confidence=confidence,
            alternatives=None,
            antipatterns_detected=None,
            time_pressure=False,
        )

        console.print(f"\n[bold]Red Flag Analysis[/bold]\n")
        console.print(f"Statement: {statement}")
        console.print(f"Confidence: {int(confidence * 100)}%\n")

        if not flags:
            console.print("✅ No red flags detected!")
            return

        console.print(f"[bold]Found {len(flags)} flag(s):[/bold]\n")

        for i, flag in enumerate(flags, 1):
            icon = {
                RedFlagSeverity.LOW: "🟢",
                RedFlagSeverity.MEDIUM: "🟡",
                RedFlagSeverity.HIGH: "🟠",
                RedFlagSeverity.CRITICAL: "🔴",
            }[flag.severity]

            console.print(f"{i}. {icon} {flag.name}")
            console.print(f"   Severity: {flag.severity.value.upper()}")
            console.print(f"   Evidence: {flag.evidence}")
            console.print(f"   Fix: {flag.recommendation}\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise typer.Exit(code=1)
