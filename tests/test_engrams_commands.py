"""Integration tests for engrams commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_engram_storage():
    """Mock EngramStorage for testing."""
    with patch("membria.commands.engrams.EngramStorage") as mock:
        storage_instance = MagicMock()
        mock.return_value = storage_instance
        yield mock


@pytest.fixture
def mock_process_manager():
    """Mock ProcessManager for testing."""
    with patch("membria.commands.engrams.ProcessManager") as mock:
        manager_instance = MagicMock()
        mock.return_value = manager_instance
        yield mock


def test_engrams_list_empty(cli_runner: CliRunner, mock_engram_storage: MagicMock) -> None:
    """Test listing engrams when none exist."""
    mock_engram_storage.return_value.list_engrams.return_value = []
    result = cli_runner.invoke(app, ["engrams", "list"])
    assert result.exit_code == 0


def test_engrams_list_with_data(cli_runner: CliRunner, sample_engram, mock_engram_storage: MagicMock) -> None:
    """Test listing engrams with data."""
    engram_dict = {
        "engram_id": sample_engram.engram_id,
        "agent": {"type": "claude-code"},
        "session_id": sample_engram.session_id,
        "timestamp": "2026-02-11T00:00:00",
    }
    mock_engram_storage.return_value.list_engrams.return_value = [engram_dict]

    result = cli_runner.invoke(app, ["engrams", "list"])
    assert result.exit_code == 0


def test_engrams_show_success(cli_runner: CliRunner, sample_engram, mock_engram_storage: MagicMock) -> None:
    """Test showing a specific engram."""
    engram_dict = {
        "engram_id": sample_engram.engram_id,
        "session_id": sample_engram.session_id,
        "timestamp": str(sample_engram.timestamp),
    }
    mock_engram_storage.return_value.load_engram.return_value = engram_dict

    result = cli_runner.invoke(app, ["engrams", "show", sample_engram.engram_id])
    assert result.exit_code == 0


def test_engrams_show_not_found(cli_runner: CliRunner, mock_engram_storage: MagicMock) -> None:
    """Test showing an engram that doesn't exist."""
    mock_engram_storage.return_value.load_engram.return_value = None

    result = cli_runner.invoke(app, ["engrams", "show", "nonexistent"])
    assert result.exit_code != 0


def test_engrams_enable(cli_runner: CliRunner, mock_engram_storage: MagicMock) -> None:
    """Test enabling git hooks."""
    mock_engram_storage.return_value.ensure_branch.return_value = True

    result = cli_runner.invoke(app, ["engrams", "enable"])
    assert result.exit_code == 0


def test_engrams_disable(cli_runner: CliRunner, mock_engram_storage: MagicMock) -> None:
    """Test disabling git hooks."""
    result = cli_runner.invoke(app, ["engrams", "disable"])
    assert result.exit_code == 0


def test_engrams_list_format_json(cli_runner: CliRunner, sample_engram, mock_engram_storage: MagicMock) -> None:
    """Test listing engrams with output."""
    engram_dict = {
        "engram_id": sample_engram.engram_id,
        "agent": {"type": "claude-code"},
        "session_id": sample_engram.session_id,
        "timestamp": "2026-02-11T00:00:00",
    }
    mock_engram_storage.return_value.list_engrams.return_value = [engram_dict]

    result = cli_runner.invoke(app, ["engrams", "list"])
    assert result.exit_code == 0
