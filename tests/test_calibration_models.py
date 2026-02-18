"""Tests for calibration models and updater."""

import pytest
from membria.calibration_models import BetaDistribution, CalibrationProfile, TeamCalibration
from membria.calibration_updater import CalibrationUpdater


class TestBetaDistribution:
    """Test Beta distribution model."""

    def test_initialization(self):
        """Test default initialization."""
        beta = BetaDistribution(domain="database")
        assert beta.domain == "database"
        assert beta.alpha == 1.0
        assert beta.beta == 1.0
        assert beta.mean == 0.5

    def test_update_success(self):
        """Test successful outcome update."""
        beta = BetaDistribution(domain="api")
        beta.update_success()
        assert beta.alpha == 2.0
        assert beta.beta == 1.0

    def test_update_failure(self):
        """Test failed outcome update."""
        beta = BetaDistribution(domain="auth")
        beta.update_failure()
        assert beta.alpha == 1.0
        assert beta.beta == 2.0

    def test_multiple_updates(self):
        """Test multiple sequential updates."""
        beta = BetaDistribution(domain="test")
        beta.update_success()
        beta.update_success()
        beta.update_failure()
        assert beta.alpha == 3.0
        assert beta.beta == 2.0
        assert beta.mean == 0.6

    def test_sample_size(self):
        """Test sample size calculation."""
        beta = BetaDistribution(domain="test")
        assert beta.sample_size == 0  # α=1, β=1, minus 2 for prior

        beta.update_success()
        beta.update_success()
        beta.update_failure()
        assert beta.sample_size == 3

    def test_variance(self):
        """Test variance calculation."""
        beta = BetaDistribution(domain="test")
        beta.update_success()
        beta.update_success()
        beta.update_failure()
        var = beta.variance
        assert var > 0
        assert var < 0.1  # Should be relatively small

    def test_confidence_interval(self):
        """Test 95% credible interval."""
        beta = BetaDistribution(domain="test")
        # With insufficient data
        lower, upper = beta.confidence_interval()
        assert lower == 0.0
        assert upper == 1.0

        # Add enough data
        for _ in range(20):
            beta.update_success()
        for _ in range(10):
            beta.update_failure()

        lower, upper = beta.confidence_interval()
        assert 0 <= lower < upper <= 1.0
        # Mean should be around 0.67 (21/31)
        assert 0.65 < beta.mean < 0.70


class TestCalibrationProfile:
    """Test calibration profile."""

    def test_profile_creation(self):
        """Test creating a profile."""
        beta = BetaDistribution(domain="database")
        profile = CalibrationProfile(domain="database", distribution=beta)
        assert profile.domain == "database"
        assert profile.confidence_gap == 0.0

    def test_should_adjust_confidence(self):
        """Test calibration adjustment detection."""
        beta = BetaDistribution(domain="test")
        profile = CalibrationProfile(domain="test", distribution=beta)

        # No adjustment needed
        profile.confidence_gap = 0.05
        assert not profile.should_adjust_confidence()

        # Adjustment needed (overconfident)
        profile.confidence_gap = 0.20
        assert profile.should_adjust_confidence()

        # Adjustment needed (underconfident)
        profile.confidence_gap = -0.20
        assert profile.should_adjust_confidence()

    def test_get_adjustment(self):
        """Test confidence adjustment values."""
        beta = BetaDistribution(domain="test")
        profile = CalibrationProfile(domain="test", distribution=beta)

        # Well calibrated
        profile.confidence_gap = 0.05
        assert profile.get_adjustment() == 0.0

        # Overconfident
        profile.confidence_gap = 0.20
        adjustment = profile.get_adjustment()
        assert adjustment < 0  # Should reduce confidence

        # Underconfident
        profile.confidence_gap = -0.20
        adjustment = profile.get_adjustment()
        assert adjustment > 0  # Should increase confidence

    def test_to_dict(self):
        """Test exporting profile as dict."""
        beta = BetaDistribution(domain="api")
        beta.update_success()
        beta.update_failure()
        profile = CalibrationProfile(domain="api", distribution=beta)

        d = profile.to_dict()
        assert d["domain"] == "api"
        assert d["alpha"] == 2.0
        assert d["beta"] == 2.0
        assert "mean_success_rate" in d


class TestTeamCalibration:
    """Test team calibration manager."""

    def test_get_or_create_domain(self):
        """Test domain creation on demand."""
        team = TeamCalibration()
        assert len(team.calibrations) == 0

        dist = team.get_or_create_domain("database")
        assert dist.domain == "database"
        assert len(team.calibrations) == 1

        # Getting same domain returns same object
        dist2 = team.get_or_create_domain("database")
        assert dist is dist2

    def test_update_from_outcome(self):
        """Test outcome-based updates."""
        team = TeamCalibration()

        team.update_from_outcome("api", success=True)
        team.update_from_outcome("api", success=True)
        team.update_from_outcome("api", success=False)

        api_dist = team.calibrations["api"]
        assert api_dist.alpha == 3.0  # 1 initial + 2 successes
        assert api_dist.beta == 2.0  # 1 initial + 1 failure

    def test_multiple_domains_isolation(self):
        """Test that domains don't interfere."""
        team = TeamCalibration()

        team.update_from_outcome("database", success=True)
        team.update_from_outcome("database", success=True)
        team.update_from_outcome("api", success=False)

        db = team.calibrations["database"]
        api = team.calibrations["api"]

        assert db.mean > 0.5
        assert api.mean < 0.5

    def test_analyze_domain(self):
        """Test domain analysis."""
        team = TeamCalibration()
        team.update_from_outcome("auth", success=True)
        team.update_from_outcome("auth", success=True)
        team.update_from_outcome("auth", success=True)

        profile = team.analyze_domain("auth")
        assert profile.domain == "auth"
        assert profile.distribution.mean > 0.7

    def test_export_metrics(self):
        """Test metrics export."""
        team = TeamCalibration()
        team.update_from_outcome("database", success=True)
        team.update_from_outcome("api", success=False)

        metrics = team.export_metrics()
        assert "created_at" in metrics
        assert "domains" in metrics
        assert "database" in metrics["domains"]
        assert "api" in metrics["domains"]


class TestCalibrationUpdater:
    """Test calibration updater."""

    def test_initialization(self):
        """Test updater creation."""
        updater = CalibrationUpdater()
        assert updater.team_calibration is not None

    def test_get_confidence_guidance_no_data(self):
        """Test guidance with no data."""
        updater = CalibrationUpdater()
        guidance = updater.get_confidence_guidance("unknown_domain")
        assert guidance["status"] == "no_data"
        assert guidance["adjustment"] == 0.0

    def test_get_confidence_guidance_with_data(self):
        """Test guidance with existing data."""
        team = TeamCalibration()
        team.update_from_outcome("database", success=True)
        team.update_from_outcome("database", success=True)
        team.update_from_outcome("database", success=False)

        updater = CalibrationUpdater(team)
        guidance = updater.get_confidence_guidance("database", decision_confidence=0.75)

        assert guidance["status"] == "data_available"
        assert guidance["sample_size"] == 3
        assert "actual_success_rate" in guidance
        assert "adjustment" in guidance

    def test_batch_update_pending_outcomes(self):
        """Test batch updating multiple outcomes."""
        updater = CalibrationUpdater()

        # Create mock outcomes
        class MockOutcome:
            def __init__(self, outcome_id, decision_id, final_status, final_score):
                self.id = outcome_id
                self.decision_id = decision_id
                self.final_status = final_status
                self.final_score = final_score

        outcomes = [
            MockOutcome("out1", "dec1", "success", 0.9),
            MockOutcome("out2", "dec2", "failure", 0.3),
            MockOutcome("out3", "dec3", "success", 0.95),
        ]

        domain_map = {
            "dec1": "database",
            "dec2": "database",
            "dec3": "api",
        }

        stats = updater.batch_update_pending_outcomes(outcomes, domain_map)
        assert stats["updated"] == 3
        assert stats["failed"] == 0

    def test_overconfident_detection(self):
        """Test detecting overconfidence."""
        team = TeamCalibration()

        # Create scenario: avg confidence 80% but only 60% success
        for _ in range(4):
            team.update_from_outcome("api", success=True)
        for _ in range(1):
            team.update_from_outcome("api", success=False)

        updater = CalibrationUpdater(team)
        guidance = updater.get_confidence_guidance("api", decision_confidence=0.80)

        assert "overconfident" in str(guidance.get("recommendation", "")).lower()

    def test_underconfident_detection(self):
        """Test detecting underconfidence."""
        team = TeamCalibration()

        # Create scenario: avg confidence 60% but 90% success
        for _ in range(9):
            team.update_from_outcome("database", success=True)
        for _ in range(1):
            team.update_from_outcome("database", success=False)

        updater = CalibrationUpdater(team)
        guidance = updater.get_confidence_guidance("database", decision_confidence=0.60)

        assert "underconfident" in str(guidance.get("recommendation", "")).lower()

    def test_get_all_profiles(self):
        """Test getting all calibration profiles."""
        team = TeamCalibration()
        team.update_from_outcome("database", success=True)
        team.update_from_outcome("api", success=False)
        team.update_from_outcome("auth", success=True)

        updater = CalibrationUpdater(team)
        profiles = updater.get_all_profiles()

        assert len(profiles) == 3
        assert "database" in profiles
        assert "api" in profiles
        assert "auth" in profiles
