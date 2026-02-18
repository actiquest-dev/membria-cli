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
    module: str  # "database", "auth", "api", "frontend", "backend"
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "claude-code"
    outcome: Optional[str] = None  # "success", "failure", "pending"
    resolved_at: Optional[datetime] = None
    actual_success_rate: Optional[float] = None
    engram_id: Optional[str] = None
    commit_sha: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Memory lifecycle metadata
    memory_type: Optional[str] = None  # episodic, semantic, procedural
    memory_subject: Optional[str] = None  # agent, user
    ttl_days: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    is_active: bool = True
    deprecated_reason: Optional[str] = None
    source: Optional[str] = None
    role_id: Optional[str] = None
    assignment_id: Optional[str] = None


@dataclass
class CodeChange:
    """Code change (commit) node in reasoning graph."""
    change_id: str
    commit_sha: str
    files_changed: List[str]
    timestamp: datetime
    author: str = "claude-code"
    decision_id: Optional[str] = None
    outcome: Optional[str] = None  # "success", "failure", "reverted"
    reverted_by: Optional[str] = None
    days_to_revert: Optional[int] = None
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class Outcome:
    """Outcome node tracking decision consequences."""
    outcome_id: str
    status: str  # "success", "failure", "partial"
    evidence: str = ""
    measured_at: datetime = field(default_factory=datetime.now)
    performance_impact: float = 1.0  # 1.0 = no impact, <1 = slower, >1 = faster
    reliability: float = 0.0  # 0-1
    maintenance_cost: float = 1.0  # Cost multiplier
    code_change_id: Optional[str] = None

    # Memory lifecycle metadata
    ttl_days: Optional[int] = None
    is_active: bool = True
    deprecated_reason: Optional[str] = None


@dataclass
class NegativeKnowledge:
    """Known failure or constraint."""
    nk_id: str
    hypothesis: str
    conclusion: str
    evidence: str
    domain: str  # "auth", "db", "api", etc.
    severity: str = "medium"  # "low", "medium", "high"
    discovered_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    blocks_pattern: Optional[str] = None
    recommendation: str = ""
    source: str = "analysis"
    # Memory lifecycle fields
    memory_type: Optional[str] = None  # "rule", "antipattern", "constraint", etc.
    memory_subject: Optional[str] = None  # domain or subsystem affected
    ttl_days: Optional[int] = None  # Time-to-live in days (None = permanent)
    last_verified_at: Optional[datetime] = None  # When this NK was last confirmed
    is_active: bool = True  # Whether this NK is still applicable
    deprecated_reason: Optional[str] = None  # Why it was deactivated


@dataclass
class Workspace:
    """Workspace container."""
    workspace_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Project:
    """Project inside workspace."""
    project_id: str
    name: str
    workspace_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Profile:
    """Execution profile (config)."""
    profile_id: str
    name: str
    config_path: str
    checksum: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    allowlist_path: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class Role:
    """Role / behavior profile."""
    role_id: str
    name: str
    description: Optional[str] = None
    prompt_path: Optional[str] = None  # Path to system prompt markdown file
    context_policy: Optional[dict] = None  # Dict of context configuration: {include_docshots, include_skills, include_nk, ...}


@dataclass
class Squad:
    """Task-specific team."""
    squad_id: str
    name: str
    strategy: str  # lead_review | parallel_arbiter | red_team
    project_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Assignment:
    """Role+Profile inside a squad."""
    assignment_id: str
    squad_id: str
    role_id: str
    profile_id: str
    order: int = 0
    weight: float = 1.0

    # Memory lifecycle metadata
    memory_type: Optional[str] = None  # episodic, semantic, procedural
    memory_subject: Optional[str] = None  # agent, user
    ttl_days: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    is_active: bool = True
    deprecated_reason: Optional[str] = None


@dataclass
class Antipattern:
    """Code pattern to avoid."""
    pattern_id: str
    name: str
    category: str
    severity: str  # "high", "medium", "low"
    repos_affected: int = 0
    occurrence_count: int = 0
    removal_rate: float = 0.0  # 0-1
    avg_days_to_removal: int = 0
    keywords: List[str] = field(default_factory=list)
    regex_pattern: str = ""
    example_bad: str = ""
    example_good: str = ""
    first_seen: datetime = field(default_factory=datetime.now)
    found_by: str = "detector"
    source: str = "analysis"
    recommendation: str = ""
