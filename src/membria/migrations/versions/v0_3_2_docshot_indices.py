"""Migration v0.3.2: Add DocShot indices for doc-first traceability."""

from membria.migrations.base import Migration


class V0_3_2_Docshot_Indices(Migration):
    """Add indices for DocShot and doc-shot relationships."""

    VERSION = "0.3.2"
    DESCRIPTION = "Add DocShot indices"
    DEPENDENCIES = ["0.3.1"]

    def migrate(self) -> None:
        self.log("Creating indices for DocShot...")

        queries = [
            "CREATE INDEX ON :DocShot(id)",
            "CREATE INDEX ON :DocShot(created_at)",
        ]
        for query in queries:
            self.execute_query(query)

        # Relationship indexes are not always supported; best-effort.
        try:
            self.execute_query("CREATE INDEX ON :USES_DOCSHOT(doc_shot_id)")
        except Exception as exc:
            self.log(f"⚠ Skipping USES_DOCSHOT index (unsupported): {exc}")

        self.log("✓ Migration v0.3.2 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.2 (indices remain)")

    def validate(self) -> bool:
        try:
            query = "MATCH (ds:DocShot) RETURN ds.id LIMIT 1"
            result = self.execute_query(query)
            return result is not None
        except Exception:
            return False
