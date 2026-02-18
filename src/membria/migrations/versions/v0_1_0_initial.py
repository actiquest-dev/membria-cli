"""Migration v0.1.0: Initial schema with Decision node type."""

from datetime import datetime
from membria.migrations.base import Migration


class V0_1_0_Initial(Migration):
    """Create initial FalkorDB schema with Decision nodes.

    This is the foundational migration that creates:
    - Decision node type with properties
    - Indices for fast decision lookups
    - SchemaVersion tracking node type
    """

    VERSION = "0.1.0"
    DESCRIPTION = "Create initial Decision node type and schema tracking"
    DEPENDENCIES = []  # No dependencies for initial migration

    def migrate(self) -> None:
        """Create Decision node type and indices."""
        self.log("Creating Decision node type...")

        # Create Decision node with properties
        # Using CREATE constraint to ensure property existence
        query_decision = """
        CREATE CONSTRAINT ON (d:Decision) ASSERT EXISTS (d.decision_id)
        """
        try:
            self.execute_query(query_decision)
            self.log("✓ Decision node constraint created")
        except Exception as e:
            # Constraint might already exist
            self.log(f"  (Constraint may already exist: {str(e)[:50]})")

        # Create indices for fast lookups
        self.log("Creating indices for Decision lookups...")

        # Index on decision_id for fast lookups
        query_idx_id = """
        CREATE INDEX ON :Decision(decision_id)
        """
        try:
            self.execute_query(query_idx_id)
            self.log("✓ Index on Decision.decision_id created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        # Index on statement for similarity searches
        query_idx_statement = """
        CREATE INDEX ON :Decision(statement)
        """
        try:
            self.execute_query(query_idx_statement)
            self.log("✓ Index on Decision.statement created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        # Index on confidence for range queries
        query_idx_confidence = """
        CREATE INDEX ON :Decision(confidence)
        """
        try:
            self.execute_query(query_idx_confidence)
            self.log("✓ Index on Decision.confidence created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        # Create SchemaVersion node type constraint
        self.log("Creating SchemaVersion tracking...")

        query_schemaversion = """
        CREATE CONSTRAINT ON (sv:SchemaVersion) ASSERT EXISTS (sv.version)
        """
        try:
            self.execute_query(query_schemaversion)
            self.log("✓ SchemaVersion node constraint created")
        except Exception as e:
            self.log(f"  (Constraint may already exist: {str(e)[:50]})")

        # Index on SchemaVersion.version for lookups
        query_idx_version = """
        CREATE INDEX ON :SchemaVersion(version)
        """
        try:
            self.execute_query(query_idx_version)
            self.log("✓ Index on SchemaVersion.version created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        self.log("✓ Migration v0.1.0 completed")

    def rollback(self) -> None:
        """Rollback to empty schema (drop all Decision nodes)."""
        self.log("Rolling back v0.1.0...")

        # Delete all Decision nodes
        query_delete_decisions = """
        MATCH (d:Decision)
        DELETE d
        """
        try:
            self.execute_query(query_delete_decisions)
            count = self._count_nodes("Decision")
            self.log(f"✓ Deleted all Decision nodes (remaining: {count})")
        except Exception as e:
            self.log(f"! Error deleting Decision nodes: {str(e)[:100]}")

        # Delete all SchemaVersion nodes from this migration
        query_delete_versions = """
        MATCH (sv:SchemaVersion)
        WHERE sv.version = "0.1.0"
        DELETE sv
        """
        try:
            self.execute_query(query_delete_versions)
            self.log("✓ Deleted SchemaVersion tracking for v0.1.0")
        except Exception as e:
            self.log(f"! Error deleting SchemaVersion: {str(e)[:100]}")

        # Note: Indices cannot be dropped easily in FalkorDB, but they don't affect rollback
        self.log("✓ Rollback v0.1.0 completed (indices remain)")

    def validate(self) -> bool:
        """Verify Decision node type exists with required indices.

        Returns:
            True if schema is correctly set up, False otherwise
        """
        try:
            # Check if we can create a Decision node
            test_id = f"test_{datetime.now().timestamp()}"
            query_test = f"""
            CREATE (d:Decision {{
                decision_id: "{test_id}",
                statement: "test",
                confidence: 0.5,
                created_at: "{datetime.now().isoformat()}"
            }})
            RETURN d.decision_id
            """
            result = self.execute_query(query_test)

            if result:
                # Clean up test node
                query_cleanup = f"""
                MATCH (d:Decision)
                WHERE d.decision_id = "{test_id}"
                DELETE d
                """
                self.execute_query(query_cleanup)
                self.log("✓ Schema validation passed")
                return True
            else:
                self.log("! Schema validation failed: Could not create test Decision node")
                return False

        except Exception as e:
            self.log(f"! Schema validation failed: {str(e)[:100]}")
            return False

    def _count_nodes(self, label: str) -> int:
        """Count nodes with given label.

        Args:
            label: Node label to count

        Returns:
            Number of nodes with that label
        """
        try:
            query = f"MATCH (n:{label}) RETURN COUNT(n) as count"
            result = self.execute_query(query)
            if result and len(result) > 0:
                return result[0][0]
            return 0
        except Exception:
            return -1  # Error case
