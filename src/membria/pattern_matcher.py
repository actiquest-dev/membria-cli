"""Pattern matcher: Stage 1-3 detection (regex, AST, context validation)."""

import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DetectionStage(str, Enum):
    """Detection pipeline stage."""
    REGEX = "stage_1_regex"
    SYNTAX = "stage_2_syntax"
    CONTEXT = "stage_3_context"
    LLM = "stage_4_llm"  # Not used in CLI, only in CodeDigger


@dataclass
class DetectionResult:
    """Result of pattern matching in code."""
    pattern_id: str
    pattern_name: str
    file_path: str
    line_number: int
    match_text: str
    confidence: float  # 0.0 to 1.0
    stage: DetectionStage
    reason: str  # Why this pattern was detected
    severity: str  # "low", "medium", "high", "critical"


class PatternMatcher:
    """Matches antipatterns in code using Stage 1-3 detection.

    Pipeline:
    - Stage 1: Regex matching against keywords
    - Stage 2: Basic syntax/import validation
    - Stage 3: Context and usage pattern validation
    - Stage 4: LLM validation (done by CodeDigger, not here)
    """

    def __init__(self):
        """Initialize pattern matcher."""
        self.compiled_regexes = {}

    def match_in_code(
        self,
        code: str,
        patterns: List[dict],
        file_path: str = "unknown",
    ) -> List[DetectionResult]:
        """Find patterns in code.

        Args:
            code: Source code to analyze
            patterns: List of pattern dicts with regex_pattern, keywords, etc.
            file_path: Path to file being analyzed

        Returns:
            List of DetectionResult objects
        """
        results = []

        for pattern in patterns:
            pattern_results = self._match_pattern(code, pattern, file_path)
            results.extend(pattern_results)

        return results

    def _match_pattern(
        self,
        code: str,
        pattern: dict,
        file_path: str,
    ) -> List[DetectionResult]:
        """Match a single pattern against code.

        Args:
            code: Source code
            pattern: Pattern definition
            file_path: File path

        Returns:
            List of DetectionResult objects
        """
        results = []

        # Stage 1: Regex matching
        regex_matches = self._stage1_regex(code, pattern)
        if not regex_matches:
            return results

        # Stage 2: Syntax validation
        syntax_matches = self._stage2_syntax(code, regex_matches, pattern)
        if not syntax_matches:
            return results

        # Stage 3: Context validation
        context_matches = self._stage3_context(code, syntax_matches, pattern)

        # Convert matches to DetectionResult
        for line_num, match_text in context_matches:
            result = DetectionResult(
                pattern_id=pattern.get("pattern_id", "unknown"),
                pattern_name=pattern.get("name", "unknown"),
                file_path=file_path,
                line_number=line_num,
                match_text=match_text[:100],  # Truncate long matches
                confidence=0.78,  # No LLM validation, so lower confidence
                stage=DetectionStage.CONTEXT,
                reason=f"Matched keywords: {', '.join(pattern.get('keywords', [])[:3])}",
                severity=pattern.get("severity", "medium"),
            )
            results.append(result)

        return results

    def _stage1_regex(
        self,
        code: str,
        pattern: dict,
    ) -> List[Tuple[int, str]]:
        """Stage 1: Regex matching.

        Args:
            code: Source code
            pattern: Pattern with regex_pattern

        Returns:
            List of (line_number, match_text) tuples
        """
        regex_pattern = pattern.get("regex_pattern")
        if not regex_pattern:
            # Fallback to keyword matching
            return self._keyword_matching(code, pattern.get("keywords", []))

        try:
            # Compile regex if not cached
            pattern_id = pattern.get("pattern_id", "")
            if pattern_id not in self.compiled_regexes:
                self.compiled_regexes[pattern_id] = re.compile(
                    regex_pattern, re.IGNORECASE | re.MULTILINE
                )

            regex = self.compiled_regexes[pattern_id]

            matches = []
            for line_num, line in enumerate(code.split("\n"), 1):
                for match in regex.finditer(line):
                    matches.append((line_num, match.group(0)))

            return matches

        except re.error as e:
            logger.warning(f"Invalid regex for pattern: {str(e)}")
            # Fallback to keyword matching
            return self._keyword_matching(code, pattern.get("keywords", []))

    def _keyword_matching(self, code: str, keywords: List[str]) -> List[Tuple[int, str]]:
        """Fallback: Match by keywords.

        Args:
            code: Source code
            keywords: List of keywords to search for

        Returns:
            List of (line_number, match_text) tuples
        """
        matches = []

        for line_num, line in enumerate(code.split("\n"), 1):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Find the actual match in the line
                    idx = line.lower().find(keyword.lower())
                    end_idx = idx + len(keyword)
                    match_text = line[idx:end_idx]
                    matches.append((line_num, match_text))
                    break  # Don't match multiple keywords on same line

        return matches

    def _stage2_syntax(
        self,
        code: str,
        matches: List[Tuple[int, str]],
        pattern: dict,
    ) -> List[Tuple[int, str]]:
        """Stage 2: Basic syntax validation.

        Checks:
        - Pattern is not in a comment
        - Pattern is in a valid syntax context

        Args:
            code: Source code
            matches: Matches from Stage 1
            pattern: Pattern definition

        Returns:
            Filtered matches
        """
        lines = code.split("\n")
        filtered = []

        for line_num, match_text in matches:
            # Get the line (1-indexed)
            if line_num > len(lines):
                continue

            line = lines[line_num - 1]

            # Check if match is in a comment
            if self._is_in_comment(line, match_text):
                logger.debug(f"Skipping match in comment: {line_num}")
                continue

            # Check if match is in a string literal
            if self._is_in_string(line, match_text):
                logger.debug(f"Skipping match in string: {line_num}")
                continue

            filtered.append((line_num, match_text))

        return filtered

    def _stage3_context(
        self,
        code: str,
        matches: List[Tuple[int, str]],
        pattern: dict,
    ) -> List[Tuple[int, str]]:
        """Stage 3: Context validation.

        Checks:
        - Pattern usage matches expected context
        - Related imports are present
        - Pattern appears in appropriate scope

        Args:
            code: Source code
            matches: Matches from Stage 2
            pattern: Pattern definition

        Returns:
            Filtered matches
        """
        # Check for required context
        required_imports = pattern.get("required_imports", [])
        if required_imports:
            has_required = any(
                imp in code for imp in required_imports
            )
            if not has_required:
                logger.debug(f"Missing required imports for pattern")
                return []

        # For now, return all matches that passed Stage 2
        # Advanced Stage 3 would do AST analysis
        return matches

    def _is_in_comment(self, line: str, match_text: str) -> bool:
        """Check if match is inside a comment.

        Args:
            line: Code line
            match_text: Text that matched

        Returns:
            True if match is in a comment
        """
        # Find the match position in the line
        match_idx = line.find(match_text)
        if match_idx < 0:
            return False

        # Look for comment markers before the match
        comment_chars = ["#", "//", "/*"]
        before_match = line[:match_idx]

        for char in comment_chars:
            if char in before_match:
                return True

        return False

    def _is_in_string(self, line: str, match_text: str) -> bool:
        """Check if match is inside a string literal.

        Args:
            line: Code line
            match_text: Text that matched

        Returns:
            True if match is in a string
        """
        match_idx = line.find(match_text)
        if match_idx < 0:
            return False

        # Simple heuristic: count quotes before match
        before_match = line[:match_idx]

        # Count unescaped quotes
        single_quotes = before_match.count("'") - before_match.count("\\'")
        double_quotes = before_match.count('"') - before_match.count('\\"')
        backticks = before_match.count("`") - before_match.count("\\`")

        # If odd number of quotes, we're inside a string
        return (single_quotes % 2 != 0) or (double_quotes % 2 != 0) or (backticks % 2 != 0)

    def get_staged_confidence(self, stage: DetectionStage) -> float:
        """Get confidence level for a detection stage.

        Args:
            stage: Detection stage

        Returns:
            Confidence value 0.0-1.0
        """
        # Without LLM validation, confidence is lower
        confidence_by_stage = {
            DetectionStage.REGEX: 0.65,
            DetectionStage.SYNTAX: 0.72,
            DetectionStage.CONTEXT: 0.78,
            DetectionStage.LLM: 0.95,  # Full LLM validation
        }
        return confidence_by_stage.get(stage, 0.5)
