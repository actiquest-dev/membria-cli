import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from membria.interactive.executor import AgentExecutor
from membria.interactive.providers import CompletionResponse
from membria.config import MembriaConfig, ConfigManager

@pytest.fixture
def mock_config_manager():
    sm = MagicMock(spec=ConfigManager)
    config = MembriaConfig()
    config.team = {
        "agents": {
            "architect": {
                "role": "architect", "provider": "openai", "model": "gpt-4o", "label": "Archie",
                "domain_scores": {"design": 0.9}
            },
            "implementer": {
                "role": "implementer", "provider": "openai", "model": "gpt-4o", "label": "Coder",
                "domain_scores": {"python": 0.95}
            },
            "reviewer": {"role": "reviewer", "provider": "openai", "model": "gpt-4o", "label": "Rev"}
        }
    }
    config.providers = {"openai": {"api_key_env": "OPENAI_API_KEY"}}
    config.orchestration = {"monitor_level": "L1"}
    sm.config = config
    return sm

@pytest.fixture
def mock_graph_client():
    client = MagicMock()
    client.is_connected = True
    client.query.return_value = [("topic1", "content1")]
    return client

@pytest.mark.asyncio
async def test_context_injection(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    mock_provider = AsyncMock()
    mock_provider.complete.return_value = CompletionResponse(content="OK", usage={})
    executor.agent_providers["implementer"] = mock_provider
    
    await executor.run_task("Help me with X", role="implementer")
    
    # Verify that the system message contains the context retrieved from graph
    call_args = mock_provider.complete.call_args[0]
    messages = call_args[1]
    system_msg = messages[0].content
    assert "CONTEXT FROM GRAPH" in system_msg
    assert "topic1: content1" in system_msg

@pytest.mark.asyncio
async def test_specialist_selection(mock_config_manager):
    executor = AgentExecutor(mock_config_manager)
    # python specialist should be implementer (score 0.95)
    role = executor._select_specialist("python")
    assert role == "implementer"
    
    # design specialist should be architect (score 0.9)
    role = executor._select_specialist("design")
    assert role == "architect"

@pytest.mark.asyncio
async def test_auto_routing_pipeline(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    
    # Mock completion for classification
    mock_provider = AsyncMock()
    mock_provider.complete.side_effect = [
        CompletionResponse(content="PIPELINE", usage={}), # Classifier
        CompletionResponse(content="Plan", usage={}),       # Architect Plan
        CompletionResponse(content="Code", usage={}),       # Implementer Code
        CompletionResponse(content="Review", usage={})     # Reviewer Review
    ]
    executor.agent_providers = {
        "architect": mock_provider,
        "implementer": mock_provider,
        "reviewer": mock_provider
    }
    
    result = await executor.run_orchestration("Complex task", mode="auto")
    assert "PROPOSED SOLUTION" in result
    # Check that the classifier prompt contains PIPELINE as an option
    first_call_messages = mock_provider.complete.call_args_list[0][0][1]
    assert "PIPELINE" in first_call_messages[1].content

@pytest.mark.asyncio
async def test_consensus_mode(mock_config_manager, mock_graph_client):
    executor = AgentExecutor(mock_config_manager, graph_client=mock_graph_client)
    
    mock_provider = AsyncMock()
    mock_provider.complete.side_effect = [
        CompletionResponse(content="Arch approach", usage={}),
        CompletionResponse(content="Impl approach", usage={}),
        CompletionResponse(content="Final synthesis", usage={})
    ]
    executor.agent_providers = {
        "architect": mock_provider,
        "implementer": mock_provider,
        "reviewer": mock_provider
    }
    
    result = await executor.run_orchestration("Design decision", mode="consensus")
    assert "CONSENSUS SOLUTION" in result
    assert "Arch approach" in result
    assert "Impl approach" in result
