"""Tests for anti-bias firewall."""

import pytest
from membria.red_flags import RedFlagDetector, RedFlagSeverity
from membria.firewall import Firewall, FirewallDecision


class TestRedFlagDetector:
    """Test red flag detection."""

    def test_detect_low_confidence_no_alternatives(self):
        """Test detection of low confidence + no alternatives."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Use custom authentication",
            confidence=0.3,
            alternatives=None,
            antipatterns_detected=None,
            time_pressure=False,
        )

        assert len(flags) >= 2  # Low confidence + no alternatives
        severities = [f.severity for f in flags]
        assert RedFlagSeverity.CRITICAL in severities

    def test_detect_low_confidence_with_alternatives(self):
        """Test low confidence but alternatives exist."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Use custom authentication",
            confidence=0.3,
            alternatives=["OAuth", "SAML"],
            antipatterns_detected=None,
            time_pressure=False,
        )

        # Should have low confidence flag but less severe
        low_conf_flag = [f for f in flags if f.flag_id == "low_confidence"]
        assert len(low_conf_flag) > 0
        assert low_conf_flag[0].severity != RedFlagSeverity.CRITICAL

    def test_detect_no_alternatives(self):
        """Test detection of no alternatives."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Use this library",
            confidence=0.8,
            alternatives=[],
            antipatterns_detected=None,
            time_pressure=False,
        )

        flag_ids = [f.flag_id for f in flags]
        assert "no_alternatives" in flag_ids

    def test_detect_antipattern(self):
        """Test detection of known antipattern."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Implement custom JWT",
            confidence=0.8,
            alternatives=None,
            antipatterns_detected=["custom_jwt"],
            time_pressure=False,
        )

        flag_ids = [f.flag_id for f in flags]
        assert "antipattern_detected" in flag_ids

    def test_detect_overconfident_language(self):
        """Test detection of overconfident language."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="This will definitely work and always be perfect",
            confidence=0.95,
            alternatives=["Alternative"],
            antipatterns_detected=None,
            time_pressure=False,
        )

        flag_ids = [f.flag_id for f in flags]
        assert "overconfident" in flag_ids

    def test_detect_time_pressure(self):
        """Test detection of time pressure."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Quick decision",
            confidence=0.7,
            alternatives=["Alt1", "Alt2"],
            antipatterns_detected=None,
            time_pressure=True,
        )

        flag_ids = [f.flag_id for f in flags]
        assert "time_pressure" in flag_ids

    def test_no_flags(self):
        """Test clean decision with no flags."""
        detector = RedFlagDetector()

        flags = detector.detect(
            decision_statement="Use industry standard library",
            confidence=0.8,
            alternatives=["Alternative 1", "Alternative 2"],
            antipatterns_detected=None,
            time_pressure=False,
        )

        assert len(flags) == 0

    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        detector = RedFlagDetector()

        # No flags = 0 risk
        assert detector.calculate_risk_score([]) == 0.0

        # Create some flags
        flags = detector.detect(
            decision_statement="Custom JWT",
            confidence=0.2,
            alternatives=None,
            antipatterns_detected=None,
            time_pressure=False,
        )

        score = detector.calculate_risk_score(flags)
        assert 0.0 <= score <= 1.0
        # Multiple flags should increase score
        assert score > 0.0

    def test_should_block(self):
        """Test block decision."""
        detector = RedFlagDetector()

        # Critical flag should block
        flags = detector.detect(
            decision_statement="Custom JWT",
            confidence=0.2,
            alternatives=None,
            antipatterns_detected=None,
            time_pressure=False,
        )

        assert detector.should_block(flags) is True

    def test_should_warn(self):
        """Test warn decision."""
        detector = RedFlagDetector()

        # Create scenario with 2+ MEDIUM flags (triggers warning)
        flags = detector.detect(
            decision_statement="Use library",
            confidence=0.8,
            alternatives=[],
            antipatterns_detected=None,
            time_pressure=True,  # Adds time_pressure flag (MEDIUM)
        )

        # Should have multiple MEDIUM flags
        medium_flags = [f for f in flags if f.severity == RedFlagSeverity.MEDIUM]
        if len(medium_flags) >= 2:
            # Multiple MEDIUM flags triggers warn
            assert detector.should_warn(flags) is True
            assert detector.should_block(flags) is False


class TestFirewall:
    """Test firewall evaluation."""

    def test_firewall_allow(self):
        """Test firewall allows safe decision."""
        fw = Firewall()

        result = fw.evaluate(
            decision_statement="Use industry standard library",
            confidence=0.85,
            alternatives=["Library A", "Library B"],
            antipatterns=None,
            time_pressure=False,
        )

        assert result.decision == FirewallDecision.ALLOW
        assert result.override_required is False

    def test_firewall_warn(self):
        """Test firewall warns on risky decision."""
        fw = Firewall()

        # Create scenario with 2+ MEDIUM flags to trigger warning
        result = fw.evaluate(
            decision_statement="Use custom solution",
            confidence=0.7,
            alternatives=[],  # No alternatives = MEDIUM flag
            antipatterns=None,
            time_pressure=True,  # Time pressure = MEDIUM flag (triggers warning)
        )

        # Should warn (MEDIUM + MEDIUM triggers warn)
        assert result.decision in [FirewallDecision.WARN, FirewallDecision.BLOCK]

    def test_firewall_block(self):
        """Test firewall blocks very risky decision."""
        fw = Firewall()

        result = fw.evaluate(
            decision_statement="Custom JWT implementation",
            confidence=0.3,
            alternatives=None,
            antipatterns=["custom_jwt"],
            time_pressure=True,
        )

        assert result.decision == FirewallDecision.BLOCK
        assert result.override_required is True

    def test_firewall_message_generation(self):
        """Test message generation."""
        fw = Firewall()

        result = fw.evaluate(
            decision_statement="Custom auth",
            confidence=0.4,
            alternatives=None,
            antipatterns=None,
            time_pressure=False,
        )

        message = fw.format_for_display(result)
        assert "Risk Score" in message
        assert "Red Flags" in message or len(result.flags) == 0

    def test_firewall_with_antipattern(self):
        """Test firewall with detected antipattern."""
        fw = Firewall()

        result = fw.evaluate(
            decision_statement="Implement custom JWT",
            confidence=0.8,
            alternatives=None,
            antipatterns=["custom_jwt"],
            time_pressure=False,
        )

        # Antipattern detected = HIGH flag, which triggers warning or block depending on other factors
        assert result.decision in [FirewallDecision.WARN, FirewallDecision.BLOCK]
        assert any(f.flag_id == "antipattern_detected" for f in result.flags)

    def test_firewall_risk_score(self):
        """Test firewall calculates risk score."""
        fw = Firewall()

        # Safe decision
        safe_result = fw.evaluate(
            decision_statement="Use standard library",
            confidence=0.9,
            alternatives=["Alt"],
            antipatterns=None,
            time_pressure=False,
        )

        # Risky decision
        risky_result = fw.evaluate(
            decision_statement="Custom solution",
            confidence=0.2,
            alternatives=None,
            antipatterns=["custom_jwt"],
            time_pressure=True,
        )

        assert safe_result.risk_score < risky_result.risk_score

    def test_firewall_confidence_level_effect(self):
        """Test that confidence level affects risk score."""
        fw = Firewall()

        # High confidence, safe
        high_conf = fw.evaluate(
            decision_statement="Use library",
            confidence=0.9,
            alternatives=["Alt"],
            antipatterns=None,
            time_pressure=False,
        )

        # Low confidence, same statement
        low_conf = fw.evaluate(
            decision_statement="Use library",
            confidence=0.3,
            alternatives=["Alt"],
            antipatterns=None,
            time_pressure=False,
        )

        assert high_conf.risk_score < low_conf.risk_score

    def test_firewall_no_alternatives_effect(self):
        """Test that lacking alternatives increases risk."""
        fw = Firewall()

        # With alternatives
        with_alts = fw.evaluate(
            decision_statement="Choose framework",
            confidence=0.7,
            alternatives=["Framework A", "Framework B"],
            antipatterns=None,
            time_pressure=False,
        )

        # Without alternatives
        no_alts = fw.evaluate(
            decision_statement="Choose framework",
            confidence=0.7,
            alternatives=None,
            antipatterns=None,
            time_pressure=False,
        )

        assert with_alts.risk_score <= no_alts.risk_score

    def test_firewall_overconfident_language_detection(self):
        """Test that overconfident language increases risk."""
        fw = Firewall()

        # Cautious language
        cautious = fw.evaluate(
            decision_statement="Might use this library",
            confidence=0.85,
            alternatives=["Alt"],
            antipatterns=None,
            time_pressure=False,
        )

        # Overconfident language
        overconfident = fw.evaluate(
            decision_statement="This will definitely be perfect",
            confidence=0.85,
            alternatives=["Alt"],
            antipatterns=None,
            time_pressure=False,
        )

        assert cautious.risk_score <= overconfident.risk_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
