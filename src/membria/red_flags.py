"""Red flag detection for risky decisions."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RedFlagSeverity(str, Enum):
    """Severity of red flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RedFlag:
    """A detected red flag in a decision."""
    flag_id: str
    name: str
    description: str
    severity: RedFlagSeverity
    evidence: str  # Why this flag was raised
    recommendation: str  # How to address it


class RedFlagDetector:
    """Detects red flags in decisions.

    Red flags indicate risky patterns:
    - Very low confidence (< 0.5) without alternatives
    - No alternatives considered
    - Known antipatterns mentioned
    - Overconfident language without evidence
    - Time pressure signals
    """

    def __init__(self):
        """Initialize detector."""
        pass

    def detect(
        self,
        decision_statement: str,
        confidence: float,
        alternatives: Optional[List[str]] = None,
        antipatterns_detected: Optional[List[str]] = None,
        time_pressure: bool = False,
    ) -> List[RedFlag]:
        """Detect red flags in a decision.

        Args:
            decision_statement: What decision is being made
            confidence: Confidence level (0.0-1.0)
            alternatives: Alternatives considered
            antipatterns_detected: Known antipatterns in the statement
            time_pressure: Whether under time pressure

        Returns:
            List of detected red flags
        """
        flags = []

        # Flag 1: Low confidence
        if confidence < 0.5:
            flags.append(self._flag_low_confidence(confidence, alternatives))

        # Flag 2: No alternatives considered
        if not alternatives or len(alternatives) < 2:
            flags.append(self._flag_no_alternatives())

        # Flag 3: Known antipattern
        if antipatterns_detected:
            for pattern in antipatterns_detected:
                flags.append(self._flag_antipattern(pattern))

        # Flag 4: Overconfident language
        if confidence > 0.85 and self._has_overconfident_language(decision_statement):
            flags.append(self._flag_overconfident_language())

        # Flag 5: Time pressure
        if time_pressure:
            flags.append(self._flag_time_pressure())

        return flags

    def _flag_low_confidence(
        self,
        confidence: float,
        alternatives: Optional[List[str]] = None,
    ) -> RedFlag:
        """Low confidence without alternatives."""
        has_alts = alternatives and len(alternatives) >= 2

        if has_alts:
            severity = RedFlagSeverity.LOW
            evidence = f"Confidence is {int(confidence * 100)}%, but alternatives exist"
            recommendation = "Proceed carefully - consider more exploration time"
        else:
            severity = RedFlagSeverity.CRITICAL
            evidence = f"Confidence is {int(confidence * 100)}% AND no alternatives considered"
            recommendation = "BLOCK: Generate alternatives first"

        return RedFlag(
            flag_id="low_confidence",
            name="Low Confidence Without Alternatives",
            description="Decision made with low confidence and no backup options",
            severity=severity,
            evidence=evidence,
            recommendation=recommendation,
        )

    def _flag_no_alternatives(self) -> RedFlag:
        """No alternatives considered."""
        return RedFlag(
            flag_id="no_alternatives",
            name="No Alternatives Considered",
            description="Only one option was evaluated",
            severity=RedFlagSeverity.MEDIUM,
            evidence="Zero alternatives listed",
            recommendation="Brainstorm at least 2-3 alternatives before deciding",
        )

    def _flag_antipattern(self, pattern_name: str) -> RedFlag:
        """Known antipattern mentioned."""
        return RedFlag(
            flag_id="antipattern_detected",
            name=f"Known Antipattern: {pattern_name}",
            description=f"Decision mentions '{pattern_name}' which is a known problematic pattern",
            severity=RedFlagSeverity.HIGH,
            evidence=f"'{pattern_name}' is removed in 80%+ of codebases",
            recommendation=f"Avoid this pattern. Use proven alternatives instead.",
        )

    def _flag_overconfident_language(self) -> RedFlag:
        """Overconfident language without evidence."""
        return RedFlag(
            flag_id="overconfident",
            name="Overconfident Language",
            description="Strong certainty claims without evidence",
            severity=RedFlagSeverity.MEDIUM,
            evidence="Words like 'definitely', 'obviously', 'always' used without qualification",
            recommendation="Add evidence or caveats. Be more precise about what you know.",
        )

    def _flag_time_pressure(self) -> RedFlag:
        """Time pressure signal."""
        return RedFlag(
            flag_id="time_pressure",
            name="Time Pressure Detected",
            description="Decision made under time constraints",
            severity=RedFlagSeverity.MEDIUM,
            evidence="Quick decision without proper analysis",
            recommendation="Slow down if possible. Take 10 minutes to reconsider.",
        )

    def _has_overconfident_language(self, statement: str) -> bool:
        """Check for overconfident language patterns."""
        overconfident_words = [
            "definitely", "obviously", "always", "never",
            "certainly", "absolutely", "100%", "guaranteed",
            "the best", "perfect", "foolproof", "unquestionably",
        ]

        statement_lower = statement.lower()
        for word in overconfident_words:
            if word in statement_lower:
                return True

        return False

    def calculate_risk_score(self, flags: List[RedFlag]) -> float:
        """Calculate overall risk score from flags.

        Args:
            flags: List of detected flags

        Returns:
            Risk score 0.0-1.0
        """
        if not flags:
            return 0.0

        # Weight by severity
        severity_weights = {
            RedFlagSeverity.LOW: 0.2,
            RedFlagSeverity.MEDIUM: 0.4,
            RedFlagSeverity.HIGH: 0.7,
            RedFlagSeverity.CRITICAL: 1.0,
        }

        total_weight = 0.0
        for flag in flags:
            total_weight += severity_weights.get(flag.severity, 0.0)

        # Normalize to 0-1 range
        # If we have 3 CRITICAL flags, score would be 3.0, so cap at 1.0
        return min(total_weight / 3.0, 1.0)

    def should_block(self, flags: List[RedFlag]) -> bool:
        """Determine if decision should be blocked.

        Args:
            flags: List of detected flags

        Returns:
            True if decision should be blocked
        """
        # Block if any CRITICAL flags
        for flag in flags:
            if flag.severity == RedFlagSeverity.CRITICAL:
                return True

        # Block if 2+ HIGH flags
        high_count = sum(1 for f in flags if f.severity == RedFlagSeverity.HIGH)
        if high_count >= 2:
            return True

        return False

    def should_warn(self, flags: List[RedFlag]) -> bool:
        """Determine if decision should warn.

        Args:
            flags: List of detected flags

        Returns:
            True if decision should warn (but allow with --force)
        """
        # Don't warn if blocked
        if self.should_block(flags):
            return False

        # Warn if 1+ HIGH or 2+ MEDIUM
        high_count = sum(1 for f in flags if f.severity == RedFlagSeverity.HIGH)
        medium_count = sum(1 for f in flags if f.severity == RedFlagSeverity.MEDIUM)

        return high_count >= 1 or medium_count >= 2
