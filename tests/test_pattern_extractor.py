"""Tests for pattern extraction."""

import pytest
from membria.pattern_extractor import PatternExtractor
from membria.graph import GraphClient


class TestPatternExtractor:
    """Test pattern extraction."""

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_initialization(self):
        """Test extractor initialization."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)
        assert extractor.graph_client is not None

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_basic(self):
        """Test basic pattern extraction."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        patterns = extractor.extract_patterns_for_domain("database")
        assert isinstance(patterns, list)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_multiple_domains(self):
        """Test pattern extraction for multiple domains."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        domains = ["database", "auth", "api", "cache", "messaging", "storage"]
        for domain in domains:
            patterns = extractor.extract_patterns_for_domain(domain)
            assert isinstance(patterns, list)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_minimum_sample_size(self):
        """Test pattern extraction respects minimum sample size."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        # Extract with min sample size
        patterns = extractor.extract_patterns_for_domain("auth", min_sample_size=3)
        assert isinstance(patterns, list)

        # All patterns should have adequate sample size
        for pattern in patterns:
            assert pattern.sample_size >= 3

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_pattern_success_rate_calculation(self):
        """Test pattern success rate is calculated."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        patterns = extractor.extract_patterns_for_domain("database")
        for pattern in patterns:
            assert 0 <= pattern.success_rate <= 1

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_pattern_has_supporting_decisions(self):
        """Test patterns have supporting decision IDs."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        patterns = extractor.extract_patterns_for_domain("api")
        for pattern in patterns:
            assert hasattr(pattern, 'supporting_decisions')
            assert isinstance(pattern.supporting_decisions, list)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_returns_pattern_objects(self):
        """Test that extract returns Pattern objects."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        patterns = extractor.extract_patterns_for_domain("auth")
        for pattern in patterns:
            # Each pattern should have required attributes
            assert hasattr(pattern, 'statement')
            assert hasattr(pattern, 'success_rate')
            assert hasattr(pattern, 'sample_size')

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_across_domains(self):
        """Test pattern extraction across all domains."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        domains = ["auth", "database", "api"]
        all_patterns = extractor.extract_patterns_across_domains(domains)
        assert isinstance(all_patterns, dict)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_pattern_statistics(self):
        """Test getting pattern statistics."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        stats = extractor.get_pattern_stats("database")
        assert isinstance(stats, dict)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_consistency(self):
        """Test that pattern extraction is consistent."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        # Extract twice - should get consistent results
        patterns1 = extractor.extract_patterns_for_domain("auth")
        patterns2 = extractor.extract_patterns_for_domain("auth")

        # Should have same number of patterns
        assert len(patterns1) == len(patterns2)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_extract_patterns_with_different_sample_sizes(self):
        """Test extraction with different minimum sample sizes."""
        graph_client = GraphClient()
        extractor = PatternExtractor(graph_client)

        patterns_1 = extractor.extract_patterns_for_domain("database", min_sample_size=1)
        patterns_3 = extractor.extract_patterns_for_domain("database", min_sample_size=3)

        # Fewer patterns with higher minimum
        assert len(patterns_1) >= len(patterns_3)
