"""Plan Context Builder - PRE-PLAN context injection

Builds extended context (~1500 tokens) BEFORE planning starts:
- Past plans for similar scope + outcomes
- Failed approaches in domain
- Successful patterns (stable, proven)
- Calibration data (overconfidence/underconfidence)
- Project constraints
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PlanContextBuilder:
    """Builds rich context for planning phase."""

    def __init__(self, graph_client, calibration_updater):
        """Initialize builder.

        Args:
            graph_client: GraphClient instance
            calibration_updater: CalibrationUpdater instance
        """
        self.graph_client = graph_client
        self.calibration_updater = calibration_updater
        try:
            from membria.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(graph_client)
        except Exception:
            self.memory_manager = None

    def build_plan_context(
        self,
        domain: str,
        scope: Optional[str] = None,
        max_tokens: int = 1500
    ) -> Dict[str, any]:
        """Build complete plan context.

        Returns:
        {
            "past_plans": [...],           # Similar plans + outcomes
            "failed_approaches": [...],    # What didn't work
            "successful_patterns": [...],  # What worked (proven)
            "calibration": {...},          # Team bias data
            "constraints": [...],          # Project constraints
            "recommendations": [...],      # Actionable guidance
            "total_tokens": 1234,
            "timestamp": "..."
        }

        Args:
            domain: Domain for context (database, auth, api, etc.)
            scope: Optional scope description
            max_tokens: Max tokens for context

        Returns:
            Dict with rich planning context
        """
        logger.info(f"Building plan context for: {domain}")

        context = {
            "domain": domain,
            "scope": scope,
            "past_plans": self._get_past_plans(domain),
            "failed_approaches": self._get_failed_approaches(domain),
            "successful_patterns": self._get_successful_patterns(domain),
            "calibration": self._get_calibration_data(domain),
            "constraints": self._get_project_constraints(),
            "recommendations": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Generate recommendations based on context
        context["recommendations"] = self._generate_recommendations(context)

        # Estimate tokens
        context["total_tokens"] = self._estimate_tokens(context)
        context["formatted"] = self._format_for_injection(context, max_tokens)

        return context

    def _get_past_plans(self, domain: str) -> List[Dict]:
        """Get past plans from similar domain.

        Returns: [
            {
                "engram_id": "eng_123",
                "domain": "auth",
                "steps_count": 5,
                "duration_estimate": "3h",
                "actual_duration": "7h",
                "estimate_accuracy": "2.3x underestimate",
                "completion_rate": "100%",
                "reworks": 2,
                "timestamp": "2026-02-01"
            }
        ]
        """
        try:
            query = f"""
            MATCH (e:Engram)<-[:MADE_IN]-(d:Decision {{module: $domain}})
            OPTIONAL MATCH (d)-[:RESULTED_IN]->(o:Outcome)
            RETURN DISTINCT e.id, e.session_id, COUNT(DISTINCT d) as decision_count,
                   COLLECT(d.outcome) as outcomes
            ORDER BY e.created_at DESC
            LIMIT 5
            """

            engs = self.graph_client.query(query, {"domain": domain}) or []

            plans = []
            for eng in engs:
                outcomes = eng.get("outcomes", [])
                successes = sum(1 for o in outcomes if o == "success")

                plans.append({
                    "engram_id": eng.get("id", "unknown"),
                    "session_id": eng.get("session_id", ""),
                    "steps_count": eng.get("decision_count", 0),
                    "completion_rate": f"{successes}/{len(outcomes)}" if outcomes else "0/0",
                    "timestamp": eng.get("created_at", ""),
                })

            return plans

        except Exception as e:
            logger.warning(f"Error getting past plans: {e}")
            return []

    def _get_failed_approaches(self, domain: str) -> List[Dict]:
        """Get approaches that failed in this domain.

        Returns: [
            {
                "approach": "Custom JWT implementation",
                "failure_count": 2,
                "decision_ids": ["dec_034", "dec_089"],
                "common_reasons": ["Token refresh edge cases", "Scope complexity"],
                "recommendation": "Use Auth0 instead"
            }
        ]
        """
        try:
            query = f"""
            MATCH (d:Decision {{module: $domain, outcome: 'failure'}})
            RETURN d.id, d.statement, COUNT(*) as failure_count
            GROUP BY d.statement
            ORDER BY failure_count DESC
            LIMIT 5
            """

            failed = self.graph_client.query(query, {"domain": domain}) or []

            approaches = []
            for item in failed:
                approaches.append({
                    "approach": item.get("statement", "Unknown"),
                    "failure_count": item.get("failure_count", 1),
                    "decision_ids": [item.get("id", "")],
                    "recommendation": "Consider why this failed before reusing approach",
                })

            return approaches

        except Exception as e:
            logger.warning(f"Error getting failed approaches: {e}")
            return []

    def _get_successful_patterns(self, domain: str) -> List[Dict]:
        """Get proven successful patterns in domain.

        Returns: [
            {
                "pattern": "PostgreSQL + Drizzle ORM",
                "success_rate": 0.95,
                "usage_count": 12,
                "stable_duration": "180 days",
                "recommendation": "Use confidently"
            }
        ]
        """
        try:
            patterns = []
            if self.memory_manager:
                items = self.memory_manager.retrieve_decisions(domain=domain, limit=10)
                for item in items:
                    if item.outcome == "success":
                        patterns.append({
                            "pattern": item.statement,
                            "success_count": 1,
                            "avg_confidence": round(item.confidence, 2),
                            "recommendation": "Consider for next iteration",
                        })
                return patterns

            # Fallback to graph queries if memory manager is unavailable
            query = f"""
            MATCH (d:Decision {{module: $domain, outcome: 'success'}})
            RETURN d.statement, COUNT(*) as success_count, AVG(d.confidence) as avg_conf
            GROUP BY d.statement
            ORDER BY success_count DESC, avg_conf DESC
            LIMIT 5
            """
            successes = self.graph_client.query(query, {"domain": domain}) or []
            for item in successes:
                count = item.get("success_count", 1)
                patterns.append({
                    "pattern": item.get("statement", "Unknown"),
                    "success_count": count,
                    "avg_confidence": round(item.get("avg_conf", 0.5), 2),
                    "recommendation": "✅ Use with confidence" if count >= 3 else "Consider for next iteration",
                })
            return patterns

        except Exception as e:
            logger.warning(f"Error getting successful patterns: {e}")
            return []

    def _get_calibration_data(self, domain: str) -> Dict:
        """Get team calibration for domain.

        Returns: {
            "domain": "auth",
            "sample_size": 25,
            "success_rate": 0.82,
            "avg_confidence": 0.90,
            "confidence_gap": 0.08,  # Overconfident by 8%
            "trend": "improving",
            "note": "Team is slightly overconfident - reduce time estimates by 10-15%"
        }
        """
        try:
            profiles = self.calibration_updater.get_all_profiles()
            if not profiles or domain not in profiles:
                return {}

            profile = profiles[domain]
            gap = profile.get("confidence_gap", 0)

            # Generate note based on gap
            if gap > 0.15:
                note = f"⚠️ OVERCONFIDENT by {gap:.0%} - Pad time estimates significantly"
            elif gap > 0.05:
                note = f"Slightly overconfident ({gap:.0%}) - Add 10-15% buffer to estimates"
            elif gap < -0.15:
                note = f"Underconfident by {abs(gap):.0%} - You can move faster than planned"
            else:
                note = "✅ Well-calibrated - estimates should be reliable"

            return {
                "domain": domain,
                "sample_size": profile.get("sample_size", 0),
                "success_rate": round(profile.get("mean_success_rate", 0), 2),
                "avg_confidence": round(profile.get("mean_success_rate", 0) + gap, 2),
                "confidence_gap": round(gap, 2),
                "trend": profile.get("trend", "stable"),
                "note": note,
            }

        except Exception as e:
            logger.warning(f"Error getting calibration data: {e}")
            return {}

    def _get_project_constraints(self) -> List[str]:
        """Get project-wide constraints.

        Example: "Uses Fastify, PostgreSQL, Docker"
        """
        # TODO: This could be stored as project metadata
        # For now, return empty
        return [
            "Uses TypeScript",
            "Docker containerized",
            "GitHub-based CI/CD",
        ]

    def _generate_recommendations(self, context: Dict) -> List[str]:
        """Generate actionable recommendations from context.

        Args:
            context: Full context dict

        Returns:
            List of recommendation strings
        """
        recs = []

        # Check for overconfidence
        cal = context.get("calibration", {})
        if cal.get("confidence_gap", 0) > 0.1:
            recs.append(f"⚠️ Add {int(cal['confidence_gap'] * 100)}-15% time buffer to estimates")

        # Check for failed approaches
        failed = context.get("failed_approaches", [])
        if failed:
            recs.append(f"⚠️ Avoid {len(failed)} known failure patterns in this domain")

        # Recommend successful patterns
        success = context.get("successful_patterns", [])
        if success:
            recs.append(f"✅ Prefer {len(success)} proven successful patterns")

        return recs

    def _format_for_injection(self, context: Dict, max_tokens: int) -> str:
        """Format context as markdown for Claude injection.

        Args:
            context: Full context dict
            max_tokens: Max tokens for output

        Returns:
            Markdown formatted context
        """
        output = f"# Plan Context: {context['domain'].upper()}\n\n"

        # Calibration warning first (most important)
        cal = context.get("calibration", {})
        if cal:
            output += f"## 🎯 Team Calibration\n"
            output += f"- **Success rate:** {cal.get('success_rate', 0):.0%}\n"
            output += f"- **Confidence gap:** {cal.get('confidence_gap', 0):+.0%}\n"
            output += f"- **Trend:** {cal.get('trend', 'stable')}\n"
            output += f"- **Note:** {cal.get('note', '')}\n\n"

        # Failed approaches (what to avoid)
        failed = context.get("failed_approaches", [])
        if failed:
            output += f"## ⚠️ Failed Approaches (Avoid)\n"
            for f in failed[:3]:
                output += f"- **{f.get('approach')}** ({f.get('failure_count')}x failed)\n"
            output += "\n"

        # Successful patterns (what works)
        success = context.get("successful_patterns", [])
        if success:
            output += f"## ✅ Successful Patterns (Use)\n"
            for s in success[:3]:
                output += f"- **{s.get('pattern')}** ({s.get('success_count')}x success)\n"
            output += "\n"

        # Recommendations
        recs = context.get("recommendations", [])
        if recs:
            output += f"## 💡 Recommendations\n"
            for rec in recs:
                output += f"- {rec}\n"

        return output

    def _estimate_tokens(self, context: Dict) -> int:
        """Estimate token count for context.

        Args:
            context: Context dict

        Returns:
            Estimated token count (~4 chars per token)
        """
        formatted = context.get("formatted", "")
        return len(formatted) // 4
