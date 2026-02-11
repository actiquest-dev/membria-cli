"""Integration tests for stats commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_graph_for_stats():
    """Mock GraphClient for stats."""
    with patch("membria.commands.stats.GraphClient") as mock:
        graph_instance = MagicMock()
        mock.return_value = graph_instance
        graph_instance.connect.return_value = True
        graph_instance.get_decisions.return_value = []
        yield mock


def test_stats_show(cli_runner: CliRunner, mock_graph_for_stats: MagicMock) -> None:
    """Test showing stats."""
    result = cli_runner.invoke(app, ["stats", "show"])
    assert result.exit_code == 0


def test_stats_show_with_period(cli_runner: CliRunner, mock_graph_for_stats: MagicMock) -> None:
    """Test stats with period filter."""
    result = cli_runner.invoke(app, ["stats", "show", "--period", "7"])
    assert result.exit_code == 0


def test_stats_show_with_module(cli_runner: CliRunner, mock_graph_for_stats: MagicMock) -> None:
    """Test stats with module filter."""
    result = cli_runner.invoke(app, ["stats", "show", "--module", "database"])
    assert result.exit_code == 0


def test_stats_show_json_format(cli_runner: CliRunner, mock_graph_for_stats: MagicMock) -> None:
    """Test stats in JSON format."""
    result = cli_runner.invoke(app, ["stats", "show", "--format", "json"])
    assert result.exit_code == 0
