"""Decision Extractor commands - Signal detection and LLM extraction."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import json

from membria.signal_detector import SignalDetector
from membria.config import ConfigManager

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
) -> None:
    """Run extraction on pending signals."""
    try:
        detector = SignalDetector()
        pending = detector.get_pending_signals()

        if not pending:
            console.print("[dim]No pending signals[/dim]")
            return

        console.print(f"[bold]Processing {len(pending)} pending signal(s)[/bold]\n")

        # In a real implementation, this would call Haiku for structured extraction
        # For now, we'll simulate what would be extracted

        table = Table(title="Would Extract")
        table.add_column("Signal ID", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Extracted Decision", style="green")
        table.add_column("Module", style="yellow")

        extracted_count = 0
        for sig in pending:
            # Simulate extraction (would call Haiku Level 3)
            decision_text = sig["text"][:60]  # Would be full structured extraction

            table.add_row(
                sig["id"][:12],
                sig["signal_type"],
                decision_text,
                sig["module"],
            )

            if not dry_run:
                # In real implementation, would save to graph and mark as extracted
                detector.mark_extracted(sig["id"], f"dec_{sig['id'][:16]}")
                extracted_count += 1

        console.print(table)

        if dry_run:
            console.print(f"\n[dim]Dry run: would process {len(pending)} signals[/dim]")
            console.print(f"[dim]Run 'membria extractor run' without --dry-run to process[/dim]")
        else:
            console.print(f"\n[bold green]✓[/bold green] Processed {extracted_count} signal(s)")
            console.print(f"[dim]Note: Level 3 (Haiku extraction) not yet implemented[/dim]")

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
