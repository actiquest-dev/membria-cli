"""Pytest configuration and fixtures for CLI tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from membria.cli import app
from membria.config import ConfigManager
from membria.models import Decision, Engram, AgentInfo, FileChange, TranscriptMessage
from datetime import datetime


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer test runner."""
    return CliRunner()


@pytest.fixture
def temp_membria_dir():
    """Create a temporary Membria config directory."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / ".membria"
    config_dir.mkdir(parents=True, exist_ok=True)

    yield config_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config(temp_membria_dir, monkeypatch):
    """Mock ConfigManager to use temp directory."""
    def mock_home():
        return temp_membria_dir.parent

    monkeypatch.setattr("pathlib.Path.home", mock_home)
    return ConfigManager()


@pytest.fixture
def mock_graph_client():
    """Mock GraphClient for testing."""
    mock = MagicMock()
    mock.connect.return_value = True
    mock.disconnect.return_value = None
    mock.health_check.return_value = {"status": "healthy"}
    mock.get_decisions.return_value = []
    mock.add_decision.return_value = True
    return mock


@pytest.fixture
def sample_decision():
    """Create a sample decision for testing."""
    return Decision(
        decision_id="dec_test123",
        statement="Use PostgreSQL instead of MongoDB",
        alternatives=["MongoDB", "SQLite"],
        confidence=0.85,
        module="database",
    )


@pytest.fixture
def sample_engram():
    """Create a sample engram for testing."""
    return Engram(
        engram_id="eng_test123",
        session_id="sess_test123",
        commit_sha="abc1234567890",
        branch="main",
        timestamp=datetime.now(),
        agent=AgentInfo(
            type="claude-code",
            model="claude-sonnet-4-5-20250514",
            session_duration_sec=300,
            total_tokens=5000,
            total_cost_usd=0.05,
        ),
        transcript=[
            TranscriptMessage(
                role="user",
                content="Test message",
                timestamp=datetime.now(),
            )
        ],
        files_changed=[
            FileChange(path="test.py", action="modified", lines_added=5, lines_removed=2)
        ],
        decisions_extracted=[],
        membria_context_injected=True,
        antipatterns_triggered=[],
    )


@pytest.fixture
def mock_bias_detector():
    """Mock BiasDetector for testing."""
    mock = MagicMock()
    mock.analyze.return_value = MagicMock(
        detected_biases=["overconfidence"],
        risk_score=0.65,
        confidence_reality_gap=0.15,
        recommendations=["Sleep on it before finalizing"],
        severity="high",
    )
    return mock


@pytest.fixture
def mock_signal_detector():
    """Mock SignalDetector for testing."""
    mock = MagicMock()
    mock.get_pending_signals.return_value = [
        {
            "signal_id": "sig_1",
            "text": "I recommend using PostgreSQL",
            "module": "database",
            "status": "pending",
        }
    ]
    return mock


@pytest.fixture
def mock_haiku_extractor():
    """Mock HaikuExtractor for testing."""
    mock = MagicMock()
    mock.batch_extract.return_value = [
        {
            "signal_id": "sig_1",
            "decision_statement": "Use PostgreSQL for data persistence",
            "alternatives": ["MongoDB", "SQLite"],
            "confidence": 0.8,
            "module": "database",
        }
    ]
    return mock
