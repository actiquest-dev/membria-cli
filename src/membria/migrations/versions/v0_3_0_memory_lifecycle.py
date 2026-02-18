"""Migration v0.3.0: Add memory lifecycle metadata to nodes."""

from membria.migrations.base import Migration


class V0_3_0_Memory_Lifecycle(Migration):
    """Add memory lifecycle fields to Decision, NegativeKnowledge, Outcome, Skill.

    Fields:
    - memory_type, memory_subject, ttl_days, last_verified_at, is_active, deprecated_reason
    """

    VERSION = "0.3.0"
    DESCRIPTION = "Add memory lifecycle metadata"
    DEPENDENCIES = ["0.2.0"]

    def migrate(self) -> None:
        self.log("Adding memory lifecycle defaults...")

        # Decisions
        query_decisions = """
        MATCH (d:Decision)
        SET d.is_active = COALESCE(d.is_active, true),
            d.ttl_days = COALESCE(d.ttl_days, 365),
            d.memory_type = COALESCE(d.memory_type, "episodic"),
            d.memory_subject = COALESCE(d.memory_subject, "agent")
        RETURN COUNT(d) as count
        """
        self.execute_query(query_decisions)

        # Negative Knowledge
        query_nk = """
        MATCH (nk:NegativeKnowledge)
        SET nk.is_active = COALESCE(nk.is_active, true),
            nk.ttl_days = COALESCE(nk.ttl_days, 365),
            nk.memory_type = COALESCE(nk.memory_type, "semantic"),
            nk.memory_subject = COALESCE(nk.memory_subject, "agent")
        RETURN COUNT(nk) as count
        """
        self.execute_query(query_nk)

        # Outcomes
        query_outcomes = """
        MATCH (o:Outcome)
        SET o.is_active = COALESCE(o.is_active, true),
            o.ttl_days = COALESCE(o.ttl_days, 365)
        RETURN COUNT(o) as count
        """
        self.execute_query(query_outcomes)

        # Skills
        query_skills = """
        MATCH (s:Skill)
        SET s.is_active = COALESCE(s.is_active, true),
            s.ttl_days = COALESCE(s.ttl_days, 720)
        RETURN COUNT(s) as count
        """
        self.execute_query(query_skills)

        self.log("✓ Migration v0.3.0 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.0 (metadata defaults only)")

    def validate(self) -> bool:
        try:
            query = """
            MATCH (d:Decision)
            RETURN d.is_active, d.ttl_days, d.memory_type, d.memory_subject
            LIMIT 1
            """
            result = self.execute_query(query)
            return bool(result is not None)
        except Exception:
            return False
