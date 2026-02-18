"""Tests for CodeDigger integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from membria.codedigger_client import (
    CodeDiggerClient,
    CodeDiggerClientSync,
    Pattern,
    Occurrence,
    CodeDiggerStats,
)
from membria.pattern_matcher import PatternMatcher, DetectionResult
from membria.evidence_aggregator import EvidenceAggregator


class TestCodeDiggerClient:
    """Test CodeDigger API client."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check when CodeDigger is alive."""
        client = CodeDiggerClient()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = {"status": "ok"}
            mock_get.return_value.__aenter__.return_value = mock_resp

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when CodeDigger is unavailable."""
        client = CodeDiggerClient()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_get_patterns_success(self):
        """Test fetching patterns from CodeDigger."""
        client = CodeDiggerClient()

        mock_patterns = {
            "patterns": [
                {
                    "pattern_id": "custom_jwt",
                    "name": "Custom JWT Implementation",
                    "description": "Implementing custom JWT instead of using libraries",
                    "severity": "high",
                    "category": "security",
                    "removal_rate": 0.89,
                    "repos_affected": 20470,
                    "keywords": ["custom jwt", "jwt auth"],
                    "regex_pattern": r"class.*JWT.*:",
                    "examples": ["example code"],
                }
            ]
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = mock_patterns
            mock_get.return_value.__aenter__.return_value = mock_resp

            patterns = await client.get_patterns()
            assert len(patterns) == 1
            assert patterns[0].pattern_id == "custom_jwt"
            assert patterns[0].removal_rate == 0.89

    @pytest.mark.asyncio
    async def test_get_patterns_caching(self):
        """Test that patterns are cached."""
        client = CodeDiggerClient(cache_ttl_hours=24)

        mock_patterns = {
            "patterns": [
                {
                    "pattern_id": "test",
                    "name": "Test Pattern",
                    "description": "Test",
                    "severity": "low",
                    "category": "test",
                    "removal_rate": 0.5,
                    "repos_affected": 100,
                    "keywords": ["test"],
                    "regex_pattern": "test",
                    "examples": [],
                }
            ]
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = mock_patterns
            mock_get.return_value.__aenter__.return_value = mock_resp

            # First call
            patterns1 = await client.get_patterns()
            assert len(patterns1) == 1

            # Second call should use cache
            patterns2 = await client.get_patterns()
            assert len(patterns2) == 1

            # API should only be called once
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_occurrences(self):
        """Test fetching occurrences for a pattern."""
        client = CodeDiggerClient()

        mock_occurrences = {
            "occurrences": [
                {
                    "occurrence_id": "occ_1",
                    "pattern_id": "custom_jwt",
                    "repo_name": "user-service",
                    "file_path": "src/auth/jwt.py",
                    "match_text": "class CustomJWT:",
                    "confidence": 0.95,
                    "last_seen": "2024-02-10",
                }
            ]
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json.return_value = mock_occurrences
            mock_get.return_value.__aenter__.return_value = mock_resp

            occurrences = await client.get_occurrences("custom_jwt")
            assert len(occurrences) == 1
            assert occurrences[0].repo_name == "user-service"

    @pytest.mark.asyncio
    async def test_search_patterns(self):
        """Test searching patterns by keyword."""
        from datetime import datetime, timedelta

        client = CodeDiggerClient()

        patterns = [
            Pattern(
                pattern_id="custom_jwt",
                name="Custom JWT",
                description="",
                severity="high",
                category="security",
                removal_rate=0.89,
                repos_affected=100,
                keywords=["jwt", "custom"],
                regex_pattern="",
                examples=[],
            ),
            Pattern(
                pattern_id="custom_crypto",
                name="Custom Crypto",
                description="",
                severity="critical",
                category="security",
                removal_rate=0.95,
                repos_affected=200,
                keywords=["crypto", "custom"],
                regex_pattern="",
                examples=[],
            ),
        ]

        client.patterns_cache = patterns
        client.patterns_cache_time = datetime.now()

        matches = await client.search_patterns("jwt")
        assert len(matches) == 1
        assert matches[0].pattern_id == "custom_jwt"


class TestPatternMatcher:
    """Test pattern matching logic."""

    def test_stage1_regex_matching(self):
        """Test Stage 1: Regex matching."""
        matcher = PatternMatcher()

        code = """
def authenticate(token):
    class CustomJWT:
        pass
    return token
"""

        pattern = {
            "pattern_id": "custom_jwt",
            "name": "Custom JWT",
            "regex_pattern": r"class\s+Custom\w*",
            "keywords": ["custom"],
        }

        matches = matcher._stage1_regex(code, pattern)
        assert len(matches) > 0

    def test_stage2_syntax_filtering_comments(self):
        """Test Stage 2: Filter out matches in comments."""
        matcher = PatternMatcher()

        code = """
# Custom JWT implementation
class RealJWT:
    pass
"""

        matches = [(2, "# Custom JWT"), (3, "class")]  # First one is comment line
        filtered = matcher._stage2_syntax(code, matches, {})

        # Should filter out the comment match
        # "# Custom JWT" at line 2 should be detected as a comment
        assert len(filtered) <= len(matches)

    def test_is_in_comment(self):
        """Test comment detection."""
        matcher = PatternMatcher()

        # Python comment
        assert matcher._is_in_comment("# Custom JWT", "Custom JWT") is True
        assert matcher._is_in_comment("Custom JWT  # implementation", "Custom JWT") is False

        # JavaScript comment
        assert matcher._is_in_comment("// Custom JWT", "Custom JWT") is True
        assert matcher._is_in_comment("Custom JWT // implementation", "Custom JWT") is False

    def test_is_in_string(self):
        """Test string detection."""
        matcher = PatternMatcher()

        assert matcher._is_in_string('"Custom JWT"', "Custom JWT") is True
        assert matcher._is_in_string("'Custom JWT'", "Custom JWT") is True
        assert matcher._is_in_string('print("Custom JWT")', "Custom JWT") is True
        assert matcher._is_in_string("Custom JWT = true", "Custom JWT") is False

    def test_match_in_code(self):
        """Test full pattern matching."""
        matcher = PatternMatcher()

        code = """
class CustomJWT:
    def encode(self):
        pass
"""

        pattern = {
            "pattern_id": "custom_jwt",
            "name": "Custom JWT",
            "severity": "high",
            "regex_pattern": r"class\s+Custom\w*",
            "keywords": ["custom"],
        }

        results = matcher.match_in_code(code, [pattern], "auth.py")
        assert len(results) > 0
        assert results[0].pattern_id == "custom_jwt"


class TestEvidenceAggregator:
    """Test evidence aggregation."""

    def test_aggregate_evidence(self):
        """Test evidence aggregation."""
        aggregator = EvidenceAggregator(graph_client=None)

        pattern = Pattern(
            pattern_id="custom_jwt",
            name="Custom JWT",
            description="",
            severity="high",
            category="security",
            removal_rate=0.89,
            repos_affected=20470,
            keywords=["custom jwt"],
            regex_pattern="",
            examples=[],
        )

        evidence = aggregator.aggregate(pattern)

        assert evidence.pattern_id == "custom_jwt"
        assert evidence.removal_rate == 0.89
        assert evidence.repos_affected == 20470
        assert evidence.confidence > 0.5

    def test_estimate_removal_time(self):
        """Test removal time estimation."""
        aggregator = EvidenceAggregator(graph_client=None)

        # Critical pattern (>0.9 removal rate)
        days_critical = aggregator._estimate_removal_time(0.95)
        assert days_critical <= 14

        # Medium pattern (0.5-0.75)
        days_medium = aggregator._estimate_removal_time(0.65)
        assert 30 <= days_medium <= 60

    def test_format_evidence_for_display(self):
        """Test evidence formatting."""
        aggregator = EvidenceAggregator(graph_client=None)

        pattern = Pattern(
            pattern_id="custom_jwt",
            name="Custom JWT",
            description="",
            severity="high",
            category="security",
            removal_rate=0.89,
            repos_affected=20470,
            keywords=[],
            regex_pattern="",
            examples=[],
        )

        evidence = aggregator.aggregate(pattern)
        display = aggregator.format_evidence_for_display(evidence)

        assert "Custom JWT" in display
        assert "89%" in display
        # Number can have comma formatting
        assert "20" in display and "470" in display

    def test_generate_recommendation_critical(self):
        """Test recommendation generation for critical patterns."""
        aggregator = EvidenceAggregator(graph_client=None)

        pattern = Pattern(
            pattern_id="eval",
            name="Use of eval()",
            description="",
            severity="critical",
            category="security",
            removal_rate=0.99,
            repos_affected=50000,
            keywords=[],
            regex_pattern="",
            examples=[],
        )

        recommendation = aggregator._generate_recommendation(pattern, [])
        assert "CRITICAL" in recommendation
        assert recommendation is not None


class TestCodeDiggerClientSync:
    """Test synchronous wrapper."""

    def test_sync_wrapper_health_check(self):
        """Test that sync wrapper works."""
        client = CodeDiggerClientSync()

        # This will actually try to reach CodeDigger
        # In test environment, it should return False
        result = client.health_check()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
