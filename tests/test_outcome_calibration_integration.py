"""Tests for OutcomeTracker and CalibrationUpdater integration."""

import pytest
from membria.outcome_tracker import OutcomeTracker
from membria.outcome_models import Outcome, OutcomeStatus
from membria.calibration_updater import CalibrationUpdater
from membria.calibration_models import TeamCalibration


class TestOutcomeTrackerCalibrationIntegration:
    """Test integration of outcome tracking with calibration updates."""

    def test_outcome_tracker_initializes_calibration_updater(self):
        """Test that OutcomeTracker creates CalibrationUpdater if not provided."""
        tracker = OutcomeTracker()
        assert tracker.calibration_updater is not None
        assert isinstance(tracker.calibration_updater, CalibrationUpdater)

    def test_outcome_tracker_uses_provided_calibration_updater(self):
        """Test that OutcomeTracker uses provided CalibrationUpdater."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)
        assert tracker.calibration_updater is updater

    def test_finalize_outcome_without_domain(self):
        """Test finalizing outcome without domain (graceful skip)."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_test")

        # Finalize without domain
        result = tracker.finalize_outcome(
            outcome.outcome_id,
            final_status="success",
            final_score=0.8
        )

        assert result.final_status == "success"
        assert result.final_score == 0.8
        # Calibration not updated since no domain provided

    def test_finalize_outcome_with_domain_updates_calibration(self):
        """Test that finalizing outcome with domain updates calibration."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)

        # Create and finalize outcome
        outcome = tracker.create_outcome("dec_api_001")
        tracker.finalize_outcome(
            outcome.outcome_id,
            final_status="success",
            final_score=0.9,
            decision_domain="api"
        )

        # Verify calibration was updated
        assert "api" in team_cal.calibrations
        api_dist = team_cal.calibrations["api"]
        assert api_dist.alpha == 2.0  # 1 initial + 1 success
        assert api_dist.beta == 1.0   # 1 initial

    def test_multiple_outcomes_accumulate_calibration(self):
        """Test that multiple outcomes accumulate into calibration metrics."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)

        # Finalize multiple outcomes
        for i in range(3):
            outcome = tracker.create_outcome(f"dec_db_{i:03d}")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="success",
                final_score=0.85,
                decision_domain="database"
            )

        for i in range(2):
            outcome = tracker.create_outcome(f"dec_db_fail_{i:03d}")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="failure",
                final_score=0.3,
                decision_domain="database"
            )

        # Verify calibration
        assert "database" in team_cal.calibrations
        db_dist = team_cal.calibrations["database"]
        assert db_dist.alpha == 4.0  # 1 initial + 3 successes
        assert db_dist.beta == 3.0   # 1 initial + 2 failures
        assert db_dist.sample_size == 5
        assert db_dist.mean == 4.0 / 7.0  # 0.571

    def test_calibration_guidance_with_outcome_data(self):
        """Test that guidance reflects outcomes from tracker."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)

        # Record successful outcomes
        for _ in range(8):
            outcome = tracker.create_outcome("dec_auth")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="success",
                final_score=0.95,
                decision_domain="auth"
            )

        for _ in range(2):
            outcome = tracker.create_outcome("dec_auth_fail")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="failure",
                final_score=0.2,
                decision_domain="auth"
            )

        # Get guidance
        guidance = updater.get_confidence_guidance("auth", decision_confidence=0.75)

        assert guidance["status"] == "data_available"
        assert guidance["sample_size"] == 10
        assert guidance["actual_success_rate"] == pytest.approx(0.75, abs=0.01)  # 9/12 = 0.75
        assert guidance["confidence_gap"] == 0.0  # Perfectly calibrated
        # No recommendation for perfect calibration

    def test_overconfident_detection_via_tracker(self):
        """Test overconfidence detection through outcome tracking."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)

        # Record 60% success despite high confidence assumptions
        for _ in range(3):
            outcome = tracker.create_outcome("dec_perf")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="success",
                final_score=0.85,
                decision_domain="performance"
            )

        for _ in range(2):
            outcome = tracker.create_outcome("dec_perf_fail")
            tracker.finalize_outcome(
                outcome.outcome_id,
                final_status="failure",
                final_score=0.25,
                decision_domain="performance"
            )

        # Get guidance with high confidence
        guidance = updater.get_confidence_guidance("performance", decision_confidence=0.85)

        assert guidance["status"] == "data_available"
        # 3 successes + 2 failures = alpha=4, beta=3, mean=4/7≈0.571, gap=0.85-0.571≈0.279
        assert guidance["confidence_gap"] == pytest.approx(0.279, abs=0.01)  # Overconfident
        assert guidance["sample_size"] == 5
        assert "overconfident" in guidance["recommendation"].lower()

    def test_calibration_error_handling(self):
        """Test that outcome finalization continues even if calibration fails."""
        tracker = OutcomeTracker()
        outcome = tracker.create_outcome("dec_test")

        # This should not raise even if calibration update fails
        result = tracker.finalize_outcome(
            outcome.outcome_id,
            final_status="success",
            final_score=0.7,
            decision_domain="api"  # Domain will still be processed
        )

        assert result.final_status == "success"
        assert result.status == OutcomeStatus.COMPLETED

    def test_domain_specific_calibration_isolation(self):
        """Test that different domains maintain separate calibration."""
        team_cal = TeamCalibration()
        updater = CalibrationUpdater(team_cal)
        tracker = OutcomeTracker(calibration_updater=updater)

        # Database: 3 successes, 1 failure
        for _ in range(3):
            outcome = tracker.create_outcome("dec_db")
            tracker.finalize_outcome(outcome.outcome_id, final_status="success", decision_domain="database")

        outcome = tracker.create_outcome("dec_db_fail")
        tracker.finalize_outcome(outcome.outcome_id, final_status="failure", decision_domain="database")

        # API: 1 success, 3 failures
        outcome = tracker.create_outcome("dec_api_ok")
        tracker.finalize_outcome(outcome.outcome_id, final_status="success", decision_domain="api")

        for _ in range(3):
            outcome = tracker.create_outcome("dec_api_fail")
            tracker.finalize_outcome(outcome.outcome_id, final_status="failure", decision_domain="api")

        # Verify isolation
        db_dist = team_cal.calibrations["database"]
        api_dist = team_cal.calibrations["api"]

        assert db_dist.mean > 0.65  # ~0.75 for database
        assert api_dist.mean < 0.4   # ~0.25 for API
        assert db_dist.sample_size == 4
        assert api_dist.sample_size == 4
