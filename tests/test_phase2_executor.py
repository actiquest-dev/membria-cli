import pytest
import asyncio
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from membria.interactive.executor import AgentExecutor
from membria.interactive.providers import CompletionResponse, Message
from membria.config import MembriaConfig, ConfigManager

@pytest.fixture
def mock_config_manager():
    sm = MagicMock(spec=ConfigManager)
    config = MembriaConfig()
    config.team = {
        "agents": {
            "architect": {"role": "architect", "provider": "openai", "model": "gpt-4o", "label": "Archie"},
            "implementer": {"role": "implementer", "provider": "openai", "model": "gpt-4o", "label": "Coder"}
        }
    }
    config.providers = {
        "openai": {"api_key_env": "OPENAI_API_KEY"}
    }
    config.orchestration = {
        "monitor_level": "L2",
        "firebreak_actions": ["delete", "drop"]
    }
    sm.config = config
    return sm

@pytest.fixture
def mock_graph_client():
    client = MagicMock()
    client.is_connected = True
    return client

@pytest.mark.asyncio
async def test_firebreak_approval(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    
    # Mock provider to avoid real API calls
    mock_provider = AsyncMock()
    executor.agent_providers["architect"] = mock_provider
    
    # Test task WITH firebreak keyword 'delete'
    with patch("rich.prompt.Confirm.ask", return_value=False) as mock_confirm:
        result = await executor.run_task("delete all records")
        assert result is None
        mock_confirm.assert_called_once()
        
    # Test task WITHOUT firebreak keyword
    mock_provider.complete.return_value = CompletionResponse(content="OK", usage={"total": 10})
    result = await executor.run_task("list all records")
    assert result == "OK"

@pytest.mark.asyncio
async def test_reputation_persistence(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    mock_provider = AsyncMock()
    mock_provider.complete.return_value = CompletionResponse(content="Done", usage={"input_tokens": 100, "output_tokens": 50})
    executor.agent_providers["architect"] = mock_provider
    
    await executor.run_task("Simple task")
    
    # Check if Cypher query was executed on mock_graph_client
    mock_graph_client.query.assert_called()
    call_args = mock_graph_client.query.call_args[0]
    assert "MERGE (a:Agent" in call_args[0]
    assert call_args[1]["role"] == "architect"

@pytest.mark.asyncio
async def test_orchestration_pipeline(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    
    # Mock multiple agent responses
    mock_arch = AsyncMock()
    mock_arch.complete.return_value = CompletionResponse(content="Plan: 1. X, 2. Y", usage={})
    
    mock_impl = AsyncMock()
    mock_impl.complete.return_value = CompletionResponse(content="Code: result", usage={})
    
    mock_rev = AsyncMock()
    mock_rev.complete.return_value = CompletionResponse(content="Review: LGTM", usage={})
    
    executor.agent_providers = {
        "architect": mock_arch,
        "implementer": mock_impl,
        "reviewer": mock_rev
    }
    
    # Mock the missing reviewer agent in config for this test
    executor.config_manager.config.team["agents"]["reviewer"] = {"provider": "openai", "model": "gpt-4o", "label": "Rev"}
    
    result = await executor.run_orchestration("Create a new module", mode="pipeline")
    
    assert "Code: result" in result
    assert "LGTM" in result
    assert mock_arch.complete.called
    assert mock_impl.complete.called
