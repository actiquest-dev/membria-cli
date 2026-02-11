"""Integration tests for decisions commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_graph(mock_graph_client):
    """Patch GraphClient globally."""
    with patch("membria.commands.decisions.GraphClient") as mock:
        mock.return_value = mock_graph_client
        yield mock


def test_decisions_list_empty(cli_runner: CliRunner, mock_graph: MagicMock) -> None:
    """Test listing decisions when none exist."""
    mock_graph.return_value.get_decisions.return_value = []
    result = cli_runner.invoke(app, ["decisions", "list"])
    assert result.exit_code == 0
    assert "No decisions" in result.stdout or "decisions" in result.stdout.lower()


def test_decisions_list_with_data(cli_runner: CliRunner, sample_decision, mock_graph: MagicMock) -> None:
    """Test listing decisions with data."""
    mock_node = MagicMock()
    mock_node.properties = {
        "id": sample_decision.decision_id,
        "statement": sample_decision.statement,
        "confidence": str(sample_decision.confidence),
    }
    mock_graph.return_value.get_decisions.return_value = [[mock_node]]

    result = cli_runner.invoke(app, ["decisions", "list"])
    assert result.exit_code == 0


def test_decisions_show_success(cli_runner: CliRunner, sample_decision, mock_graph: MagicMock) -> None:
    """Test showing a specific decision."""
    mock_node = MagicMock()
    mock_node.properties = {
        "id": sample_decision.decision_id,
        "statement": sample_decision.statement,
        "alternatives": '["MongoDB", "SQLite"]',
        "confidence": str(sample_decision.confidence),
    }
    mock_graph.return_value.get_decisions.return_value = [[mock_node]]

    result = cli_runner.invoke(app, ["decisions", "show", sample_decision.decision_id])
    assert result.exit_code == 0


def test_decisions_show_not_found(cli_runner: CliRunner, mock_graph: MagicMock) -> None:
    """Test showing a decision that doesn't exist."""
    mock_graph.return_value.get_decisions.return_value = []

    result = cli_runner.invoke(app, ["decisions", "show", "nonexistent"])
    assert result.exit_code != 0


def test_decisions_record_success(cli_runner: CliRunner, mock_graph: MagicMock) -> None:
    """Test recording a new decision."""
    mock_graph.return_value.add_decision.return_value = True

    result = cli_runner.invoke(app, [
        "decisions", "record",
        "--statement", "Use PostgreSQL",
        "--alternatives", "MongoDB",
        "--alternatives", "SQLite",
        "--confidence", "0.85",
    ])
    assert result.exit_code == 0
    assert "success" in result.stdout.lower() or "recorded" in result.stdout.lower()


def test_decisions_record_invalid_confidence(cli_runner: CliRunner) -> None:
    """Test recording with invalid confidence."""
    result = cli_runner.invoke(app, [
        "decisions", "record",
        "--statement", "Use PostgreSQL",
        "--confidence", "1.5",
    ])
    assert result.exit_code != 0


def test_decisions_record_missing_statement(cli_runner: CliRunner) -> None:
    """Test recording without statement."""
    result = cli_runner.invoke(app, [
        "decisions", "record",
        "--confidence", "0.85",
    ])
    assert result.exit_code != 0
