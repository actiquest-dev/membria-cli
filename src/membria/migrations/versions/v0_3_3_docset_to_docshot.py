"""Migration v0.3.3: Rename DocSet to DocShot and USES_DOCSET to USES_DOCSHOT."""

from membria.migrations.base import Migration


class V0_3_3_Docset_To_Docshot(Migration):
    """Rename DocSet nodes and USES_DOCSET relationships for consistency."""

    VERSION = "0.3.3"
    DESCRIPTION = "Rename DocSet to DocShot and USES_DOCSET to USES_DOCSHOT"
    DEPENDENCIES = ["0.3.2"]

    def migrate(self) -> None:
        self.log("Renaming DocSet nodes to DocShot...")
        self.execute_query(
            """
            MATCH (ds:DocSet)
            SET ds:DocShot
            REMOVE ds:DocSet
            RETURN COUNT(ds) as count
            """
        )

        self.log("Renaming USES_DOCSET relationships to USES_DOCSHOT...")
        self.execute_query(
            """
            MATCH (d:Decision)-[r:USES_DOCSET]->(ds)
            MERGE (d)-[r2:USES_DOCSHOT]->(ds)
            SET r2 += r,
                r2.doc_shot_id = COALESCE(r.doc_shot_id, r.doc_set_id)
            DELETE r
            RETURN COUNT(r2) as count
            """
        )

        self.log("Updating DOCUMENTS relationship properties (doc_set_id -> doc_shot_id)...")
        self.execute_query(
            """
            MATCH ()-[r:DOCUMENTS]->()
            WHERE r.doc_set_id IS NOT NULL AND r.doc_shot_id IS NULL
            SET r.doc_shot_id = r.doc_set_id
            REMOVE r.doc_set_id
            RETURN COUNT(r) as count
            """
        )

        self.log("✓ Migration v0.3.3 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.3 (rename only)")

    def validate(self) -> bool:
        try:
            result = self.execute_query("MATCH (ds:DocShot) RETURN ds.id LIMIT 1")
            return result is not None
        except Exception:
            return False
