"""Anti-bias firewall: Block risky decisions before they become bugs."""

import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from membria.red_flags import RedFlagDetector, RedFlag, RedFlagSeverity

logger = logging.getLogger(__name__)


class FirewallDecision(str, Enum):
    """Firewall decision outcome."""
    ALLOW = "allow"
    WARN = "warn"  # Allow but show warnings
    BLOCK = "block"  # Force confirmation


@dataclass
class FirewallResult:
    """Result of firewall evaluation."""
    decision: FirewallDecision
    risk_score: float  # 0.0-1.0
    flags: List[RedFlag]
    message: str  # User-friendly message
    override_required: bool  # Is --force override needed?


class Firewall:
    """Anti-bias firewall for decisions.

    Responsibilities:
    - Detect red flags in decisions
    - Score risk level
    - Make allow/warn/block decisions
    - Provide evidence for decisions
    """

    def __init__(self):
        """Initialize firewall."""
        self.detector = RedFlagDetector()

    def evaluate(
        self,
        decision_statement: str,
        confidence: float,
        alternatives: Optional[List[str]] = None,
        antipatterns: Optional[List[str]] = None,
        time_pressure: bool = False,
    ) -> FirewallResult:
        """Evaluate a decision through the firewall.

        Args:
            decision_statement: What decision is being made
            confidence: Confidence level (0.0-1.0)
            alternatives: Alternatives considered
            antipatterns: Known antipatterns detected
            time_pressure: Under time pressure?

        Returns:
            FirewallResult with decision and evidence
        """
        # Detect red flags
        flags = self.detector.detect(
            decision_statement=decision_statement,
            confidence=confidence,
            alternatives=alternatives,
            antipatterns_detected=antipatterns,
            time_pressure=time_pressure,
        )

        # Calculate risk score
        risk_score = self.detector.calculate_risk_score(flags)

        # Make firewall decision
        if self.detector.should_block(flags):
            decision = FirewallDecision.BLOCK
            override_required = True
        elif self.detector.should_warn(flags):
            decision = FirewallDecision.WARN
            override_required = False
        else:
            decision = FirewallDecision.ALLOW
            override_required = False

        # Generate message
        message = self._generate_message(decision, flags, risk_score)

        return FirewallResult(
            decision=decision,
            risk_score=risk_score,
            flags=flags,
            message=message,
            override_required=override_required,
        )

    def _generate_message(
        self,
        decision: FirewallDecision,
        flags: List[RedFlag],
        risk_score: float,
    ) -> str:
        """Generate user-friendly message.

        Args:
            decision: Firewall decision
            flags: Detected flags
            risk_score: Risk score 0.0-1.0

        Returns:
            Message for user
        """
        lines = []

        # Header
        if decision == FirewallDecision.ALLOW:
            lines.append("✅ Decision looks good")
        elif decision == FirewallDecision.WARN:
            lines.append("⚠️  Warning: This decision has some risks")
        elif decision == FirewallDecision.BLOCK:
            lines.append("🚫 BLOCKED: This decision is too risky")

        # Risk score
        lines.append(f"\n📊 Risk Score: {int(risk_score * 100)}%")

        # Flags
        if flags:
            lines.append("\n🚩 Red Flags:")
            for flag in flags:
                icon = {
                    RedFlagSeverity.LOW: "🟢",
                    RedFlagSeverity.MEDIUM: "🟡",
                    RedFlagSeverity.HIGH: "🟠",
                    RedFlagSeverity.CRITICAL: "🔴",
                }[flag.severity]

                lines.append(f"  {icon} {flag.name}")
                lines.append(f"      {flag.evidence}")

        # Recommendations
        if flags:
            lines.append("\n💡 What to do:")
            for i, flag in enumerate(flags, 1):
                lines.append(f"  {i}. {flag.recommendation}")

        # Call to action
        if decision == FirewallDecision.BLOCK:
            lines.append(
                "\n🔐 To proceed anyway, use: --force --reason 'explanation'"
            )
        elif decision == FirewallDecision.WARN:
            lines.append("\n✓ You can proceed with: --force")

        return "\n".join(lines)

    def format_for_display(self, result: FirewallResult) -> str:
        """Format result for terminal display.

        Args:
            result: FirewallResult object

        Returns:
            Formatted string for display
        """
        return result.message
