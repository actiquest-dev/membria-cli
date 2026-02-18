"""Post-generation validators: Check generated code matches decision."""

import logging
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from membria.decision_capture import DecisionCapture

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    checks: List[str]  # List of checks performed
    failures: List[str]  # Failed checks
    warnings: List[str]  # Non-blocking warnings
    score: float  # 0.0-1.0


class DecisionConsistencyValidator:
    """Validates generated code matches the decision."""

    def validate_code_matches_decision(
        self,
        code: str,
        decision: DecisionCapture,
    ) -> ValidationResult:
        """Check if code implements the chosen decision.

        Args:
            code: Generated code
            decision: Decision that was made

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, checks=[], failures=[], warnings=[], score=1.0)

        # Extract key terms from decision
        decision_terms = decision.statement.lower().split()

        # Look for main decision keywords in code
        code_lower = code.lower()
        matches = sum(1 for term in decision_terms if term in code_lower)

        result.checks.append(f"Decision implementation keywords: {matches}/{len(decision_terms)}")

        if matches < len(decision_terms) // 2:
            result.failures.append(
                f"Code doesn't seem to implement '{decision.statement}'. "
                f"Only {matches} of {len(decision_terms)} decision keywords found."
            )
            result.is_valid = False
            result.score = 0.5
        else:
            result.score = min(1.0, 0.7 + (matches / len(decision_terms)) * 0.3)

        return result

    def validate_negative_knowledge_respected(
        self,
        code: str,
        negative_patterns: List[str],
    ) -> ValidationResult:
        """Check code doesn't use known antipatterns.

        Args:
            code: Generated code
            negative_patterns: Patterns to avoid (e.g., ["custom_jwt", "eval"])

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, checks=[], failures=[], warnings=[], score=1.0)

        code_lower = code.lower()

        violations = []
        for pattern in negative_patterns:
            # Simple keyword matching
            if pattern.lower() in code_lower:
                violations.append(pattern)

        result.checks.append(f"Antipattern check: {len(negative_patterns)} patterns")

        if violations:
            result.failures.append(
                f"Code uses antipatterns: {', '.join(violations)}. "
                f"These are known to fail in {len(violations)} ways."
            )
            result.is_valid = False
            result.score = 0.3
        else:
            result.score = 1.0

        return result

    def validate_alternatives_considered(
        self,
        code: str,
        decision: DecisionCapture,
    ) -> ValidationResult:
        """Check if code acknowledges alternatives in comments.

        Args:
            code: Generated code
            decision: Decision with alternatives

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, checks=[], failures=[], warnings=[], score=1.0)

        result.checks.append(f"Alternatives acknowledgment: {len(decision.alternatives)} considered")

        # Check for comment mentioning decision
        comment_patterns = [
            r"#.*decision",
            r"#.*alternative",
            r"#.*considered",
            r"//.*decision",
            r"//.*alternative",
            r"//.*considered",
        ]

        has_comment = any(re.search(pattern, code, re.IGNORECASE) for pattern in comment_patterns)

        if has_comment:
            result.warnings.append("✓ Decision is documented in code")
            result.score = 1.0
        else:
            result.warnings.append(
                "Consider adding a comment explaining why this approach was chosen "
                "over alternatives"
            )
            result.score = 0.8

        return result

    def validate_assumptions_addressed(
        self,
        code: str,
        assumptions: List[str],
    ) -> ValidationResult:
        """Check if code addresses stated assumptions.

        Args:
            code: Generated code
            assumptions: Assumptions from decision

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, checks=[], failures=[], warnings=[], score=1.0)

        result.checks.append(f"Assumption validation: {len(assumptions)} assumptions")

        # Look for evidence that assumptions are addressed
        evidence_count = 0

        for assumption in assumptions:
            # Extract key terms from assumption
            terms = assumption.lower().split()
            if any(term in code.lower() for term in terms[:2]):
                evidence_count += 1
                result.warnings.append(f"✓ Assumption addressed: {assumption[:50]}...")

        coverage = evidence_count / len(assumptions) if assumptions else 1.0

        if coverage < 0.5 and assumptions:
            result.warnings.append(
                f"Only {evidence_count}/{len(assumptions)} assumptions "
                "appear to be addressed in code"
            )
            result.score = 0.6
        else:
            result.score = 0.9 + (coverage * 0.1)

        return result

    def validate_code_quality(self, code: str) -> ValidationResult:
        """Check general code quality signals.

        Args:
            code: Generated code

        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, checks=[], failures=[], warnings=[], score=1.0)

        checks = []

        # Check for error handling
        error_patterns = [
            r"try\s*{",
            r"catch\s*\(",
            r"except\s*:",
            r"error\s*=>",
            r"\.catch\s*\(",
        ]
        has_error_handling = any(re.search(p, code) for p in error_patterns)
        checks.append(("Error handling", has_error_handling))

        # Check for input validation
        validation_patterns = [r"validate", r"check\s*\(", r"if\s*\(.*\)", r"schema"]
        has_validation = any(re.search(p, code, re.IGNORECASE) for p in validation_patterns)
        checks.append(("Input validation", has_validation))

        # Check for comments
        comment_patterns = [r"#", r"//", r"/\*"]
        has_comments = any(re.search(p, code) for p in comment_patterns)
        checks.append(("Comments/documentation", has_comments))

        # Check for logging
        logging_patterns = [r"log\s*\(", r"console\.", r"logger\."]
        has_logging = any(re.search(p, code, re.IGNORECASE) for p in logging_patterns)
        checks.append(("Logging", has_logging))

        score = 0.0
        for check_name, passed in checks:
            result.checks.append(f"{check_name}: {'✓' if passed else '✗'}")
            if passed:
                score += 0.25

        result.score = score
        return result


class ValidatorChain:
    """Runs multiple validators and aggregates results."""

    def __init__(self):
        """Initialize validator chain."""
        self.consistency_validator = DecisionConsistencyValidator()

    def validate_implementation(
        self,
        code: str,
        decision: DecisionCapture,
        negative_patterns: Optional[List[str]] = None,
    ) -> ValidationResult:
        """Run all validators on generated code.

        Args:
            code: Generated code
            decision: Decision that was made
            negative_patterns: Patterns to avoid

        Returns:
            Aggregated ValidationResult
        """
        all_checks = []
        all_failures = []
        all_warnings = []
        all_scores = []

        # Check 1: Decision consistency
        consistency = self.consistency_validator.validate_code_matches_decision(code, decision)
        all_checks.extend(consistency.checks)
        all_failures.extend(consistency.failures)
        all_warnings.extend(consistency.warnings)
        all_scores.append(consistency.score)

        # Check 2: Negative knowledge
        if negative_patterns:
            negative = self.consistency_validator.validate_negative_knowledge_respected(
                code, negative_patterns
            )
            all_checks.extend(negative.checks)
            all_failures.extend(negative.failures)
            all_warnings.extend(negative.warnings)
            all_scores.append(negative.score)

        # Check 3: Alternatives
        alternatives = self.consistency_validator.validate_alternatives_considered(code, decision)
        all_checks.extend(alternatives.checks)
        all_failures.extend(alternatives.failures)
        all_warnings.extend(alternatives.warnings)
        all_scores.append(alternatives.score)

        # Check 4: Assumptions
        if decision.assumptions:
            assumptions = self.consistency_validator.validate_assumptions_addressed(
                code, decision.assumptions
            )
            all_checks.extend(assumptions.checks)
            all_failures.extend(assumptions.failures)
            all_warnings.extend(assumptions.warnings)
            all_scores.append(assumptions.score)

        # Check 5: Code quality
        quality = self.consistency_validator.validate_code_quality(code)
        all_checks.extend(quality.checks)
        all_failures.extend(quality.failures)
        all_warnings.extend(quality.warnings)
        all_scores.append(quality.score)

        # Aggregate
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.5
        is_valid = len(all_failures) == 0

        return ValidationResult(
            is_valid=is_valid,
            checks=all_checks,
            failures=all_failures,
            warnings=all_warnings,
            score=avg_score,
        )

    def format_results(self, result: ValidationResult) -> str:
        """Format validation results for display.

        Args:
            result: ValidationResult object

        Returns:
            Formatted string
        """
        lines = []

        # Header
        if result.is_valid:
            lines.append("✅ CODE VALIDATION PASSED")
        else:
            lines.append("❌ CODE VALIDATION FAILED")

        lines.append(f"\nValidation Score: {int(result.score * 100)}%\n")

        # Checks
        if result.checks:
            lines.append("CHECKS PERFORMED:")
            for check in result.checks:
                lines.append(f"  • {check}")
            lines.append("")

        # Failures
        if result.failures:
            lines.append("FAILURES:")
            for failure in result.failures:
                lines.append(f"  ❌ {failure}")
            lines.append("")

        # Warnings
        if result.warnings:
            lines.append("NOTES:")
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        return "\n".join(lines)
