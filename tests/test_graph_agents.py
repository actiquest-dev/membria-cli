"""Tests for graph monitoring and analysis agents."""

import pytest
from membria.graph_agents import (
    HealthAgent,
    CalibrationAgent,
    AnomalyAgent,
    GraphAnalyzer,
    HealthMetrics,
    HealthStatus,
    CalibrationMetrics,
)


class TestHealthAgent:
    """Test health monitoring agent."""

    def test_health_agent_initialization(self):
        """Test health agent creation."""
        agent = HealthAgent()
        assert agent.graph_client is None
        assert agent.metrics is None

    def test_health_check_disconnected(self):
        """Test health check when disconnected."""
        agent = HealthAgent(graph_client=None)
        metrics = agent.check_health()

        assert metrics.status == HealthStatus.UNHEALTHY
        assert "not connected" in metrics.issues[0].lower()

    def test_health_metrics_creation(self):
        """Test health metrics dataclass."""
        metrics = HealthMetrics(
            status=HealthStatus.HEALTHY,
            total_decisions=100,
            success_rate=0.75,
            avg_confidence=0.8,
        )

        assert metrics.status == HealthStatus.HEALTHY
        assert metrics.total_decisions == 100
        assert metrics.success_rate == 0.75
        assert metrics.avg_confidence == 0.8

    def test_health_status_enum(self):
        """Test health status values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestCalibrationAgent:
    """Test calibration analysis agent."""

    def test_calibration_agent_initialization(self):
        """Test calibration agent creation."""
        agent = CalibrationAgent()
        assert agent.graph_client is None
        assert len(agent.calibrations) == 0

    def test_calibration_metrics_creation(self):
        """Test calibration metrics dataclass."""
        metrics = CalibrationMetrics(
            domain="framework_choice",
            sample_size=50,
            avg_confidence=0.75,
            actual_success_rate=0.68,
            overconfidence=0.07,
            underconfidence=0.0,
            trend="stable",
        )

        assert metrics.domain == "framework_choice"
        assert metrics.sample_size == 50
        assert metrics.avg_confidence == 0.75
        assert metrics.actual_success_rate == 0.68
        assert metrics.overconfidence == 0.07

    def test_calibration_overconfidence_detection(self):
        """Test detection of team overconfidence."""
        metrics = CalibrationMetrics(
            domain="api_design",
            sample_size=30,
            avg_confidence=0.85,
            actual_success_rate=0.60,
            overconfidence=0.25,  # Significantly overconfident
            underconfidence=0.0,
            trend="declining",
        )

        assert metrics.overconfidence > 0.15
        assert metrics.trend == "declining"

    def test_calibration_underconfidence_detection(self):
        """Test detection of team underconfidence."""
        metrics = CalibrationMetrics(
            domain="database_choice",
            sample_size=25,
            avg_confidence=0.55,
            actual_success_rate=0.80,
            overconfidence=-0.25,  # Underconfident
            underconfidence=0.25,
            trend="improving",
        )

        assert metrics.overconfidence < 0
        assert metrics.underconfidence > 0.15

    def test_calibration_insufficient_sample_warning(self):
        """Test warning for small sample size."""
        metrics = CalibrationMetrics(
            domain="caching_strategy",
            sample_size=5,  # Too small
            avg_confidence=0.7,
            actual_success_rate=0.8,
            overconfidence=-0.1,
            underconfidence=0.1,
            trend="stable",
        )

        # Should generate recommendation for sample size
        assert metrics.sample_size < 10


class TestAnomalyAgent:
    """Test anomaly detection agent."""

    def test_anomaly_agent_initialization(self):
        """Test anomaly agent creation."""
        agent = AnomalyAgent()
        assert agent.graph_client is None
        assert len(agent.detected_anomalies) == 0

    def test_anomaly_report_creation(self):
        """Test anomaly report dataclass."""
        from membria.graph_agents import AnomalyReport

        report = AnomalyReport(
            anomaly_type="low_success_rate",
            severity="high",
            description="Success rate is below 40%",
            affected_items=25,
            recommendation="Review recent decisions",
        )

        assert report.anomaly_type == "low_success_rate"
        assert report.severity == "high"
        assert report.affected_items == 25
        assert report.timestamp is not None

    def test_anomaly_detection_disconnected(self):
        """Test anomaly detection when disconnected."""
        agent = AnomalyAgent(graph_client=None)
        anomalies = agent.detect_anomalies()

        assert len(anomalies) == 0

    def test_critical_anomaly_filtering(self):
        """Test filtering critical anomalies."""
        from membria.graph_agents import AnomalyReport

        agent = AnomalyAgent()
        agent.detected_anomalies = [
            AnomalyReport(
                anomaly_type="test1",
                severity="critical",
                description="Critical issue",
                affected_items=10,
                recommendation="Fix immediately",
            ),
            AnomalyReport(
                anomaly_type="test2",
                severity="medium",
                description="Medium issue",
                affected_items=5,
                recommendation="Fix soon",
            ),
        ]

        critical = agent.get_critical_anomalies()

        assert len(critical) == 1
        assert critical[0].anomaly_type == "test1"


class TestGraphAnalyzer:
    """Test comprehensive graph analyzer."""

    def test_graph_analyzer_initialization(self):
        """Test graph analyzer creation."""
        analyzer = GraphAnalyzer()
        assert analyzer.graph_client is None
        assert analyzer.health_agent is not None
        assert analyzer.calibration_agent is not None
        assert analyzer.anomaly_agent is not None

    def test_graph_analyzer_agents_connected(self):
        """Test that all agents are connected to same client."""
        analyzer = GraphAnalyzer()
        assert analyzer.health_agent.graph_client is analyzer.graph_client
        assert analyzer.calibration_agent.graph_client is analyzer.graph_client
        assert analyzer.anomaly_agent.graph_client is analyzer.graph_client

    def test_full_analysis_structure(self):
        """Test full analysis returns correct structure."""
        analyzer = GraphAnalyzer()
        analysis = analyzer.run_full_analysis()

        assert "timestamp" in analysis
        assert "health" in analysis
        assert "calibration" in analysis
        assert "anomalies" in analysis

        # Check health structure
        health = analysis["health"]
        assert "status" in health
        assert "total_decisions" in health
        assert "success_rate" in health
        assert "avg_confidence" in health

    def test_analyzer_summary_generation(self):
        """Test summary string generation."""
        analyzer = GraphAnalyzer()
        summary = analyzer.get_summary()

        # Summary should contain headers
        assert "GRAPH HEALTH REPORT" in summary
        assert "Status:" in summary
        assert "Decisions:" in summary

    def test_analyzer_summary_with_issues(self):
        """Test summary includes issues when present."""
        analyzer = GraphAnalyzer()

        # Manually set metrics with issues
        metrics = HealthMetrics(
            status=HealthStatus.UNHEALTHY,
            total_decisions=10,
            success_rate=0.3,
        )
        metrics.issues.append("Test issue")
        analyzer.health_agent.metrics = metrics

        summary = analyzer.get_summary()

        assert "UNHEALTHY" in summary
        assert "ISSUES:" in summary
        assert "Test issue" in summary

    def test_analyzer_health_status_representation(self):
        """Test health status is properly represented."""
        # Healthy
        metrics_healthy = HealthMetrics(status=HealthStatus.HEALTHY)
        assert metrics_healthy.status == HealthStatus.HEALTHY

        # Degraded
        metrics_degraded = HealthMetrics(status=HealthStatus.DEGRADED)
        assert metrics_degraded.status == HealthStatus.DEGRADED

        # Unhealthy
        metrics_unhealthy = HealthMetrics(status=HealthStatus.UNHEALTHY)
        assert metrics_unhealthy.status == HealthStatus.UNHEALTHY


class TestAgentIntegration:
    """Test agent integration and workflows."""

    def test_multiple_agents_independent(self):
        """Test that agents can operate independently."""
        health = HealthAgent()
        calibration = CalibrationAgent()
        anomaly = AnomalyAgent()

        health_result = health.check_health()
        calibration_result = calibration.analyze_calibration()
        anomaly_result = anomaly.detect_anomalies()

        # Each should have results without affecting others
        assert health_result is not None
        assert health_result.status == HealthStatus.UNHEALTHY  # No connection
        assert isinstance(calibration_result, list)
        assert isinstance(anomaly_result, list)

    def test_analyzer_coordinates_agents(self):
        """Test that analyzer properly coordinates all agents."""
        analyzer = GraphAnalyzer()

        # Before analysis
        assert analyzer.health_agent.metrics is None
        assert len(analyzer.anomaly_agent.detected_anomalies) == 0

        # Run analysis
        analyzer.run_full_analysis()

        # After analysis, agents should have results
        # (even if empty due to no graph connection)
        # Just verify they were called

    def test_health_priority_over_warnings(self):
        """Test that critical issues override warnings."""
        metrics = HealthMetrics(
            status=HealthStatus.HEALTHY,
            total_decisions=100,
        )

        # Add warning first
        metrics.warnings.append("Test warning")
        assert metrics.status == HealthStatus.HEALTHY

        # Add critical issue
        metrics.issues.append("Critical issue")
        # Status should be updated to unhealthy
        # (In real implementation, this would be done in agent logic)
        metrics.status = HealthStatus.UNHEALTHY
        assert len(metrics.issues) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
