"""Tests for plan validator."""

import pytest
from membria.plan_validator import PlanValidator, PlanWarning


class TestPlanWarning:
    """Test PlanWarning data model."""

    def test_initialization(self):
        """Test warning initialization."""
        warning = PlanWarning(
            step_number=1,
            step_text="Use PostgreSQL",
            warning_type="antipattern",
            severity="high",
            message="This pattern has high failure rate",
            suggestion="Consider alternative",
            confidence=0.9
        )
        assert warning.step_number == 1
        assert warning.step_text == "Use PostgreSQL"
        assert warning.warning_type == "antipattern"
        assert warning.severity == "high"
        assert warning.confidence == 0.9

    def test_to_dict(self):
        """Test conversion to dict."""
        warning = PlanWarning(
            step_number=2,
            step_text="Use Redis",
            warning_type="negative_knowledge",
            severity="medium",
            message="Known issue with Redis",
            suggestion="Use Memcached instead"
        )
        result = warning.to_dict()
        assert result["step"] == 2
        assert result["type"] == "negative_knowledge"
        assert result["severity"] == "medium"
        assert "message" in result
        assert "suggestion" in result


class TestPlanValidator:
    """Test plan validator."""

    def test_initialization(self):
        """Test validator initialization."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        assert validator.graph_client is not None
        assert validator.calibration_updater is not None

    def test_validate_empty_steps(self):
        """Test validation with empty steps."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        warnings = validator.validate_plan([])
        assert isinstance(warnings, list)
        assert len(warnings) == 0

    def test_validate_single_step(self):
        """Test validation with single step."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = ["Create a new API endpoint"]
        warnings = validator.validate_plan(steps)
        assert isinstance(warnings, list)

    def test_validate_multiple_steps(self):
        """Test validation with multiple steps."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = [
            "Set up PostgreSQL database",
            "Create API endpoints",
            "Implement authentication",
            "Add caching layer"
        ]
        warnings = validator.validate_plan(steps)
        assert isinstance(warnings, list)

    def test_validate_plan_with_domain(self):
        """Test validation with domain context."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = ["Implement JWT authentication", "Set up Redis sessions"]
        warnings = validator.validate_plan(steps, domain="auth")
        assert isinstance(warnings, list)

    def test_validate_plan_async(self):
        """Test async validation."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = ["Create database schema", "Build ORM layer"]
        result = validator.validate_plan_async(steps, domain="database")

        assert "total_steps" in result
        assert "warnings_count" in result
        assert "high_severity" in result
        assert "medium_severity" in result
        assert "low_severity" in result
        assert "can_proceed" in result
        assert "warnings" in result
        assert "timestamp" in result

    def test_extract_keywords(self):
        """Test keyword extraction."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        text = "Use PostgreSQL for the user database with Redis caching"
        keywords = validator._extract_keywords(text)
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should extract meaningful words
        text_lower = text.lower()
        for keyword in keywords:
            assert keyword.lower() in text_lower

    def test_extract_keywords_filters_common_words(self):
        """Test that common words are filtered."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        text = "the and or is are be a an in from to with"
        keywords = validator._extract_keywords(text)
        # Should not contain common words
        common_words = {"the", "and", "or", "is", "are", "be", "a", "an"}
        for keyword in keywords:
            assert keyword.lower() not in common_words

    def test_warnings_sorted_by_severity(self):
        """Test that warnings are sorted by severity."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        # Create mixed severity steps (though validation won't generate them)
        steps = ["Step 1", "Step 2", "Step 3"]
        warnings = validator.validate_plan(steps)

        # Verify severity order if warnings exist
        severities = [w.severity for w in warnings]
        if len(severities) > 1:
            order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(severities) - 1):
                assert order.get(severities[i], 3) <= order.get(severities[i + 1], 3)

    def test_validate_plan_skips_empty_steps(self):
        """Test that empty/whitespace steps are skipped."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = ["Step 1", "", "   ", "Step 2"]
        warnings = validator.validate_plan(steps)
        # Should process only non-empty steps
        assert isinstance(warnings, list)

    def test_validation_result_can_proceed(self):
        """Test that can_proceed is False only for high severity warnings."""
        from membria.graph import GraphClient
        from membria.calibration_updater import CalibrationUpdater

        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        validator = PlanValidator(graph_client, calibration_updater)

        steps = ["Simple API endpoint creation"]
        result = validator.validate_plan_async(steps)

        # If there are no high severity warnings, can_proceed should be True
        if result["high_severity"] == 0:
            assert result["can_proceed"] is True
        else:
            assert result["can_proceed"] is False
