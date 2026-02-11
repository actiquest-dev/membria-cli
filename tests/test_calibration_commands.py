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
