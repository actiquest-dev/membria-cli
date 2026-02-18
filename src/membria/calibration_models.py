"""Beta distribution models for team calibration tracking.

Implements Bayesian calibration updates using conjugate Beta distributions.
Each domain has its own Beta(α, β) model tracking success/failure outcomes.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from datetime import datetime
import math


@dataclass
class BetaDistribution:
    """Beta distribution for domain calibration."""

    domain: str
    alpha: float = 1.0  # Successes + prior
    beta: float = 1.0  # Failures + prior
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def sample_size(self) -> int:
        """Total number of decisions observed."""
        return int(self.alpha + self.beta - 2)  # Subtract prior counts

    @property
    def mean(self) -> float:
        """Mean success rate: α/(α+β)."""
        if self.alpha + self.beta == 0:
            return 0.5
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Variance of the distribution."""
        total = self.alpha + self.beta
        if total <= 1:
            return 0.0
        return (self.alpha * self.beta) / (total * total * (total + 1))

    def update_success(self) -> None:
        """Record a successful outcome."""
        self.alpha += 1.0
        self.last_updated = datetime.now().isoformat()

    def update_failure(self) -> None:
        """Record a failed outcome."""
        self.beta += 1.0
        self.last_updated = datetime.now().isoformat()

    def confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate credible interval for success rate.

        Args:
            confidence: Credible level (default 0.95 for 95% CI)

        Returns:
            (lower_bound, upper_bound)
        """
        # Simplified: use normal approximation for large samples
        if self.sample_size < 3:
            return (0.0, 1.0)  # Insufficient data

        z = 1.96 if confidence == 0.95 else 2.576  # 99% CI
        margin = z * math.sqrt(self.variance)
        lower = max(0.0, self.mean - margin)
        upper = min(1.0, self.mean + margin)
        return (lower, upper)


@dataclass
class CalibrationProfile:
    """Calibration metrics for a single domain."""

    domain: str
    distribution: BetaDistribution
    confidence_gap: float = 0.0  # avg_confidence - actual_success_rate
    trend: str = "stable"  # "improving", "stable", "declining"
    recommendations: list = field(default_factory=list)
    last_evaluation: Optional[str] = None

    def should_adjust_confidence(self) -> bool:
        """Check if confidence adjustment is needed (gap > ±0.15)."""
        return abs(self.confidence_gap) > 0.15

    def get_adjustment(self) -> float:
        """Get confidence adjustment (-0.15 to 0.15).

        Negative = reduce confidence, Positive = increase confidence.
        """
        if abs(self.confidence_gap) <= 0.05:
            return 0.0  # Well-calibrated, no adjustment

        if self.confidence_gap > 0:  # Overconfident (gap > 0)
            return -0.15 if self.confidence_gap > 0.25 else -0.10
        else:  # Underconfident (gap < 0)
            return 0.10 if self.confidence_gap < -0.25 else 0.05

    def to_dict(self) -> dict:
        """Export as dictionary for storage."""
        return {
            "domain": self.domain,
            "alpha": self.distribution.alpha,
            "beta": self.distribution.beta,
            "sample_size": self.distribution.sample_size,
            "mean_success_rate": self.distribution.mean,
            "variance": self.distribution.variance,
            "confidence_gap": self.confidence_gap,
            "trend": self.trend,
            "recommendations": self.recommendations,
            "last_updated": self.distribution.last_updated,
            "last_evaluation": self.last_evaluation,
        }


class TeamCalibration:
    """Manages calibration profiles for all domains."""

    def __init__(self):
        """Initialize with empty calibrations."""
        self.calibrations: Dict[str, BetaDistribution] = {}
        self.created_at = datetime.now().isoformat()

    def get_or_create_domain(self, domain: str) -> BetaDistribution:
        """Get existing or create new domain calibration."""
        if domain not in self.calibrations:
            self.calibrations[domain] = BetaDistribution(domain=domain)
        return self.calibrations[domain]

    def update_from_outcome(
        self, domain: str, success: bool, score: float = 1.0
    ) -> None:
        """Update calibration from outcome.

        Args:
            domain: Decision domain
            success: Whether outcome was successful
            score: Outcome score (0-1, used for weighted updates)
        """
        dist = self.get_or_create_domain(domain)

        if success:
            dist.update_success()
        else:
            dist.update_failure()

    def get_confidence_adjustment(self, domain: str) -> float:
        """Get confidence adjustment for domain (-0.15 to 0.15)."""
        if domain not in self.calibrations:
            return 0.0

        dist = self.calibrations[domain]

        # Need actual confidence data to compute gap
        # This is a placeholder - actual implementation needs
        # average decision confidence from OutcomeTracker
        return 0.0

    def analyze_domain(self, domain: str) -> CalibrationProfile:
        """Analyze calibration for a domain."""
        dist = self.get_or_create_domain(domain)

        profile = CalibrationProfile(
            domain=domain,
            distribution=dist,
            confidence_gap=0.0,  # Would be computed from actual confidence
            trend=self._compute_trend(domain),
            last_evaluation=datetime.now().isoformat(),
        )

        return profile

    def _compute_trend(self, domain: str) -> str:
        """Compute trend: improving | stable | declining."""
        if domain not in self.calibrations:
            return "stable"

        dist = self.calibrations[domain]

        # Simple heuristic: if success rate improving, trend is improving
        if dist.mean >= 0.75:
            return "improving"
        elif dist.mean >= 0.5:
            return "stable"
        else:
            return "declining"

    def get_all_domains(self) -> Dict[str, BetaDistribution]:
        """Get all calibration distributions."""
        return self.calibrations.copy()

    def export_metrics(self) -> dict:
        """Export all metrics as dict."""
        return {
            "created_at": self.created_at,
            "domains": {
                domain: {
                    "alpha": dist.alpha,
                    "beta": dist.beta,
                    "sample_size": dist.sample_size,
                    "mean": dist.mean,
                    "variance": dist.variance,
                    "last_updated": dist.last_updated,
                }
                for domain, dist in self.calibrations.items()
            },
        }
