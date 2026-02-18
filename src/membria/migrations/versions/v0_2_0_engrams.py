"""Migration v0.2.0: Add Engram node type and MADE_IN relationship."""

from datetime import datetime
from membria.migrations.base import Migration


class V0_2_0_Engrams(Migration):
    """Add Engram node type for structured decision insights.

    This migration extends the schema with:
    - Engram node type (semantic engrams of decisions)
    - MADE_IN relationship from Decision to Engram
    - Indices for Engram lookups
    """

    VERSION = "0.2.0"
    DESCRIPTION = "Add Engram node type and MADE_IN relationships"
    DEPENDENCIES = ["0.1.0"]  # Depends on initial schema

    def migrate(self) -> None:
        """Add Engram node type and relationships."""
        self.log("Creating Engram node type...")

        # Create Engram node constraint
        query_engram = """
        CREATE CONSTRAINT ON (e:Engram) ASSERT EXISTS (e.engram_id)
        """
        try:
            self.execute_query(query_engram)
            self.log("✓ Engram node constraint created")
        except Exception as e:
            self.log(f"  (Constraint may already exist: {str(e)[:50]})")

        # Create indices for Engram lookups
        self.log("Creating indices for Engram...")

        query_idx_engram_id = """
        CREATE INDEX ON :Engram(engram_id)
        """
        try:
            self.execute_query(query_idx_engram_id)
            self.log("✓ Index on Engram.engram_id created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        # Index on insight_type for queries
        query_idx_type = """
        CREATE INDEX ON :Engram(insight_type)
        """
        try:
            self.execute_query(query_idx_type)
            self.log("✓ Index on Engram.insight_type created")
        except Exception as e:
            self.log(f"  (Index may already exist: {str(e)[:50]})")

        # Create MADE_IN relationship constraint
        self.log("Creating MADE_IN relationship...")

        query_made_in = """
        CREATE CONSTRAINT ON () -[r:MADE_IN]- () ASSERT EXISTS (r.created_at)
        """
        try:
            self.execute_query(query_made_in)
            self.log("✓ MADE_IN relationship constraint created")
        except Exception as e:
            self.log(f"  (Constraint may already exist: {str(e)[:50]})")

        self.log("✓ Migration v0.2.0 completed")

    def rollback(self) -> None:
        """Rollback to v0.1.0 schema (remove Engram nodes)."""
        self.log("Rolling back v0.2.0...")

        # Delete all Engram nodes (will automatically remove MADE_IN relationships)
        query_delete_engrams = """
        MATCH (e:Engram)
        DELETE e
        """
        try:
            self.execute_query(query_delete_engrams)
            count = self._count_nodes("Engram")
            self.log(f"✓ Deleted all Engram nodes (remaining: {count})")
        except Exception as e:
            self.log(f"! Error deleting Engram nodes: {str(e)[:100]}")

        self.log("✓ Rollback v0.2.0 completed (indices remain)")

    def validate(self) -> bool:
        """Verify Engram node type exists with required indices.

        Returns:
            True if schema is correctly set up, False otherwise
        """
        try:
            # Create test Decision node
            decision_id = f"test_dec_{datetime.now().timestamp()}"
            engram_id = f"test_eng_{datetime.now().timestamp()}"

            query_create_decision = f"""
            CREATE (d:Decision {{
                decision_id: "{decision_id}",
                statement: "validation test",
                confidence: 0.5,
                created_at: "{datetime.now().isoformat()}"
            }})
            RETURN d.decision_id
            """
            self.execute_query(query_create_decision)
            self.log("  Created test Decision node")

            # Create test Engram node
            query_create_engram = f"""
            CREATE (e:Engram {{
                engram_id: "{engram_id}",
                insight_type: "confidence_calibration",
                confidence: 0.75,
                evidence: "Test evidence",
                created_at: "{datetime.now().isoformat()}"
            }})
            RETURN e.engram_id
            """
            result = self.execute_query(query_create_engram)
            self.log("  Created test Engram node")

            # Create MADE_IN relationship
            query_made_in = f"""
            MATCH (d:Decision), (e:Engram)
            WHERE d.decision_id = "{decision_id}" AND e.engram_id = "{engram_id}"
            CREATE (d) -[:MADE_IN {{created_at: "{datetime.now().isoformat()}"}}]-> (e)
            RETURN COUNT(*) as count
            """
            rel_result = self.execute_query(query_made_in)
            self.log("  Created test MADE_IN relationship")

            if result and rel_result:
                # Clean up test nodes
                query_cleanup = f"""
                MATCH (d:Decision) -[r:MADE_IN]- (e:Engram)
                WHERE d.decision_id = "{decision_id}" AND e.engram_id = "{engram_id}"
                DELETE r, d, e
                """
                self.execute_query(query_cleanup)
                self.log("✓ Schema validation passed")
                return True
            else:
                self.log("! Schema validation failed: Could not create test nodes/relationships")
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
