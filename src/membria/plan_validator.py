"""Plan Validator - MID-PLAN validation for decision quality

When Claude generates a plan, scan each step for:
1. Conflicts with NegativeKnowledge
2. Matches against AntiPatterns
3. Similarity to past failed plans
4. Overconfidence detection from CalibrationProfile

Returns warnings to guide plan refinement BEFORE execution.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PlanWarning:
    """Warning about a plan step."""

    step_number: int
    step_text: str
    warning_type: str  # "negative_knowledge", "antipattern", "past_failure", "calibration"
    severity: str  # "high", "medium", "low"
    message: str
    suggestion: Optional[str] = None
    confidence: float = 1.0  # How confident is this warning (0-1)

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "step": self.step_number,
            "type": self.warning_type,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "confidence": round(self.confidence, 2),
        }


class PlanValidator:
    """Validates plan steps against graph knowledge.

    Algorithm:
    For each step in plan:
    1. Check semantic similarity to NegativeKnowledge (threshold 0.7)
    2. Check regex match against AntiPatterns
    3. Check similarity to past failed decisions
    4. Check for overconfidence signals
    """

    def __init__(self, graph_client, calibration_updater):
        """Initialize validator.

        Args:
            graph_client: GraphClient instance
            calibration_updater: CalibrationUpdater instance
        """
        self.graph_client = graph_client
        self.calibration_updater = calibration_updater

    def validate_plan(self, steps: List[str], domain: Optional[str] = None) -> List[PlanWarning]:
        """Validate all plan steps.

        Args:
            steps: List of plan step descriptions
            domain: Optional domain context (database, auth, api, etc.)

        Returns:
            List of PlanWarning objects, sorted by severity
        """
        warnings = []

        for step_num, step_text in enumerate(steps, 1):
            if not step_text or not step_text.strip():
                continue

            # 1. Check against NegativeKnowledge
            nk_warnings = self._check_negative_knowledge(step_num, step_text, domain)
            warnings.extend(nk_warnings)

            # 2. Check against AntiPatterns
            ap_warnings = self._check_antipatterns(step_num, step_text, domain)
            warnings.extend(ap_warnings)

            # 3. Check against past failures
            pf_warnings = self._check_past_failures(step_num, step_text, domain)
            warnings.extend(pf_warnings)

            # 4. Check for overconfidence
            oc_warnings = self._check_overconfidence(step_num, step_text, domain)
            warnings.extend(oc_warnings)

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        warnings.sort(key=lambda w: severity_order.get(w.severity, 3))

        logger.info(f"Plan validation: {len(steps)} steps, {len(warnings)} warnings")

        return warnings

    def _check_negative_knowledge(
        self, step_num: int, step_text: str, domain: Optional[str]
    ) -> List[PlanWarning]:
        """Check step against NegativeKnowledge using semantic similarity.

        Args:
            step_num: Step number in plan
            step_text: Step description
            domain: Optional domain filter

        Returns:
            List of warnings if NK conflicts found
        """
        warnings = []

        try:
            # Query NegativeKnowledge for domain (if provided)
            if domain:
                query = f"""
                MATCH (nk:NegativeKnowledge {{domain: $domain}})
                RETURN nk.id, nk.hypothesis, nk.conclusion, nk.severity, nk.domain
                ORDER BY nk.severity DESC
                LIMIT 10
                """
                params = {"domain": domain}
            else:
                query = f"""
                MATCH (nk:NegativeKnowledge)
                RETURN nk.id, nk.hypothesis, nk.conclusion, nk.severity, nk.domain
                ORDER BY nk.severity DESC
                LIMIT 20
                """
                params = {}

            nk_list = self.graph_client.query(query, params) or []

            # Simple text similarity check
            step_words = set(step_text.lower().split())

            for nk in nk_list:
                hypothesis = nk.get("hypothesis", "").lower()
                conclusion = nk.get("conclusion", "")

                # Check if keywords from NK hypothesis appear in step
                nk_words = set(hypothesis.split())
                overlap = step_words & nk_words

                if len(overlap) >= 2:  # Minimum 2 word overlap
                    severity = nk.get("severity", "medium")
                    message = f"Step mentions '{' '.join(overlap)}' - known issue: {hypothesis}"
                    suggestion = f"Recommendation: {conclusion}"

                    warnings.append(
                        PlanWarning(
                            step_number=step_num,
                            step_text=step_text,
                            warning_type="negative_knowledge",
                            severity=severity,
                            message=message,
                            suggestion=suggestion,
                            confidence=min(1.0, len(overlap) / 3),
                        )
                    )

        except Exception as e:
            logger.warning(f"Error checking NegativeKnowledge: {e}")

        return warnings

    def _check_antipatterns(
        self, step_num: int, step_text: str, domain: Optional[str]
    ) -> List[PlanWarning]:
        """Check step against AntiPatterns using regex.

        Args:
            step_num: Step number
            step_text: Step description
            domain: Optional domain filter

        Returns:
            List of warnings if AP matches found
        """
        warnings = []

        try:
            # Query AntiPatterns
            if domain:
                query = f"""
                MATCH (ap:AntiPattern {{domain: $domain}})
                RETURN ap.id, ap.name, ap.failure_rate, ap.regex_pattern, ap.severity
                ORDER BY ap.failure_rate DESC
                LIMIT 10
                """
                params = {"domain": domain}
            else:
                query = f"""
                MATCH (ap:AntiPattern)
                RETURN ap.id, ap.name, ap.failure_rate, ap.regex_pattern, ap.severity
                ORDER BY ap.failure_rate DESC
                LIMIT 20
                """
                params = {}

            ap_list = self.graph_client.query(query, params) or []

            for ap in ap_list:
                pattern = ap.get("regex_pattern", "")
                name = ap.get("name", "Unknown")
                failure_rate = ap.get("failure_rate", 0)

                if pattern:
                    try:
                        if re.search(pattern, step_text, re.IGNORECASE):
                            # Determine severity based on failure rate
                            if failure_rate > 0.70:
                                severity = "high"
                            elif failure_rate > 0.50:
                                severity = "medium"
                            else:
                                severity = "low"

                            message = f"Step matches antipattern: {name} ({failure_rate:.0%} failure rate)"
                            suggestion = f"This pattern is commonly removed/fixed in similar projects"

                            warnings.append(
                                PlanWarning(
                                    step_number=step_num,
                                    step_text=step_text,
                                    warning_type="antipattern",
                                    severity=severity,
                                    message=message,
                                    suggestion=suggestion,
                                    confidence=failure_rate,
                                )
                            )

                    except re.error:
                        logger.warning(f"Invalid regex pattern: {pattern}")

        except Exception as e:
            logger.warning(f"Error checking AntiPatterns: {e}")

        return warnings

    def _check_past_failures(
        self, step_num: int, step_text: str, domain: Optional[str]
    ) -> List[PlanWarning]:
        """Check step against similar past failed decisions.

        Args:
            step_num: Step number
            step_text: Step description
            domain: Optional domain filter

        Returns:
            List of warnings if similar failures found
        """
        warnings = []

        try:
            # Extract keywords from step
            keywords = self._extract_keywords(step_text)

            if not keywords:
                return warnings

            # Query past failures
            for keyword in keywords[:3]:  # Check top 3 keywords
                query = f"""
                MATCH (d:Decision {{outcome: 'failure'}})
                WHERE d.statement CONTAINS '{keyword}'
                RETURN d.id, d.statement, d.module, d.confidence, d.resolved_at
                ORDER BY d.resolved_at DESC
                LIMIT 3
                """

                past_failures = self.graph_client.query(query) or []

                for failure in past_failures:
                    statement = failure.get("statement", "")
                    decision_id = failure.get("id", "unknown")
                    module = failure.get("module", "")

                    message = f"Similar approach failed before: '{statement}' ({decision_id})"
                    suggestion = f"Consider why it failed last time in {module} domain"

                    warnings.append(
                        PlanWarning(
                            step_number=step_num,
                            step_text=step_text,
                            warning_type="past_failure",
                            severity="medium",
                            message=message,
                            suggestion=suggestion,
                            confidence=0.7,
                        )
                    )

        except Exception as e:
            logger.warning(f"Error checking past failures: {e}")

        return warnings

    def _check_overconfidence(
        self, step_num: int, step_text: str, domain: Optional[str]
    ) -> List[PlanWarning]:
        """Check if step shows signs of overconfidence based on domain calibration.

        Args:
            step_num: Step number
            step_text: Step description
            domain: Optional domain filter

        Returns:
            List of warnings if overconfidence detected
        """
        warnings = []

        try:
            # If no domain specified, skip
            if not domain:
                return warnings

            # Get calibration for domain
            profiles = self.calibration_updater.get_all_profiles()
            if not profiles or domain not in profiles:
                return warnings

            calibration = profiles[domain]
            gap = calibration.get("confidence_gap", 0)

            # If team is significantly overconfident
            if gap > 0.15:
                message = f"Domain '{domain}' shows overconfidence bias: {gap:.0%}"
                suggestion = f"Team tends to underestimate effort/complexity in {domain}. Pad estimates."

                warnings.append(
                    PlanWarning(
                        step_number=step_num,
                        step_text=step_text,
                        warning_type="calibration",
                        severity="low",
                        message=message,
                        suggestion=suggestion,
                        confidence=0.8,
                    )
                )

        except Exception as e:
            logger.warning(f"Error checking overconfidence: {e}")

        return warnings

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract meaningful keywords from plan step.

        Args:
            text: Step text
            max_keywords: Max keywords to return

        Returns:
            List of keywords
        """
        # Simple keyword extraction - skip common words
        common_words = {
            "the", "a", "an", "and", "or", "is", "are", "be", "this", "that",
            "with", "from", "to", "in", "for", "of", "by", "at", "will", "should"
        }

        words = [
            w.strip(".,;:!?").lower()
            for w in text.split()
            if w.strip(".,;:!?").lower() not in common_words and len(w) > 3
        ]

        return list(set(words))[:max_keywords]

    def validate_plan_async(
        self, steps: List[str], domain: Optional[str] = None
    ) -> Dict:
        """Validate plan and return structured result.

        Args:
            steps: Plan steps
            domain: Optional domain context

        Returns:
            Dict with validation results
        """
        warnings = self.validate_plan(steps, domain)

        return {
            "total_steps": len(steps),
            "warnings_count": len(warnings),
            "high_severity": sum(1 for w in warnings if w.severity == "high"),
            "medium_severity": sum(1 for w in warnings if w.severity == "medium"),
            "low_severity": sum(1 for w in warnings if w.severity == "low"),
            "warnings": [w.to_dict() for w in warnings],
            "can_proceed": len([w for w in warnings if w.severity == "high"]) == 0,
            "timestamp": datetime.now().isoformat(),
        }
