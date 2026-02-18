"""Tests for Phase 1 advanced features: Context injection and validation."""

import pytest
from membria.context_injector import ContextInjector, InjectionContext
from membria.decision_capture import DecisionCapture
from membria.decision_surface import DecisionContext
from membria.validators import DecisionConsistencyValidator, ValidatorChain
from membria.task_router import TaskType


class TestContextInjector:
    """Test context compilation for injection."""

    def test_compile_injection_decision_type(self):
        """Test compilation for DECISION type task."""
        injector = ContextInjector()

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify for REST API",
            confidence=0.75,
            alternatives=["Express", "Koa"],
            assumptions=["Handles 10k req/s"],
        )

        injection = injector.compile_injection(
            task_type=TaskType.DECISION,
            decision=decision,
        )

        assert injection.decision_statement == "Use Fastify for REST API"
        assert len(injection.constraints) > 0
        assert len(injection.assumptions) > 0

    def test_compile_injection_tactical_type(self):
        """Test no injection for TACTICAL type."""
        injector = ContextInjector()

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Add error handling",
            confidence=0.8,
        )

        injection = injector.compile_injection(
            task_type=TaskType.TACTICAL,
            decision=decision,
        )

        assert injection.decision_statement is None

    def test_extract_constraints(self):
        """Test constraint extraction from decision."""
        injector = ContextInjector()

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify",
            confidence=0.75,
            alternatives=["Express", "Koa"],
        )

        constraints = injector._extract_constraints(decision)

        assert any("Fastify" in c for c in constraints)
        assert any("Express" in c for c in constraints)

    def test_generate_system_prompt(self):
        """Test system prompt generation."""
        injector = ContextInjector()

        injection = InjectionContext(
            decision_statement="Use Fastify",
            decision_id="dec_123",
            constraints=["Use Fastify", "Avoid Express"],
            team_patterns=["Use /api/v1/ prefix"],
            assumptions=["10k req/s"],
        )

        prompt = injector.generate_system_prompt(injection)

        assert "Use Fastify" in prompt
        assert "dec_123" in prompt
        assert "/api/v1/" in prompt
        assert "10k req/s" in prompt

    def test_claude_code_integration_prompt(self):
        """Test full Claude Code integration prompt."""
        injector = ContextInjector()

        injection = InjectionContext(
            decision_statement="Use Fastify",
            constraints=["Use Fastify"],
        )

        prompt = injector.get_claude_code_integration_prompt(injection)

        assert "decision" in prompt.lower()
        assert "Claude Code" in prompt or "developer" in prompt.lower()

    def test_generate_calibration_warnings(self):
        """Test warning generation from calibration."""
        injector = ContextInjector()

        calibration = {
            "domain": "framework_choice",
            "avg_confidence": 0.78,
            "actual_success": 0.61,
            "overconfidence": 0.17,
            "sample_size": 45,
        }

        warnings = injector._generate_calibration_warnings(calibration)

        assert len(warnings) > 0
        assert "overconfident" in warnings[0].lower() or "OVERCONFIDENT" in warnings[0]


class TestDecisionConsistencyValidator:
    """Test code validation against decision."""

    def test_validate_code_matches_decision_success(self):
        """Test validation passes when code matches decision."""
        validator = DecisionConsistencyValidator()

        code = """
import fastify from 'fastify';
const app = fastify();
const server = app.listen(3000);
app.get('/', (req, reply) => {
  reply.send({ hello: 'world' });
});
"""

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify REST",
            confidence=0.75,
            alternatives=["Express"],
        )

        result = validator.validate_code_matches_decision(code, decision)

        # Should have reasonable score due to "Fastify" and "REST" (via listen/app) keywords
        assert result.score >= 0.5

    def test_validate_code_matches_decision_failure(self):
        """Test validation fails when code doesn't match decision."""
        validator = DecisionConsistencyValidator()

        code = """
import express from 'express';
const app = express();
"""

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify for REST API",
            confidence=0.75,
            alternatives=["Express"],
        )

        result = validator.validate_code_matches_decision(code, decision)

        assert len(result.failures) > 0

    def test_validate_negative_knowledge_respected(self):
        """Test validation detects antipatterns."""
        validator = DecisionConsistencyValidator()

        code = "class CustomJWT { } eval()"
        negative_patterns = ["custom_jwt", "eval"]

        result = validator.validate_negative_knowledge_respected(code, negative_patterns)

        # Should detect "eval" which is exact match in lowercase
        assert len(result.failures) > 0
        assert result.is_valid is False

    def test_validate_negative_knowledge_clean(self):
        """Test validation passes when code is clean."""
        validator = DecisionConsistencyValidator()

        code = "const token = jwt.sign(payload, secret);"
        negative_patterns = ["custom_jwt", "eval", "danger"]

        result = validator.validate_negative_knowledge_respected(code, negative_patterns)

        assert len(result.failures) == 0
        assert result.is_valid is True

    def test_validate_code_quality(self):
        """Test code quality validation."""
        validator = DecisionConsistencyValidator()

        good_code = """
try {
  const user = validateInput(input);
  logger.info('User created');
  // Handle creation
} catch (error) {
  console.error(error);
}
"""

        result = validator.validate_code_quality(good_code)

        # Should pass multiple quality checks
        assert result.score > 0.5

    def test_validate_code_quality_poor(self):
        """Test poor quality code."""
        validator = DecisionConsistencyValidator()

        poor_code = "x = y + z"

        result = validator.validate_code_quality(poor_code)

        # Should have low quality score
        assert result.score < 1.0


class TestValidatorChain:
    """Test integrated validation."""

    def test_validate_implementation_complete(self):
        """Test complete validation flow."""
        chain = ValidatorChain()

        code = """
import fastify from 'fastify';
// Decision: Use Fastify for REST API
const app = fastify();

try {
  // Validate input
  const user = validateUser(req.body);

  app.get('/users', (req, reply) => {
    logger.info('Fetching users');
    reply.send(users);
  });
} catch (error) {
  console.error(error);
}
"""

        decision = DecisionCapture(
            decision_id="dec_123",
            statement="Use Fastify for REST API",
            confidence=0.75,
            alternatives=["Express"],
            assumptions=["Handles 10k req/s"],
        )

        result = chain.validate_implementation(
            code=code,
            decision=decision,
            negative_patterns=["custom_jwt"],
        )

        assert result.score > 0.5
        assert len(result.checks) > 0

    def test_format_validation_results(self):
        """Test result formatting."""
        from membria.validators import ValidationResult

        chain = ValidatorChain()

        result = ValidationResult(
            is_valid=True,
            checks=["Check 1", "Check 2"],
            failures=[],
            warnings=["Warning 1"],
            score=0.85,
        )

        formatted = chain.format_results(result)

        assert "PASSED" in formatted
        assert "85%" in formatted
        assert "Check 1" in formatted
        assert "Warning 1" in formatted

    def test_format_validation_failures(self):
        """Test failure result formatting."""
        from membria.validators import ValidationResult

        chain = ValidatorChain()

        result = ValidationResult(
            is_valid=False,
            checks=["Check 1"],
            failures=["Failure 1"],
            warnings=[],
            score=0.3,
        )

        formatted = chain.format_results(result)

        assert "FAILED" in formatted
        assert "30%" in formatted
        assert "Failure 1" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
