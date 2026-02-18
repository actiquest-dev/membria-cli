"""FalkorDB Analytics Queries - Causal Memory Analysis

Key queries for extracting insights from the decision memory graph.
All queries follow the pattern: MATCH → FILTER → AGGREGATE → RETURN
"""


class GraphQueries:
    """Collection of analytics queries for the reasoning graph"""

    # ========================================================================
    # SUCCESS RATE QUERIES
    # ========================================================================

    @staticmethod
    def success_rate_by_module() -> str:
        """Success rate of decisions by module (database, auth, api, etc.)"""
        return """
        MATCH (d:Decision {outcome: "success"})
        WITH d.module as module, count(*) as successes
        MATCH (d:Decision {module: module})
        WITH module, successes, count(*) as total
        RETURN module,
               successes,
               total,
               round(100.0 * successes / total, 1) as success_rate
        ORDER BY success_rate DESC
        """

    @staticmethod
    def success_rate_by_confidence_bucket() -> str:
        """Calibration: Confidence vs actual success rate"""
        return """
        MATCH (d:Decision {outcome: "success"})
        WITH
          round(d.confidence * 10) / 10 as confidence_bucket,
          count(*) as successful,
          avg(d.actual_success_rate) as actual_rate
        MATCH (d:Decision)
        WHERE round(d.confidence * 10) / 10 = confidence_bucket
        WITH confidence_bucket, successful, actual_rate, count(*) as total
        RETURN confidence_bucket,
               successful,
               total,
               round(actual_rate * 100, 1) as actual_rate_pct,
               CASE
                 WHEN actual_rate IS NULL THEN "unknown"
                 WHEN abs(confidence_bucket - actual_rate) < 0.05 THEN "well-calibrated"
                 WHEN confidence_bucket > actual_rate THEN "overconfident"
                 ELSE "underconfident"
               END as calibration_status
        ORDER BY confidence_bucket DESC
        """

    # ========================================================================
    # REWORK DETECTION QUERIES
    # ========================================================================

    @staticmethod
    def decisions_by_rework_count() -> str:
        """Which decisions get reworked most often?"""
        return """
        MATCH (d:Decision)-[r:REWORKED_BY]->(c:CodeChange)
        WITH d, count(r) as rework_count, avg(r.days_to_revert) as avg_days_to_rework
        WHERE rework_count > 0
        RETURN d.statement,
               d.module,
               d.confidence,
               rework_count,
               avg_days_to_rework
        ORDER BY rework_count DESC
        """

    @staticmethod
    def low_confidence_decisions_rework_rate() -> str:
        """Low confidence decisions (0.6-0.7) - how often reworked?"""
        return """
        MATCH (d:Decision)
        WHERE d.confidence >= 0.6 AND d.confidence <= 0.7
        WITH d, exists((d)-[:REWORKED_BY]->(:CodeChange)) as was_reworked
        RETURN d.module,
               d.confidence,
               count(CASE WHEN was_reworked THEN 1 END) as reworked_count,
               count(*) as total,
               round(100.0 * count(CASE WHEN was_reworked THEN 1 END) / count(*), 1) as rework_rate
        ORDER BY rework_rate DESC
        """

    # ========================================================================
    # NEGATIVE KNOWLEDGE EFFECTIVENESS
    # ========================================================================

    @staticmethod
    def negative_knowledge_prevention_value() -> str:
        """How many decisions were prevented by negative knowledge?"""
        return """
        MATCH (nk:NegativeKnowledge)-[r:PREVENTED]->(d:Decision)
        RETURN nk.hypothesis,
               nk.severity,
               nk.domain,
               count(r) as decisions_prevented,
               nk.recommendation
        ORDER BY decisions_prevented DESC
        """

    @staticmethod
    def learned_failures_by_domain() -> str:
        """What have we learned not to do, by domain?"""
        return """
        MATCH (nk:NegativeKnowledge)
        RETURN nk.domain,
               count(*) as failure_count,
               collect(nk.hypothesis) as failures
        ORDER BY failure_count DESC
        """

    # ========================================================================
    # ANTIPATTERN STATISTICS
    # ========================================================================

    @staticmethod
    def antipatterns_by_removal_rate() -> str:
        """Most problematic antipatterns (highest removal rate)"""
        return """
        MATCH (ap:AntiPattern)
        RETURN ap.name,
               ap.category,
               ap.severity,
               ap.removal_rate,
               ap.avg_days_to_removal,
               ap.repos_affected,
               ap.recommendation
        ORDER BY ap.removal_rate DESC
        """

    @staticmethod
    def antipatterns_triggered_in_commits() -> str:
        """Which antipatterns triggered most in our commits?"""
        return """
        MATCH (c:CodeChange)-[r:TRIGGERED]->(ap:AntiPattern)
        RETURN ap.name,
               ap.severity,
               count(r) as triggered_count,
               ap.recommendation
        ORDER BY triggered_count DESC
        """

    # ========================================================================
    # DECISION CORRELATION QUERIES
    # ========================================================================

    @staticmethod
    def decision_to_outcome_flow() -> str:
        """Trace decision → implementation → outcome"""
        return """
        MATCH (d:Decision)-[impl:IMPLEMENTED_IN]->(c:CodeChange)-[res:RESULTED_IN]->(o:Outcome)
        RETURN d.statement,
               d.confidence,
               c.commit_sha,
               o.status,
               o.reliability,
               res.days_to_outcome
        ORDER BY res.days_to_outcome DESC
        """

    @staticmethod
    def decision_rework_timeline() -> str:
        """When decisions get reworked (timeline)"""
        return """
        MATCH (d:Decision)-[impl:IMPLEMENTED_IN]->(c1:CodeChange),
              (d)-[rework:REWORKED_BY]->(c2:CodeChange)
        RETURN d.statement,
               c1.timestamp as implementation_time,
               c2.timestamp as rework_time,
               (c2.timestamp - c1.timestamp) / 86400 as days_to_rework,
               rework.reason
        ORDER BY days_to_rework ASC
        """

    # ========================================================================
    # SESSION & CONTEXT QUERIES
    # ========================================================================

    @staticmethod
    def decisions_per_session() -> str:
        """How many decisions extracted per session?"""
        return """
        MATCH (e:Engram)<-[r:MADE_IN]-(d:Decision)
        RETURN e.session_id,
               e.branch,
               count(d) as decision_count,
               e.commit_sha,
               e.created_at
        ORDER BY decision_count DESC
        """

    @staticmethod
    def high_risk_sessions() -> str:
        """Sessions where many decisions later failed"""
        return """
        MATCH (e:Engram)<-[r:MADE_IN]-(d:Decision {outcome: "failure"})
        RETURN e.session_id,
               e.branch,
               e.commit_sha,
               count(d) as failed_decision_count,
               e.created_at
        ORDER BY failed_decision_count DESC
        """

    # ========================================================================
    # TREND & EVOLUTION QUERIES
    # ========================================================================

    @staticmethod
    def success_rate_over_time() -> str:
        """Track success rate trend (7 day windows)"""
        return """
        MATCH (d:Decision {outcome: "success"})
        WITH round(d.created_at / 604800) as week_bucket, count(*) as weekly_success
        MATCH (d:Decision)
        WHERE round(d.created_at / 604800) = week_bucket
        WITH week_bucket, weekly_success, count(*) as weekly_total
        RETURN week_bucket * 604800 as week_start,
               weekly_success,
               weekly_total,
               round(100.0 * weekly_success / weekly_total, 1) as weekly_success_rate
        ORDER BY week_bucket DESC
        """

    @staticmethod
    def confidence_trend() -> str:
        """Average confidence over time"""
        return """
        MATCH (d:Decision)
        WITH round(d.created_at / 604800) as week_bucket,
             avg(d.confidence) as avg_confidence,
             count(*) as count
        RETURN week_bucket * 604800 as week_start,
               round(avg_confidence, 2) as avg_confidence,
               count
        ORDER BY week_bucket DESC
        """

    # ========================================================================
    # SIMILARITY & RECOMMENDATIONS
    # ========================================================================

    @staticmethod
    def similar_decisions_with_outcomes() -> str:
        """Find similar past decisions and their outcomes"""
        return """
        MATCH (d1:Decision)-[sim:SIMILAR_TO]->(d2:Decision)
        WHERE sim.similarity_score > 0.8
        RETURN d1.statement as current_decision,
               d1.confidence as current_confidence,
               d2.statement as similar_past_decision,
               d2.outcome as past_outcome,
               d2.actual_success_rate as past_success_rate,
               sim.similarity_score
        ORDER BY sim.similarity_score DESC
        """

    # ========================================================================
    # DATA QUALITY & SCHEMA CHECKS
    # ========================================================================

    @staticmethod
    def decisions_without_outcome() -> str:
        """Decisions still pending (no outcome recorded)"""
        return """
        MATCH (d:Decision)
        WHERE d.outcome IS NULL OR d.outcome = "pending"
        RETURN count(*) as pending_decisions,
               round(avg(d.confidence), 2) as avg_confidence,
               collect(d.module) as modules
        """

    @staticmethod
    def graph_statistics() -> str:
        """Overall graph statistics"""
        return """
        MATCH (d:Decision) WITH count(*) as decision_count
        MATCH (e:Engram) WITH decision_count, count(*) as engram_count
        MATCH (c:CodeChange) WITH decision_count, engram_count, count(*) as change_count
        MATCH (o:Outcome) WITH decision_count, engram_count, change_count, count(*) as outcome_count
        MATCH (nk:NegativeKnowledge) WITH decision_count, engram_count, change_count, outcome_count, count(*) as nk_count
        MATCH (ap:AntiPattern) WITH decision_count, engram_count, change_count, outcome_count, nk_count, count(*) as ap_count
        RETURN decision_count,
               engram_count,
               change_count,
               outcome_count,
               nk_count,
               ap_count,
               decision_count + engram_count + change_count + outcome_count + nk_count + ap_count as total_nodes
        """

    @staticmethod
    def schema_version() -> str:
        """Get current schema version"""
        return """
        MATCH (sv:SchemaVersion)
        RETURN sv.version,
               sv.timestamp,
               sv.migration_count
        ORDER BY sv.timestamp DESC
        LIMIT 1
        """

    @staticmethod
    def migration_history() -> str:
        """Show migration history"""
        return """
        MATCH (m:Migration)
        RETURN m.id,
               m.version_from,
               m.version_to,
               m.timestamp,
               m.status,
               m.description
        ORDER BY m.timestamp DESC
        """


class CausalQueries:
    """Cypher queries for causal analysis and prevention cycles (spec 4.6.4)."""

    @staticmethod
    def similar_decisions_by_module(module: str):
        """Find similar decisions by module (spec 4.6.4 query #1)."""
        query = """
        MATCH (d:Decision {module: $module})
        RETURN d.id, d.statement, d.confidence, d.created_at, d.outcome
        ORDER BY d.created_at DESC
        LIMIT 20
        """
        return query, {"module": module}

    @staticmethod
    def negative_knowledge_for_domain(domain: str):
        """Get negative knowledge for specific domain (spec 4.6.4 query #2)."""
        query = """
        MATCH (nk:NegativeKnowledge {domain: $domain})
        RETURN nk.id, nk.hypothesis, nk.conclusion, nk.severity, nk.discovered_at
        ORDER BY nk.discovered_at DESC
        """
        return query, {"domain": domain}

    @staticmethod
    def causal_chain_for_decision(decision_id: str):
        """Trace causal chain: why did we decide this? (spec 4.6.4 query #3)."""
        query = """
        MATCH (d:Decision {id: $decision_id})
        OPTIONAL MATCH (d)-[:IMPLEMENTED_IN]->(cc:CodeChange)-[:RESULTED_IN]->(o:Outcome)-[:CAUSED]->(nk:NegativeKnowledge)
        OPTIONAL MATCH (nk)-[:PREVENTED]->(future_d:Decision)
        RETURN
            d.id as decision_id,
            d.statement,
            d.confidence,
            cc.commit_sha,
            o.status,
            o.evidence,
            nk.conclusion,
            nk.recommendation,
            future_d.id as prevented_decision
        """
        return query, {"decision_id": decision_id}

    @staticmethod
    def antipatterns_for_files(files: list):
        """Find antipatterns for specific files (spec 4.6.4 query #4)."""
        query = """
        MATCH (cc:CodeChange)-[:TRIGGERED]->(ap:AntiPattern)
        WHERE any(f in cc.files_changed WHERE f in $files)
        RETURN ap.id, ap.name, ap.category, ap.severity, ap.removal_rate, cc.timestamp
        """
        return query, {"files": files}

    @staticmethod
    def decisions_by_commit_sha(commit_sha: str):
        """Get decisions linked by commit SHA (spec 4.6.4 query #5)."""
        query = """
        MATCH (d:Decision {commit_sha: $commit_sha})
        OPTIONAL MATCH (d)-[:IMPLEMENTED_IN]->(cc:CodeChange {commit_sha: $commit_sha})
        RETURN d.id, d.statement, d.confidence, cc.id
        """
        return query, {"commit_sha": commit_sha}

    @staticmethod
    def prevention_cycle() -> str:
        """Analyze prevention cycle effectiveness (spec 4.6.4 query #6)."""
        return """
        MATCH (d:Decision)-[:IMPLEMENTED_IN]->(cc:CodeChange)-[:RESULTED_IN]->(o:Outcome)
        WHERE o.status = 'failure'
        OPTIONAL MATCH (o)-[:CAUSED]->(nk:NegativeKnowledge)-[:PREVENTED]->(future_d:Decision)
        RETURN
            count(DISTINCT d) as total_decisions,
            count(DISTINCT o) as failed_outcomes,
            count(DISTINCT nk) as lessons_learned,
            count(DISTINCT future_d) as prevented_decisions,
            toFloat(count(DISTINCT future_d)) / CASE WHEN count(DISTINCT d) = 0 THEN 1 ELSE count(DISTINCT d) END as prevention_rate
        """

    @staticmethod
    def find_antipattern_triggers(domain: str):
        """Find antipattern triggers by domain."""
        query = """
        MATCH (d:Decision {module: $domain})
            -[:IMPLEMENTED_IN]->(cc:CodeChange)
            -[:TRIGGERED]->(ap:AntiPattern)
        RETURN ap.id as pattern_id, ap.name as pattern_name, count(DISTINCT cc) as trigger_count
        ORDER BY trigger_count DESC
        """
        return query, {"domain": domain}

    @staticmethod
    def semantic_search_decisions(query_vector: str) -> str:
        """Find semantically similar decisions using FalkorDB vector embeddings.

        Args:
            query_vector: Vector to search for (e.g., embedding of "Use database for persistence")

        Requires: Vector indices created via:
            CALL db.idx.vector.createNodeIndex('Decision', 'embedding', 1536, 'cosine')
        """
        return """
        MATCH (d:Decision)
        WHERE d.embedding IS NOT NULL AND vec.euclideanDistance(d.embedding, $query_vector) < $threshold
        RETURN d.id, d.statement, d.module, vec.euclideanDistance(d.embedding, $query_vector) as distance
        ORDER BY distance
        LIMIT 10
        """

    @staticmethod
    def semantic_search_negative_knowledge(query_vector: str) -> str:
        """Find semantically similar negative knowledge using embeddings."""
        return """
        MATCH (nk:NegativeKnowledge)
        WHERE nk.embedding IS NOT NULL AND vec.euclideanDistance(nk.embedding, $query_vector) < $threshold
        RETURN nk.id, nk.hypothesis, nk.domain, nk.severity, vec.euclideanDistance(nk.embedding, $query_vector) as distance
        ORDER BY distance
        LIMIT 10
        """

    @staticmethod
    def rework_cycles() -> str:
        """Analyze decision rework patterns (Decision -> REWORKED_BY -> CodeChange)."""
        return """
        MATCH (d:Decision)-[:REWORKED_BY]->(cc:CodeChange)
        OPTIONAL MATCH (cc)-[:RESULTED_IN]->(o:Outcome)
        RETURN
            d.id as decision_id,
            d.module,
            count(cc) as rework_count,
            collect(DISTINCT o.status) as outcome_statuses
        ORDER BY rework_count DESC
        """

    @staticmethod
    def prevention_effectiveness_by_domain() -> str:
        """Which domains have best prevention effectiveness?"""
        return """
        MATCH (nk:NegativeKnowledge)-[:PREVENTED]->(d:Decision)
        RETURN
            nk.domain,
            count(DISTINCT d) as prevented_decisions,
            count(DISTINCT nk) as lessons_learned,
            toFloat(count(DISTINCT d)) / count(DISTINCT nk) as avg_prevention_per_lesson
        ORDER BY prevented_decisions DESC
        """


class SkillQueries:
    """Cypher queries for skill-related operations."""

    @staticmethod
    def get_skills_for_domain(domain: str, min_quality: float = 0.5):
        """Get all active skills for a domain with quality filter.

        Args:
            domain: Domain name (database, auth, api, etc.)
            min_quality: Minimum quality score (0-1)

        Returns:
            Cypher query string
        """
        query = """
        MATCH (sk:Skill {domain: $domain, is_active: true})
        WHERE sk.quality_score >= $min_quality
        RETURN {{
            skill_id: sk.id,
            domain: sk.domain,
            name: sk.name,
            version: sk.version,
            success_rate: sk.success_rate,
            confidence: sk.confidence,
            sample_size: sk.sample_size,
            quality_score: sk.quality_score,
            procedure: sk.procedure
        }}
        ORDER BY sk.quality_score DESC, sk.version DESC
        """
        return query, {"domain": domain, "min_quality": min_quality}

    @staticmethod
    def get_latest_skill_version(domain: str, name: str):
        """Get latest version of a skill.

        Args:
            domain: Domain name
            name: Skill name

        Returns:
            Cypher query string
        """
        query = """
        MATCH (sk:Skill {domain: $domain, name: $name, is_active: true})
        RETURN sk
        ORDER BY sk.version DESC
        LIMIT 1
        """
        return query, {"domain": domain, "name": name}

    @staticmethod
    def get_skills_by_quality(min_quality: float = 0.5):
        """Get all active skills above quality threshold.

        Args:
            min_quality: Minimum quality score

        Returns:
            Cypher query string
        """
        query = """
        MATCH (sk:Skill {is_active: true})
        WHERE sk.quality_score >= $min_quality
        RETURN {{
            skill_id: sk.id,
            domain: sk.domain,
            quality_score: sk.quality_score,
            success_rate: sk.success_rate,
            sample_size: sk.sample_size
        }}
        ORDER BY sk.quality_score DESC
        """
        return query, {"min_quality": min_quality}

    @staticmethod
    def find_conflicting_skills(domain: str):
        """Find skills that conflict with each other in a domain.

        Args:
            domain: Domain name

        Returns:
            Cypher query string
        """
        query = """
        MATCH (sk1:Skill {domain: $domain})-[c:CONFLICTS_WITH]->(sk2:Skill)
        RETURN {{
            skill_id_1: sk1.id,
            skill_id_2: sk2.id,
            version_1: sk1.version,
            version_2: sk2.version
        }}
        """
        return query, {"domain": domain}

    @staticmethod
    def get_skill_generation_candidates(domain: str, min_decisions: int = 3):
        """Find domains ready for skill generation.

        Requirements: ≥min_decisions outcomes with success rate data.

        Args:
            domain: Domain name
            min_decisions: Minimum decision count required

        Returns:
            Cypher query string
        """
        query = """
        MATCH (d:Decision {module: $domain})
        OPTIONAL MATCH (d)-[:IMPLEMENTED_IN]->(cc:CodeChange)-[:RESULTED_IN]->(o:Outcome)
        WITH d.module as domain, count(DISTINCT d) as decision_count,
             count(CASE WHEN o.status = 'success' THEN 1 END) as success_count
        WHERE decision_count >= $min_decisions
        RETURN {{
            domain: domain,
            total_decisions: decision_count,
            successes: success_count,
            success_rate: toFloat(success_count) / decision_count,
            ready_for_generation: decision_count >= $min_decisions
        }}
        """
        return query, {"domain": domain, "min_decisions": min_decisions}

    @staticmethod
    def get_skill_coverage(domain: str):
        """Get skill coverage metrics for a domain.

        Args:
            domain: Domain name

        Returns:
            Cypher query string
        """
        query = """
        MATCH (sk:Skill {domain: $domain, is_active: true})
        OPTIONAL MATCH (sk)-[:GENERATED_FROM]->(d:Decision)
        RETURN {{
            total_skills: count(DISTINCT sk),
            total_covered_decisions: count(DISTINCT d),
            avg_quality: avg(sk.quality_score),
            avg_success_rate: avg(sk.success_rate),
            max_quality: max(sk.quality_score),
            min_quality: min(sk.quality_score)
        }}
        """
        return query, {"domain": domain}

    @staticmethod
    def get_skills_needing_review(domain: str = None):
        """Find skills past their next_review date.

        Args:
            domain: Optional domain filter

        Returns:
            Cypher query string
        """
        domain_filter = " AND sk.domain = $domain" if domain else ""

        query = f"""
        MATCH (sk:Skill {{is_active: true}}{domain_filter})
        WHERE sk.next_review < timestamp()
        RETURN {{
            skill_id: sk.id,
            domain: sk.domain,
            version: sk.version,
            last_updated: sk.last_updated,
            next_review: sk.next_review,
            quality_score: sk.quality_score
        }}
        ORDER BY sk.next_review ASC
        """
        params = {"domain": domain} if domain else {}
        return query, params


class SemanticQueries:
    """Cypher queries for vector-based semantic search and similarity matching."""

    @staticmethod
    def find_similar_decisions(decision_id: str, limit: int = 10, threshold: float = 0.75):
        """Find similar decisions using vector embeddings.

        Requires Decision nodes to have embedding vectors set.

        Args:
            decision_id: Reference decision ID
            limit: Number of results to return
            threshold: Similarity threshold (0-1, higher = more similar)

        Returns:
            Cypher query string
        """
        query = """
        MATCH (ref_d:Decision {id: $decision_id})
        WHERE ref_d.embedding IS NOT NULL
        MATCH (d:Decision)
        WHERE d.embedding IS NOT NULL AND d.id <> $decision_id
        WITH d, ref_d,
             1.0 - (vec.euclideanDistance(d.embedding, ref_d.embedding) /
             (sqrt(reduce(s = 0.0, x IN ref_d.embedding | s + x * x)) *
              sqrt(reduce(s = 0.0, x IN d.embedding | s + x * x)))) AS similarity
        WHERE similarity > $threshold
        RETURN {{
            decision_id: d.id,
            statement: d.statement,
            module: d.module,
            confidence: d.confidence,
            similarity_score: similarity,
            outcome: d.outcome
        }}
        ORDER BY similarity DESC
        LIMIT $limit
        """
        return query, {"decision_id": decision_id, "limit": limit, "threshold": threshold}

    @staticmethod
    def find_similar_negative_knowledge(nk_id: str, limit: int = 5, threshold: float = 0.70):
        """Find similar negative knowledge entries using embeddings.

        Args:
            nk_id: Reference negative knowledge ID
            limit: Number of results to return
            threshold: Similarity threshold (0-1)

        Returns:
            Cypher query string
        """
        query = """
        MATCH (ref_nk:NegativeKnowledge {id: $nk_id})
        WHERE ref_nk.embedding IS NOT NULL
        MATCH (nk:NegativeKnowledge)
        WHERE nk.embedding IS NOT NULL AND nk.id <> $nk_id
        WITH nk, ref_nk,
             1.0 - (vec.euclideanDistance(nk.embedding, ref_nk.embedding) /
             (sqrt(reduce(s = 0.0, x IN ref_nk.embedding | s + x * x)) *
              sqrt(reduce(s = 0.0, x IN nk.embedding | s + x * x)))) AS similarity
        WHERE similarity > $threshold
        RETURN {{
            nk_id: nk.id,
            hypothesis: nk.hypothesis,
            conclusion: nk.conclusion,
            domain: nk.domain,
            severity: nk.severity,
            similarity_score: similarity
        }}
        ORDER BY similarity DESC
        LIMIT $limit
        """
        return query, {"nk_id": nk_id, "limit": limit, "threshold": threshold}

    @staticmethod
    def decisions_with_embeddings_by_module(module: str):
        """Get decisions with embeddings in a module for vector operations.

        Args:
            module: Module name (database, auth, api, etc.)

        Returns:
            Cypher query string
        """
        query = """
        MATCH (d:Decision {module: $module})
        WHERE d.embedding IS NOT NULL
        RETURN {{
            decision_id: d.id,
            statement: d.statement,
            confidence: d.confidence,
            has_embedding: true
        }}
        ORDER BY d.created_at DESC
        """
        return query, {"module": module}


class DomainQueries:
    """Cypher queries for domain-specific analysis and health checks."""

    @staticmethod
    def get_domain_decisions(domain: str):
        """Get all decisions in a domain with their outcomes.

        Args:
            domain: Domain name (database, auth, api, etc.)

        Returns:
            Cypher query string
        """
        query = """
        MATCH (d:Decision {module: $domain})
        OPTIONAL MATCH (d)-[:IMPLEMENTED_IN]->(cc:CodeChange)-[:RESULTED_IN]->(o:Outcome)
        RETURN {{
            decision_id: d.id,
            statement: d.statement,
            confidence: d.confidence,
            created_at: d.created_at,
            code_change_sha: cc.commit_sha,
            outcome_status: o.status,
            outcome_evidence: o.evidence
        }}
        ORDER BY d.created_at DESC
        """
        return query, {"domain": domain}

    @staticmethod
    def get_domain_negative_knowledge(domain: str, severity: str = None):
        """Get all negative knowledge for a domain.

        Args:
            domain: Domain name
            severity: Optional severity filter (high, medium, low)

        Returns:
            Cypher query string
        """
        severity_filter = " AND nk.severity = $severity" if severity else ""
        query = f"""
        MATCH (nk:NegativeKnowledge {{domain: $domain{severity_filter}}})
        OPTIONAL MATCH (nk)-[:PREVENTED]->(d:Decision)
        RETURN {{
            nk_id: nk.id,
            hypothesis: nk.hypothesis,
            conclusion: nk.conclusion,
            severity: nk.severity,
            recommendation: nk.recommendation,
            prevented_count: count(DISTINCT d),
            discovered_at: nk.discovered_at
        }}
        ORDER BY nk.severity DESC, prevented_count DESC
        """
        params = {"domain": domain}
        if severity:
            params["severity"] = severity
        return query, params

    @staticmethod
    def domain_health_summary(domain: str):
        """Get health summary for a domain.

        Args:
            domain: Domain name

        Returns:
            Cypher query string
        """
        query = """
        MATCH (d:Decision {module: $domain})
        OPTIONAL MATCH (d)-[:IMPLEMENTED_IN]->(cc:CodeChange)-[:RESULTED_IN]->(o:Outcome)
        WITH d, o, cc
        RETURN {{
            total_decisions: count(DISTINCT d),
            success_count: count(CASE WHEN o.status = 'success' THEN 1 END),
            failure_count: count(CASE WHEN o.status = 'failure' THEN 1 END),
            pending_count: count(CASE WHEN o.status IS NULL THEN 1 END),
            avg_confidence: avg(d.confidence),
            success_rate: toFloat(count(CASE WHEN o.status = 'success' THEN 1 END)) / count(DISTINCT d)
        }}
        """
        return query, {"domain": domain}


class GraphHealthQueries:
    """Cypher queries for graph integrity, health, and anomaly detection."""

    @staticmethod
    def count_all_nodes() -> str:
        """Count nodes by type."""
        return """
        MATCH (n)
        RETURN labels(n)[0] as node_type, COUNT(n) as count
        ORDER BY count DESC
        """

    @staticmethod
    def orphaned_code_changes() -> str:
        """Find code changes without RESULTED_IN relationships (broken causal chain)."""
        return """
        MATCH (cc:CodeChange)
        WHERE NOT EXISTS((cc)-[:RESULTED_IN]->())
        RETURN {{
            code_change_id: cc.id,
            commit_sha: cc.commit_sha,
            timestamp: cc.timestamp,
            decision_id: cc.decision_id
        }}
        ORDER BY cc.timestamp DESC
        """

    @staticmethod
    def broken_causal_chains() -> str:
        """Find failures without NegativeKnowledge (no learning recorded)."""
        return """
        MATCH (o:Outcome {{status: 'failure'}})
        WHERE NOT EXISTS((o)-[:CAUSED]->())
        OPTIONAL MATCH (cc:CodeChange)-[:RESULTED_IN]->(o)
        OPTIONAL MATCH (d:Decision)-[:IMPLEMENTED_IN]->(cc)
        RETURN {{
            outcome_id: o.id,
            code_change_id: cc.id,
            decision_id: d.id,
            evidence: o.evidence
        }}
        """

    @staticmethod
    def prevention_cycle_gaps(domain: str = None):
        """Find NegativeKnowledge without PREVENTED relationships (no actionable prevention).

        Args:
            domain: Optional domain filter

        Returns:
            Cypher query string
        """
        domain_filter = " AND nk.domain = $domain" if domain else ""
        query = f"""
        MATCH (nk:NegativeKnowledge)
        WHERE NOT EXISTS((nk)-[:PREVENTED]->()) {domain_filter}
        RETURN {{
            nk_id: nk.id,
            hypothesis: nk.hypothesis,
            domain: nk.domain,
            discovered_at: nk.discovered_at
        }}
        ORDER BY nk.discovered_at DESC
        """
        params = {"domain": domain} if domain else {}
        return query, params

    @staticmethod
    def high_rework_decisions() -> str:
        """Detect decisions being reworked multiple times (quality issue)."""
        return """
        MATCH (d:Decision)-[:REWORKED_BY]->(cc:CodeChange)
        WITH d, count(cc) as rework_count
        WHERE rework_count > 2
        RETURN {{
            decision_id: d.id,
            statement: d.statement,
            module: d.module,
            rework_count: rework_count,
            confidence: d.confidence
        }}
        ORDER BY rework_count DESC
        """

    @staticmethod
    def antipattern_trigger_rate(domain: str = None):
        """Analyze antipattern trigger rates (should be low).

        Args:
            domain: Optional domain filter

        Returns:
            Cypher query string
        """
        domain_filter = " AND d.module = $domain" if domain else ""
        query = f"""
        MATCH (d:Decision)
            -[:IMPLEMENTED_IN]->(cc:CodeChange)
            -[:TRIGGERED]->(ap:AntiPattern)
        WHERE true {domain_filter}
        WITH d.module as module, ap.id as pattern_id, ap.name as pattern_name, count(DISTINCT cc) as trigger_count
        RETURN {{
            module: module,
            pattern_id: pattern_id,
            pattern_name: pattern_name,
            trigger_count: trigger_count
        }}
        ORDER BY trigger_count DESC
        """
        params = {"domain": domain} if domain else {}
        return query, params
