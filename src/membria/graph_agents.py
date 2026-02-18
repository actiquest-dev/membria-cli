"""Graph Management Agents: Monitor, analyze, and optimize the decision graph.

These agents provide intelligent analysis and control of the FalkorDB graph,
tracking:
- Graph health and integrity
- Decision patterns and trends
- Calibration quality
- Performance metrics
- Anomalies and issues
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from membria.graph_queries import CausalQueries, SemanticQueries, GraphHealthQueries

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthMetrics:
    """Graph health metrics - full schema coverage including vectors and documents."""
    status: HealthStatus = HealthStatus.HEALTHY
    total_decisions: int = 0
    total_outcomes: int = 0
    total_signals: int = 0
    total_negative_knowledge: int = 0
    total_antipatterns: int = 0
    total_documents: int = 0
    total_embeddings: int = 0  # Decisions/NK with vector embeddings
    calibration_quality: float = 0.0  # 0-1
    avg_confidence: float = 0.0  # 0-1
    success_rate: float = 0.0  # 0-1
    rework_rate: float = 0.0  # 0-1
    prevention_rate: float = 0.0  # 0-1: prevented_decisions / total_decisions
    causal_chain_health: float = 1.0  # 0-1: % of failures with NK -> prevention links
    error_count: int = 0
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_check: Optional[str] = None


@dataclass
class CalibrationMetrics:
    """Team calibration analysis."""
    domain: str
    sample_size: int
    avg_confidence: float
    actual_success_rate: float
    overconfidence: float  # positive = overconfident
    underconfidence: float  # positive = underconfident
    trend: str  # "improving", "declining", "stable"
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AnomalyReport:
    """Detected anomalies in the graph."""
    anomaly_type: str  # "low_success", "high_rework", "calibration_drift", etc
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_items: int  # decisions, commits, etc
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PreventionMetrics:
    """Prevention cycle effectiveness metrics."""
    total_failures: int = 0
    lessons_learned: int = 0
    prevented_decisions: int = 0
    prevention_rate: float = 0.0  # prevented / total decisions
    active_preventions: List[str] = field(default_factory=list)  # List of active NK preventing decisions


@dataclass
class CausalChain:
    """A complete causal chain: Decision -> CodeChange -> Outcome -> NegativeKnowledge."""
    decision_id: str
    decision_statement: str
    decision_confidence: float
    code_change_sha: Optional[str] = None
    outcome_status: Optional[str] = None
    outcome_evidence: Optional[str] = None
    learned_lesson: Optional[str] = None
    recommendation: Optional[str] = None
    prevented_future_decisions: List[str] = field(default_factory=list)




class HealthAgent:
    """Agent for monitoring graph health."""

    def __init__(self, graph_client=None):
        """Initialize health agent.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client
        self.metrics: Optional[HealthMetrics] = None
        self.last_check_time: Optional[datetime] = None

    def check_health(self) -> HealthMetrics:
        """Perform comprehensive health check.

        Returns:
            HealthMetrics with current status
        """
        metrics = HealthMetrics()

        try:
            if not self.graph_client or not self.graph_client.connected:
                metrics.status = HealthStatus.UNHEALTHY
                metrics.issues.append("Graph client not connected")
                return metrics

            # Get basic counts
            decisions = self.graph_client.get_decisions() or []
            metrics.total_decisions = len(decisions) if decisions else 0

            # Check for schema integrity
            if metrics.total_decisions == 0:
                metrics.warnings.append("No decisions in graph")

            # Calculate success rate
            if metrics.total_decisions > 0:
                successful = sum(1 for d in decisions if self._get_outcome(d) == "success")
                metrics.success_rate = successful / metrics.total_decisions

                if metrics.success_rate < 0.4:
                    metrics.warnings.append(
                        f"Low success rate: {metrics.success_rate:.1%}"
                    )

            # Check calibration
            metrics.calibration_quality = self._assess_calibration_quality()

            if metrics.calibration_quality < 0.6:
                metrics.status = HealthStatus.DEGRADED
                metrics.issues.append(
                    f"Poor calibration: {metrics.calibration_quality:.1%}"
                )

            # Calculate average confidence
            confidences = self._extract_confidences(decisions)
            if confidences:
                metrics.avg_confidence = sum(confidences) / len(confidences)

            # Check for rework patterns
            metrics.rework_rate = self._calculate_rework_rate()

            if metrics.rework_rate > 0.3:
                metrics.warnings.append(
                    f"High rework rate: {metrics.rework_rate:.1%}"
                )

            # Determine overall status
            if metrics.issues:
                metrics.status = HealthStatus.UNHEALTHY
            elif metrics.warnings:
                metrics.status = HealthStatus.DEGRADED
            else:
                metrics.status = HealthStatus.HEALTHY

            metrics.last_check = datetime.now().isoformat()
            self.metrics = metrics
            self.last_check_time = datetime.now()

            logger.info(f"Health check complete: {metrics.status.value}")
            return metrics

        except Exception as e:
            logger.error(f"Error during health check: {e}")
            metrics.status = HealthStatus.UNHEALTHY
            metrics.issues.append(f"Health check error: {str(e)}")
            metrics.error_count += 1
            return metrics

    def _get_outcome(self, decision: Dict[str, Any]) -> Optional[str]:
        """Extract outcome from decision object."""
        if isinstance(decision, list) and len(decision) > 0:
            decision = decision[0]
        if isinstance(decision, dict):
            return decision.get("outcome")
        if hasattr(decision, "properties"):
            return decision.properties.get("outcome")
        return None

    def _extract_confidences(self, decisions: List) -> List[float]:
        """Extract confidence values from decisions."""
        confidences = []
        for d in decisions:
            if isinstance(d, list) and len(d) > 0:
                d = d[0]
            confidence = None
            if isinstance(d, dict):
                confidence = d.get("confidence")
            elif hasattr(d, "properties"):
                confidence = d.properties.get("confidence")

            if confidence is not None:
                confidences.append(float(confidence))

        return confidences

    def _assess_calibration_quality(self) -> float:
        """Assess overall calibration quality (0-1)."""
        # TODO: Query FalkorDB for calibration data
        # For now, return placeholder
        return 0.7

    def _calculate_rework_rate(self) -> float:
        """Calculate percentage of decisions that were reworked."""
        # TODO: Query for rework relationships
        # For now, return placeholder
        return 0.15


class CalibrationAgent:
    """Agent for analyzing team calibration."""

    def __init__(self, graph_client=None):
        """Initialize calibration agent.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client
        self.calibrations: Dict[str, CalibrationMetrics] = {}

    def analyze_calibration(self, domain: Optional[str] = None) -> List[CalibrationMetrics]:
        """Analyze team calibration by domain.

        Args:
            domain: Specific domain to analyze, or None for all

        Returns:
            List of calibration metrics
        """
        results = []

        try:
            if not self.graph_client or not self.graph_client.connected:
                logger.warning("Cannot analyze calibration: graph not connected")
                return results

            decisions = self.graph_client.get_decisions() or []

            if not decisions:
                logger.info("No decisions to analyze")
                return results

            # Group by domain
            by_domain: Dict[str, List] = {}
            for d in decisions:
                d_domain = self._extract_domain(d)
                if domain and d_domain != domain:
                    continue

                if d_domain not in by_domain:
                    by_domain[d_domain] = []
                by_domain[d_domain].append(d)

            # Analyze each domain
            for d, decisions_in_domain in by_domain.items():
                metrics = self._analyze_domain(d, decisions_in_domain)
                results.append(metrics)
                self.calibrations[d] = metrics

            return results

        except Exception as e:
            logger.error(f"Error analyzing calibration: {e}")
            return results

    def _extract_domain(self, decision: Dict[str, Any]) -> str:
        """Extract domain from decision."""
        if isinstance(decision, list) and len(decision) > 0:
            decision = decision[0]
        if isinstance(decision, dict):
            return decision.get("domain", "general")
        if hasattr(decision, "properties"):
            return decision.properties.get("domain", "general")
        return "general"

    def _analyze_domain(self, domain: str, decisions: List) -> CalibrationMetrics:
        """Analyze calibration for a specific domain."""
        confidences = []
        successes = []

        for d in decisions:
            if isinstance(d, list) and len(d) > 0:
                d = d[0]

            confidence = None
            outcome = None

            if isinstance(d, dict):
                confidence = d.get("confidence")
                outcome = d.get("outcome")
            elif hasattr(d, "properties"):
                confidence = d.properties.get("confidence")
                outcome = d.properties.get("outcome")

            if confidence is not None:
                confidences.append(float(confidence))

            if outcome == "success":
                successes.append(True)
            elif outcome == "failure":
                successes.append(False)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        success_rate = sum(successes) / len(successes) if successes else 0.5
        overconfidence = avg_confidence - success_rate

        # Determine trend (placeholder)
        trend = "stable"

        metrics = CalibrationMetrics(
            domain=domain,
            sample_size=len(decisions),
            avg_confidence=avg_confidence,
            actual_success_rate=success_rate,
            overconfidence=overconfidence,
            underconfidence=-overconfidence if overconfidence < 0 else 0,
            trend=trend,
        )

        # Generate recommendations
        if abs(overconfidence) > 0.15:
            if overconfidence > 0:
                metrics.recommendations.append(
                    f"Team is overconfident by {overconfidence:.0%} in {domain}"
                )
            else:
                metrics.recommendations.append(
                    f"Team is underconfident by {-overconfidence:.0%} in {domain}"
                )

        if len(confidences) < 10:
            metrics.recommendations.append(
                f"Insufficient sample size ({len(confidences)}) for {domain}"
            )

        return metrics

    def get_recommendations(self) -> List[str]:
        """Get all calibration recommendations."""
        recommendations = []
        for metrics in self.calibrations.values():
            recommendations.extend(metrics.recommendations)
        return recommendations


class AnomalyAgent:
    """Agent for detecting anomalies in the graph."""

    def __init__(self, graph_client=None):
        """Initialize anomaly agent.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client
        self.detected_anomalies: List[AnomalyReport] = []

    def detect_anomalies(self) -> List[AnomalyReport]:
        """Detect anomalies in the decision graph.

        Returns:
            List of detected anomalies
        """
        anomalies = []

        try:
            if not self.graph_client or not self.graph_client.connected:
                logger.warning("Cannot detect anomalies: graph not connected")
                return anomalies

            decisions = self.graph_client.get_decisions() or []

            if not decisions:
                return anomalies

            # Check for low success rate
            success_count = sum(
                1 for d in decisions
                if isinstance(d, dict) and d.get("outcome") == "success"
                or (hasattr(d, "properties") and d.properties.get("outcome") == "success")
            )
            success_rate = success_count / len(decisions) if decisions else 0

            if success_rate < 0.4:
                anomalies.append(
                    AnomalyReport(
                        anomaly_type="low_success_rate",
                        severity="high",
                        description=f"Success rate is {success_rate:.1%}, expected > 40%",
                        affected_items=len(decisions),
                        recommendation="Review recent decisions for root causes",
                    )
                )

            # Check for high rework rate
            # TODO: Query for REWORKED_BY relationships

            # Check for confidence drift
            confidences = []
            for d in decisions:
                conf = None
                if isinstance(d, dict):
                    conf = d.get("confidence")
                elif hasattr(d, "properties"):
                    conf = d.properties.get("confidence")
                if conf is not None:
                    confidences.append(float(conf))

            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                if avg_conf < 0.5:
                    anomalies.append(
                        AnomalyReport(
                            anomaly_type="low_average_confidence",
                            severity="medium",
                            description=f"Average confidence is {avg_conf:.1%}",
                            affected_items=len(confidences),
                            recommendation="Review decision quality and clarity",
                        )
                    )

            self.detected_anomalies = anomalies
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return anomalies

    def get_critical_anomalies(self) -> List[AnomalyReport]:
        """Get only critical severity anomalies."""
        return [a for a in self.detected_anomalies if a.severity == "critical"]


class CausalAgent:
    """Agent for analyzing causal chains and prevention effectiveness."""

    def __init__(self, graph_client=None):
        """Initialize causal agent.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client
        self.causal_chains: List[CausalChain] = []
        self.prevention_metrics: Optional[PreventionMetrics] = None

    def analyze_causal_chains(self) -> List[CausalChain]:
        """Extract and analyze complete causal chains.

        Returns:
            List of CausalChain objects showing Decision -> CodeChange -> Outcome -> NegativeKnowledge
        """
        chains = []

        try:
            if not self.graph_client or not self.graph_client.connected:
                logger.warning("Cannot analyze causal chains: graph not connected")
                return chains

            # Query all decisions and build chains
            decisions = self.graph_client.get_decisions() or []

            for decision in decisions:
                if isinstance(decision, list) and len(decision) > 0:
                    decision = decision[0]

                if isinstance(decision, dict):
                    decision_id = decision.get("id")
                    statement = decision.get("statement", "")
                    confidence = decision.get("confidence", 0.0)

                    # Build causal chain from this decision
                    chain = CausalChain(
                        decision_id=decision_id,
                        decision_statement=statement,
                        decision_confidence=float(confidence) if confidence else 0.0
                    )

                    # TODO: Query for IMPLEMENTED_IN -> CodeChange -> RESULTED_IN -> Outcome
                    # TODO: Query for CAUSED -> NegativeKnowledge
                    # TODO: Query for PREVENTED -> future decisions

                    chains.append(chain)

            self.causal_chains = chains
            return chains

        except Exception as e:
            logger.error(f"Error analyzing causal chains: {e}")
            return chains

    def analyze_prevention_effectiveness(self) -> PreventionMetrics:
        """Analyze how effective the prevention cycle is.

        Prevention cycle: Decision -> CodeChange -> Outcome (failure) ->
                        NegativeKnowledge -> PREVENTED -> future Decision

        Returns:
            PreventionMetrics showing prevention rate and effectiveness
        """
        metrics = PreventionMetrics()

        try:
            if not self.graph_client or not self.graph_client.connected:
                logger.warning("Cannot analyze prevention: graph not connected")
                return metrics

            # Get all decisions
            decisions = self.graph_client.get_decisions() or []
            total_decisions = len(decisions)

            if total_decisions == 0:
                return metrics

            # Count failed outcomes
            failed_count = 0
            nk_count = 0
            prevented_count = 0

            for decision in decisions:
                if isinstance(decision, list) and len(decision) > 0:
                    decision = decision[0]

                if isinstance(decision, dict):
                    # Check if outcome is failure
                    if decision.get("outcome") == "failure":
                        failed_count += 1

            # Use CausalQueries to check prevention effectiveness
            # For now, estimate based on available data
            metrics.total_failures = failed_count
            metrics.lessons_learned = nk_count
            metrics.prevented_decisions = prevented_count
            metrics.prevention_rate = (
                prevented_count / total_decisions
                if total_decisions > 0
                else 0.0
            )

            self.prevention_metrics = metrics
            return metrics

        except Exception as e:
            logger.error(f"Error analyzing prevention: {e}")
            return metrics

    def find_similar_decisions(self, decision_statement: str, module: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find similar decisions (by module or vector embeddings if available).

        Args:
            decision_statement: The statement to search for
            module: Optional module filter

        Returns:
            List of similar decisions with outcomes
        """
        similar = []

        try:
            if not self.graph_client or not self.graph_client.connected:
                logger.warning("Cannot find similar decisions: graph not connected")
                return similar

            # Extract module from statement or use provided module
            if not module:
                # Try to infer module from statement
                keywords = {
                    "database": ["database", "sql", "postgres", "mongo", "redis"],
                    "auth": ["auth", "jwt", "oauth", "security", "password"],
                    "api": ["api", "rest", "endpoint", "http", "request"],
                    "frontend": ["react", "vue", "angular", "ui", "component"],
                    "performance": ["cache", "optimize", "slow", "latency", "speed"],
                }

                statement_lower = decision_statement.lower()
                for mod, keywords_list in keywords.items():
                    if any(kw in statement_lower for kw in keywords_list):
                        module = mod
                        break

            if module:
                # Get similar decisions by module
                decisions = self.graph_client.get_decisions() or []

                for decision in decisions:
                    if isinstance(decision, list) and len(decision) > 0:
                        decision = decision[0]

                    if isinstance(decision, dict) and decision.get("module") == module:
                        similar.append({
                            "id": decision.get("id"),
                            "statement": decision.get("statement"),
                            "confidence": decision.get("confidence"),
                            "outcome": decision.get("outcome"),
                            "module": decision.get("module"),
                        })

            return similar

        except Exception as e:
            logger.error(f"Error finding similar decisions: {e}")
            return similar

    def get_prevention_recommendations(self) -> List[str]:
        """Get actionable recommendations from negative knowledge.

        Returns:
            List of recommendations to prevent future issues
        """
        recommendations = []

        try:
            if not self.graph_client or not self.graph_client.connected:
                return recommendations

            # Query graph for NegativeKnowledge entries
            # This is a placeholder - actual implementation would query NK nodes
            # and extract their recommendations field

            # For now, return empty (would need proper NK node querying)
            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return recommendations


class GraphAnalyzer:
    """Comprehensive graph analyzer coordinating all agents."""

    def __init__(self, graph_client=None):
        """Initialize graph analyzer.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client
        self.health_agent = HealthAgent(graph_client)
        self.calibration_agent = CalibrationAgent(graph_client)
        self.anomaly_agent = AnomalyAgent(graph_client)
        self.causal_agent = CausalAgent(graph_client)

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run comprehensive analysis of the graph.

        Returns:
            Dict with all analysis results including causal chains and prevention
        """
        logger.info("Starting comprehensive graph analysis")

        health = self.health_agent.check_health()
        calibrations = self.calibration_agent.analyze_calibration()
        anomalies = self.anomaly_agent.detect_anomalies()
        causal_chains = self.causal_agent.analyze_causal_chains()
        prevention = self.causal_agent.analyze_prevention_effectiveness()

        return {
            "timestamp": datetime.now().isoformat(),
            "health": {
                "status": health.status.value,
                "total_decisions": health.total_decisions,
                "total_negative_knowledge": health.total_negative_knowledge,
                "total_antipatterns": health.total_antipatterns,
                "success_rate": health.success_rate,
                "avg_confidence": health.avg_confidence,
                "rework_rate": health.rework_rate,
                "prevention_rate": health.prevention_rate,
                "causal_chain_health": health.causal_chain_health,
                "calibration_quality": health.calibration_quality,
                "issues": health.issues,
                "warnings": health.warnings,
            },
            "calibration": [
                {
                    "domain": c.domain,
                    "sample_size": c.sample_size,
                    "avg_confidence": c.avg_confidence,
                    "actual_success_rate": c.actual_success_rate,
                    "overconfidence": c.overconfidence,
                    "trend": c.trend,
                    "recommendations": c.recommendations,
                }
                for c in calibrations
            ],
            "anomalies": [
                {
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "affected_items": a.affected_items,
                    "recommendation": a.recommendation,
                }
                for a in anomalies
            ],
            "prevention": {
                "total_failures": prevention.total_failures,
                "lessons_learned": prevention.lessons_learned,
                "prevented_decisions": prevention.prevented_decisions,
                "prevention_rate": prevention.prevention_rate,
                "active_preventions": prevention.active_preventions,
            },
            "causal_chains": len(causal_chains),
        }

    def get_summary(self) -> str:
        """Get human-readable summary of graph state.

        Returns:
            Formatted summary string
        """
        health = self.health_agent.metrics or self.health_agent.check_health()

        lines = [
            "═" * 70,
            "GRAPH HEALTH REPORT",
            "═" * 70,
            "",
            f"Status: {health.status.value.upper()}",
            f"Decisions: {health.total_decisions}",
            f"Success Rate: {health.success_rate:.1%}",
            f"Average Confidence: {health.avg_confidence:.1%}",
            f"Rework Rate: {health.rework_rate:.1%}",
            f"Prevention Rate: {health.prevention_rate:.1%}",
            f"Causal Chain Health: {health.causal_chain_health:.1%}",
            f"Calibration Quality: {health.calibration_quality:.1%}",
            "",
            f"Knowledge Base: {health.total_negative_knowledge} NK entries, {health.total_antipatterns} antipatterns, {health.total_documents} documents",
        ]

        if health.issues:
            lines.append("\nISSUES:")
            for issue in health.issues:
                lines.append(f"  ❌ {issue}")

        if health.warnings:
            lines.append("\nWARNINGS:")
            for warning in health.warnings:
                lines.append(f"  ⚠️  {warning}")

        calibrations = list(self.calibration_agent.calibrations.values())
        if calibrations:
            lines.append("\nCALIBRATION BY DOMAIN:")
            for cal in calibrations:
                overconf = cal.overconfidence
                if abs(overconf) > 0.1:
                    status = "OVERCONFIDENT" if overconf > 0 else "UNDERCONFIDENT"
                    lines.append(
                        f"  {cal.domain}: {status} by {abs(overconf):.0%} "
                        f"(n={cal.sample_size})"
                    )

        anomalies = self.anomaly_agent.detected_anomalies
        if anomalies:
            lines.append("\nDETECTED ANOMALIES:")
            for anomaly in anomalies:
                icon = "🔴" if anomaly.severity == "critical" else "🟠" if anomaly.severity == "high" else "🟡"
                lines.append(f"  {icon} {anomaly.anomaly_type}: {anomaly.description}")

        lines.extend(["", "═" * 70])

        return "\n".join(lines)


class CausalAgent:
    """Agent for analyzing causal chains and semantic relationships.

    Traces complete decision outcomes and finds similar past decisions using vectors.
    """

    def __init__(self, graph_client=None):
        """Initialize causal agent.

        Args:
            graph_client: GraphClient instance
        """
        self.graph_client = graph_client

    def get_causal_chain(self, decision_id: str) -> Optional[CausalChain]:
        """Trace full causal chain for a decision.

        Decision → CodeChange → Outcome → NegativeKnowledge → Prevention

        Args:
            decision_id: ID of decision to trace

        Returns:
            CausalChain with complete chain data, or None if not found
        """
        if not self.graph_client:
            return None

        try:
            # Query causal chain
            query, params = CausalQueries.causal_chain_for_decision(decision_id)
            result = self.graph_client.query(query, params)

            if not result or len(result) == 0:
                return None

            row = result[0]
            return CausalChain(
                decision_id=row.get("decision_id"),
                decision_statement=row.get("statement"),
                decision_confidence=row.get("confidence", 0),
                code_change_sha=row.get("commit_sha"),
                outcome_status=row.get("status"),
                outcome_evidence=row.get("evidence"),
                learned_lesson=row.get("conclusion"),
                recommendation=row.get("recommendation"),
                prevented_future_decisions=[row.get("prevented_decision")] if row.get("prevented_decision") else []
            )
        except Exception as e:
            logger.error(f"Error tracing causal chain for {decision_id}: {e}")
            return None

    def find_similar_decisions(self, decision_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find semantically similar decisions using vector embeddings.

        Requires Decision nodes to have embedding vectors.

        Args:
            decision_id: Reference decision
            limit: Number of similar decisions to return

        Returns:
            List of similar decisions with similarity scores
        """
        if not self.graph_client:
            return []

        try:
            query, params = SemanticQueries.find_similar_decisions(decision_id, limit=limit)
            results = self.graph_client.query(query, params)
            return results or []
        except Exception as e:
            logger.warning(f"Semantic search unavailable (no embeddings): {e}")
            return []

    def analyze_prevention_effectiveness(self, domain: Optional[str] = None) -> PreventionMetrics:
        """Analyze how effective prevention cycle is.

        Counts: failures → NK → prevented decisions

        Args:
            domain: Optional domain to filter by

        Returns:
            PreventionMetrics with cycle effectiveness data
        """
        metrics = PreventionMetrics()

        if not self.graph_client:
            return metrics

        try:
            query = CausalQueries.prevention_cycle()
            result = self.graph_client.query(query)

            if result and len(result) > 0:
                row = result[0]
                metrics.total_failures = row.get("total_decisions", 0)
                metrics.lessons_learned = row.get("lessons_learned", 0)
                metrics.prevented_decisions = row.get("prevented_decisions", 0)
                metrics.prevention_rate = row.get("prevention_rate", 0.0)

        except Exception as e:
            logger.error(f"Error analyzing prevention cycle: {e}")

        return metrics

    def find_prevention_gaps(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find NegativeKnowledge without PREVENTED relationships.

        These are lessons learned but not yet actionable.

        Args:
            domain: Optional domain filter

        Returns:
            List of prevention gaps
        """
        if not self.graph_client:
            return []

        try:
            query, params = GraphHealthQueries.prevention_cycle_gaps(domain)
            results = self.graph_client.query(query, params)
            return results or []
        except Exception as e:
            logger.error(f"Error finding prevention gaps: {e}")
            return []

    def get_antipattern_triggers_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get antipatterns being triggered in a domain.

        Args:
            domain: Domain to analyze

        Returns:
            List of triggered antipatterns with counts
        """
        if not self.graph_client:
            return []

        try:
            query, params = CausalQueries.find_antipattern_triggers(domain)
            results = self.graph_client.query(query, params)
            return results or []
        except Exception as e:
            logger.error(f"Error getting antipattern triggers: {e}")
            return []

    def analyze_causal_chains(self) -> List[CausalChain]:
        """Analyze causal chains in the graph.

        Gets all decisions and their causal chains.

        Returns:
            List of CausalChain objects
        """
        chains = []

        if not self.graph_client:
            return chains

        try:
            # Get all decisions
            decisions = self.graph_client.get_decisions() or []
            for decision in decisions:
                decision_id = decision.get("id") if isinstance(decision, dict) else getattr(decision, "id", None)
                if decision_id:
                    chain = self.get_causal_chain(decision_id)
                    if chain:
                        chains.append(chain)
        except Exception as e:
            logger.error(f"Error analyzing causal chains: {e}")

        return chains

