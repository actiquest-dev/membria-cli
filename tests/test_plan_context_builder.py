"""Tests for plan context builder."""

import pytest
from membria.plan_context_builder import PlanContextBuilder


class TestPlanContextBuilder:
    """Test plan context builder."""

    def test_initialization(self):
        """Test builder initialization."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        assert builder.graph_client is not None
        assert builder.calibration_updater is not None

    def test_build_plan_context_basic(self):
        """Test building plan context for domain."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(domain="database")

        assert isinstance(context, dict)
        assert "domain" in context
        assert "scope" in context
        assert "past_plans" in context
        assert "failed_approaches" in context
        assert "successful_patterns" in context
        assert "calibration" in context
        assert "constraints" in context
        assert "recommendations" in context
        assert "total_tokens" in context
        assert "timestamp" in context
        assert "formatted" in context

    def test_build_plan_context_with_scope(self):
        """Test building context with scope."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(
            domain="auth",
            scope="JWT implementation with refresh tokens"
        )

        assert context["domain"] == "auth"
        assert context["scope"] == "JWT implementation with refresh tokens"

    def test_build_plan_context_multiple_domains(self):
        """Test building context for different domains."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        domains = ["database", "auth", "api", "cache"]
        for domain in domains:
            context = builder.build_plan_context(domain=domain)
            assert context["domain"] == domain
            assert "formatted" in context

    def test_plan_context_tokens_reasonable(self):
        """Test that token estimates are reasonable."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(domain="database")

        # Token count should be reasonable (positive, less than max)
        assert context["total_tokens"] >= 0
        assert context["total_tokens"] <= 1500  # max_tokens

    def test_plan_context_formatted_is_markdown(self):
        """Test that formatted context is markdown."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(domain="auth")
        formatted = context["formatted"]

        # Should contain markdown formatting
        assert isinstance(formatted, str)
        assert "#" in formatted or len(formatted) == 0

    def test_get_past_plans(self):
        """Test getting past plans."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        past_plans = builder._get_past_plans(domain="database")
        assert isinstance(past_plans, list)

    def test_get_failed_approaches(self):
        """Test getting failed approaches."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        failed = builder._get_failed_approaches(domain="auth")
        assert isinstance(failed, list)

    def test_get_successful_patterns(self):
        """Test getting successful patterns."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        patterns = builder._get_successful_patterns(domain="database")
        assert isinstance(patterns, list)

    def test_get_calibration_data(self):
        """Test getting calibration data."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        calibration = builder._get_calibration_data(domain="api")
        assert isinstance(calibration, dict)

    def test_get_project_constraints(self):
        """Test getting project constraints."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        constraints = builder._get_project_constraints()
        assert isinstance(constraints, list)
        # Should have some default constraints
        assert len(constraints) > 0

    def test_generate_recommendations(self):
        """Test generating recommendations."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = {
            "calibration": {"confidence_gap": 0.15},
            "failed_approaches": [{"approach": "Custom JWT"}],
            "successful_patterns": [{"pattern": "PostgreSQL + Drizzle"}]
        }

        recommendations = builder._generate_recommendations(context)
        assert isinstance(recommendations, list)

    def test_format_for_injection(self):
        """Test formatting context for injection."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(domain="database", max_tokens=1500)

        formatted = context["formatted"]
        assert isinstance(formatted, str)

    def test_estimate_tokens(self):
        """Test token estimation."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = {"formatted": "This is a test context with some words"}
        tokens = builder._estimate_tokens(context)

        assert isinstance(tokens, int)
        assert tokens > 0
        # Rough estimate: 1 token ≈ 4 chars
        assert tokens == len(context["formatted"]) // 4

    def test_build_plan_context_max_tokens_respected(self):
        """Test that max tokens parameter is respected."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        # Test with small token limit
        context = builder.build_plan_context(
            domain="database",
            max_tokens=500
        )

        # Token count should not exceed max (or be very close)
        assert context["total_tokens"] <= 500 or context["total_tokens"] < 550

    def test_plan_context_has_timestamp(self):
        """Test that context has ISO timestamp."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        builder = PlanContextBuilder(graph_client, calibration_updater)

        context = builder.build_plan_context(domain="auth")

        assert "timestamp" in context
        assert isinstance(context["timestamp"], str)
        # ISO format check
        assert "T" in context["timestamp"]
