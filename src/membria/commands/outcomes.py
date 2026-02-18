"""Outcome tracking commands: Record and view decision results."""

import typer
import json
from typing import Optional

from membria.outcome_tracker import OutcomeTracker
from membria.outcome_models import OutcomeStatus
from membria.github_client import GitHubClient

app = typer.Typer(help="Track decision outcomes and results")


@app.command()
def create(
    decision_id: str = typer.Option(..., "--decision-id", help="Decision ID to track"),
    outcome_id: Optional[str] = typer.Option(None, "--outcome-id", help="Specific outcome ID (auto-generated if not provided)"),
) -> None:
    """Create new outcome tracking record."""
    tracker = OutcomeTracker()
    outcome = tracker.create_outcome(decision_id, outcome_id)

    typer.echo(f"✅ Outcome created")
    typer.echo(f"   ID: {outcome.outcome_id}")
    typer.echo(f"   Decision: {decision_id}")
    typer.echo(f"   Status: {outcome.status.value}")


@app.command()
def view(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID to view"),
) -> None:
    """View outcome tracking record."""
    tracker = OutcomeTracker()
    outcome = tracker.get_outcome(outcome_id)

    if not outcome:
        typer.echo(f"❌ Outcome {outcome_id} not found")
        raise typer.Exit(1)

    typer.echo(f"📊 Outcome: {outcome.outcome_id}")
    typer.echo(f"   Decision: {outcome.decision_id}")
    typer.echo(f"   Status: {outcome.status.value}")

    if outcome.pr_number:
        typer.echo(f"   PR #: {outcome.pr_number}")
        typer.echo(f"   PR URL: {outcome.pr_url}")

    typer.echo(f"   Signals: {len(outcome.signals)}")
    for signal in outcome.signals:
        icon = "✅" if signal.valence.value == "positive" else "❌" if signal.valence.value == "negative" else "ℹ️"
        typer.echo(f"      {icon} {signal.signal_type.value}: {signal.description}")

    if outcome.lessons_learned:
        typer.echo("\n   Lessons Learned:")
        for lesson in outcome.lessons_learned:
            typer.echo(f"      • {lesson}")

    # Success assessment
    assessment = tracker.check_success_criteria(outcome_id)
    typer.echo(f"\n   Estimated Success: {int(assessment['estimated_success'] * 100)}%")
    if assessment["needs_attention"]:
        typer.echo("   ⚠️  Needs attention (negative signals detected)")


@app.command()
def pr_created(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID to record PR for"),
    pr_number: int = typer.Option(..., "--pr-number", help="GitHub PR number"),
    branch: str = typer.Option("HEAD", "--branch", help="Branch name"),
) -> None:
    """Record PR creation for decision implementation."""
    tracker = OutcomeTracker()

    try:
        github = GitHubClient()
        repo = github.repo or "unknown/unknown"
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"

        outcome = tracker.record_pr_created(outcome_id, pr_number, pr_url, branch)

        typer.echo("✅ PR recorded")
        typer.echo(f"   PR #{pr_number}: {pr_url}")
        typer.echo(f"   Status: {outcome.status.value}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def pr_merged(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID to record merge for"),
    pr_number: int = typer.Option(..., "--pr-number", help="GitHub PR number that merged"),
) -> None:
    """Record PR merge event."""
    tracker = OutcomeTracker()

    try:
        outcome = tracker.record_pr_merged(outcome_id, pr_number)

        typer.echo("✅ PR merge recorded")
        typer.echo(f"   PR #{pr_number} merged")
        typer.echo(f"   Status: {outcome.status.value}")
        typer.echo(f"   Merged at: {outcome.merged_at}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def ci_result(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID to record CI result for"),
    passed: bool = typer.Option(True, "--passed/--failed", help="Whether CI tests passed"),
    details: Optional[str] = typer.Option(None, "--details", help="Test failure details"),
) -> None:
    """Record CI test result."""
    tracker = OutcomeTracker()

    try:
        outcome = tracker.record_ci_result(outcome_id, passed, details)

        status_icon = "✅" if passed else "❌"
        typer.echo(f"{status_icon} CI result recorded")
        typer.echo(f"   Status: {'PASSED' if passed else 'FAILED'}")
        if details:
            typer.echo(f"   Details: {details}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def incident(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID"),
    severity: str = typer.Option("medium", "--severity", help="Incident severity"),
    description: str = typer.Option(..., "--description", help="Incident description"),
) -> None:
    """Record incident/bug found in production."""
    tracker = OutcomeTracker()

    try:
        outcome = tracker.record_incident(outcome_id, severity, description)

        typer.echo("❌ Incident recorded")
        typer.echo(f"   Severity: {severity}")
        typer.echo(f"   Description: {description}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def performance(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID"),
    latency_ms: Optional[float] = typer.Option(None, "--latency-ms", help="Average latency in ms"),
    throughput_rps: Optional[float] = typer.Option(None, "--throughput-rps", help="Throughput in requests/sec"),
    error_rate: Optional[float] = typer.Option(None, "--error-rate", help="Error rate percentage"),
    uptime: Optional[float] = typer.Option(None, "--uptime", help="Uptime percentage"),
) -> None:
    """Record performance metrics."""
    tracker = OutcomeTracker()

    try:
        metrics = {}
        if latency_ms is not None:
            metrics["avg_latency_ms"] = latency_ms
        if throughput_rps is not None:
            metrics["throughput_rps"] = throughput_rps
        if error_rate is not None:
            metrics["error_rate_percent"] = error_rate
        if uptime is not None:
            metrics["uptime_percent"] = uptime

        outcome = tracker.record_performance(outcome_id, metrics)

        typer.echo("✅ Performance recorded")
        for key, value in metrics.items():
            typer.echo(f"   {key}: {value}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def finalize(
    outcome_id: str = typer.Option(..., "--outcome-id", help="Outcome ID to finalize"),
    status: str = typer.Option("success", "--status", help="Final outcome status"),
    score: float = typer.Option(0.5, "--score", help="Final success score (0.0-1.0)"),
) -> None:
    """Mark outcome as complete (after 30-day evaluation period)."""
    tracker = OutcomeTracker()

    try:
        outcome = tracker.finalize_outcome(
            outcome_id,
            final_status=status,
            final_score=score,
            lessons_learned=[],
        )

        typer.echo("✅ Outcome finalized")
        typer.echo(f"   Status: {status}")
        typer.echo(f"   Score: {int(score * 100)}%")

        if outcome.lessons_learned:
            typer.echo("   Lessons Learned:")
            for l in outcome.lessons_learned:
                typer.echo(f"      • {l}")

    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def list(
    decision_id: Optional[str] = typer.Option(None, "--decision-id", help="Filter by decision ID"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List outcomes with optional filtering."""
    tracker = OutcomeTracker()

    # Parse status enum if provided
    status_enum = None
    if status:
        status_enum = OutcomeStatus(status)

    outcomes = tracker.list_outcomes(decision_id=decision_id, status=status_enum)

    if output_json:
        data = [tracker.export_outcome(o.outcome_id) for o in outcomes]
        typer.echo(json.dumps(data, indent=2))
    else:
        if not outcomes:
            typer.echo("No outcomes found")
            return

        typer.echo("📊 Outcomes")
        for outcome in outcomes:
            status_icon = "⏳" if outcome.status == OutcomeStatus.PENDING else "📤" if outcome.status == OutcomeStatus.SUBMITTED else "✅" if outcome.status == OutcomeStatus.MERGED else "🏁"
            typer.echo(f"\n   {status_icon} {outcome.outcome_id}")
            typer.echo(f"      Decision: {outcome.decision_id}")
            typer.echo(f"      Status: {outcome.status.value}")
            if outcome.pr_number:
                typer.echo(f"      PR: #{outcome.pr_number}")
            typer.echo(f"      Signals: {len(outcome.signals)}")
