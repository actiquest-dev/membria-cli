"""Migration v0.3.1: Add DocSet indices for doc-first traceability."""

from membria.migrations.base import Migration


class V0_3_1_Docset_Indices(Migration):
    """Add indices for DocSet and doc-set relationships."""

    VERSION = "0.3.1"
    DESCRIPTION = "Add DocSet indices"
    DEPENDENCIES = ["0.3.0"]

    def migrate(self) -> None:
        self.log("Creating indices for DocSet...")

        queries = [
            "CREATE INDEX ON :DocSet(id)",
            "CREATE INDEX ON :DocSet(created_at)",
        ]
        for query in queries:
            self.execute_query(query)

        # Relationship indexes are not always supported; best-effort.
        try:
            self.execute_query("CREATE INDEX ON :USES_DOCSET(doc_set_id)")
        except Exception as exc:
            self.log(f"⚠ Skipping USES_DOCSET index (unsupported): {exc}")

        self.log("✓ Migration v0.3.1 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.1 (indices remain)")

    def validate(self) -> bool:
        try:
            query = "MATCH (ds:DocSet) RETURN ds.id LIMIT 1"
            result = self.execute_query(query)
            return result is not None
        except Exception:
            return False
