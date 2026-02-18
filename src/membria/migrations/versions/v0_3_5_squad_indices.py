"""Migration v0.3.5: Add indices for Squad-related nodes."""

from membria.migrations.base import Migration


class V0_3_5_Squad_Indices(Migration):
    """Add indices for Squad, Profile, Role, Project, Workspace, Assignment."""

    VERSION = "0.3.5"
    DESCRIPTION = "Add indices for squad orchestration nodes"
    DEPENDENCIES = ["0.3.4"]

    def migrate(self) -> None:
        self.log("Creating indices for Squad orchestration nodes...")
        queries = [
            "CREATE INDEX ON :Workspace(id)",
            "CREATE INDEX ON :Project(id)",
            "CREATE INDEX ON :Project(workspace_id)",
            "CREATE INDEX ON :Squad(id)",
            "CREATE INDEX ON :Squad(project_id)",
            "CREATE INDEX ON :Squad(strategy)",
            "CREATE INDEX ON :Assignment(id)",
            "CREATE INDEX ON :Profile(id)",
            "CREATE INDEX ON :Profile(name)",
            "CREATE INDEX ON :Role(id)",
            "CREATE INDEX ON :Role(name)",
        ]
        for query in queries:
            self.execute_query(query)
        self.log("✓ Migration v0.3.5 completed")

    def rollback(self) -> None:
        self.log("Rollback not supported for v0.3.5 (indices remain)")

    def validate(self) -> bool:
        try:
            result = self.execute_query("MATCH (s:Squad) RETURN s.id LIMIT 1")
            return result is not None
        except Exception:
            return False
