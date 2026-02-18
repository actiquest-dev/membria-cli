"""Context Injector: Prepare system prompt injection for Claude Code."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from membria.decision_capture import DecisionCapture
from membria.decision_surface import DecisionContext
from membria.task_router import TaskType
from membria.security import sanitize_text, sanitize_list

logger = logging.getLogger(__name__)


@dataclass
class InjectionContext:
    """System prompt injection context."""

    decision_statement: Optional[str] = None
    decision_id: Optional[str] = None
    constraints: List[str] = None  # ["DO NOT use custom JWT", "Use passport-jwt"]
    team_patterns: List[str] = None  # ["Use /api/v1/ prefix", "Explicit error handling"]
    assumptions: List[str] = None  # Assumptions to validate
    negative_knowledge: List[str] = None  # Patterns to avoid
    similar_decisions: List[Dict[str, Any]] = None
    team_calibration: Optional[Dict[str, Any]] = None
    warnings: List[str] = None  # User warnings

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []
        if self.team_patterns is None:
            self.team_patterns = []
        if self.assumptions is None:
            self.assumptions = []
        if self.negative_knowledge is None:
            self.negative_knowledge = []
        if self.similar_decisions is None:
            self.similar_decisions = []
        if self.warnings is None:
            self.warnings = []


class ContextInjector:
    """Compiles context for system prompt injection.

    Sources:
    1. Decision Capture: statement, alternatives, assumptions
    2. Decision Surface: similar decisions, team calibration
    3. Negative Knowledge: patterns to avoid
    4. Team Patterns: local conventions
    """

    def __init__(self):
        """Initialize injector."""
        pass

    def compile_injection(
        self,
        task_type: TaskType,
        decision: Optional[DecisionCapture] = None,
        surface_context: Optional[DecisionContext] = None,
    ) -> InjectionContext:
        """Compile injection context from decision and surface.

        Args:
            task_type: Type of task (DECISION, TACTICAL, LEARNING)
            decision: Decision capture data
            surface_context: Context from Decision Surface

        Returns:
            InjectionContext ready for prompt injection
        """
        injection = InjectionContext()

        # Only inject if DECISION type
        if task_type != TaskType.DECISION:
            return injection

        if not decision:
            return injection

        # Core decision
        injection.decision_statement = sanitize_text(decision.statement, max_len=300)
        injection.decision_id = sanitize_text(decision.decision_id, max_len=80)

        # Constraints from alternatives
        injection.constraints = self._extract_constraints(decision)

        # Assumptions to validate
        injection.assumptions = sanitize_list(decision.assumptions, max_len=200)

        # Negative knowledge alerts
        if surface_context and surface_context.negative_knowledge_alerts:
            injection.negative_knowledge = [
                sanitize_text(
                    f"{alert.get('pattern', '')}: {alert.get('recommendation', 'Avoid')}",
                    max_len=240,
                )
                for alert in surface_context.negative_knowledge_alerts
            ]

        # Similar decisions for reference
        if surface_context and surface_context.similar_decisions:
            injection.similar_decisions = surface_context.similar_decisions

        # Team calibration warnings
        if surface_context and surface_context.team_calibration:
            injection.team_calibration = surface_context.team_calibration
            injection.warnings = self._generate_calibration_warnings(
                surface_context.team_calibration
            )

        # Team patterns
        injection.team_patterns = sanitize_list(self._get_team_patterns(), max_len=200)

        return injection

    def _extract_constraints(self, decision: DecisionCapture) -> List[str]:
        """Extract constraints from decision alternatives.

        Args:
            decision: Decision capture

        Returns:
            List of constraints
        """
        constraints = []

        # Main constraint: what was chosen
        constraints.append(f"✅ IMPLEMENT: {sanitize_text(decision.statement, max_len=200)}")

        # Alternatives to avoid
        for alt in decision.alternatives:
            if alt.lower() != decision.statement.lower():
                constraints.append(f"❌ DO NOT use: {sanitize_text(alt, max_len=200)}")

        return constraints

    def _generate_calibration_warnings(self, calibration: Dict[str, Any]) -> List[str]:
        """Generate warnings from team calibration.

        Args:
            calibration: Team calibration data

        Returns:
            List of warnings
        """
        warnings = []

        overconfidence = calibration.get("overconfidence", 0)
        sample_size = calibration.get("sample_size", 0)

        if overconfidence > 0.15:
            warning = (
                f"⚠️  TEAM OVERCONFIDENT by {int(overconfidence * 100)}% "
                f"in {calibration.get('domain', 'this area')} (n={sample_size})"
            )
            warnings.append(warning)
            warnings.append("   → Be more cautious than your confidence suggests")
        elif overconfidence < -0.1:
            warning = (
                f"ℹ️  TEAM UNDERCONFIDENT by {int(-overconfidence * 100)}% "
                f"in {calibration.get('domain', 'this area')}"
            )
            warnings.append(warning)
            warnings.append("   → You may be more capable than you think")

        return warnings

    def _get_team_patterns(self) -> List[str]:
        """Get local team patterns and conventions.

        Args:
            None (would read from config in real implementation)

        Returns:
            List of team patterns
        """
        # In real implementation, would read from team config
        # For now, return common patterns
        patterns = [
            "Use explicit error handling (try/catch)",
            "Add input validation on API endpoints",
            "Document assumptions in comments",
            "Write tests before implementation",
            "Use conventional commit messages",
        ]
        return patterns

    def generate_system_prompt(self, injection: InjectionContext) -> str:
        """Generate system prompt injection text.

        Args:
            injection: Compiled injection context

        Returns:
            System prompt text to prepend
        """
        if not injection.decision_statement:
            return ""

        lines = []

        lines.append("=" * 70)
        lines.append("MEMBRIA DECISION CONTEXT")
        lines.append("=" * 70)
        lines.append("")

        # Decision statement
        lines.append(f"DECISION: {injection.decision_statement}")
        if injection.decision_id:
            lines.append(f"ID: {injection.decision_id}")
        lines.append("")

        # Constraints
        if injection.constraints:
            lines.append("CONSTRAINTS:")
            for constraint in injection.constraints:
                lines.append(f"  {constraint}")
            lines.append("")

        # Team patterns
        if injection.team_patterns:
            lines.append("TEAM PATTERNS & CONVENTIONS:")
            for pattern in injection.team_patterns:
                lines.append(f"  • {pattern}")
            lines.append("")

        # Assumptions to validate
        if injection.assumptions:
            lines.append("ASSUMPTIONS TO VALIDATE:")
            for assumption in injection.assumptions:
                lines.append(f"  • {assumption}")
            lines.append("")

        # Negative knowledge
        if injection.negative_knowledge:
            lines.append("NEGATIVE KNOWLEDGE (AVOID):")
            for nk in injection.negative_knowledge:
                lines.append(f"  ⚠️  {nk}")
            lines.append("")

        # Similar decisions
        if injection.similar_decisions:
            lines.append("SIMILAR PAST DECISIONS:")
            for decision in injection.similar_decisions[:3]:
                outcome_icon = "✅" if decision.get("outcome") == "success" else "❌"
                statement = sanitize_text(decision.get("statement", "Unknown"), max_len=200)
                lines.append(
                    f"  {outcome_icon} {statement[:60]}"
                )
            lines.append("")

        # Calibration warnings
        if injection.warnings:
            lines.append("CALIBRATION ALERTS:")
            for warning in injection.warnings:
                lines.append(f"  {sanitize_text(warning, max_len=200)}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("")

        return "\n".join(lines)

    def get_claude_code_integration_prompt(
        self,
        injection: InjectionContext,
    ) -> str:
        """Get the full prompt for Claude Code integration.

        This is what gets injected into Claude Code's system message.

        Args:
            injection: Compiled injection context

        Returns:
            Full system prompt injection
        """
        base_prompt = self.generate_system_prompt(injection)

        if not base_prompt:
            return ""

        # Add instruction for Claude Code
        instruction = (
            "\n\nYou are implementing a decision made by the developer. "
            "Use the constraints and context above to guide your implementation. "
            "Validate the assumptions and flag any concerns. "
            "Follow team patterns and conventions."
        )

        return base_prompt + instruction

    def extract_from_surface_context(
        self,
        surface_context: DecisionContext,
    ) -> Dict[str, Any]:
        """Extract structured data from surface context.

        Args:
            surface_context: Context from Decision Surface

        Returns:
            Dict with extracted information
        """
        return {
            "similar_decisions": surface_context.similar_decisions,
            "team_calibration": surface_context.team_calibration,
            "negative_knowledge": surface_context.negative_knowledge_alerts,
        }
