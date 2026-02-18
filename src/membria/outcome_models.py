"""Outcome tracking models and data structures."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OutcomeStatus(str, Enum):
    """Status of a decision outcome."""
    PENDING = "pending"  # Decision made, waiting for execution
    SUBMITTED = "submitted"  # Code submitted (PR created)
    MERGED = "merged"  # Code merged to main
    COMPLETED = "completed"  # Full outcome measured (30 days)
    FAILED = "failed"  # Decision didn't work out
    ABANDONED = "abandoned"  # Decision not pursued


class SignalType(str, Enum):
    """Type of outcome signal."""
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"
    CI_PASSED = "ci_passed"
    CI_FAILED = "ci_failed"
    TEST_FAILED = "test_failed"
    BUG_FOUND = "bug_found"
    INCIDENT = "incident"
    PERFORMANCE_OK = "performance_ok"
    PERFORMANCE_POOR = "performance_poor"
    STABILITY_OK = "stability_ok"
    STABILITY_POOR = "stability_poor"


class SignalValence(str, Enum):
    """How positive/negative a signal is."""
    POSITIVE = "positive"  # Good outcome
    NEGATIVE = "negative"  # Bad outcome
    NEUTRAL = "neutral"  # Informational


@dataclass
class Signal:
    """Single signal/event in outcome tracking."""

    signal_type: SignalType
    valence: SignalValence  # positive, negative, neutral
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""  # "PR #123 merged", "All tests pass", "P99 latency 45ms"
    severity: Optional[str] = None  # For negative signals: "low", "medium", "high"
    metrics: Dict[str, Any] = field(default_factory=dict)  # uptime, latency, throughput


@dataclass
class Outcome:
    """Complete outcome of a decision."""

    outcome_id: str
    decision_id: str
    status: OutcomeStatus

    # Timeline tracking
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    submitted_at: Optional[str] = None  # When PR created
    merged_at: Optional[str] = None  # When PR merged
    completed_at: Optional[str] = None  # When 30 days passed

    # Links
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    repo: Optional[str] = None

    # Signals
    signals: List[Signal] = field(default_factory=list)

    # Final evaluation
    final_status: Optional[str] = None  # "success", "partial", "failure"
    final_score: float = 0.5  # 0.0-1.0

    # Lessons learned
    lessons_learned: List[str] = field(default_factory=list)
    # ["Fastify handles 15k req/s (vs 10k assumed)",
    #  "Team learned it in 3 days (vs 1 week)"]

    # Performance metrics (measured after 30 days)
    metrics: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "uptime": 99.95,
    #   "avg_latency_ms": 45,
    #   "p99_latency_ms": 120,
    #   "throughput_rps": 12000,
    #   "bug_count": 2,
    #   "incident_count": 0,
    # }

    def add_signal(
        self,
        signal_type: SignalType,
        valence: SignalValence,
        description: str = "",
        severity: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a signal to the outcome.

        Args:
            signal_type: Type of signal
            valence: positive/negative/neutral
            description: Human-readable description
            severity: For negative signals
            metrics: Optional metrics dict
        """
        signal = Signal(
            signal_type=signal_type,
            valence=valence,
            description=description,
            severity=severity,
            metrics=metrics or {},
        )
        self.signals.append(signal)

    def has_negative_signals(self) -> bool:
        """Check if outcome has any negative signals.

        Returns:
            True if any signal is negative
        """
        return any(s.valence == SignalValence.NEGATIVE for s in self.signals)

    def positive_signal_count(self) -> int:
        """Count positive signals."""
        return sum(1 for s in self.signals if s.valence == SignalValence.POSITIVE)

    def negative_signal_count(self) -> int:
        """Count negative signals."""
        return sum(1 for s in self.signals if s.valence == SignalValence.NEGATIVE)

    def estimate_success(self) -> float:
        """Estimate success probability from signals.

        Returns:
            Score 0.0-1.0
        """
        if not self.signals:
            return 0.5

        positive = self.positive_signal_count()
        negative = self.negative_signal_count()
        total = len(self.signals)

        # Simple heuristic: positive signals increase score
        base_score = 0.5
        signal_score = (positive - negative) / max(total, 1) * 0.5

        return max(0.0, min(1.0, base_score + signal_score))


@dataclass
class AssumptionValidation:
    """Validation of a specific assumption."""

    assumption: str  # "Fastify handles 10k req/s"
    predicted_value: Optional[str] = None  # "10k req/s"
    actual_value: Optional[str] = None  # "12k req/s"
    status: str = "unvalidated"  # unvalidated, validated, failed, partially_validated
    evidence: str = ""  # "Measured throughput at peak: 12k/s"

    def validate(self, actual: str, matches: bool) -> None:
        """Mark assumption as validated.

        Args:
            actual: Actual measured value
            matches: Whether it matched expectation
        """
        self.actual_value = actual
        self.status = "validated" if matches else "failed"
        if matches:
            self.evidence = f"Confirmed: {actual}"
        else:
            self.evidence = f"Expected {self.predicted_value}, got {actual}"

    def partially_validate(self) -> None:
        """Mark assumption as partially validated."""
        self.status = "partially_validated"


@dataclass
class OutcomeMetrics:
    """Metrics measured for outcome evaluation."""

    uptime_percent: Optional[float] = None  # 99.9
    avg_latency_ms: Optional[float] = None  # 45
    p99_latency_ms: Optional[float] = None  # 120
    p95_latency_ms: Optional[float] = None  # 85
    throughput_rps: Optional[float] = None  # 12000
    error_rate_percent: Optional[float] = None  # 0.1
    bug_count: Optional[int] = None  # 0
    incident_count: Optional[int] = None  # 0
    performance_degradation_percent: Optional[float] = None  # -5 (negative = improvement)

    def is_good(self) -> bool:
        """Heuristic: is outcome good?

        Returns:
            True if metrics look healthy
        """
        checks = []

        if self.uptime_percent is not None:
            checks.append(self.uptime_percent >= 99.0)
        if self.error_rate_percent is not None:
            checks.append(self.error_rate_percent < 1.0)
        if self.bug_count is not None:
            checks.append(self.bug_count <= 2)
        if self.incident_count is not None:
            checks.append(self.incident_count == 0)

        if not checks:
            return True  # No metrics to evaluate

        return all(checks)
