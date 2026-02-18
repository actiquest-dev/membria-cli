"""Antipattern detection commands: Check code for CodeDigger patterns."""

import typer
from typing import Optional
from pathlib import Path

from membria.codedigger_client import CodeDiggerClientSync
from membria.pattern_matcher import PatternMatcher
from membria.evidence_aggregator import EvidenceAggregator
from membria.graph import GraphClient

app = typer.Typer(help="Antipattern detection and prevention")


@app.command()
def check(
    path: Optional[str] = typer.Argument(None, help="File or directory to check"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Minimum severity to report (low|medium|high|critical)"),
) -> None:
    """Check code for antipatterns.

    Analyzes code and detects known antipatterns using CodeDigger patterns.

    Args:
        path: File or directory to check. If None, checks current directory.
        severity: Minimum severity level to report

    Examples:
        membria antipattern check                  # Check current directory
        membria antipattern check src/             # Check specific directory
        membria antipattern check file.py --severity high  # Only high+ severity
    """
    try:
        # Default to current directory
        if not path:
            path = "."

        file_path = Path(path)
        if not file_path.exists():
            typer.echo(f"❌ Path not found: {path}", err=True)
            raise typer.Exit(1)

        # Get CodeDigger patterns
        typer.echo("📦 Fetching patterns from CodeDigger...", err=True)
        client = CodeDiggerClientSync()

        if not client.health_check():
            typer.echo("❌ CodeDigger is not accessible", err=True)
            raise typer.Exit(1)

        patterns_list = client.get_patterns()
        if not patterns_list:
            typer.echo("❌ Could not fetch patterns", err=True)
            raise typer.Exit(1)

        typer.echo(f"✓ Fetched {len(patterns_list)} patterns", err=True)

        # Convert Pattern objects to dicts for matcher
        patterns_dict = [
            {
                "pattern_id": p.pattern_id,
                "name": p.name,
                "severity": p.severity,
                "removal_rate": p.removal_rate,
                "repos_affected": p.repos_affected,
                "keywords": p.keywords,
                "regex_pattern": p.regex_pattern,
            }
            for p in patterns_list
        ]

        # Collect files to check
        files_to_check = []
        if file_path.is_file():
            files_to_check = [file_path]
        else:
            # Recursively find source files
            for ext in [".py", ".js", ".ts", ".java", ".go", ".rb", ".php"]:
                files_to_check.extend(file_path.rglob(f"*{ext}"))

        if not files_to_check:
            typer.echo("✓ No source files found to check", err=True)
            raise typer.Exit(0)

        typer.echo(f"🔍 Checking {len(files_to_check)} files...", err=True)

        # Pattern matching
        matcher = PatternMatcher()
        all_detections = []

        for file_path in files_to_check:
            try:
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                detections = matcher.match_in_code(code, patterns_dict, str(file_path))
                all_detections.extend(detections)
            except Exception as e:
                typer.echo(f"⚠️  Could not check {file_path}: {str(e)[:100]}", err=True)

        # Filter by severity if requested
        if severity:
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            min_severity_level = severity_order.get(severity.lower(), 0)
            all_detections = [
                d for d in all_detections
                if severity_order.get(d.severity.lower(), 0) >= min_severity_level
            ]

        # Display results
        if not all_detections:
            typer.echo("✓ No antipatterns detected!")
            raise typer.Exit(0)

        typer.echo(f"\n⚠️  Found {len(all_detections)} antipattern(s):\n")

        for detection in all_detections:
            typer.echo(f"• {detection.pattern_name} [{detection.severity.upper()}]")
            typer.echo(f"  File: {detection.file_path}:{detection.line_number}")
            typer.echo(f"  Code: {detection.match_text}")
            typer.echo(f"  Confidence: {int(detection.confidence * 100)}%")
            typer.echo()

        typer.echo(f"📋 Run 'membria antipattern evidence <pattern-id>' for details")
        raise typer.Exit(1)  # Exit with error to indicate issues found

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def evidence(
    pattern_id: str = typer.Argument(..., help="Pattern ID to get evidence for"),
) -> None:
    """Show evidence for a detected antipattern.

    Displays:
    - Industry statistics (removal rate, affected repos)
    - Team history with this pattern
    - Real-world examples from GitHub
    - Recommendations

    Args:
        pattern_id: Pattern ID (e.g., "custom_jwt")

    Examples:
        membria antipattern evidence custom_jwt
    """
    try:
        client = CodeDiggerClientSync()

        # Get pattern
        pattern = client.get_pattern_by_id(pattern_id)
        if not pattern:
            typer.echo(f"❌ Pattern not found: {pattern_id}", err=True)
            raise typer.Exit(1)

        # Get examples
        typer.echo(f"📦 Fetching examples for {pattern.name}...", err=True)
        occurrences = client.get_occurrences(pattern_id)

        # Aggregate evidence
        aggregator = EvidenceAggregator()
        evidence = aggregator.aggregate(pattern, occurrences)

        # Display
        display_text = aggregator.format_evidence_for_display(evidence)
        typer.echo(display_text)

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def list() -> None:
    """List all available antipatterns."""
    try:
        client = CodeDiggerClientSync()

        # Get patterns
        patterns = client.get_patterns()
        if not patterns:
            typer.echo("❌ Could not fetch patterns", err=True)
            raise typer.Exit(1)

        # Group by severity
        by_severity = {"critical": [], "high": [], "medium": [], "low": []}
        for p in patterns:
            severity = p.severity.lower()
            if severity in by_severity:
                by_severity[severity].append(p)

        typer.echo(f"\n📊 {len(patterns)} Antipatterns:\n")

        for severity in ["critical", "high", "medium", "low"]:
            patterns_at_level = by_severity[severity]
            if not patterns_at_level:
                continue

            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[severity]
            typer.echo(f"{icon} {severity.upper()} ({len(patterns_at_level)})")

            for p in patterns_at_level[:5]:  # Show top 5 per severity
                removal = int(p.removal_rate * 100)
                typer.echo(f"  • {p.pattern_id}: {p.name} ({removal}% removed)")

            if len(patterns_at_level) > 5:
                typer.echo(f"  ... and {len(patterns_at_level) - 5} more")

            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def search(
    keyword: str = typer.Argument(..., help="Keyword to search for"),
) -> None:
    """Search antipatterns by keyword.

    Args:
        keyword: Keyword to search for (e.g., "jwt", "crypto", "async")

    Examples:
        membria antipattern search jwt
    """
    try:
        client = CodeDiggerClientSync()

        # Search patterns
        matches = client.search_patterns(keyword)
        if not matches:
            typer.echo(f"No patterns found for '{keyword}'", err=True)
            raise typer.Exit(0)

        typer.echo(f"\n🔍 Found {len(matches)} patterns matching '{keyword}':\n")

        for p in matches:
            removal = int(p.removal_rate * 100)
            icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(p.severity.lower(), "⚪")

            typer.echo(f"{icon} {p.pattern_id}: {p.name}")
            typer.echo(f"   Severity: {p.severity} | Removed: {removal}%")
            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
