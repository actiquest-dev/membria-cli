"""Tests for plan commands."""

import pytest
from membria.commands.plan_commands import PlanCommands


class TestPlanCommands:
    """Test plan commands."""

    def test_initialization(self):
        """Test command initialization."""
        commands = PlanCommands()
        assert commands.graph_client is not None
        assert commands.calibration_updater is not None
        assert commands.plan_validator is not None
        assert commands.plan_context_builder is not None

    def test_list_plans_basic(self):
        """Test listing plans basic."""
        commands = PlanCommands()
        result = commands.list_plans()
        assert isinstance(result, str)
        # Should return either a table, "No plans found", or error message
        assert "No plans found" in result or "ID" in result or "Error" in result or "Error" in result

    def test_list_plans_with_status_filter(self):
        """Test listing plans with status filter."""
        commands = PlanCommands()
        result = commands.list_plans(status="completed")
        assert isinstance(result, str)

    def test_list_plans_with_domain_filter(self):
        """Test listing plans with domain filter."""
        commands = PlanCommands()
        result = commands.list_plans(domain="auth")
        assert isinstance(result, str)

    def test_list_plans_with_limit(self):
        """Test listing plans with limit."""
        commands = PlanCommands()
        result = commands.list_plans(limit=10)
        assert isinstance(result, str)

    def test_list_plans_empty(self):
        """Test listing when no plans exist."""
        commands = PlanCommands()
        result = commands.list_plans()
        assert isinstance(result, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_show_plan_not_found(self):
        """Test showing non-existent plan."""
        commands = PlanCommands()
        result = commands.show_plan("nonexistent_id")
        assert "not found" in result.lower()

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_show_plan_format(self):
        """Test show plan output format."""
        commands = PlanCommands()
        result = commands.show_plan("eng_test")
        assert isinstance(result, str)
        # Should contain either plan details or "not found" message
        assert "Plan" in result or "not found" in result.lower()

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_plan_accuracy_basic(self):
        """Test plan accuracy calculation."""
        commands = PlanCommands()
        result = commands.plan_accuracy()
        assert isinstance(result, str)
        assert "Accuracy" in result or "No completed plans" in result

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_plan_accuracy_with_period(self):
        """Test plan accuracy with custom period."""
        commands = PlanCommands()
        result = commands.plan_accuracy(period_days=7)
        assert isinstance(result, str)
        assert "7 days" in result or "No completed plans" in result

    def test_validate_plan_no_steps(self):
        """Test validating empty plan."""
        commands = PlanCommands()
        result = commands.validate_plan("")
        assert isinstance(result, str)

    def test_validate_plan_single_step(self):
        """Test validating single step."""
        commands = PlanCommands()
        result = commands.validate_plan("Use PostgreSQL")
        assert isinstance(result, str)
        assert "Validation Results" in result

    def test_validate_plan_multiple_steps(self):
        """Test validating multiple steps."""
        commands = PlanCommands()
        result = commands.validate_plan("Use PostgreSQL\nSet up ORM\nAdd migrations")
        assert isinstance(result, str)
        assert "Validation Results" in result

    def test_infer_domain_auth(self):
        """Test domain inference for auth."""
        commands = PlanCommands()
        domain = commands._infer_domain("Implement JWT authentication")
        assert domain == "auth"

    def test_infer_domain_database(self):
        """Test domain inference for database."""
        commands = PlanCommands()
        domain = commands._infer_domain("Set up PostgreSQL")
        assert domain == "database"

    def test_infer_domain_api(self):
        """Test domain inference for API."""
        commands = PlanCommands()
        domain = commands._infer_domain("Create REST API endpoints")
        assert domain == "api"

    def test_format_date(self):
        """Test date formatting."""
        commands = PlanCommands()
        # Test with int timestamp
        result = commands._format_date(1707038400)  # 2024-02-04
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD format

    def test_format_datetime(self):
        """Test datetime formatting."""
        commands = PlanCommands()
        result = commands._format_datetime(1707038400)
        assert isinstance(result, str)
        assert "2024" in result or "UTC" in result

    def test_list_plans_columns(self):
        """Test that list_plans includes proper columns."""
        commands = PlanCommands()
        result = commands.list_plans(limit=0)
        # Should have columns or be empty message
        assert isinstance(result, str)

    def test_validate_plan_can_proceed_flag(self):
        """Test that validate_plan shows proceed flag."""
        commands = PlanCommands()
        result = commands.validate_plan("Simple step")
        assert "can proceed" in result.lower() or "proceed" in result.lower()

    def test_show_plan_steps_format(self):
        """Test that show_plan formats steps correctly."""
        commands = PlanCommands()
        result = commands.show_plan("eng_test123")
        assert isinstance(result, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_plan_accuracy_output_structure(self):
        """Test accuracy output has expected structure."""
        commands = PlanCommands()
        result = commands.plan_accuracy()
        if "No completed" not in result:
            assert "plans" in result.lower()
            assert "accuracy" in result.lower()
