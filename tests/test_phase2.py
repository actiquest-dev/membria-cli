"""Tests for Phase 2: Outcome tracking and learning loop."""

import pytest
from datetime import datetime

from membria.outcome_models import (
    Outcome,
    OutcomeStatus,
    Signal,
    SignalType,
    SignalValence,
    OutcomeMetrics,
    AssumptionValidation,
)
from membria.outcome_tracker import OutcomeTracker


class TestOutcomeModels:
    """Test outcome data models."""

    def test_signal_creation(self):
        """Test Signal creation."""
        signal = Signal(
            signal_type=SignalType.PR_CREATED,
            valence=SignalValence.POSITIVE,
            description="PR #123 created",
        )

        assert signal.signal_type == SignalType.PR_CREATED
        assert signal.valence == SignalValence.POSITIVE
        assert signal.description == "PR #123 created"
        assert signal.timestamp is not None

    def test_outcome_creation(self):
        """Test Outcome creation."""
        outcome = Outcome(
            outcome_id="outcome_123",
            decision_id="dec_123",
            status=OutcomeStatus.PENDING,
        )

        assert outcome.outcome_id == "outcome_123"
        assert outcome.decision_id == "dec_123"
        assert outcome.status == OutcomeStatus.PENDING
        assert outcome.created_at is not None
        assert len(outcome.signals) == 0

    def test_outcome_add_signal(self):
        """Test adding signals to outcome."""
        outcome = Outcome(
            outcome_id="outcome_123",
            decision_id="dec_123",
            status=OutcomeStatus.PENDING,
        )

        outcome.add_signal(
            SignalType.PR_CREATED,
            SignalValence.POSITIVE,
            description="PR created",
        )

        assert len(outcome.signals) == 1
        assert outcome.signals[0].signal_type == SignalType.PR_CREATED

    def test_outcome_signal_counts(self):
        """Test counting signals by valence."""
        outcome = Outcome(
            outcome_id="outcome_123",
            decision_id="dec_123",
            status=OutcomeStatus.PENDING,
        )

        outcome.add_signal(SignalType.PR_CREATED, SignalValence.POSITIVE)
        outcome.add_signal(SignalType.CI_PASSED, SignalValence.POSITIVE)
        outcome.add_signal(SignalType.CI_FAILED, SignalValence.NEGATIVE)

        assert outcome.positive_signal_count() == 2
        assert outcome.negative_signal_count() == 1
        assert outcome.has_negative_signals() is True

    def test_outcome_success_estimation(self):
        """Test success score estimation from signals."""
        outcome = Outcome(
            outcome_id="outcome_123",
            decision_id="dec_123",
            status=OutcomeStatus.PENDING,
        )

        # No signals → baseline 0.5
        assert outcome.estimate_success() == 0.5

        # Add positive signals
        outcome.add_signal(SignalType.PR_CREATED, SignalValence.POSITIVE)
        outcome.add_signal(SignalType.PR_MERGED, SignalValence.POSITIVE)
        score_with_positive = outcome.estimate_success()
        assert score_with_positive > 0.5

        # Add negative signals
        outcome.add_signal(SignalType.CI_FAILED, SignalValence.NEGATIVE)
        score_with_negative = outcome.estimate_success()
        assert score_with_negative < score_with_positive

    def test_assumption_validation(self):
        """Test assumption validation."""
        assumption = AssumptionValidation(
            assumption="Fastify handles 10k req/s",
            predicted_value="10k req/s",
        )

        assert assumption.status == "unvalidated"

        # Validate that assumption held
        assumption.validate("12k req/s", matches=True)
        assert assumption.status == "validated"
        assert assumption.actual_value == "12k req/s"
        assert "Confirmed" in assumption.evidence

        # Create another and validate failure
        assumption2 = AssumptionValidation(
            assumption="Response time < 50ms",
            predicted_value="< 50ms",
        )
        assumption2.validate("120ms", matches=False)
        assert assumption2.status == "failed"
        assert "Expected" in assumption2.evidence

    def test_outcome_metrics(self):
        """Test outcome metrics evaluation."""
        metrics = OutcomeMetrics(
            uptime_percent=99.95,
            avg_latency_ms=45,
            error_rate_percent=0.1,
            bug_count=0,
            incident_count=0,
        )

        assert metrics.is_good() is True

        # Bad metrics
        bad_metrics = OutcomeMetrics(
            uptime_percent=95.0,  # Too low
            error_rate_percent=5.0,  # Too high
            bug_count=5,
        )

        assert bad_metrics.is_good() is False


class TestOutcomeTracker:
    """Test outcome tracking operations."""

    def test_create_outcome(self):
        """Test creating outcome."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        assert outcome.decision_id == "dec_123"
        assert outcome.status == OutcomeStatus.PENDING
        assert outcome.outcome_id is not None

    def test_create_outcome_with_id(self):
        """Test creating outcome with specific ID."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123", outcome_id="custom_id")

        assert outcome.outcome_id == "custom_id"

    def test_record_commit(self):
        """Test recording commit."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        updated = tracker.record_commit(
            outcome.outcome_id,
            "abc123def456",
            "Implement decision",
        )

        assert updated.commit_sha == "abc123de"
        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.PR_CREATED

    def test_record_pr_created(self):
        """Test recording PR creation."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        updated = tracker.record_pr_created(
            outcome.outcome_id,
            pr_number=456,
            pr_url="https://github.com/org/repo/pull/456",
            branch="feature/dec_123",
        )

        assert updated.status == OutcomeStatus.SUBMITTED
        assert updated.pr_number == 456
        assert updated.submitted_at is not None
        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.PR_CREATED
        assert updated.signals[0].valence == SignalValence.POSITIVE

    def test_record_pr_merged(self):
        """Test recording PR merge."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")
        tracker.record_pr_created(
            outcome.outcome_id,
            pr_number=456,
            pr_url="https://github.com/org/repo/pull/456",
            branch="feature/dec_123",
        )

        updated = tracker.record_pr_merged(outcome.outcome_id, 456)

        assert updated.status == OutcomeStatus.MERGED
        assert updated.merged_at is not None
        assert len(updated.signals) == 2
        assert updated.signals[1].signal_type == SignalType.PR_MERGED
        assert updated.signals[1].valence == SignalValence.POSITIVE

    def test_record_ci_result_passed(self):
        """Test recording passing CI."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        updated = tracker.record_ci_result(
            outcome.outcome_id,
            passed=True,
            details="All 42 tests passed",
        )

        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.CI_PASSED
        assert updated.signals[0].valence == SignalValence.POSITIVE

    def test_record_ci_result_failed(self):
        """Test recording failing CI."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        updated = tracker.record_ci_result(
            outcome.outcome_id,
            passed=False,
            details="3 tests failed",
        )

        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.CI_FAILED
        assert updated.signals[0].valence == SignalValence.NEGATIVE

    def test_record_incident(self):
        """Test recording incident."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        updated = tracker.record_incident(
            outcome.outcome_id,
            severity="high",
            description="API timeout under load",
        )

        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.INCIDENT
        assert updated.signals[0].valence == SignalValence.NEGATIVE
        assert updated.signals[0].severity == "high"

    def test_record_performance(self):
        """Test recording performance metrics."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        metrics = {
            "avg_latency_ms": 45,
            "throughput_rps": 12000,
        }

        updated = tracker.record_performance(outcome.outcome_id, metrics)

        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.PERFORMANCE_OK
        assert updated.signals[0].valence == SignalValence.POSITIVE
        assert updated.signals[0].metrics == metrics

    def test_record_poor_performance(self):
        """Test recording poor performance."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        metrics = {
            "avg_latency_ms": 500,
            "throughput_rps": 100,
        }

        updated = tracker.record_performance(outcome.outcome_id, metrics)

        assert len(updated.signals) == 1
        assert updated.signals[0].signal_type == SignalType.PERFORMANCE_POOR
        assert updated.signals[0].valence == SignalValence.NEGATIVE

    def test_check_success_criteria(self):
        """Test success criteria assessment."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        # Add mixed signals
        tracker.record_ci_result(outcome.outcome_id, passed=True)
        tracker.record_incident(outcome.outcome_id, severity="low", description="Minor issue")

        assessment = tracker.check_success_criteria(outcome.outcome_id)

        assert assessment["outcome_id"] == outcome.outcome_id
        assert assessment["positive_signals"] == 1
        assert assessment["negative_signals"] == 1
        assert "estimated_success" in assessment
        assert assessment["needs_attention"] is True

    def test_finalize_outcome(self):
        """Test outcome finalization."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        # Add some signals
        tracker.record_pr_merged(outcome.outcome_id, 123)
        tracker.record_ci_result(outcome.outcome_id, passed=True)

        finalized = tracker.finalize_outcome(
            outcome.outcome_id,
            final_status="success",
            final_score=0.85,
            lessons_learned=[
                "Fastify handles 15k req/s",
                "Team learned in 3 days",
            ],
        )

        assert finalized.status == OutcomeStatus.COMPLETED
        assert finalized.final_status == "success"
        assert finalized.final_score == 0.85
        assert finalized.completed_at is not None
        assert len(finalized.lessons_learned) == 2

    def test_get_outcome(self):
        """Test retrieving outcome by ID."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")

        retrieved = tracker.get_outcome(outcome.outcome_id)

        assert retrieved is not None
        assert retrieved.outcome_id == outcome.outcome_id
        assert retrieved.decision_id == "dec_123"

    def test_get_nonexistent_outcome(self):
        """Test retrieving nonexistent outcome."""
        tracker = OutcomeTracker()

        retrieved = tracker.get_outcome("nonexistent")

        assert retrieved is None

    def test_list_outcomes(self):
        """Test listing outcomes."""
        tracker = OutcomeTracker()

        # Create multiple outcomes
        outcome1 = tracker.create_outcome("dec_123")
        outcome2 = tracker.create_outcome("dec_123")
        outcome3 = tracker.create_outcome("dec_456")

        all_outcomes = tracker.list_outcomes()
        assert len(all_outcomes) == 3

        # Filter by decision
        dec_123_outcomes = tracker.list_outcomes(decision_id="dec_123")
        assert len(dec_123_outcomes) == 2

        # Filter by status
        pending_outcomes = tracker.list_outcomes(status=OutcomeStatus.PENDING)
        assert len(pending_outcomes) == 3

    def test_list_outcomes_filter_status(self):
        """Test filtering outcomes by status."""
        tracker = OutcomeTracker()

        outcome1 = tracker.create_outcome("dec_123")
        outcome2 = tracker.create_outcome("dec_456")

        # Update one to merged
        tracker.record_pr_created(outcome1.outcome_id, 123, "https://...", "main")
        tracker.record_pr_merged(outcome1.outcome_id, 123)

        pending = tracker.list_outcomes(status=OutcomeStatus.PENDING)
        merged = tracker.list_outcomes(status=OutcomeStatus.MERGED)

        assert len(pending) == 1
        assert len(merged) == 1

    def test_export_outcome(self):
        """Test outcome export as dict."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_123")
        tracker.record_pr_created(outcome.outcome_id, 456, "https://...", "main")
        tracker.record_ci_result(outcome.outcome_id, passed=True)

        exported = tracker.export_outcome(outcome.outcome_id)

        assert exported["outcome_id"] == outcome.outcome_id
        assert exported["decision_id"] == "dec_123"
        assert exported["pr_number"] == 456
        assert len(exported["signals"]) == 2
        assert all(isinstance(s["signal_type"], str) for s in exported["signals"])
        assert all(isinstance(s["valence"], str) for s in exported["signals"])

    def test_export_nonexistent_outcome(self):
        """Test exporting nonexistent outcome."""
        tracker = OutcomeTracker()

        with pytest.raises(ValueError):
            tracker.export_outcome("nonexistent")

    def test_complete_outcome_lifecycle(self):
        """Test complete outcome tracking lifecycle."""
        tracker = OutcomeTracker()

        # Create outcome
        outcome = tracker.create_outcome("dec_123")
        assert outcome.status == OutcomeStatus.PENDING

        # Record PR creation
        tracker.record_pr_created(
            outcome.outcome_id,
            pr_number=789,
            pr_url="https://github.com/org/repo/pull/789",
            branch="feature/fastify",
        )
        outcome = tracker.get_outcome(outcome.outcome_id)
        assert outcome.status == OutcomeStatus.SUBMITTED

        # Record CI pass
        tracker.record_ci_result(outcome.outcome_id, passed=True, details="All 50 tests passed")

        # Record performance
        tracker.record_performance(
            outcome.outcome_id,
            {
                "avg_latency_ms": 45,
                "throughput_rps": 15000,
            },
        )

        # Record PR merge
        tracker.record_pr_merged(outcome.outcome_id, 789)
        outcome = tracker.get_outcome(outcome.outcome_id)
        assert outcome.status == OutcomeStatus.MERGED

        # Finalize after 30 days
        tracker.finalize_outcome(
            outcome.outcome_id,
            final_status="success",
            final_score=0.92,
            lessons_learned=[
                "Fastify handles 15k req/s (exceeds 10k assumption)",
                "Team productivity improved by 20%",
            ],
        )

        outcome = tracker.get_outcome(outcome.outcome_id)
        assert outcome.status == OutcomeStatus.COMPLETED
        assert outcome.final_score == 0.92
        assert len(outcome.lessons_learned) == 2
        assert len(outcome.signals) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
