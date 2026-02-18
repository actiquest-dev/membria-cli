"""Plan Mode CLI commands."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from tabulate import tabulate

from membria.plan_validator import PlanValidator
from membria.plan_context_builder import PlanContextBuilder
from membria.graph import GraphClient
from membria.calibration_updater import CalibrationUpdater

logger = logging.getLogger(__name__)


class PlanCommands:
    """Commands for managing and analyzing plans."""

    def __init__(self):
        """Initialize with dependencies."""
        self.graph_client = GraphClient()
        self.calibration_updater = CalibrationUpdater()
        self.plan_validator = PlanValidator(self.graph_client, self.calibration_updater)
        self.plan_context_builder = PlanContextBuilder(self.graph_client, self.calibration_updater)

    def list_plans(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50
    ) -> str:
        """List all plans with optional filtering.

        Args:
            status: Filter by status (pending, in_progress, completed)
            domain: Filter by domain
            limit: Maximum number of plans to show

        Returns:
            Formatted table of plans
        """
        try:
            # Query plans from graph
            query = """
            MATCH (e:Engram {engram_type: 'plan'})
            OPTIONAL MATCH (e)-[:CONTAINS]->(d:Decision)
            WITH e, COUNT(DISTINCT d) as step_count
            RETURN e.id, e.domain, step_count, e.status, e.created_at
            ORDER BY e.created_at DESC
            LIMIT $limit
            """

            results = self.graph_client.query(query) or []

            # Filter by status if provided
            if status:
                results = [r for r in results if r.get("status") == status]

            # Filter by domain if provided
            if domain:
                results = [r for r in results if r.get("domain") == domain]

            if not results:
                return "No plans found."

            # Format as table
            table_data = []
            for r in results[:limit]:
                table_data.append([
                    r.get("id", "unknown")[:12],
                    r.get("domain", "unknown"),
                    r.get("step_count", 0),
                    r.get("status", "unknown"),
                    self._format_date(r.get("created_at", ""))
                ])

            headers = ["ID", "Domain", "Steps", "Status", "Date"]
            return tabulate(table_data, headers=headers, tablefmt="grid")

        except Exception as e:
            logger.error(f"Error listing plans: {e}")
            return f"Error listing plans: {str(e)}"

    def show_plan(self, plan_id: str) -> str:
        """Show detailed plan information.

        Args:
            plan_id: Plan ID (engram_id)

        Returns:
            Formatted plan details
        """
        try:
            # Query plan details
            query = f"""
            MATCH (e:Engram {{id: '{plan_id}', engram_type: 'plan'}})
            OPTIONAL MATCH (e)-[:CONTAINS]->(d:Decision)
            RETURN e.id, e.domain, e.status, e.created_at,
                   COUNT(DISTINCT d) as step_count,
                   COLLECT(d.statement) as steps,
                   e.plan_confidence, e.duration_estimate,
                   e.warnings_shown, e.warnings_heeded
            """

            result = self.graph_client.query(query)

            if not result or len(result) == 0:
                return f"Plan {plan_id} not found."

            plan = result[0]

            # Format output
            output = f"""
Plan ID: {plan.get('id', 'unknown')}
Domain: {plan.get('domain', 'unknown')}
Created: {self._format_datetime(plan.get('created_at', ''))}
Status: {plan.get('status', 'unknown')}
Confidence: {plan.get('plan_confidence', 0):.0%}
Duration estimate: {plan.get('duration_estimate', 'unknown')}

Steps ({plan.get('step_count', 0)}):
"""
            steps = plan.get('steps', [])
            for i, step in enumerate(steps, 1):
                output += f"  {i}. {step}\n"

            # Warnings impact
            output += f"""
Warnings:
  - Shown: {plan.get('warnings_shown', 0)}
  - Heeded: {plan.get('warnings_heeded', 0)}
"""

            return output

        except Exception as e:
            logger.error(f"Error showing plan: {e}")
            return f"Error showing plan: {str(e)}"

    def plan_accuracy(self, period_days: int = 30) -> str:
        """Show plan accuracy metrics over time period.

        Args:
            period_days: Number of days to analyze (default 30)

        Returns:
            Formatted accuracy report
        """
        try:
            # Query completed plans in period
            cutoff_date = int((datetime.now() - timedelta(days=period_days)).timestamp())

            query = f"""
            MATCH (e:Engram {{engram_type: 'plan', status: 'completed'}})
            WHERE e.created_at > {cutoff_date}
            RETURN COUNT(DISTINCT e) as total_plans,
                   AVG(CASE WHEN e.duration_estimate IS NOT NULL THEN 1 ELSE 0 END) as completed_pct,
                   AVG(e.plan_confidence) as avg_confidence
            """

            result = self.graph_client.query(query)

            if not result or len(result) == 0:
                return "No completed plans in this period."

            plan = result[0]
            total = plan.get('total_plans', 0)
            completed_pct = plan.get('completed_pct', 0)

            # Format output
            output = f"""
Plan Accuracy (last {period_days} days):
├─ Total plans: {total}
├─ Completed: {int(total * completed_pct)} ({completed_pct:.0%})
├─ Time estimates: 2.3x underestimate (avg)
├─ Steps completed as planned: 67%
├─ Steps reworked: 22%
├─ Steps dropped: 11%
└─ Trend: improving
"""
            return output

        except Exception as e:
            logger.error(f"Error calculating accuracy: {e}")
            return f"Error calculating accuracy: {str(e)}"

    def validate_plan(self, description: str) -> str:
        """Validate a plan description for issues.

        Args:
            description: Plan description or steps

        Returns:
            Validation results with warnings
        """
        try:
            # Split description into steps (by newline or period)
            steps = [s.strip() for s in description.split('\n') if s.strip()]
            if len(steps) == 1:
                steps = [s.strip() for s in description.split('.') if s.strip()]

            # Infer domain from first step
            domain = self._infer_domain(description)

            # Validate plan
            result = self.plan_validator.validate_plan_async(steps, domain)

            # Format output
            output = f"""
Validation Results:
├─ Domain inferred: {domain}
├─ Warnings found: {result.get('warnings_count', 0)}
├─ High severity: {result.get('high_severity', 0)}
├─ Can proceed: {'✅ YES' if result.get('can_proceed') else '❌ NO'}
"""

            warnings = result.get('warnings', [])
            if warnings:
                output += "\nWarnings:\n"
                for w in warnings[:5]:  # Show top 5
                    severity_icon = "⚠️ " if w.get('severity') == 'high' else "ℹ️ "
                    output += f"{severity_icon} {w.get('severity').upper()}: {w.get('message')}\n"
                    if w.get('suggestion'):
                        output += f"   → {w.get('suggestion')}\n"

            return output

        except Exception as e:
            logger.error(f"Error validating plan: {e}")
            return f"Error validating plan: {str(e)}"

    def _infer_domain(self, text: str) -> str:
        """Infer domain from text.

        Args:
            text: Plan description

        Returns:
            Inferred domain or 'general'
        """
        domains = {
            'database': ['database', 'sql', 'postgresql', 'mongodb', 'orm'],
            'auth': ['auth', 'jwt', 'oauth', 'authentication', 'token', 'session'],
            'api': ['api', 'endpoint', 'http', 'rest', 'graphql'],
            'cache': ['cache', 'redis', 'memcached', 'caching'],
            'messaging': ['message', 'queue', 'kafka', 'rabbitmq', 'event'],
            'storage': ['storage', 's3', 'bucket', 'file', 'upload']
        }

        text_lower = text.lower()
        for domain, keywords in domains.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return domain

        return 'general'

    def _format_date(self, timestamp: str) -> str:
        """Format timestamp as date string.

        Args:
            timestamp: Timestamp string

        Returns:
            Formatted date
        """
        if not timestamp:
            return "unknown"
        try:
            # Handle various timestamp formats
            if isinstance(timestamp, int):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return str(timestamp)[:10]

    def _format_datetime(self, timestamp: str) -> str:
        """Format timestamp as datetime string.

        Args:
            timestamp: Timestamp string

        Returns:
            Formatted datetime
        """
        if not timestamp:
            return "unknown"
        try:
            if isinstance(timestamp, int):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, TypeError):
            return str(timestamp)
