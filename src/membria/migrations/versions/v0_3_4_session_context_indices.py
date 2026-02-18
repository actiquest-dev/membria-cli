"""Migration v0.3.4: Add SessionContext indices."""

from membria.migrations.base import Migration


class V0_3_4_Session_Context_Indices(Migration):
    """Add indices for SessionContext."""

    VERSION = "0.3.4"
    DESCRIPTION = "Add SessionContext indices"
    DEPENDENCIES = ["0.3.3"]

    def migrate(self) -> None:
        self.log("Creating indices for SessionContext...")
        queries = [
            "CREATE INDEX ON :SessionContext(session_id)",
            "CREATE INDEX ON :SessionContext(expires_at)",
        ]
        for query in queries:
            self.execute_query(query)
        self.log("✓ Migration v0.3.4 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.4 (indices remain)")

    def validate(self) -> bool:
        try:
            result = self.execute_query("MATCH (sc:SessionContext) RETURN sc.id LIMIT 1")
            return result is not None
        except Exception:
            return False
