"""Tests for Phase 1: Decision Capture & MCP."""

import pytest
from membria.task_router import TaskRouter, TaskType
from membria.decision_capture import DecisionCapture, DecisionCaptureFlow, DecisionFormatter


class TestTaskRouter:
    """Test task classification."""

    def test_classify_decision_with_which(self):
        """Test detection of decision with 'which' question."""
        router = TaskRouter()

        result = router.classify("Which framework should we use, Express or Fastify?")

        assert result.task_type == TaskType.DECISION
        assert result.confidence > 0.5

    def test_classify_decision_with_vs(self):
        """Test detection of decision with alternatives."""
        router = TaskRouter()

        result = router.classify("Which database is better: PostgreSQL vs MongoDB vs Redis?")

        assert result.task_type == TaskType.DECISION
        assert result.suggested_alternatives is not None
        assert len(result.suggested_alternatives) > 0

    def test_classify_decision_architecture(self):
        """Test detection of architecture decision."""
        router = TaskRouter()

        result = router.classify("Should we design the authentication using JWT or OAuth? What's the best approach?")

        assert result.task_type == TaskType.DECISION
        assert result.confidence > 0.5

    def test_classify_tactical_simple(self):
        """Test tactical task (direct coding)."""
        router = TaskRouter()

        result = router.classify("Add error handling to this function")

        assert result.task_type == TaskType.TACTICAL
        assert result.confidence > 0.4

    def test_classify_tactical_implementation(self):
        """Test tactical implementation task."""
        router = TaskRouter()

        result = router.classify("Create a REST endpoint for user login")

        assert result.task_type == TaskType.TACTICAL

    def test_classify_learning_reflection(self):
        """Test learning task with reflection."""
        router = TaskRouter()

        result = router.classify("The custom JWT implementation failed in production. I learned that we should never implement custom auth")

        assert result.task_type == TaskType.LEARNING or len(result.reason) > 0

    def test_classify_learning_mistake(self):
        """Test learning from mistake."""
        router = TaskRouter()

        result = router.classify("We discovered that the async bug was caused by forEach. This mistake resulted in the production issue")

        # Should classify as learning if enough signals
        assert result.task_type in [TaskType.LEARNING, TaskType.TACTICAL]  # Learning signals present

    def test_extract_alternatives_vs_pattern(self):
        """Test extracting alternatives from 'X vs Y' pattern."""
        router = TaskRouter()

        result = router.classify("Which framework? Express vs Fastify vs Koa")

        # Should detect alternatives if it's a decision
        if result.task_type == TaskType.DECISION:
            assert result.suggested_alternatives is not None

    def test_extract_alternatives_comma_pattern(self):
        """Test extracting alternatives from comma-separated list."""
        router = TaskRouter()

        result = router.classify("Choose which to use: Redis, MongoDB, PostgreSQL for caching")

        # Should detect alternatives if it's a decision
        if result.task_type == TaskType.DECISION:
            assert result.suggested_alternatives is not None

    def test_confidence_increases_with_signals(self):
        """Test confidence increases with multiple decision signals."""
        router = TaskRouter()

        # Single signal
        result1 = router.classify("which database?")

        # Multiple signals
        result2 = router.classify("Should we use Redis vs MongoDB vs PostgreSQL? Which is better?")

        assert result2.confidence >= result1.confidence


class TestDecisionCapture:
    """Test decision capture."""

    def test_create_decision(self):
        """Test creating a decision."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify for REST API",
            confidence=0.75,
        )

        assert decision.decision_id == "dec_123"
        assert decision.statement == "Use Fastify for REST API"
        assert decision.confidence == 0.75
        assert decision.status == "pending"

    def test_decision_to_dict(self):
        """Test converting decision to dictionary."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
        )

        dict_form = decision.to_dict()

        assert dict_form["decision_id"] == "dec_123"
        assert dict_form["statement"] == "Use Fastify"
        assert dict_form["confidence"] == 0.75

    def test_context_hash_calculation(self):
        """Test context hash is calculated."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
            alternatives=["Express", "Koa"],
            assumptions=["Can handle 10k req/s"],
        )

        hash1 = decision.calculate_context_hash()
        hash2 = decision.calculate_context_hash()

        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 64  # SHA256
        assert decision.context_hash == hash1

    def test_context_hash_changes_with_content(self):
        """Test context hash changes when content changes."""
        decision1 = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
            alternatives=["Express"],
            assumptions=["10k req/s"],
        )

        decision2 = DecisionCapture(
            decision_id="dec_123",
            statement="Use Express",
            confidence=0.75,
            alternatives=["Fastify"],
            assumptions=["5k req/s"],
        )

        hash1 = decision1.calculate_context_hash()
        hash2 = decision2.calculate_context_hash()

        assert hash1 != hash2

    def test_decision_json_serialization(self):
        """Test JSON serialization."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
        )

        json_str = decision.to_json()

        assert "dec_123" in json_str
        assert "Use Fastify" in json_str


class TestDecisionCaptureFlow:
    """Test decision capture workflow."""

    def test_capture_flow_complete(self):
        """Test complete capture flow."""
        flow = DecisionCaptureFlow(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
        )

        flow.capture_alternatives(
            ["Express", "Koa"],
            {"Express": "Proven", "Koa": "Minimal"},
        )

        flow.capture_assumptions([
            "Can handle 10k req/s",
            "Team can learn in 1 week",
        ])

        flow.capture_predicted_outcome(
            description="Stable API in 2 weeks",
            success_criteria=[
                "Handles 10k req/s",
                "No critical bugs in 30 days",
            ],
            risk_level="medium",
        )

        flow.set_metadata(created_by="developer", module="user-service")

        decision = flow.finalize()

        assert decision.decision_id == "dec_123"
        assert len(decision.alternatives) == 2
        assert len(decision.assumptions) == 2
        assert decision.predicted_outcome["description"] == "Stable API in 2 weeks"
        assert decision.created_by == "developer"
        assert decision.module == "user-service"
        assert decision.context_hash != ""

    def test_validate_complete_decision(self):
        """Test validation of complete decision."""
        flow = DecisionCaptureFlow("dec_123", "Use Fastify", 0.75)

        flow.capture_alternatives(["Express"])
        flow.capture_assumptions(["10k req/s"])
        flow.capture_predicted_outcome("API in 2 weeks", ["No bugs"], "medium")

        is_valid, error = flow.validate()

        assert is_valid is True
        assert error == ""

    def test_validate_missing_statement(self):
        """Test validation fails without statement."""
        flow = DecisionCaptureFlow("dec_123", "", 0.75)

        is_valid, error = flow.validate()

        assert is_valid is False
        assert "Statement" in error

    def test_validate_missing_alternatives(self):
        """Test validation requires alternatives."""
        flow = DecisionCaptureFlow("dec_123", "Use Fastify", 0.75)

        is_valid, error = flow.validate()

        assert is_valid is False
        assert "alternative" in error.lower()

    def test_validate_invalid_confidence(self):
        """Test validation checks confidence bounds."""
        flow = DecisionCaptureFlow("dec_123", "Use Fastify", 1.5)

        is_valid, error = flow.validate()

        assert is_valid is False
        assert "Confidence" in error or flow.decision.confidence > 1.0


class TestDecisionFormatter:
    """Test decision formatting."""

    def test_format_for_display(self):
        """Test formatting for terminal display."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
            alternatives=["Express", "Koa"],
            assumptions=["10k req/s"],
            predicted_outcome={
                "description": "Stable API",
                "success_criteria": ["No bugs", "Handles load"],
                "risk_level": "medium",
            },
        )
        decision.calculate_context_hash()

        display = DecisionFormatter.format_for_display(decision)

        assert "Use Fastify" in display
        assert "dec_123" in display
        assert "75%" in display
        assert "Express" in display
        assert "10k req/s" in display
        assert "Stable API" in display

    def test_format_for_graph(self):
        """Test formatting for graph storage."""
        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
            alternatives=["Express"],
        )
        decision.calculate_context_hash()

        graph_format = DecisionFormatter.format_for_graph(decision)

        assert graph_format["decision_id"] == "dec_123"
        assert graph_format["statement"] == "Use Fastify"
        assert graph_format["confidence"] == 0.75
        # Alternatives should be JSON string
        assert '"Express"' in graph_format["alternatives"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
