"""Decision Capture: Record decisions with full context."""

import logging
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class DecisionCapture:
    """Full decision record with context."""

    # Core decision
    decision_id: str  # Unique ID
    statement: str  # What decision is being made
    confidence: float  # 0.0-1.0

    # Alternatives
    alternatives: List[str] = field(default_factory=list)
    alternatives_with_reasons: Dict[str, str] = field(default_factory=dict)
    # {
    #   "Express.js": "Slower but proven",
    #   "Fastify": "Faster, team inexperienced",
    # }

    # Assumptions
    assumptions: List[str] = field(default_factory=list)
    # [
    #   "Fastify can handle 10k req/s",
    #   "Team can learn it in 1 week",
    # ]

    # Predicted outcome
    predicted_outcome: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "description": "Stable API in 2 weeks",
    #   "success_criteria": [
    #     "Handles 10k req/s",
    #     "No critical bugs in 30 days"
    #   ],
    #   "risk_level": "medium"
    # }

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "unknown"
    module: str = "unknown"  # Service/module affected
    context_hash: str = ""  # SHA256 of decision context

    # Status tracking
    status: str = "pending"  # pending | executed | completed | failed
    linked_pr: Optional[str] = None  # GitHub PR URL
    linked_commit: Optional[str] = None  # Commit SHA

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def calculate_context_hash(self) -> str:
        """Calculate hash of decision context (immutable).

        Includes: statement, alternatives, assumptions, predicted_outcome
        """
        context = {
            "statement": self.statement,
            "alternatives": sorted(self.alternatives),
            "assumptions": sorted(self.assumptions),
            "predicted_outcome": self.predicted_outcome,
        }
        context_str = json.dumps(context, sort_keys=True)
        self.context_hash = hashlib.sha256(context_str.encode()).hexdigest()
        return self.context_hash


class DecisionCaptureFlow:
    """Interactive workflow for capturing decisions."""

    def __init__(self, decision_id: str, statement: str, confidence: float):
        """Initialize capture flow.

        Args:
            decision_id: Unique decision ID
            statement: Decision statement
            confidence: Initial confidence estimate
        """
        self.decision = DecisionCapture(
            decision_id=decision_id,
            statement=statement,
            confidence=confidence,
        )

    def capture_alternatives(self, alternatives: List[str], reasons: Optional[Dict[str, str]] = None) -> None:
        """Record alternatives being considered.

        Args:
            alternatives: List of alternative approaches
            reasons: Optional {alternative: reason} mapping
        """
        self.decision.alternatives = alternatives
        if reasons:
            self.decision.alternatives_with_reasons = reasons
        else:
            # Auto-generate empty reasons
            self.decision.alternatives_with_reasons = {
                alt: "Consider..." for alt in alternatives
            }
        logger.debug(f"Recorded {len(alternatives)} alternatives")

    def capture_assumptions(self, assumptions: List[str]) -> None:
        """Record assumptions being made.

        Args:
            assumptions: List of assumptions
        """
        self.decision.assumptions = assumptions
        logger.debug(f"Recorded {len(assumptions)} assumptions")

    def capture_predicted_outcome(
        self,
        description: str,
        success_criteria: List[str],
        risk_level: str = "medium",
    ) -> None:
        """Record predicted outcome and success criteria.

        Args:
            description: Expected outcome description
            success_criteria: List of success criteria
            risk_level: "low", "medium", "high", "critical"
        """
        self.decision.predicted_outcome = {
            "description": description,
            "success_criteria": success_criteria,
            "risk_level": risk_level,
        }
        logger.debug(f"Recorded predicted outcome: {description}")

    def set_metadata(
        self,
        created_by: Optional[str] = None,
        module: Optional[str] = None,
    ) -> None:
        """Set decision metadata.

        Args:
            created_by: User who made decision
            module: Affected module/service
        """
        if created_by:
            self.decision.created_by = created_by
        if module:
            self.decision.module = module

    def finalize(self) -> DecisionCapture:
        """Finalize decision capture.

        Calculates context hash and returns decision.

        Returns:
            Final DecisionCapture object
        """
        self.decision.calculate_context_hash()
        self.decision.status = "pending"
        logger.info(f"Decision {self.decision.decision_id} captured with hash {self.decision.context_hash[:8]}")
        return self.decision

    def validate(self) -> tuple[bool, str]:
        """Validate captured decision is complete.

        Returns:
            (is_valid, error_message)
        """
        if not self.decision.statement:
            return False, "Statement is required"

        if not (0.0 <= self.decision.confidence <= 1.0):
            return False, "Confidence must be 0.0-1.0"

        if not self.decision.alternatives:
            return False, "At least 1 alternative must be considered"

        if not self.decision.assumptions:
            return False, "At least 1 assumption must be listed"

        if not self.decision.predicted_outcome:
            return False, "Predicted outcome is required"

        return True, ""


class DecisionFormatter:
    """Format decisions for display and storage."""

    @staticmethod
    def format_for_display(decision: DecisionCapture) -> str:
        """Format decision for terminal display.

        Args:
            decision: DecisionCapture object

        Returns:
            Formatted string
        """
        lines = []

        lines.append(f"\n📋 Decision: {decision.statement}")
        lines.append(f"🎯 ID: {decision.decision_id}")
        lines.append(f"📊 Confidence: {int(decision.confidence * 100)}%\n")

        # Alternatives
        lines.append("🔀 Alternatives Considered:")
        for alt in decision.alternatives:
            reason = decision.alternatives_with_reasons.get(alt, "")
            if reason:
                lines.append(f"  • {alt}: {reason}")
            else:
                lines.append(f"  • {alt}")
        lines.append("")

        # Assumptions
        lines.append("🤔 Assumptions:")
        for assumption in decision.assumptions:
            lines.append(f"  • {assumption}")
        lines.append("")

        # Predicted outcome
        if decision.predicted_outcome:
            lines.append("🎯 Predicted Outcome:")
            outcome = decision.predicted_outcome
            lines.append(f"  Description: {outcome.get('description', 'N/A')}")
            lines.append(f"  Risk Level: {outcome.get('risk_level', 'unknown').upper()}")
            if outcome.get("success_criteria"):
                lines.append("  Success Criteria:")
                for criterion in outcome["success_criteria"]:
                    lines.append(f"    ✓ {criterion}")
            lines.append("")

        # Metadata
        lines.append("ℹ️  Metadata:")
        lines.append(f"  Created: {decision.created_at}")
        lines.append(f"  Module: {decision.module}")
        lines.append(f"  Status: {decision.status}")
        lines.append(f"  Context Hash: {decision.context_hash[:16]}...\n")

        return "\n".join(lines)

    @staticmethod
    def format_for_graph(decision: DecisionCapture) -> Dict[str, Any]:
        """Format decision for FalkorDB storage.

        Args:
            decision: DecisionCapture object

        Returns:
            Dict suitable for graph node creation
        """
        return {
            "decision_id": decision.decision_id,
            "statement": decision.statement,
            "confidence": decision.confidence,
            "alternatives": json.dumps(decision.alternatives),
            "alternatives_with_reasons": json.dumps(decision.alternatives_with_reasons),
            "assumptions": json.dumps(decision.assumptions),
            "predicted_outcome": json.dumps(decision.predicted_outcome),
            "created_at": decision.created_at,
            "created_by": decision.created_by,
            "module": decision.module,
            "context_hash": decision.context_hash,
            "status": decision.status,
            "linked_pr": decision.linked_pr,
            "linked_commit": decision.linked_commit,
        }
