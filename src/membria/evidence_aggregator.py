"""Evidence aggregator: Compile antipattern evidence from CodeDigger + team history."""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from membria.codedigger_client import Pattern, Occurrence
from membria.graph import GraphClient

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """Compiled evidence for a detected antipattern."""
    pattern_id: str
    pattern_name: str
    severity: str
    removal_rate: float  # 0.0 to 1.0
    repos_affected: int
    avg_days_to_removal: Optional[float]  # How long before teams remove it
    team_history: List[Dict[str, Any]]  # [{decision_id, date, result}]
    examples: List[Dict[str, str]]  # [{repo, file, code}]
    recommendation: Optional[str]
    confidence: float  # 0.0 to 1.0


class EvidenceAggregator:
    """Aggregates evidence from multiple sources.

    Sources:
    1. CodeDigger statistics (industry-wide)
    2. Team decision history (from FalkorDB)
    3. GitHub examples (from CodeDigger)
    """

    def __init__(self, graph_client: Optional[GraphClient] = None):
        """Initialize aggregator.

        Args:
            graph_client: FalkorDB client for accessing team history
        """
        self.graph_client = graph_client or GraphClient()

    def aggregate(
        self,
        pattern: Pattern,
        occurrences: Optional[List[Occurrence]] = None,
    ) -> Evidence:
        """Aggregate all evidence for a pattern.

        Args:
            pattern: Pattern from CodeDigger
            occurrences: Examples from GitHub (optional)

        Returns:
            Evidence object with all compiled information
        """
        # Industry-wide evidence
        removal_rate = pattern.removal_rate
        repos_affected = pattern.repos_affected

        # Calculate average days to removal
        # This would come from CodeDigger's historical data
        # For now, estimate based on removal rate
        avg_days = self._estimate_removal_time(removal_rate)

        # Team history
        team_history = self._get_team_history(pattern.pattern_id)

        # GitHub examples
        examples = self._format_examples(occurrences or [])

        # Recommendation
        recommendation = self._generate_recommendation(pattern, team_history)

        # Confidence
        confidence = self._calculate_confidence(pattern, team_history)

        return Evidence(
            pattern_id=pattern.pattern_id,
            pattern_name=pattern.name,
            severity=pattern.severity,
            removal_rate=removal_rate,
            repos_affected=repos_affected,
            avg_days_to_removal=avg_days,
            team_history=team_history,
            examples=examples,
            recommendation=recommendation,
            confidence=confidence,
        )

    def _estimate_removal_time(self, removal_rate: float) -> Optional[float]:
        """Estimate average days to removal based on removal rate.

        Higher removal rate = faster removal (more consensus)

        Args:
            removal_rate: Removal rate 0.0-1.0

        Returns:
            Estimated days to removal
        """
        # Simple heuristic based on removal rate
        if removal_rate > 0.9:
            return 14.0  # ~2 weeks for critical patterns
        elif removal_rate > 0.75:
            return 30.0  # ~1 month
        elif removal_rate > 0.5:
            return 60.0  # ~2 months
        else:
            return 90.0  # ~3 months for less clear patterns

    def _get_team_history(self, pattern_id: str) -> List[Dict[str, Any]]:
        """Get team's decision history for this antipattern.

        Queries FalkorDB for decisions about this pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            List of decision records
        """
        if not self.graph_client or not self.graph_client.connected:
            return []

        try:
            graph = self.graph_client.graph

            # Query for decisions involving this antipattern
            query = f"""
            MATCH (d:Decision) -[:TRIGGERED]-> (ap:AntiPattern)
            WHERE ap.pattern_id = "{pattern_id}"
            RETURN d.decision_id, d.created_at, d.confidence, d.statement
            LIMIT 10
            """

            result = graph.query(query)

            if not result:
                return []

            history = [
                {
                    "decision_id": row[0],
                    "date": row[1],
                    "confidence": row[2],
                    "statement": row[3],
                }
                for row in result
            ]

            logger.debug(f"Found {len(history)} team decisions for pattern {pattern_id}")
            return history

        except Exception as e:
            logger.warning(f"Could not query team history: {str(e)}")
            return []

    def _format_examples(self, occurrences: List[Occurrence]) -> List[Dict[str, str]]:
        """Format GitHub examples for display.

        Args:
            occurrences: List of occurrences from CodeDigger

        Returns:
            List of formatted examples
        """
        examples = []

        for occ in occurrences[:3]:  # Top 3 examples
            examples.append(
                {
                    "repo": occ.repo_name,
                    "file": occ.file_path,
                    "code": occ.match_text[:200],  # Truncate
                    "confidence": str(round(occ.confidence * 100)) + "%",
                }
            )

        return examples

    def _generate_recommendation(
        self,
        pattern: Pattern,
        team_history: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Generate a recommendation based on pattern severity.

        Args:
            pattern: Pattern definition
            team_history: Team's past decisions

        Returns:
            Recommendation text
        """
        if team_history:
            # Team has tried this before
            if pattern.severity == "critical":
                return f"❌ CRITICAL: Your team tried this and it failed. Use alternative patterns."
            elif pattern.severity == "high":
                return f"⚠️  HIGH: Your team has avoided this pattern. Don't use it."
            else:
                return f"ℹ️ Your team has experience with this. Proceed with caution."

        # Default recommendations by severity
        if pattern.severity == "critical":
            return "❌ CRITICAL: Removed in 95%+ of codebases. Use battle-tested alternatives."
        elif pattern.severity == "high":
            return f"⚠️  HIGH: Removed in {int(pattern.removal_rate * 100)}% of repos. Choose established solutions."
        elif pattern.severity == "medium":
            return f"ℹ️ MEDIUM: {int(pattern.removal_rate * 100)}% of teams avoid this. Consider alternatives."
        else:
            return f"ℹ️ LOW: Optional to remove, but better alternatives exist."

    def _calculate_confidence(
        self,
        pattern: Pattern,
        team_history: List[Dict[str, Any]],
    ) -> float:
        """Calculate confidence in the evidence.

        Args:
            pattern: Pattern definition
            team_history: Team's past decisions

        Returns:
            Confidence value 0.0-1.0
        """
        confidence = 0.5  # Base confidence

        # Increase based on removal rate
        confidence += pattern.removal_rate * 0.3  # Up to +0.3

        # Increase if we have team history
        if team_history:
            confidence += 0.15

        # Cap at 1.0
        return min(confidence, 1.0)

    def format_evidence_for_display(self, evidence: Evidence) -> str:
        """Format evidence for CLI display.

        Args:
            evidence: Evidence object

        Returns:
            Formatted string for terminal output
        """
        lines = []

        lines.append("")
        lines.append(f"⚠️  ANTIPATTERN DETECTED: {evidence.pattern_name}")
        lines.append("")

        # Evidence section
        lines.append("📊 EVIDENCE:")
        lines.append(f"├─ Industry: {int(evidence.removal_rate * 100)}% removed ({evidence.repos_affected:,} repos)")
        lines.append(f"├─ Avg removal: {int(evidence.avg_days_to_removal or 30)} days")

        # Team history
        if evidence.team_history:
            lines.append(f"├─ Your team: Tried {len(evidence.team_history)}x, ")
            for hist in evidence.team_history[:2]:
                lines.append(f"│  └─ {hist['date']}: {hist['statement'][:60]}...")
        else:
            lines.append("├─ Your team: First time trying this")

        # Examples
        if evidence.examples:
            lines.append("├─ Examples:")
            for ex in evidence.examples[:2]:
                lines.append(f"│  └─ {ex['repo']}/{ex['file']} ({ex['confidence']})")

        lines.append(f"└─ Confidence: {int(evidence.confidence * 100)}%")
        lines.append("")

        # Recommendation
        if evidence.recommendation:
            lines.append("💡 Recommendation:")
            lines.append(evidence.recommendation)
            lines.append("")

        return "\n".join(lines)
