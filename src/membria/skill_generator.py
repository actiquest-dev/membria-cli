"""Skill Generator - Core implementation

Generates procedural knowledge (Skills) from team decision outcomes.

Pipeline:
1. Extract patterns from domain decisions
2. Get calibration metrics
3. Get negative knowledge
4. Calculate quality score
5. Generate human-readable procedure
6. Create Skill node in FalkorDB
"""

import logging
import math
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from membria.skill_models import Skill
from membria.pattern_extractor import PatternExtractor
from membria.graph_queries import DomainQueries
from membria.security import sanitize_text

logger = logging.getLogger(__name__)


class SkillGenerator:
    """Generate skills from decision patterns and outcomes.

    Quality Score Formula:
    - quality_score = success_rate * (1 - 1/sqrt(sample_size))
    - Ranges 0-1, rewards both high success rate and large sample sizes
    - Minimum sample size requirement: 3 decisions
    """

    def __init__(self, graph_client, calibration_updater):
        """Initialize skill generator.

        Args:
            graph_client: GraphClient instance for queries and writes
            calibration_updater: CalibrationUpdater for calibration data
        """
        self.graph_client = graph_client
        self.calibration_updater = calibration_updater
        self.pattern_extractor = PatternExtractor(graph_client)

    def generate_skill_for_domain(
        self,
        domain: str,
        min_patterns: int = 3,
        min_sample_size: int = 3
    ) -> Optional[Skill]:
        """Generate a skill for a domain.

        Full pipeline:
        1. Extract patterns
        2. Get calibration
        3. Get negative knowledge
        4. Generate procedure
        5. Calculate quality
        6. Create and save skill

        Args:
            domain: Domain name (database, auth, api, etc.)
            min_patterns: Minimum patterns required
            min_sample_size: Minimum decisions per pattern

        Returns:
            Skill object if successful, None otherwise
        """
        logger.info(f"Generating skill for domain: {domain}")

        try:
            # 1. Extract patterns
            patterns = self.pattern_extractor.extract_patterns_for_domain(
                domain, min_sample_size=min_sample_size
            )

            if len(patterns) < min_patterns:
                logger.info(
                    f"Insufficient patterns for {domain}: {len(patterns)} < {min_patterns}"
                )
                return None

            # 2. Get calibration
            profiles = self.calibration_updater.get_all_profiles()
            if not profiles or domain not in profiles:
                logger.warning(f"No calibration data for {domain}")
                return None

            calibration = profiles[domain]

            # 3. Get negative knowledge
            nk_query, nk_params = DomainQueries.get_domain_negative_knowledge(domain)
            negative_knowledge = self.graph_client.query(nk_query, nk_params) or []

            # 4. Generate procedure
            procedure = self._generate_procedure(domain, patterns, negative_knowledge, calibration)

            # 5. Calculate quality score
            quality_score = self._calculate_quality_score(
                calibration.get("mean_success_rate", 0),
                calibration.get("sample_size", 0)
            )

            # 6. Get next version
            next_version = self._get_next_skill_version(domain)

            # 7. Create Skill object
            skill = Skill(
                skill_id=f"sk-{domain}-v{next_version}",
                domain=domain,
                name=f"{domain}_recommendation",
                version=next_version,
                success_rate=calibration.get("mean_success_rate", 0),
                confidence=calibration.get("mean_success_rate", 0),
                sample_size=calibration.get("sample_size", 0),
                procedure=procedure,
                green_zone=[p.statement for p in patterns if p.success_rate > 0.75],
                yellow_zone=[p.statement for p in patterns if 0.50 <= p.success_rate <= 0.75],
                red_zone=[p.statement for p in patterns if p.success_rate < 0.50],
                quality_score=quality_score,
                generated_from_decisions=[d for p in patterns for d in p.supporting_decisions],
                created_at=int(datetime.now().timestamp()),
                last_updated=int(datetime.now().timestamp()),
                next_review=int((datetime.now() + timedelta(days=90)).timestamp()),
                ttl_days=720,
            )

            # 8. Save to graph
            self._save_skill_to_graph(skill)

            logger.info(f"✅ Skill generated: {skill.skill_id} (quality: {quality_score:.0%})")
            return skill

        except Exception as e:
            logger.error(f"Error generating skill for {domain}: {e}", exc_info=True)
            return None

    def _generate_procedure(self, domain: str, patterns, nk_list, calibration) -> str:
        """Generate human-readable decision procedure from patterns.

        Structure:
        - Team Experience (sample size, success rate, gap, trend)
        - Strongly Recommend (>75% success)
        - Consider Carefully (50-75%)
        - Avoid (<50%)
        - Known Failures (NK)

        Args:
            domain: Domain name
            patterns: List of Pattern objects
            nk_list: Negative knowledge entries
            calibration: Calibration profile dict

        Returns:
            Markdown procedure text
        """
        procedure = f"# {domain.title()} Decision Procedure\n\n"

        # Team Experience section
        procedure += "## 📊 Team Experience\n\n"
        procedure += f"Based on **{calibration.get('sample_size', 0)} decisions** in this domain:\n"
        procedure += f"- Success rate: **{calibration.get('mean_success_rate', 0):.0%}**\n"

        gap = calibration.get("confidence_gap", 0)
        if gap > 0:
            procedure += f"- Team is overconfident by {gap:.0%}\n"
        elif gap < 0:
            procedure += f"- Team is underconfident by {abs(gap):.0%}\n"

        trend = calibration.get("trend", "stable")
        procedure += f"- Trend: {trend}\n\n"

        # Strongly Recommend
        strong_recs = [p for p in patterns if p.success_rate > 0.75]
        if strong_recs:
            procedure += "## ✅ Strongly Recommend\n\n"
            for p in strong_recs:
                statement = sanitize_text(p.statement, max_len=160)
                procedure += f"- **{statement}** ({p.success_rate:.0%} success, {p.sample_size} decisions)\n"
            procedure += "\n"

        # Consider Carefully
        medium_recs = [p for p in patterns if 0.50 <= p.success_rate <= 0.75]
        if medium_recs:
            procedure += "## ⚠️ Consider Carefully\n\n"
            for p in medium_recs:
                statement = sanitize_text(p.statement, max_len=160)
                procedure += f"- **{statement}** ({p.success_rate:.0%} success, {p.sample_size} decisions)\n"
            procedure += "\n"

        # Avoid
        avoid_recs = [p for p in patterns if p.success_rate < 0.50]
        if avoid_recs:
            procedure += "## 🛑 Avoid\n\n"
            for p in avoid_recs:
                statement = sanitize_text(p.statement, max_len=160)
                procedure += f"- **{statement}** ({p.success_rate:.0%} success, {p.sample_size} decisions)\n"
            procedure += "\n"

        # Known Failures
        if nk_list:
            procedure += "## 📚 Known Failures (Negative Knowledge)\n\n"
            for nk in nk_list[:5]:  # Top 5
                hypothesis = nk.get("hypothesis", "")
                conclusion = nk.get("conclusion", "")
                if hypothesis and conclusion:
                    procedure += f"- {sanitize_text(hypothesis, max_len=160)} → {sanitize_text(conclusion, max_len=160)}\n"
            procedure += "\n"

        # Quality note
        procedure += "---\n"
        procedure += f"*Procedure generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*\n"

        return procedure

    def _calculate_quality_score(self, success_rate: float, sample_size: int) -> float:
        """Calculate quality score for skill.

        Formula: quality_score = success_rate * (1 - 1/sqrt(sample_size))

        - Rewards high success rate
        - Scales up with larger sample sizes
        - Minimum sample size: 3 → quality starts at 0.42
        - At sample size 100 → quality ≈ success_rate * 0.9

        Args:
            success_rate: Success rate (0-1)
            sample_size: Number of observations

        Returns:
            Quality score (0-1)
        """
        if sample_size < 3:
            return 0.5

        try:
            confidence_factor = 1 - (1 / math.sqrt(sample_size))
            return success_rate * confidence_factor
        except (ValueError, ZeroDivisionError):
            return success_rate

    def _get_next_skill_version(self, domain: str) -> int:
        """Get next version number for a skill.

        Queries FalkorDB for current max version, increments by 1.

        Args:
            domain: Domain name

        Returns:
            Next version number (1 if no skills yet)
        """
        try:
            query = f"""
            MATCH (s:Skill {{domain: $domain}})
            RETURN MAX(s.version) as max_version
            """
            result = self.graph_client.query(query, {"domain": domain})

            if result and result[0].get("max_version"):
                return result[0]["max_version"] + 1

            return 1

        except Exception as e:
            logger.warning(f"Error getting next skill version: {e}, defaulting to 1")
            return 1

    def _save_skill_to_graph(self, skill: Skill) -> bool:
        """Save skill node to FalkorDB.

        Creates Skill node and optionally relationships.

        Args:
            skill: Skill object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            from membria.graph_schema import SkillNodeSchema

            # Convert Skill to SkillNodeSchema
            skill_schema = SkillNodeSchema(
                id=skill.skill_id,
                domain=skill.domain,
                name=skill.name,
                version=skill.version,
                success_rate=skill.success_rate,
                confidence=skill.confidence,
                sample_size=skill.sample_size,
                procedure=skill.procedure,
                green_zone=skill.green_zone,
                yellow_zone=skill.yellow_zone,
                red_zone=skill.red_zone,
                created_at=skill.created_at,
                last_updated=skill.last_updated,
                next_review=skill.next_review,
                ttl_days=skill.ttl_days,
                quality_score=skill.quality_score,
                generated_from_decisions=skill.generated_from_decisions,
                conflicts_with=skill.conflicts_with,
                related_skills=skill.related_skills,
                is_active=skill.is_active,
            )

            # Create Cypher statement
            cypher, params = skill_schema.to_cypher_create()
            self.graph_client.query(cypher, params)

            logger.info(f"✅ Saved skill to graph: {skill.skill_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving skill to graph: {e}", exc_info=True)
            return False

    def generate_skills_for_domains(self, domains: List[str]) -> Dict[str, Optional[Skill]]:
        """Generate skills for multiple domains.

        Args:
            domains: List of domain names

        Returns:
            Dict mapping domain -> Skill (or None if generation failed)
        """
        results = {}

        for domain in domains:
            skill = self.generate_skill_for_domain(domain)
            results[domain] = skill

        successful = sum(1 for s in results.values() if s is not None)
        logger.info(f"Generated {successful}/{len(domains)} skills")

        return results

    def get_skill_readiness(self, domains: List[str]) -> Dict[str, Dict[str, any]]:
        """Check if domains are ready for skill generation.

        Returns:
            Dict with readiness status for each domain
        """
        readiness = {}

        for domain in domains:
            patterns = self.pattern_extractor.extract_patterns_for_domain(domain, min_sample_size=1)
            profiles = self.calibration_updater.get_all_profiles()
            has_calibration = domain in profiles if profiles else False

            readiness[domain] = {
                "patterns": len(patterns),
                "has_calibration": has_calibration,
                "ready": len(patterns) >= 3 and has_calibration,
                "reason": self._get_readiness_reason(len(patterns), has_calibration),
            }

        return readiness

    def _get_readiness_reason(self, pattern_count: int, has_calibration: bool) -> str:
        """Get human-readable reason for readiness status.

        Args:
            pattern_count: Number of patterns found
            has_calibration: Whether calibration data exists

        Returns:
            Reason string
        """
        if not has_calibration:
            return "No calibration data (need ≥1 outcome)"

        if pattern_count < 3:
            return f"Need {3 - pattern_count} more patterns (need ≥3 decisions per pattern)"

        return "✅ Ready for skill generation"
