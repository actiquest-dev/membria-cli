"""Memory policy: scoring, freshness, and forgetting rules."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import exp
from typing import Optional


@dataclass
class MemoryPolicy:
    """Policy rules for memory lifecycle."""

    default_ttl_days: int = 365
    min_confidence: float = 0.2
    half_life_days: int = 180
    allow_hard_delete: bool = False
    ttl_by_type: dict = field(default_factory=lambda: {
        "episodic": 180,
        "semantic": 365,
        "procedural": 720,
    })

    def get_ttl(self, memory_type: Optional[str]) -> int:
        if memory_type and memory_type in self.ttl_by_type:
            return self.ttl_by_type[memory_type]
        return self.default_ttl_days

    def freshness(self, created_at_ts: int, ttl_days: Optional[int] = None) -> float:
        ttl = ttl_days or self.default_ttl_days
        age_days = max(0, (datetime.utcnow() - datetime.utcfromtimestamp(created_at_ts)).days)
        if age_days >= ttl:
            return 0.0
        half_life = max(1, self.half_life_days)
        return exp(-age_days / half_life)

    def should_forget(self, created_at_ts: int, ttl_days: Optional[int] = None) -> bool:
        ttl = ttl_days or self.default_ttl_days
        age_days = max(0, (datetime.utcnow() - datetime.utcfromtimestamp(created_at_ts)).days)
        return age_days >= ttl

    def score(self, relevance: float, confidence: float, freshness: float, impact: float) -> float:
        rel = max(0.0, min(1.0, relevance))
        conf = max(0.0, min(1.0, confidence))
        imp = max(0.0, min(1.0, impact))
        return rel * conf * freshness * (0.5 + 0.5 * imp)
