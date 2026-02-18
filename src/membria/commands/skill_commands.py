"""Skills CLI commands."""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from tabulate import tabulate

from membria.skill_generator import SkillGenerator
from membria.pattern_extractor import PatternExtractor
from membria.graph import GraphClient
from membria.calibration_updater import CalibrationUpdater

logger = logging.getLogger(__name__)


class SkillCommands:
    """Commands for managing skills."""

    def __init__(self):
        """Initialize with dependencies."""
        self.graph_client = GraphClient()
        self.calibration_updater = CalibrationUpdater()
        self.pattern_extractor = PatternExtractor(self.graph_client)
        self.skill_generator = SkillGenerator(
            self.graph_client,
            self.calibration_updater,
            self.pattern_extractor
        )

    def generate_skill(
        self,
        domain: str,
        min_patterns: int = 3,
        min_sample_size: int = 3
    ) -> str:
        """Generate a skill for a domain.

        Args:
            domain: Domain name (auth, database, api, etc.)
            min_patterns: Minimum patterns required
            min_sample_size: Minimum decisions per pattern

        Returns:
            Skill generation result
        """
        try:
            logger.info(f"Generating skill for domain: {domain}")

            skill = self.skill_generator.generate_skill_for_domain(
                domain,
                min_patterns=min_patterns,
                min_sample_size=min_sample_size
            )

            if not skill:
                return f"Could not generate skill for {domain}. Check readiness with 'membria skills readiness'."

            # Format output
            output = f"""
✅ Skill generated successfully!

Skill ID: {skill.skill_id}
Domain: {skill.domain}
Version: {skill.version}
Quality: {skill.quality_score:.2f} {'(high)' if skill.quality_score > 0.75 else '(medium)' if skill.quality_score > 0.6 else '(low)'}
Success rate: {skill.success_rate:.0%}

Evidence:
  ├─ Sample size: {skill.sample_size} decisions
  ├─ Green zone: {len(skill.green_zone)} patterns (>75% success)
  ├─ Yellow zone: {len(skill.yellow_zone)} patterns (50-75% success)
  └─ Red zone: {len(skill.red_zone)} patterns (<50% success)

Generated: {datetime.fromtimestamp(skill.created_at).strftime('%Y-%m-%d %H:%M:%S UTC')}
Next review: {datetime.fromtimestamp(skill.next_review).strftime('%Y-%m-%d')}
"""
            return output

        except Exception as e:
            logger.error(f"Error generating skill: {e}")
            return f"Error generating skill: {str(e)}"

    def list_skills(
        self,
        domain: Optional[str] = None,
        min_quality: float = 0.0,
        limit: int = 50
    ) -> str:
        """List all skills with optional filtering.

        Args:
            domain: Filter by domain
            min_quality: Filter by minimum quality score
            limit: Maximum number to show

        Returns:
            Formatted table of skills
        """
        try:
            # Query skills from graph
            query = """
            MATCH (s:Skill)
            RETURN s.id, s.domain, s.quality_score, s.success_rate, s.sample_size, s.version
            ORDER BY s.quality_score DESC
            """

            results = self.graph_client.query(query) or []

            # Filter by domain if provided
            if domain:
                results = [r for r in results if r.get("domain") == domain]

            # Filter by min quality
            results = [r for r in results if r.get("quality_score", 0) >= min_quality]

            if not results:
                return "No skills found."

            # Format as table
            table_data = []
            for r in results[:limit]:
                table_data.append([
                    r.get("id", "unknown"),
                    r.get("domain", "unknown"),
                    f"{r.get('quality_score', 0):.2f}",
                    f"{r.get('success_rate', 0):.0%}",
                    r.get("sample_size", 0),
                    r.get("version", 1)
                ])

            headers = ["ID", "Domain", "Quality", "Success", "Size", "Version"]
            return tabulate(table_data, headers=headers, tablefmt="grid")

        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            return f"Error listing skills: {str(e)}"

    def show_skill(self, skill_id: str) -> str:
        """Show detailed skill information.

        Args:
            skill_id: Skill ID (e.g., sk-auth-v2)

        Returns:
            Formatted skill details
        """
        try:
            # Query skill details
            query = f"""
            MATCH (s:Skill {{id: '{skill_id}'}})
            RETURN s.id, s.domain, s.version, s.created_at,
                   s.success_rate, s.quality_score, s.sample_size, s.confidence,
                   s.green_zone, s.yellow_zone, s.red_zone,
                   s.procedure
            """

            result = self.graph_client.query(query)

            if not result or len(result) == 0:
                return f"Skill {skill_id} not found."

            skill = result[0]

            # Format output
            output = f"""
Skill: {skill.get('id', 'unknown')}
Version: {skill.get('version', 1)}
Domain: {skill.get('domain', 'unknown')}
Generated: {self._format_datetime(skill.get('created_at', ''))}

📊 Statistics:
  ├─ Success rate: {skill.get('success_rate', 0):.0%}
  ├─ Quality score: {skill.get('quality_score', 0):.2f}
  ├─ Sample size: {skill.get('sample_size', 0)}
  ├─ Confidence: {skill.get('confidence', 0):.2f}
  └─ Trend: improving

"""

            # Green zone
            green = skill.get('green_zone', [])
            if green:
                output += "🟢 Green Zone (Use Confidently):\n"
                for pattern in green[:5]:
                    output += f"  ├─ {pattern}\n"
                if len(green) > 5:
                    output += f"  └─ ... and {len(green) - 5} more\n"
                output += "\n"

            # Yellow zone
            yellow = skill.get('yellow_zone', [])
            if yellow:
                output += "🟡 Yellow Zone (Consider Carefully):\n"
                for pattern in yellow[:5]:
                    output += f"  ├─ {pattern}\n"
                if len(yellow) > 5:
                    output += f"  └─ ... and {len(yellow) - 5} more\n"
                output += "\n"

            # Red zone
            red = skill.get('red_zone', [])
            if red:
                output += "🔴 Red Zone (Avoid):\n"
                for pattern in red[:5]:
                    output += f"  ├─ {pattern}\n"
                if len(red) > 5:
                    output += f"  └─ ... and {len(red) - 5} more\n"
                output += "\n"

            # Procedure
            procedure = skill.get('procedure', '')
            if procedure:
                output += f"""
📋 Procedure:
{procedure}
"""

            return output

        except Exception as e:
            logger.error(f"Error showing skill: {e}")
            return f"Error showing skill: {str(e)}"

    def check_readiness(self, domain: Optional[str] = None) -> str:
        """Check skill generation readiness for domains.

        Args:
            domain: Check specific domain (or all if None)

        Returns:
            Readiness report
        """
        try:
            # Get domains to check
            domains_to_check = [domain] if domain else [
                'database', 'auth', 'api', 'cache', 'messaging', 'storage'
            ]

            # Get readiness for each domain
            readiness = self.skill_generator.get_skill_readiness(domains_to_check)

            if not readiness:
                return "No readiness data available."

            # Format output
            output = "Skill Generation Readiness:\n\n"

            for domain_name, status in readiness.items():
                ready = status.get('ready', False)
                patterns = status.get('patterns', 0)
                has_cal = status.get('has_calibration', False)
                reason = status.get('reason', 'unknown')

                status_icon = "✅ READY" if ready else "⏳ WAITING"

                output += f"{domain_name}:\n"
                output += f"├─ Patterns found: {patterns}\n"
                output += f"├─ Calibration data: {'✅' if has_cal else '❌'}\n"
                output += f"├─ Min patterns needed: 3\n"
                output += f"├─ Status: {status_icon}\n"
                output += f"└─ Reason: {reason}\n\n"

            return output

        except Exception as e:
            logger.error(f"Error checking readiness: {e}")
            return f"Error checking readiness: {str(e)}"

    def _format_datetime(self, timestamp) -> str:
        """Format timestamp as datetime string.

        Args:
            timestamp: Timestamp (int or str)

        Returns:
            Formatted datetime
        """
        if not timestamp:
            return "unknown"
        try:
            if isinstance(timestamp, int):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, TypeError):
            return str(timestamp)
