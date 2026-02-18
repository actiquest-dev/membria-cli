import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from membria.interactive.commands import CommandHandler
from membria.interactive.models import OrchestrationConfig
from membria.config import MembriaConfig, ConfigManager

@pytest.fixture
def mock_config_manager():
    cm = MagicMock(spec=ConfigManager)
    cm.config = MembriaConfig()
    cm.config.orchestration = {"monitor_level": "L1"}
    cm.save = MagicMock()
    return cm

@pytest.mark.asyncio
async def test_slash_help(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    with patch("membria.interactive.commands.console") as mock_console:
        result = await handler.handle_command("/help")
        assert result is True
        mock_console.print.assert_called()

@pytest.mark.asyncio
async def test_slash_status(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    with patch("membria.interactive.commands.console") as mock_console:
        with patch("membria.interactive.splash.show_status_panel") as mock_panel:
            result = await handler.handle_command("/status")
            assert result is True
            mock_panel.assert_called_once()

@pytest.mark.asyncio
async def test_slash_monitor(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    with patch("membria.interactive.commands.console") as mock_console:
        # Test valid level from DeepMind paper
        await handler.handle_command("/monitor L2")
        assert mock_config_manager.config.orchestration["monitor_level"] == "L2"
        mock_config_manager.save.assert_called()
        mock_console.print.assert_any_call("Monitoring level set to [bold magenta]L2[/bold magenta]")
        
        # Test invalid level
        mock_config_manager.save.reset_mock()
        await handler.handle_command("/monitor L99")
        mock_config_manager.save.assert_not_called()
        mock_console.print.assert_any_call("[red]Invalid level. Use L0, L1, L2, or L3.[/red]")

@pytest.mark.asyncio
async def test_slash_exit(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    result = await handler.handle_command("/exit")
    assert result is False

@pytest.mark.asyncio
async def test_slash_agents_stub(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    with patch("membria.interactive.commands.console") as mock_console:
        result = await handler.handle_command("/agents list")
        assert result is True
        mock_console.print.assert_called()  # "Not implemented" message

@pytest.mark.asyncio
async def test_unknown_command(mock_config_manager):
    handler = CommandHandler(mock_config_manager)
    with patch("membria.interactive.commands.console") as mock_console:
        result = await handler.handle_command("/foobar")
        assert result is True
        mock_console.print.assert_any_call("[red]Unknown command: /foobar[/red]")
