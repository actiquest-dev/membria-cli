"""Integration tests for extractor commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_signal_detector_cmd():
    """Mock SignalDetector for extractor commands."""
    with patch("membria.commands.extractor.SignalDetector") as mock:
        detector_instance = MagicMock()
        mock.return_value = detector_instance
        detector_instance.get_pending_signals.return_value = []
        yield mock


@pytest.fixture
def mock_haiku_extractor_cmd():
    """Mock HaikuExtractor for extractor commands."""
    with patch("membria.commands.extractor.HaikuExtractor") as mock:
        extractor_instance = MagicMock()
        mock.return_value = extractor_instance
        extractor_instance.batch_extract.return_value = []
        yield mock


def test_extractor_status(cli_runner: CliRunner, mock_signal_detector_cmd: MagicMock) -> None:
    """Test extractor status."""
    result = cli_runner.invoke(app, ["extractor", "status"])
    assert result.exit_code == 0


def test_extractor_log(cli_runner: CliRunner, mock_signal_detector_cmd: MagicMock) -> None:
    """Test extractor logs."""
    result = cli_runner.invoke(app, ["extractor", "log", "--pending"])
    assert result.exit_code == 0


def test_extractor_log_with_limit(cli_runner: CliRunner, mock_signal_detector_cmd: MagicMock) -> None:
    """Test extractor logs with limit."""
    result = cli_runner.invoke(app, ["extractor", "log", "--limit", "20"])
    assert result.exit_code == 0


def test_extractor_run_level2(
    cli_runner: CliRunner,
    mock_signal_detector_cmd: MagicMock,
    mock_haiku_extractor_cmd: MagicMock,
) -> None:
    """Test running Level 2 extraction (without Haiku)."""
    result = cli_runner.invoke(app, ["extractor", "run"])
    assert result.exit_code == 0


def test_extractor_run_level3(
    cli_runner: CliRunner,
    mock_signal_detector_cmd: MagicMock,
    mock_haiku_extractor_cmd: MagicMock,
) -> None:
    """Test running Level 3 extraction (with Haiku)."""
    result = cli_runner.invoke(app, ["extractor", "run", "--level3"])
    assert result.exit_code == 0


def test_extractor_run_dry_run(
    cli_runner: CliRunner,
    mock_signal_detector_cmd: MagicMock,
    mock_haiku_extractor_cmd: MagicMock,
) -> None:
    """Test dry-run mode."""
    result = cli_runner.invoke(app, ["extractor", "run", "--dry-run"])
    assert result.exit_code == 0
