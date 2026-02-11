"""Integration tests for safety commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_bias_detector_cmd():
    """Mock BiasDetector for safety commands."""
    with patch("membria.commands.safety.BiasDetector") as mock:
        detector_instance = MagicMock()
        mock.return_value = detector_instance
        detector_instance.analyze.return_value = MagicMock(
            detected_biases=["overconfidence"],
            risk_score=0.65,
            confidence_reality_gap=0.15,
            recommendations=["Sleep on it before finalizing"],
            severity="high",
        )
        yield mock


@pytest.fixture
def mock_graph_for_safety():
    """Mock GraphClient for safety commands."""
    with patch("membria.commands.safety.GraphClient") as mock:
        graph_instance = MagicMock()
        mock.return_value = graph_instance
        graph_instance.connect.return_value = True
        graph_instance.disconnect.return_value = None
        graph_instance.get_decisions.return_value = []
        yield mock


def test_safety_analyze_with_text(
    cli_runner: CliRunner,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test analyzing decision text directly."""
    result = cli_runner.invoke(app, [
        "safety", "analyze",
        "--text", "I'm definitely sure this will succeed"
    ])
    assert result.exit_code == 0
    assert "Bias Analysis" in result.stdout


def test_safety_analyze_with_decision_id(
    cli_runner: CliRunner,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test analyzing decision by ID."""
    mock_node = MagicMock()
    mock_node.properties = {
        "id": "dec_test123",
        "statement": "Use PostgreSQL",
        "alternatives": '["MongoDB", "SQLite"]',
        "confidence": "0.85",
    }
    mock_graph_for_safety.return_value.get_decisions.return_value = [[mock_node]]

    result = cli_runner.invoke(app, [
        "safety", "analyze",
        "--decision", "dec_test123"
    ])
    assert result.exit_code == 0


def test_safety_analyze_no_args(
    cli_runner: CliRunner,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test analyze without required arguments."""
    result = cli_runner.invoke(app, ["safety", "analyze"])
    assert result.exit_code != 0


def test_safety_analyze_not_found(
    cli_runner: CliRunner,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test analyzing nonexistent decision."""
    mock_graph_for_safety.return_value.get_decisions.return_value = []

    result = cli_runner.invoke(app, [
        "safety", "analyze",
        "--decision", "nonexistent"
    ])
    assert result.exit_code != 0


def test_safety_status(
    cli_runner: CliRunner,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test safety status."""
    result = cli_runner.invoke(app, ["safety", "status"])
    assert result.exit_code == 0
    assert "Safety Status" in result.stdout


def test_safety_status_with_decisions(
    cli_runner: CliRunner,
    sample_decision,
    mock_bias_detector_cmd: MagicMock,
    mock_graph_for_safety: MagicMock,
) -> None:
    """Test safety status with decisions."""
    mock_node = MagicMock()
    mock_node.properties = {
        "id": sample_decision.decision_id,
        "statement": sample_decision.statement,
        "confidence": str(sample_decision.confidence),
    }
    mock_graph_for_safety.return_value.get_decisions.return_value = [[mock_node]]

    result = cli_runner.invoke(app, ["safety", "status"])
    assert result.exit_code == 0
