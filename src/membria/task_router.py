"""Task Router: Classify user requests into TACTICAL, DECISION, or LEARNING."""

import logging
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Type of user task."""
    TACTICAL = "tactical"  # Direct coding, no decision-making
    DECISION = "decision"  # Choose between options, architecture, approach
    LEARNING = "learning"  # Reflect on outcomes, update knowledge


@dataclass
class TaskClassification:
    """Classification result for user input."""
    task_type: TaskType
    confidence: float  # 0.0-1.0
    reason: str  # Explanation of classification
    suggested_alternatives: Optional[List[str]] = None  # If decision


class TaskRouter:
    """Classifies user requests into task types.

    Decision signals:
    - Question words: "which", "should", "what if", "how to choose"
    - Multiple options: "vs", "or", "instead of"
    - Architecture keywords: "pattern", "design", "approach", "strategy"
    - Confidence words: "confident", "uncertain", "best"

    Learning signals:
    - Past tense: "was", "failed", "worked"
    - Reflection: "learned", "mistake", "should have"
    - Linking: "because of", "resulted in"
    """

    def __init__(self):
        """Initialize router."""
        # Decision indicators
        self.decision_questions = [
            "which", "should", "what if", "how to choose",
            "better", "best", "prefer", "choice", "option",
            "alternative", "instead", "versus", "vs",
        ]

        self.decision_keywords = [
            "pattern", "design", "architecture", "approach",
            "strategy", "framework", "library", "tool",
            "implement", "build", "structure", "refactor",
        ]

        self.learning_keywords = [
            "learned", "mistake", "failed", "worked", "success",
            "discovered", "found", "realized", "issue", "problem",
            "bug", "regression", "incident", "rework",
        ]

    def classify(
        self,
        user_input: str,
        context: Optional[str] = None,
    ) -> TaskClassification:
        """Classify user request into task type.

        Args:
            user_input: User's request/statement
            context: Optional context (recent changes, file names, etc)

        Returns:
            TaskClassification with type and confidence
        """
        input_lower = user_input.lower()
        context_lower = context.lower() if context else ""

        # Check for learning signals (highest priority)
        learning_score = self._score_learning(input_lower, context_lower)
        if learning_score > 0.7:
            return TaskClassification(
                task_type=TaskType.LEARNING,
                confidence=learning_score,
                reason="Reflects on past outcomes and learning",
            )

        # Check for decision signals
        decision_score = self._score_decision(input_lower, context_lower)
        if decision_score > 0.6:
            alternatives = self._extract_alternatives(user_input)
            return TaskClassification(
                task_type=TaskType.DECISION,
                confidence=decision_score,
                reason="Choosing between approaches or making architectural decision",
                suggested_alternatives=alternatives,
            )

        # Default to tactical
        return TaskClassification(
            task_type=TaskType.TACTICAL,
            confidence=max(0.5, 1.0 - max(learning_score, decision_score)),
            reason="Direct implementation task, no major decision-making",
        )

    def _score_learning(self, text: str, context: str) -> float:
        """Score likelihood this is a learning task.

        Args:
            text: User input
            context: Context string

        Returns:
            Score 0.0-1.0
        """
        score = 0.0

        # Check for learning keywords
        keyword_matches = sum(
            1 for kw in self.learning_keywords
            if kw in text or kw in context
        )
        score += min(keyword_matches * 0.15, 0.6)

        # Check for outcome linking patterns
        outcome_patterns = [
            "resulted in", "led to", "caused", "because of",
            "due to", "as a result", "fixed", "resolved",
        ]
        for pattern in outcome_patterns:
            if pattern in text:
                score += 0.2
                break

        # Check for reflection questions
        reflection_patterns = [
            "why did", "how did", "what went", "what should",
            "looking back", "in retrospect",
        ]
        for pattern in reflection_patterns:
            if pattern in text:
                score += 0.15
                break

        return min(score, 1.0)

    def _score_decision(self, text: str, context: str) -> float:
        """Score likelihood this is a decision task.

        Args:
            text: User input
            context: Context string

        Returns:
            Score 0.0-1.0
        """
        score = 0.0

        # Check for decision questions
        question_matches = sum(
            1 for q in self.decision_questions
            if q in text or q in context
        )
        score += min(question_matches * 0.2, 0.6)

        # Check for decision keywords
        keyword_matches = sum(
            1 for kw in self.decision_keywords
            if kw in text or kw in context
        )
        score += min(keyword_matches * 0.1, 0.4)

        # Check for multiple alternatives
        if self._has_alternatives(text):
            score += 0.25

        # Check for uncertainty signals
        uncertainty_words = [
            "uncertain", "unsure", "not sure", "conflicted",
            "should i", "can i", "which", "how to",
        ]
        for word in uncertainty_words:
            if word in text:
                score += 0.1
                break

        return min(score, 1.0)

    def _has_alternatives(self, text: str) -> bool:
        """Check if text mentions multiple alternatives.

        Args:
            text: User input

        Returns:
            True if alternatives are mentioned
        """
        # Look for alternative patterns
        alternative_indicators = [
            " vs ", " or ", " instead of ",
            " over ", " rather than ", " versus ",
            "option 1", "option 2", "alternative",
            "approach a", "approach b",
        ]

        text_lower = text.lower()
        for indicator in alternative_indicators:
            if indicator in text_lower:
                return True

        # Check for comma-separated list of frameworks/libraries
        if any(char in text for char in [","]):
            framework_keywords = [
                "react", "vue", "angular", "express", "fastify",
                "postgres", "mongodb", "redis", "docker", "kubernetes",
            ]
            for fw in framework_keywords:
                if fw in text_lower:
                    return True

        return False

    def _extract_alternatives(self, text: str) -> Optional[List[str]]:
        """Extract mentioned alternatives from text.

        Args:
            text: User input

        Returns:
            List of alternatives, or None if none found
        """
        alternatives = []

        # Look for "X vs Y" pattern
        if " vs " in text.lower():
            parts = text.lower().split(" vs ")
            for part in parts:
                # Extract last word/phrase from each part
                words = part.strip().split()
                if words:
                    alternatives.append(words[-1])

        # Look for "X or Y" pattern
        if " or " in text.lower():
            parts = text.lower().split(" or ")
            for part in parts:
                words = part.strip().split()
                if words:
                    alternatives.append(words[-1])

        # Look for listed frameworks/libraries
        if "," in text:
            potential_alts = [p.strip() for p in text.split(",")]
            # Filter to keep only reasonable-length alternatives
            alternatives.extend([
                a for a in potential_alts
                if 2 < len(a) < 50 and any(c.isalpha() for c in a)
            ])

        return list(set(alternatives)) if alternatives else None

    def get_task_type_emoji(self, task_type: TaskType) -> str:
        """Get emoji for task type.

        Args:
            task_type: Task type

        Returns:
            Emoji string
        """
        emojis = {
            TaskType.TACTICAL: "⚙️",   # Hammer - direct action
            TaskType.DECISION: "🤔",   # Thinking - decision
            TaskType.LEARNING: "📚",   # Books - learning
        }
        return emojis.get(task_type, "❓")
