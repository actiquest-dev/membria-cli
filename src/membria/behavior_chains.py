"""Behavior Chains - Evidence-based context injection for decisions

Four chains operationalize skills using evidence:
1. Positive Precedent - Concrete successful decisions
2. Negative Evidence - Known failures with reasoning
3. Calibration Warning - Debiasing through team data
4. AntiPattern Guard - Post-generation pattern detection

Key principle: "Данные убеждают, правила обходятся" (Data convinces, rules are bypassed)
"""

import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PositivePrecedentChain:
    """Chain 1: Show concrete successful decisions (not abstract rules).

    Evidence-based context showing past successful decisions in the same domain.
    More convincing than rules because it shows real outcomes.
    """

    def __init__(self, graph_client):
        """Initialize with graph client.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client

    def build(self, domain: str, current_statement: str) -> str:
        """Build positive precedent chain output.

        Args:
            domain: Domain name
            current_statement: Current decision statement

        Returns:
            Markdown formatted precedent examples, or empty string if none found
        """
        try:
            # Query similar successful decisions in domain
            from membria.graph_queries import DomainQueries

            query, params = DomainQueries.get_domain_decisions(domain)
            decisions = self.graph_client.query(query, params)

            if not decisions:
                return ""

            # Filter for successes only
            successes = [
                d
                for d in decisions
                if d.get("outcome_status") == "success" or d.get("outcome") == "success"
            ]

            if not successes:
                return ""

            # Format top 3 successful precedents
            output = "## ✅ Positive Precedents (Successful Decisions)\n\n"
            for dec in successes[:3]:
                statement = dec.get("statement", "Unknown")
                confidence = dec.get("confidence", 0)
                created_at = dec.get("created_at", "Unknown")

                output += f"- **{statement}**\n"
                output += f"  - Confidence: {confidence:.0%}\n"
                output += f"  - Outcome: SUCCESS\n"
                output += f"  - Date: {created_at}\n"

                # Add outcome evidence if available
                evidence = dec.get("outcome_evidence")
                if evidence:
                    output += f"  - Evidence: {evidence}\n"

                output += "\n"

            return output

        except Exception as e:
            logger.warning(f"Error building positive precedent chain: {e}")
            return ""


class NegativeEvidenceChain:
    """Chain 2: Evidence-based warnings with NegativeKnowledge data.

    Shows what failed and why, with concrete numbers and patterns.
    More effective than "avoid" rules because it shows causation.
    """

    def __init__(self, graph_client):
        """Initialize with graph client.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client

    def build(self, domain: str) -> str:
        """Build negative evidence chain output.

        Args:
            domain: Domain name

        Returns:
            Markdown formatted failures with evidence, or empty string if none found
        """
        try:
            from membria.graph_queries import DomainQueries

            # Query negative knowledge for domain
            query, params = DomainQueries.get_domain_negative_knowledge(domain, severity="high")
            nk_list = self.graph_client.query(query, params)

            if not nk_list:
                return ""

            output = "## ⚠️ Known Failures (Evidence-Based Warnings)\n\n"

            for nk in nk_list[:5]:  # Top 5
                hypothesis = nk.get("hypothesis", "Unknown")
                conclusion = nk.get("conclusion", "Failed")
                severity = nk.get("severity", "medium").upper()
                prevented = nk.get("prevented_count", 0)
                recommendation = nk.get("recommendation", "Avoid this pattern")

                output += f"### {hypothesis}\n"
                output += f"**Conclusion:** {conclusion}\n"
                output += f"- Severity: {severity}\n"
                output += f"- Prevented future decisions: {prevented}\n"
                output += f"- Recommendation: {recommendation}\n"
                output += "\n"

            return output

        except Exception as e:
            logger.warning(f"Error building negative evidence chain: {e}")
            return ""


class CalibrationWarningChain:
    """Chain 3: Debiasing through CalibrationProfile data.

    When team has systematic bias (overconfident or underconfident),
    show the gap and recommend confidence adjustment.
    """

    def __init__(self, calibration_updater):
        """Initialize with calibration updater.

        Args:
            calibration_updater: CalibrationUpdater instance
        """
        self.calibration_updater = calibration_updater

    def build(self, domain: str, current_confidence: float) -> str:
        """Build calibration warning chain output.

        Args:
            domain: Domain name
            current_confidence: Developer's stated confidence (0-1)

        Returns:
            Markdown formatted calibration warning, or empty string if no adjustment needed
        """
        try:
            # Get calibration profile
            profiles = self.calibration_updater.get_all_profiles()

            if not profiles or domain not in profiles:
                return ""

            profile = profiles[domain]
            gap = profile.get("confidence_gap", 0)
            mean_success = profile.get("mean_success_rate", 0)
            sample_size = profile.get("sample_size", 0)
            trend = profile.get("trend", "stable")

            # Only show warning if gap is meaningful (>10%)
            if abs(gap) <= 0.10:
                return ""

            bias_type = "OVERCONFIDENT" if gap > 0 else "UNDERCONFIDENT"

            output = "## 🎯 Calibration Warning (Team Bias Detection)\n\n"
            output += f"Team is **{bias_type}** by {abs(gap):.0%} in **{domain}** domain.\n\n"

            output += "### Historical Data\n"
            output += f"- Decisions analyzed: {sample_size}\n"
            output += f"- Actual success rate: {mean_success:.0%}\n"
            output += f"- Average confidence: {mean_success + gap:.0%}\n"
            output += f"- Confidence gap: {gap:+.0%}\n"
            output += f"- Trend: {trend}\n\n"

            output += "### Your Decision\n"
            output += f"- Your confidence: {current_confidence:.0%}\n"

            # Recommend adjustment
            if gap > 0:
                adjusted = max(0, current_confidence - abs(gap))
                output += f"- Recommended: {adjusted:.0%} (reduce by {abs(gap):.0%})\n"
                output += f"- Reasoning: Team tends to overestimate success in this domain\n"
            else:
                adjusted = min(1, current_confidence + abs(gap))
                output += f"- Recommended: {adjusted:.0%} (increase by {abs(gap):.0%})\n"
                output += f"- Reasoning: Team tends to underestimate success in this domain\n"

            output += "\n"

            return output

        except Exception as e:
            logger.warning(f"Error building calibration warning chain: {e}")
            return ""


class AntiPatternGuardChain:
    """Chain 4: Post-generation regex scan + recommendation.

    Scans decision statement against known antipatterns (regex-based).
    Detects dangerous patterns and recommends remediation.
    """

    def __init__(self, graph_client):
        """Initialize with graph client.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client

    def build(self, domain: str, current_statement: str) -> str:
        """Build antipattern guard chain output.

        Args:
            domain: Domain name
            current_statement: Decision statement to scan

        Returns:
            Markdown formatted antipattern warnings, or empty string if none detected
        """
        try:
            # Query antipatterns for domain
            query = f"""
            MATCH (ap:AntiPattern)
            WHERE ap.category = '{domain}' OR ap.domain = '{domain}'
            RETURN ap.id, ap.name, ap.failure_rate, ap.regex_pattern, ap.category, ap.severity
            ORDER BY ap.failure_rate DESC
            """
            antipatterns = self.graph_client.query(query)

            if not antipatterns:
                return ""

            # Scan statement for antipatterns
            detected = []
            for ap in antipatterns:
                pattern = ap.get("regex_pattern", "")
                if pattern:
                    try:
                        if re.search(pattern, current_statement, re.IGNORECASE):
                            detected.append(ap)
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {pattern}")

            if not detected:
                return ""

            output = "## 🛑 AntiPattern Guard (Known Problematic Patterns)\n\n"
            output += f"**Statement scanned:** {current_statement}\n\n"

            for ap in detected[:5]:  # Top 5
                name = ap.get("name", "Unknown")
                failure_rate = ap.get("failure_rate", 0)
                severity = ap.get("severity", "medium").upper()

                output += f"### ⚠️ {name}\n"
                output += f"- Failure rate: {failure_rate:.0%}\n"
                output += f"- Severity: {severity}\n"

                # Provide remediation guidance
                if failure_rate > 0.70:
                    output += f"- **RECOMMENDATION**: Strongly reconsider this approach\n"
                elif failure_rate > 0.50:
                    output += f"- **RECOMMENDATION**: Review carefully, pattern fails often\n"
                else:
                    output += f"- **RECOMMENDATION**: Possible issues, verify mitigations\n"

                output += "\n"

            return output

        except Exception as e:
            logger.warning(f"Error building antipattern guard chain: {e}")
            return ""


class ChainExecutionResult:
    """Result of executing a single behavior chain."""

    def __init__(self, chain_name: str, content: str = "", error: Optional[str] = None):
        """Initialize result.

        Args:
            chain_name: Name of the chain (e.g., "positive_precedent")
            content: Markdown output from chain
            error: Any error that occurred
        """
        self.chain_name = chain_name
        self.content = content
        self.error = error
        self.triggered = bool(content)  # Chain triggered if it produced output
        self.timestamp = datetime.now().isoformat()

    def is_empty(self) -> bool:
        """Check if chain produced no meaningful output."""
        return not self.content or len(self.content.strip()) == 0
