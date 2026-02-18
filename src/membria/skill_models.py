"""Skill Generator Data Models - Procedural Knowledge from Outcomes

Defines data structures for:
- Patterns extracted from decision outcomes
- Skills generated from patterns
- Behavior chains for context injection
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class Pattern:
    """Pattern extracted from decision outcomes.

    Represents a recurring decision option with its success rate
    across multiple observations.
    """

    statement: str  # "PostgreSQL", "Auth0", etc.
    success_rate: float  # 0.89 (successes / total)
    sample_size: int  # Number of decisions observed
    supporting_decisions: List[str]  # [dec-001, dec-005, ...]

    def __post_init__(self):
        if not 0 <= self.success_rate <= 1:
            raise ValueError(f"Success rate must be 0-1, got {self.success_rate}")
        if self.sample_size < 1:
            raise ValueError(f"Sample size must be ≥1, got {self.sample_size}")


@dataclass
class BehaviorChainOutput:
    """Output from a single behavior chain."""

    chain_name: str  # "positive_precedent", "negative_evidence", etc.
    content: str  # Markdown content
    triggered: bool = False  # Whether chain produced meaningful output
    priority: int = 0  # 0-10, higher = more important


@dataclass
class Skill:
    """Skill - Procedural knowledge generated from outcomes.

    Represents a decision-making procedure learned from team experience.
    Based on Beta distribution calibration and pattern analysis.
    """

    # Identity
    skill_id: str  # sk-database_strategy-v2
    domain: str  # database, auth, api, etc.
    name: str  # "database_strategy_recommendation"
    version: int  # 2

    # Evidence
    success_rate: float  # 0.89
    confidence: float  # From Beta distribution
    sample_size: int  # Number of decisions observed

    # Content
    procedure: str  # Markdown with decision procedure

    # Applicability zones
    green_zone: List[str] = field(default_factory=list)  # Use confidently (>75% success)
    yellow_zone: List[str] = field(default_factory=list)  # Review carefully (50-75%)
    red_zone: List[str] = field(default_factory=list)  # Avoid (<50% success)

    # Metadata
    created_at: int = 0  # Unix timestamp
    last_updated: int = 0  # Unix timestamp
    next_review: int = 0  # When to regenerate
    ttl_days: Optional[int] = None  # When to deprecate if no updates

    # Quality
    quality_score: float = 0.5  # 0-1 (success_rate * (1 - 1/sqrt(sample_size)))
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 1.0

    # Links
    generated_from_decisions: List[str] = field(default_factory=list)  # Decision IDs
    conflicts_with: List[str] = field(default_factory=list)  # Skill IDs
    related_skills: List[str] = field(default_factory=list)

    # Deprecation
    is_active: bool = True
    deprecated_reason: Optional[str] = None

    def __post_init__(self):
        """Validate skill data."""
        if not 0 <= self.success_rate <= 1:
            raise ValueError(f"Success rate must be 0-1, got {self.success_rate}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")
        if not 0 <= self.quality_score <= 1:
            raise ValueError(f"Quality score must be 0-1, got {self.quality_score}")
        if self.sample_size < 1:
            raise ValueError(f"Sample size must be ≥1, got {self.sample_size}")


@dataclass
class SkillMetrics:
    """Metrics about skills in a domain."""

    domain: str
    total_skills: int
    active_skills: int
    avg_quality_score: float
    avg_success_rate: float
    skills_by_quality: Dict[str, int]  # "high": 5, "medium": 3, "low": 1
    last_generated: Optional[int] = None  # Unix timestamp
    skills_to_regenerate: List[str] = field(default_factory=list)  # Skill IDs due for review


@dataclass
class SkillComparison:
    """Comparison between two skill versions."""

    skill_id: str
    old_version: int
    new_version: int

    # Changes
    success_rate_delta: float  # new - old (can be negative)
    sample_size_delta: int  # new - old
    quality_score_delta: float  # new - old

    # Procedure changes
    new_recommendations: List[str]  # New items in green zone
    removed_recommendations: List[str]  # Items moved out of green zone

    is_improvement: bool = False
    reason: str = ""  # Why skill was regenerated

    def __post_init__(self):
        """Determine if regeneration is an improvement."""
        self.is_improvement = (
            self.success_rate_delta >= -0.05 and
            self.sample_size_delta >= 5
        )
