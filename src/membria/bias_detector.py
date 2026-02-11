"""Cognitive Safety Layer - Bias detection and debiasing."""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class BiasAnalysis:
    """Bias analysis result."""
    detected_biases: List[str]
    risk_score: float  # 0-1
    confidence_reality_gap: float
    recommendations: List[str]
    severity: str  # low, medium, high


class BiasDetector:
    """Detect cognitive biases in decisions."""

    # Bias patterns
    ANCHORING_PATTERNS = [
        r"first.*idea",
        r"initial.*proposal",
        r"original.*decision",
        r"stick.*with.*initial",
    ]

    CONFIRMATION_PATTERNS = [
        r"only.*evidence.*for",
        r"ignore.*negative",
        r"evidence.*supporting",
        r"avoiding.*contrary",
    ]

    OVERCONFIDENCE_PATTERNS = [
        r"definitely|certainly|obviously|must",
        r"no.*doubt",
        r"guaranteed|will.*succeed",
        r"can't.*fail",
    ]

    SUNK_COST_PATTERNS = [
        r"invested.*so.*much",
        r"can't.*waste",
        r"already.*started",
        r"too.*late.*change",
    ]

    def analyze(
        self,
        decision_statement: str,
        alternatives: List[str],
        confidence: float,
        actual_success_rate: Optional[float] = None,
    ) -> BiasAnalysis:
        """Analyze decision for biases."""
        text = decision_statement.lower()
        detected = []
        risk_score = 0.0

        # Check each bias type
        if self._check_pattern(text, self.ANCHORING_PATTERNS):
            detected.append("anchoring")
            risk_score += 0.15

        if self._check_pattern(text, self.CONFIRMATION_PATTERNS):
            detected.append("confirmation")
            risk_score += 0.2

        if self._check_pattern(text, self.OVERCONFIDENCE_PATTERNS):
            detected.append("overconfidence")
            risk_score += 0.25

        if self._check_pattern(text, self.SUNK_COST_PATTERNS):
            detected.append("sunk_cost")
            risk_score += 0.2

        # Check alternatives
        if not alternatives or len(alternatives) <= 1:
            detected.append("lack_of_alternatives")
            risk_score += 0.15

        # Confidence vs reality gap
        gap = 0.0
        if actual_success_rate is not None:
            gap = abs(confidence - actual_success_rate)
            if gap > 0.2:
                detected.append("overconfident")
                risk_score += gap * 0.5

        # Cap risk score
        risk_score = min(risk_score, 1.0)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            detected, confidence, len(alternatives) if alternatives else 0
        )

        return BiasAnalysis(
            detected_biases=detected,
            risk_score=risk_score,
            confidence_reality_gap=gap,
            recommendations=recommendations,
            severity="high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low",
        )

    def _check_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _generate_recommendations(
        self, biases: List[str], confidence: float, num_alternatives: int
    ) -> List[str]:
        """Generate debiasing recommendations."""
        recs = []

        if "anchoring" in biases:
            recs.append("🔄 Premortem: Imagine this decision fails. Why did it fail?")

        if "confirmation" in biases:
            recs.append("😈 Devil's Advocate: What's the strongest case AGAINST this?")

        if "overconfidence" in biases:
            recs.append("📉 Confidence Gap: Your confidence is higher than success rate")
            recs.append("⏸️  Cool-off: Sleep on it before finalizing")

        if "sunk_cost" in biases:
            recs.append("🔄 Fresh Start: Evaluate as if starting from scratch")

        if "lack_of_alternatives" in biases:
            recs.append("🤔 Generate: List 3 more alternative approaches")

        if not recs:
            recs.append("✓ Decision looks solid. Proceed with confidence!")

        return recs
