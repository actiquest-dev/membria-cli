"""Data models for Membria."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """Task classification from Claude Code."""
    TACTICAL = "tactical"
    DECISION = "decision"
    LEARNING = "learning"


class ToolCallType(str, Enum):
    """Types of tool calls in engrams."""
    READ_FILE = "read_file"
    GREP = "grep"
    WRITE_FILE = "write_file"
    GIT_OPERATION = "git_operation"
    GRAPH_QUERY = "graph_query"


@dataclass
class AgentInfo:
    """Information about the agent that created the session."""
    type: str  # "claude-code", "monty", etc.
    model: str  # "claude-sonnet-4-5-20250514"
    session_duration_sec: int
    total_tokens: int
    total_cost_usd: float


@dataclass
class TranscriptMessage:
    """Single message in a session transcript."""
    role: str  # "user", "assistant"
    content: str
    timestamp: datetime
    tool_calls: List[str] = field(default_factory=list)


@dataclass
class FileChange:
    """File modification during session."""
    path: str
    action: str  # "created", "modified", "deleted"
    lines_added: int
    lines_removed: int
    diff: Optional[str] = None


@dataclass
class MontyState:
    """Serialized Monty VM state for session resumption."""
    snapshot: bytes
    paused_at_function: Optional[str] = None
    pending_args: Optional[Dict[str, Any]] = None
    resumable: bool = True


@dataclass
class HypothesisEvaluation:
    """Reasoning trail: hypothesis evaluation."""
    hypothesis: str
    evidence_for: int
    evidence_against: int


@dataclass
class ContextWindowSnapshot:
    """What context was injected into the LLM."""
    injected_context: Dict[str, Any]
    context_influenced_outcome: bool


@dataclass
class ToolCallGraph:
    """Graph of tool calls and their consequences."""
    tool: str
    args: str
    led_to: str  # "decision_change", "alternative_discovered", etc.


@dataclass
class ConfidencePoint:
    """Confidence level at a point in time."""
    t: int  # time in seconds
    value: float  # 0-1
    trigger: str  # what caused this change


@dataclass
class EnergyCost:
    """Resource usage during session."""
    tokens_total: int
    monty_executions: int
    monty_total_time_us: int
    graph_queries: int
    files_read: int


@dataclass
class EngramSummary:
    """High-level summary of engram."""
    intent: str
    outcome: str
    learnings: str
    friction_points: List[str]
    open_items: List[str]


@dataclass
class Engram:
    """Complete agent session checkpoint."""
    engram_id: str
    session_id: str
    commit_sha: str
    branch: str
    timestamp: datetime

    # Agent information
    agent: AgentInfo

    # Session content
    transcript: List[TranscriptMessage]
    files_changed: List[FileChange]
    decisions_extracted: List[str]  # Decision IDs

    # Membria-specific enrichment
    membria_context_injected: bool
    antipatterns_triggered: List[str]

    # Runtime state
    monty_state: Optional[MontyState] = None
    reasoning_trail: List[HypothesisEvaluation] = field(default_factory=list)
    context_window_snapshot: Optional[ContextWindowSnapshot] = None
    tool_call_graph: List[ToolCallGraph] = field(default_factory=list)
    confidence_trajectory: List[ConfidencePoint] = field(default_factory=list)
    energy_cost: Optional[EnergyCost] = None
    summary: Optional[EngramSummary] = None


@dataclass
class Decision:
    """Decision node in reasoning graph."""
    decision_id: str
    statement: str
    alternatives: List[str]
    confidence: float
    outcome: Optional[str] = None  # "success", "failure", "pending"
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    module: Optional[str] = None
    engram_id: Optional[str] = None
    commit_sha: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NegativeKnowledge:
    """Known failure or constraint."""
    hypothesis: str
    evidence: str
    domain: str
    last_attempt: datetime
    severity: str = "medium"  # "low", "medium", "high"


@dataclass
class Antipattern:
    """Code pattern to avoid."""
    pattern_id: str
    name: str
    description: str
    prevalence: str  # "89% removed within 97 days"
    recommendation: str
    triggered_count: int = 0
