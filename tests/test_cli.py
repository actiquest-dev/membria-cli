"""Integration tests for main CLI application."""

from typer.testing import CliRunner

from membria.cli import app


def test_cli_version(cli_runner: CliRunner) -> None:
    """Test --version flag."""
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "Membria CLI v" in result.stdout


def test_cli_help(cli_runner: CliRunner) -> None:
    """Test help command."""
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI-powered decision memory" in result.stdout


def test_cli_init(cli_runner: CliRunner) -> None:
    """Test init command."""
    result = cli_runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initializing Membria" in result.stdout


def test_cli_doctor(cli_runner: CliRunner) -> None:
    """Test doctor command."""
    result = cli_runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Membria Health Check" in result.stdout


def test_cli_invalid_command(cli_runner: CliRunner) -> None:
    """Test invalid command."""
    result = cli_runner.invoke(app, ["invalid_command"])
    assert result.exit_code == 2


def test_daemon_subcommand_help(cli_runner: CliRunner) -> None:
    """Test daemon subcommand help."""
    result = cli_runner.invoke(app, ["daemon", "--help"])
    assert result.exit_code == 0
    assert "Manage the Membria MCP daemon" in result.stdout


def test_decisions_subcommand_help(cli_runner: CliRunner) -> None:
    """Test decisions subcommand help."""
    result = cli_runner.invoke(app, ["decisions", "--help"])
    assert result.exit_code == 0
    assert "Manage decisions" in result.stdout


def test_engrams_subcommand_help(cli_runner: CliRunner) -> None:
    """Test engrams subcommand help."""
    result = cli_runner.invoke(app, ["engrams", "--help"])
    assert result.exit_code == 0
    assert "Manage" in result.stdout.lower() or "engram" in result.stdout.lower()


def test_stats_subcommand_help(cli_runner: CliRunner) -> None:
    """Test stats subcommand help."""
    result = cli_runner.invoke(app, ["stats", "--help"])
    assert result.exit_code == 0


def test_calibration_subcommand_help(cli_runner: CliRunner) -> None:
    """Test calibration subcommand help."""
    result = cli_runner.invoke(app, ["calibration", "--help"])
    assert result.exit_code == 0


def test_extractor_subcommand_help(cli_runner: CliRunner) -> None:
    """Test extractor subcommand help."""
    result = cli_runner.invoke(app, ["extractor", "--help"])
    assert result.exit_code == 0


def test_safety_subcommand_help(cli_runner: CliRunner) -> None:
    """Test safety subcommand help."""
    result = cli_runner.invoke(app, ["safety", "--help"])
    assert result.exit_code == 0
    assert "Cognitive safety and bias detection" in result.stdout
