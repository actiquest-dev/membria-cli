from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ModelInfo(BaseModel):
    """Information about a specific LLM model."""
    id: str
    name: str
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0

class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    name: str
    api_key_env: str
    endpoint: Optional[str] = None
    models: List[ModelInfo] = Field(default_factory=list)

class AgentConfig(BaseModel):
    """Configuration for a specific agent role."""
    role: str           # architect, senior, junior, reviewer, debugger
    provider: str
    model: str
    label: str
    strengths: List[str] = Field(default_factory=list)
    on_demand: bool = False
    cost_priority: bool = False
    
    # DeepMind: Reputation & Performance Ledger
    # Tracks agent performance over time for intelligent delegation
    tasks_completed: int = 0
    tasks_succeeded: int = 0
    avg_cost: float = 0.0
    domain_scores: Dict[str, float] = Field(default_factory=dict)  # e.g., {"python": 0.85, "react": 0.4}

class TeamConfig(BaseModel):
    """Configuration for the agent team."""
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)

class OrchestrationConfig(BaseModel):
    """Configuration for multi-agent orchestration."""
    default_mode: str = "pipeline"
    auto_apply: bool = False
    max_parallel: int = 4
    timeout: int = 120
    cost_limit: float = 5.0
    prefer_cheap: bool = True
    
    # DeepMind: Monitoring & Safety
    # L0=heartbeat, L1=step-by-step, L2=CoT trace, L3=full state
    monitor_level: str = "L1"
    # Actions that require mandatory human approval (liability firebreaks)
    firebreak_actions: List[str] = ["delete", "deploy", "migrate", "drop"]
