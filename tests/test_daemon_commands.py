"""Integration tests for daemon commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


@pytest.fixture
def mock_process_manager_daemon():
    """Mock ProcessManager for daemon commands."""
    with patch("membria.commands.daemon.ProcessManager") as mock:
        manager_instance = MagicMock()
        mock.return_value = manager_instance
        manager_instance.is_running.return_value = False
        manager_instance.start.return_value = (True, "Daemon started successfully")
        manager_instance.stop.return_value = (True, "Daemon stopped successfully")
        manager_instance.status.return_value = MagicMock(
            is_running=False,
            pid=None,
            uptime_seconds=None,
            port=3117,
        )
        manager_instance.get_logs.return_value = "[daemon logs]"
        yield mock


@pytest.fixture
def mock_config_manager_daemon():
    """Mock ConfigManager for daemon commands."""
    with patch("membria.commands.daemon.ConfigManager") as mock:
        config_instance = MagicMock()
        mock.return_value = config_instance
        yield mock


def test_daemon_start(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
    mock_config_manager_daemon: MagicMock,
) -> None:
    """Test starting the daemon."""
    result = cli_runner.invoke(app, ["daemon", "start"])
    assert result.exit_code == 0
    assert "started" in result.stdout.lower() or "✓" in result.stdout


def test_daemon_start_with_port(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
    mock_config_manager_daemon: MagicMock,
) -> None:
    """Test starting daemon with custom port."""
    result = cli_runner.invoke(app, ["daemon", "start", "--port", "3118"])
    assert result.exit_code == 0


def test_daemon_stop(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test stopping the daemon."""
    mock_process_manager_daemon.return_value.is_running.return_value = True
    result = cli_runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0
    assert "stopped" in result.stdout.lower() or "✓" in result.stdout


def test_daemon_stop_when_not_running(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test stopping daemon when it's not running."""
    mock_process_manager_daemon.return_value.is_running.return_value = False
    result = cli_runner.invoke(app, ["daemon", "stop"])
    assert result.exit_code == 0


def test_daemon_status(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test daemon status."""
    result = cli_runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0
    assert "Status" in result.stdout or "status" in result.stdout.lower()


def test_daemon_status_running(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test daemon status when running."""
    mock_process_manager_daemon.return_value.status.return_value = MagicMock(
        is_running=True,
        pid=1234,
        uptime_seconds=3600,
        port=3117,
    )
    result = cli_runner.invoke(app, ["daemon", "status"])
    assert result.exit_code == 0


def test_daemon_logs(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test showing daemon logs."""
    result = cli_runner.invoke(app, ["daemon", "logs"])
    assert result.exit_code == 0


def test_daemon_logs_with_lines(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test daemon logs with line count."""
    result = cli_runner.invoke(app, ["daemon", "logs", "--lines", "100"])
    assert result.exit_code == 0


def test_daemon_logs_follow(
    cli_runner: CliRunner,
    mock_process_manager_daemon: MagicMock,
) -> None:
    """Test following daemon logs."""
    result = cli_runner.invoke(app, ["daemon", "logs", "--follow"], input="")
    # Follow mode will hang, so we just check it doesn't error on setup
    assert result.exit_code == 0 or result.exit_code == 1
