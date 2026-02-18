"""Pattern Extractor - Mining patterns from decision outcomes

Analyzes successful and failed decisions in a domain to extract recurring patterns.
Patterns form the basis for skill generation.
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict

from membria.skill_models import Pattern
from membria.graph_queries import DomainQueries

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extract decision patterns from outcomes in a domain.

    Algorithm:
    1. Query all decisions for a domain (with outcomes)
    2. Group by pattern key (extracted from statement)
    3. Calculate success rate per pattern
    4. Filter by minimum sample size
    5. Return Pattern objects sorted by success rate
    """

    def __init__(self, graph_client):
        """Initialize pattern extractor.

        Args:
            graph_client: GraphClient instance for querying
        """
        self.graph_client = graph_client
        self.keywords = {
            "database": ["PostgreSQL", "MongoDB", "SQLite", "MySQL", "Redis", "DynamoDB"],
            "auth": ["Auth0", "JWT", "OAuth", "Firebase", "Cognito", "Keycloak"],
            "api": ["REST", "GraphQL", "gRPC", "FastAPI", "Express", "Django"],
            "cache": ["Redis", "Memcached", "Varnish", "CloudFlare"],
            "messaging": ["RabbitMQ", "Kafka", "SQS", "Pub/Sub"],
            "storage": ["S3", "GCS", "Azure Blob", "MinIO"],
            "monitoring": ["Datadog", "New Relic", "Prometheus", "CloudWatch"],
        }

    def extract_patterns_for_domain(self, domain: str, min_sample_size: int = 3) -> List[Pattern]:
        """Extract patterns from all decisions in a domain.

        Args:
            domain: Domain name (database, auth, api, etc.)
            min_sample_size: Minimum decisions per pattern to include

        Returns:
            List of Pattern objects, sorted by success rate (descending)
        """
        try:
            # 1. Get all decisions for domain with outcomes
            query, params = DomainQueries.get_domain_decisions(domain)
            decisions = self.graph_client.query(query, params)

            if not decisions:
                logger.info(f"No decisions found for domain: {domain}")
                return []

            # 2. Group decisions by pattern
            pattern_groups = self._group_by_pattern(decisions)

            # 3. Calculate success rates
            patterns = []
            for pattern_key, group in pattern_groups.items():
                total = len(group)

                if total < min_sample_size:
                    continue

                successes = sum(1 for d in group if d.get("outcome_status") == "success")
                failures = sum(1 for d in group if d.get("outcome_status") == "failure")
                success_rate = successes / total if total > 0 else 0

                pattern = Pattern(
                    statement=pattern_key,
                    success_rate=success_rate,
                    sample_size=total,
                    supporting_decisions=[d.get("decision_id") for d in group]
                )
                patterns.append(pattern)

            # 4. Sort by success rate (descending)
            patterns.sort(key=lambda p: p.success_rate, reverse=True)

            logger.info(
                f"Extracted {len(patterns)} patterns from {len(decisions)} decisions in {domain}"
            )

            return patterns

        except Exception as e:
            logger.error(f"Error extracting patterns for {domain}: {e}")
            return []

    def _group_by_pattern(self, decisions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group decisions by extracted pattern key.

        Args:
            decisions: List of decision dicts

        Returns:
            Dict mapping pattern key to list of decisions
        """
        groups = defaultdict(list)

        for decision in decisions:
            statement = decision.get("statement", "")
            pattern_key = self._extract_pattern_key(statement)
            groups[pattern_key].append(decision)

        return groups

    def _extract_pattern_key(self, statement: str) -> str:
        """Extract pattern key from decision statement.

        Uses keyword matching to extract the main technology/option.
        Falls back to full statement if no keywords match.

        Examples:
        - "Use PostgreSQL for user database" -> "PostgreSQL"
        - "Implement Auth0 for OAuth" -> "Auth0"
        - "Use Redis for caching" -> "Redis"

        Args:
            statement: Decision statement

        Returns:
            Pattern key (technology name or full statement)
        """
        if not statement:
            return "unknown"

        # Search all keywords across all categories
        all_keywords = set()
        for keywords_list in self.keywords.values():
            all_keywords.update(keywords_list)

        # Find first matching keyword (case-insensitive)
        statement_lower = statement.lower()
        for keyword in all_keywords:
            if keyword.lower() in statement_lower:
                return keyword

        # Fallback: use first meaningful noun/word
        # Extract first capitalized word or first word
        words = statement.split()
        for word in words:
            if word and word[0].isupper():
                return word.strip(".,;:")

        # Last resort: use full statement
        return statement.strip()

    def get_pattern_stats(self, domain: str) -> Dict[str, any]:
        """Get statistics about patterns in a domain.

        Args:
            domain: Domain name

        Returns:
            Dict with pattern statistics
        """
        patterns = self.extract_patterns_for_domain(domain, min_sample_size=1)

        if not patterns:
            return {
                "domain": domain,
                "total_patterns": 0,
                "total_decisions": 0,
                "avg_success_rate": 0,
                "high_confidence_patterns": 0,
                "low_confidence_patterns": 0,
            }

        total_decisions = sum(p.sample_size for p in patterns)
        high_confidence = sum(1 for p in patterns if p.success_rate > 0.75)
        low_confidence = sum(1 for p in patterns if p.success_rate < 0.50)
        avg_success = sum(p.success_rate * p.sample_size for p in patterns) / total_decisions

        return {
            "domain": domain,
            "total_patterns": len(patterns),
            "total_decisions": total_decisions,
            "avg_success_rate": round(avg_success, 3),
            "high_confidence_patterns": high_confidence,  # >75% success
            "medium_confidence_patterns": len(patterns) - high_confidence - low_confidence,
            "low_confidence_patterns": low_confidence,  # <50% success
            "patterns_by_success_rate": [
                {"statement": p.statement, "rate": round(p.success_rate, 2), "count": p.sample_size}
                for p in patterns[:10]  # Top 10
            ],
        }

    def extract_patterns_across_domains(self, domains: List[str]) -> Dict[str, List[Pattern]]:
        """Extract patterns for multiple domains.

        Args:
            domains: List of domain names

        Returns:
            Dict mapping domain -> List[Pattern]
        """
        results = {}
        for domain in domains:
            patterns = self.extract_patterns_for_domain(domain)
            results[domain] = patterns

        return results

    def find_related_patterns(self, pattern_statement: str, domain: str) -> List[Pattern]:
        """Find patterns related to a given pattern in same domain.

        Useful for detecting conflicting or complementary patterns.

        Args:
            pattern_statement: The pattern to match
            domain: Domain name

        Returns:
            List of related Pattern objects
        """
        all_patterns = self.extract_patterns_for_domain(domain, min_sample_size=1)

        # Simple similarity: check if patterns reference same keywords
        related = []
        pattern_words = set(pattern_statement.lower().split())

        for p in all_patterns:
            if p.statement == pattern_statement:
                continue  # Skip the pattern itself

            statement_words = set(p.statement.lower().split())
            # Patterns are related if they share keywords
            if pattern_words & statement_words:
                related.append(p)

        return related

    def detect_conflicting_patterns(self, domain: str) -> List[tuple]:
        """Detect conflicting patterns (high success for both opposites).

        Example: "Use PostgreSQL" (90% success) vs "Use MongoDB" (85% success)
        Both succeed, so decisions need context-based guidance.

        Args:
            domain: Domain name

        Returns:
            List of (pattern1, pattern2) tuples representing conflicts
        """
        patterns = self.extract_patterns_for_domain(domain, min_sample_size=3)

        # Look for patterns with similar success rates but opposite implications
        conflicts = []
        for i, p1 in enumerate(patterns):
            for p2 in patterns[i + 1 :]:
                # Conflict if both have good success rates (>60%) but different statements
                if p1.success_rate > 0.60 and p2.success_rate > 0.60:
                    # Check if they're actually different (not substrings of each other)
                    if p1.statement.lower() not in p2.statement.lower():
                        conflicts.append((p1, p2))

        return conflicts
