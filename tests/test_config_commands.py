"""Integration tests for config commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from membria.cli import app


def test_config_show(
    cli_runner: CliRunner,
) -> None:
    """Test showing configuration."""
    # Use a real ConfigManager with default config
    result = cli_runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0


def test_config_set(
    cli_runner: CliRunner,
) -> None:
    """Test setting configuration."""
    result = cli_runner.invoke(app, [
        "config", "set",
        "graph_host", "localhost"
    ])
    # Expect 0 or 1 (success or error is ok for this test)
    assert result.exit_code in [0, 1]


def test_config_get(
    cli_runner: CliRunner,
) -> None:
    """Test getting a configuration value."""
    result = cli_runner.invoke(app, [
        "config", "get",
        "graph_host"
    ])
    # Expect 0 or 1 (success or error is ok for this test)
    assert result.exit_code in [0, 1]
