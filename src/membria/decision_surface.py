"""Decision Surface: Show relevant context before code generation."""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DecisionContext:
    """Context to show before code generation."""

    # Similar past decisions
    similar_decisions: List[Dict[str, Any]]
    # [
    #   {
    #     "decision_id": "dec_142",
    #     "statement": "Use Fastify for REST API",
    #     "outcome": "success",
    #     "created_at": "2024-01-15",
    #     "success_rate": 1.0
    #   }
    # ]

    # Team calibration
    team_calibration: Optional[Dict[str, Any]] = None
    # {
    #   "domain": "library_choice",
    #   "avg_confidence": 0.78,
    #   "actual_success": 0.61,
    #   "overconfidence": 0.17,
    #   "sample_size": 45
    # }

    # Alerts and warnings
    negative_knowledge_alerts: List[Dict[str, Any]] = None
    # [
    #   {
    #     "pattern": "custom_jwt",
    #     "removed_rate": 0.89,
    #     "team_experience": "failed_2x",
    #     "recommendation": "Use passport-jwt"
    #   }
    # ]

    def __post_init__(self):
        if self.negative_knowledge_alerts is None:
            self.negative_knowledge_alerts = []


class DecisionSurface:
    """Shows context before code generation.

    Queries FalkorDB for:
    1. Similar past decisions and their outcomes
    2. Team calibration for this domain
    3. Negative knowledge (patterns to avoid)
    """

    def __init__(self, graph_client: Optional[Any] = None):
        """Initialize surface.

        Args:
            graph_client: FalkorDB client for queries
        """
        self.graph_client = graph_client
        try:
            from membria.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(graph_client)
        except Exception:
            self.memory_manager = None

    def generate_context(
        self,
        decision_statement: str,
        module: Optional[str] = None,
    ) -> DecisionContext:
        """Generate context for a decision.

        Args:
            decision_statement: Decision being made
            module: Module/service affected

        Returns:
            DecisionContext with all relevant information
        """
        similar_decisions = []
        team_calibration = None
        alerts = []

        if self.graph_client and self.graph_client.connected:
            # Get team calibration for domain
            if module:
                team_calibration = self._get_team_calibration(module)

            # If no memory manager, fall back to graph queries
            if not self.memory_manager:
                similar_decisions = self._find_similar_decisions(decision_statement, module)
                alerts = self._find_negative_knowledge_alerts(decision_statement)

        # Use memory manager for decisions if available (preferred)
        if self.memory_manager and module:
            items = self.memory_manager.retrieve_decisions(domain=module, limit=5)
            if items:
                similar_decisions = [
                    {
                        "decision_id": item.id,
                        "statement": item.statement,
                        "outcome": item.outcome or "unknown",
                        "created_at": item.created_at,
                        "success_rate": item.confidence,
                    }
                    for item in items
                ]

        # Prefer MemoryManager for NegativeKnowledge if available
        if self.memory_manager:
            nk = self.memory_manager.retrieve_negative_knowledge(domain=module, limit=5)
            if nk:
                alerts = [
                    {
                        "pattern": item.get("hypothesis", ""),
                        "description": item.get("conclusion", ""),
                        "removed_rate": 0.0,
                        "recommendation": item.get("recommendation", ""),
                        "team_experience": item.get("severity", ""),
                    }
                    for item in nk
                ]

        return DecisionContext(
            similar_decisions=similar_decisions,
            team_calibration=team_calibration,
            negative_knowledge_alerts=alerts,
        )

    def _find_similar_decisions(
        self,
        statement: str,
        module: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find similar past decisions.

        Args:
            statement: Decision statement
            module: Module name

        Returns:
            List of similar decisions with outcomes
        """
        if not self.graph_client:
            return []

        try:
            # Query similar decisions from graph
            # This is simplified - real implementation would use similarity search
            graph = self.graph_client.graph

            query = """
            MATCH (d:Decision)
            WHERE d.statement CONTAINS $keyword
            """
            if module:
                query += " AND d.module = $module"

            query += """
            OPTIONAL MATCH (d) -[:RESULTED_IN]-> (o:Outcome)
            RETURN d.decision_id, d.statement, d.created_at, d.confidence,
                   o.status, COUNT(o) as outcome_count
            ORDER BY d.created_at DESC
            LIMIT 5
            """

            params = {"keyword": statement.split()[0] if statement else ""}
            if module:
                params["module"] = module

            result = graph.query(query, params)

            decisions = [
                {
                    "decision_id": row[0],
                    "statement": row[1],
                    "created_at": row[2],
                    "confidence": row[3],
                    "outcome": row[4],
                    "outcome_count": row[5],
                }
                for row in (result or [])
            ]

            logger.debug(f"Found {len(decisions)} similar decisions")
            return decisions

        except Exception as e:
            logger.warning(f"Could not query similar decisions: {str(e)}")
            return []

    def _get_team_calibration(self, module: str) -> Optional[Dict[str, Any]]:
        """Get team calibration for a module/domain.

        Args:
            module: Module name

        Returns:
            Calibration data or None
        """
        if not self.graph_client:
            return None

        try:
            graph = self.graph_client.graph

            # Query calibration from graph
            query = """
            MATCH (c:Calibration {module: $module})
            RETURN c.avg_confidence, c.actual_success, c.sample_size,
                   c.overconfidence_percent
            LIMIT 1
            """

            result = graph.query(query, {"module": module})
            rows = result.result_set if hasattr(result, "result_set") else result

            if rows and len(rows) > 0:
                row = rows[0]
                overconfidence = (float(row[0]) - float(row[1])) if row[0] and row[1] else 0.0

                return {
                    "domain": module,
                    "avg_confidence": float(row[0]) if row[0] else None,
                    "actual_success": float(row[1]) if row[1] else None,
                    "overconfidence": round(overconfidence, 3),
                    "sample_size": int(row[2]) if row[2] else 0,
                }

            return None

        except Exception as e:
            logger.warning(f"Could not query calibration: {str(e)}")
            return None

    def _find_negative_knowledge_alerts(
        self,
        statement: str,
    ) -> List[Dict[str, Any]]:
        """Find negative knowledge alerts relevant to decision.

        Args:
            statement: Decision statement

        Returns:
            List of alerts
        """
        if not self.graph_client:
            return []

        try:
            graph = self.graph_client.graph

            # Query negative knowledge matching keywords
            keywords = statement.split()[:3]  # First 3 words

            query = """
            MATCH (nk:NegativeKnowledge)
            WHERE """

            conditions = [f'nk.keywords CONTAINS $keyword{i}' for i in range(len(keywords))]
            query += " OR ".join(conditions)

            query += """
            RETURN nk.pattern_id, nk.description, nk.removal_rate,
                   nk.recommendation, nk.team_experience
            LIMIT 5
            """

            params = {f"keyword{i}": kw for i, kw in enumerate(keywords)}
            result = graph.query(query, params)

            alerts = [
                {
                    "pattern": row[0],
                    "description": row[1],
                    "removed_rate": float(row[2]) if row[2] else 0.0,
                    "recommendation": row[3],
                    "team_experience": row[4],
                }
                for row in (result or [])
            ]

            logger.debug(f"Found {len(alerts)} relevant alerts")
            return alerts

        except Exception as e:
            logger.warning(f"Could not query negative knowledge: {str(e)}")
            return []

    def format_for_display(self, context: DecisionContext) -> str:
        """Format context for terminal display.

        Args:
            context: DecisionContext object

        Returns:
            Formatted string
        """
        lines = []

        lines.append("\n" + "=" * 60)
        lines.append("🧠 MEMBRIA DECISION CONTEXT")
        lines.append("=" * 60)

        # Similar decisions
        if context.similar_decisions:
            lines.append("\n📊 RELEVANT HISTORY:")
            for decision in context.similar_decisions:
                icon = "✅" if decision.get("outcome") == "success" else "❌" if decision.get("outcome") == "failed" else "⚠️"
                lines.append(f"  {icon} {decision['statement'][:50]}...")
                lines.append(f"     Confidence: {int(decision.get('confidence', 0) * 100)}% | {decision.get('created_at', 'unknown')[:10]}")
        else:
            lines.append("\n📊 RELEVANT HISTORY:")
            lines.append("  No similar past decisions found")

        # Team calibration
        if context.team_calibration:
            calib = context.team_calibration
            lines.append("\n📈 TEAM CALIBRATION:")
            lines.append(f"  Domain: {calib.get('domain', 'unknown')}")
            lines.append(f"  Avg Confidence: {int(calib.get('avg_confidence', 0) * 100)}%")
            lines.append(f"  Actual Success: {int(calib.get('actual_success', 0) * 100)}%")

            overconf = calib.get("overconfidence", 0)
            if overconf > 0.1:
                lines.append(f"  ⚠️  OVERCONFIDENT by {int(overconf * 100)}%")
            elif overconf < -0.1:
                lines.append(f"  ℹ️  UNDERCONFIDENT by {int(-overconf * 100)}%")
            else:
                lines.append(f"  ✓ Well calibrated")

            lines.append(f"  Sample Size: {calib.get('sample_size', 0)} decisions")

        # Alerts
        if context.negative_knowledge_alerts:
            lines.append("\n⚠️  RELEVANT ALERTS:")
            for alert in context.negative_knowledge_alerts:
                removal = int(alert.get("removed_rate", 0) * 100)
                lines.append(f"  🚫 {alert['pattern']}: Removed in {removal}% of teams")
                if alert.get("recommendation"):
                    lines.append(f"     💡 {alert['recommendation']}")

        lines.append("\n" + "=" * 60 + "\n")

        return "\n".join(lines)
