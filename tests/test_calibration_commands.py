"""Integration tests for calibration commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_graph_for_calibration():
    """Mock GraphClient for calibration."""
    with patch("membria.commands.calibration.GraphClient") as mock:
        graph_instance = MagicMock()
        mock.return_value = graph_instance
        graph_instance.connect.return_value = True
        graph_instance.get_decisions.return_value = []
        yield mock


def test_calibration_show(cli_runner: CliRunner, mock_graph_for_calibration: MagicMock) -> None:
    """Test showing calibration metrics."""
    result = cli_runner.invoke(app, ["calibration", "show"])
    assert result.exit_code == 0


def test_calibration_show_with_domain(cli_runner: CliRunner, mock_graph_for_calibration: MagicMock) -> None:
    """Test calibration with domain filter."""
    result = cli_runner.invoke(app, ["calibration", "show", "--domain", "database"])
    assert result.exit_code == 0


def test_calibration_show_json_format(cli_runner: CliRunner, mock_graph_for_calibration: MagicMock) -> None:
    """Test calibration in JSON format."""
    result = cli_runner.invoke(app, ["calibration", "show", "--format", "json"])
    assert result.exit_code == 0


def test_calibration_profile_no_data(cli_runner: CliRunner) -> None:
    """Test profile command with no data."""
    result = cli_runner.invoke(app, ["calibration", "profile", "unknown_domain"])
    assert result.exit_code == 0
    assert "No calibration data" in result.stdout


def test_calibration_profile_json_format(cli_runner: CliRunner) -> None:
    """Test profile command in JSON format."""
    result = cli_runner.invoke(app, ["calibration", "profile", "api", "--format", "json"])
    # Should exit cleanly even with no data
    assert result.exit_code == 0


def test_calibration_guidance_no_data(cli_runner: CliRunner) -> None:
    """Test guidance command with no data."""
    result = cli_runner.invoke(app, ["calibration", "guidance", "database"])
    assert result.exit_code == 0
    assert "No calibration data" in result.stdout


def test_calibration_guidance_with_confidence(cli_runner: CliRunner) -> None:
    """Test guidance command with confidence value."""
    result = cli_runner.invoke(app, ["calibration", "guidance", "auth", "--confidence", "0.75"])
    assert result.exit_code == 0


def test_calibration_all_profiles(cli_runner: CliRunner) -> None:
    """Test listing all calibration profiles."""
    result = cli_runner.invoke(app, ["calibration", "all"])
    assert result.exit_code == 0


def test_calibration_all_profiles_json(cli_runner: CliRunner) -> None:
    """Test listing all calibration profiles in JSON."""
    result = cli_runner.invoke(app, ["calibration", "all", "--format", "json"])
    assert result.exit_code == 0
