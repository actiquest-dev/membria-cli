"""Decision Extractor commands - Signal detection and LLM extraction."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import json

from membria.signal_detector import SignalDetector
from membria.haiku_extractor import HaikuExtractor
from membria.config import ConfigManager
from membria.graph import GraphClient

extractor_app = typer.Typer(help="Decision extraction and signal detection")
console = Console()


@extractor_app.command("status")
def status() -> None:
    """Show extractor status."""
    try:
        detector = SignalDetector()
        pending = detector.get_pending_signals()
        history = detector.get_signal_history(limit=5)

        console.print("[bold]Decision Extractor Status[/bold]\n")

        # Overall status
        status_table = Table(title="Pipeline Status")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="white")
        status_table.add_row("Level 1 (Explicit)", "✅ Ready (membria_record_decision)")
        status_table.add_row("Level 2 (Signals)", "✅ Running (rule-based)")
        status_table.add_row("Level 3 (Haiku)", "⏳ Pending signals")
        status_table.add_row("Pending Signals", f"[yellow]{len(pending)}[/yellow]")

        console.print(status_table)

        # Recent signals
        if history:
            console.print("\n[bold]Recent Signals[/bold]\n")
            signals_table = Table()
            signals_table.add_column("ID", style="cyan")
            signals_table.add_column("Type", style="white")
            signals_table.add_column("Module", style="green")
            signals_table.add_column("Confidence", style="yellow")
            signals_table.add_column("Status", style="magenta")

            for sig in history[:5]:
                signals_table.add_row(
                    sig["id"][:12],
                    sig["signal_type"],
                    sig["module"],
                    f"{sig['confidence']:.2f}",
                    sig["status"],
                )

            console.print(signals_table)

        console.print(f"\n[dim]Run 'membria extractor run' to process pending signals[/dim]")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@extractor_app.command("log")
def log(
    pending: bool = typer.Option(False, "--pending", help="Show only pending signals"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of entries to show"),
) -> None:
    """Show extraction history."""
    try:
        detector = SignalDetector()

        if pending:
            signals = detector.get_pending_signals()
        else:
            signals = detector.get_signal_history(limit=limit)

        if not signals:
            console.print("[dim]No signals recorded[/dim]")
            return

        console.print("[bold]Signal Detection Log[/bold]\n")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Timestamp", style="white")
        table.add_column("Type", style="green")
        table.add_column("Module", style="yellow")
        table.add_column("Confidence", style="magenta")
        table.add_column("Status", style="blue")

        for sig in signals[:limit]:
            status_color = "green" if sig["status"] == "extracted" else "yellow"
            table.add_row(
                sig["id"][:12],
                sig.get("timestamp", "?")[:19],
                sig["signal_type"],
                sig["module"],
                f"{sig['confidence']:.2f}",
                f"[{status_color}]{sig['status']}[/{status_color}]",
            )

        console.print(table)

        if pending:
            console.print(f"\n[dim]Pending signals: {len(signals)}[/dim]")
            console.print(f"[dim]Run 'membria extractor run' to process[/dim]")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@extractor_app.command("run")
def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be extracted without saving"),
    level3: bool = typer.Option(False, "--level3", help="Use Haiku for structured extraction (Level 3)"),
) -> None:
    """Run extraction on pending signals."""
    try:
        detector = SignalDetector()
        pending = detector.get_pending_signals()

        if not pending:
            console.print("[dim]No pending signals[/dim]")
            return

        console.print(f"[bold]Processing {len(pending)} pending signal(s)[/bold]\n")

        table = Table(title="Extraction Results")
        table.add_column("Signal ID", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Decision/Text", style="green")
        table.add_column("Module", style="yellow")

        extracted_count = 0
        saved_count = 0

        if level3:
            # Level 3: Use Haiku for structured extraction
            console.print("[dim]Using Claude Haiku for structured extraction (Level 3)...[/dim]\n")
            extractor = HaikuExtractor()

            extracted = extractor.batch_extract(pending)

            for sig in pending:
                # Find corresponding extraction
                ext = next((e for e in extracted if e.get("signal_id") == sig["id"]), None)

                if ext:
                    table.add_row(
                        sig["id"][:12],
                        "HIGH",
                        ext.get("decision_statement", "")[:40],
                        ext.get("module", sig["module"]),
                    )
                    extracted_count += 1

                    if not dry_run:
                        # Import and save to graph
                        try:
                            from membria.models import Decision
                            import uuid

                            decision = Decision(
                                decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                                statement=ext.get("decision_statement", ""),
                                alternatives=ext.get("alternatives", []),
                                confidence=float(ext.get("confidence", 0.5)),
                                module=ext.get("module", "general"),
                            )

                            config = ConfigManager()
                            falkordb_config = config.get_falkordb_config()
                            graph = GraphClient(falkordb_config)

                            if graph.connect():
                                if graph.add_decision(decision):
                                    detector.mark_extracted(sig["id"], decision.decision_id)
                                    extractor.save_decision(ext, decision.decision_id)
                                    saved_count += 1
                                graph.disconnect()

                        except Exception as e:
                            console.print(f"[yellow]Warning: Failed to save decision: {e}[/yellow]")

                else:
                    # No extraction, just show signal
                    table.add_row(
                        sig["id"][:12],
                        sig["signal_type"],
                        sig["text"][:40],
                        sig["module"],
                    )

        else:
            # Level 2: Rule-based only
            for sig in pending:
                decision_text = sig["text"][:40]

                table.add_row(
                    sig["id"][:12],
                    sig["signal_type"],
                    decision_text,
                    sig["module"],
                )

                if not dry_run:
                    detector.mark_extracted(sig["id"], f"dec_{sig['id'][:16]}")
                    extracted_count += 1

        console.print(table)

        if dry_run:
            console.print(f"\n[dim]Dry run: would process {len(pending)} signals[/dim]")
            console.print(f"[dim]Run 'membria extractor run' without --dry-run to process[/dim]")
            if level3:
                console.print(f"[dim]Level 3 (Haiku) would extract {extracted_count} decisions[/dim]")
        else:
            if level3:
                console.print(f"\n[bold green]✓[/bold green] Processed {extracted_count} signal(s)")
                console.print(f"[bold green]✓[/bold green] Saved {saved_count} decision(s) to graph")
            else:
                console.print(f"\n[bold green]✓[/bold green] Processed {extracted_count} signal(s)")
                console.print(f"[dim]Use --level3 flag for Haiku structured extraction[/dim]")

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@extractor_app.command("test")
def test(text: str = typer.Argument(..., help="Text to test for signals")) -> None:
    """Test signal detection on custom text."""
    try:
        detector = SignalDetector()
        signals = detector.detect(text)

        console.print(f"[bold]Signal Detection Test[/bold]\n")
        console.print(f"Input: {text}\n")

        if not signals:
            console.print("[dim]No signals detected[/dim]")
            return

        for sig in signals:
            confidence_color = "green" if sig["confidence"] > 0.75 else "yellow"
            console.print(f"Signal Type: [{confidence_color}]{sig['signal_type'].upper()}[/{confidence_color}]")
            console.print(f"Confidence: {sig['confidence']:.2f}")
            console.print(f"Module: {sig['module']}")
            console.print(f"Matches: {len(sig['matches'])} pattern(s)")
            console.print()

    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error: {e}")
        raise typer.Exit(code=1)


@extractor_app.command("plugins")
def plugins() -> None:
    """List custom extractor plugins."""
    console.print("[bold]Custom Extractor Plugins[/bold]\n")
    console.print("[dim]Monty plugins: ~/.membria/extractors/[/dim]")
    console.print("[dim]Run 'membria extractor plugins list' for details[/dim]")
