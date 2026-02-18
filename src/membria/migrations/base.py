"""Base Migration class for schema versioning and updates."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from falkordb import FalkorDB
from pathlib import Path


@dataclass
class MigrationRecord:
    """Record of a migration execution."""
    version: str
    executed_at: datetime
    duration_ms: float
    status: str  # "success" or "failed"
    error: Optional[str] = None


class Migration(ABC):
    """Base class for all database migrations.

    Each migration:
    - Has a unique VERSION string (e.g., "0.1.0")
    - Describes what it does in DESCRIPTION
    - Lists DEPENDENCIES (other migrations that must run first)
    - Implements migrate() to apply changes
    - Implements rollback() to undo changes
    - Implements validate() to verify schema is correct
    """

    VERSION: str  # e.g., "0.1.0"
    DESCRIPTION: str  # e.g., "Create initial Decision node type"
    DEPENDENCIES: List[str] = []  # e.g., ["0.0.1"]

    def __init__(self, db: FalkorDB):
        """Initialize migration with database connection.

        Args:
            db: FalkorDB connection instance
        """
        self.db = db
        self.graph = db.select_graph("membria")
        self.start_time: Optional[datetime] = None

    @abstractmethod
    def migrate(self) -> None:
        """Apply the migration.

        Must be idempotent - running twice should not cause errors.
        """
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Undo the migration.

        Should restore database to state before migrate() was run.
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Verify that the migration applied correctly.

        Returns:
            True if schema is correct, False otherwise
        """
        pass

    def log(self, message: str) -> None:
        """Log a migration step.

        Args:
            message: Message to log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.VERSION}: {message}")

    def execute_query(self, query: str) -> any:
        """Execute a Cypher query safely.

        Args:
            query: Cypher query to execute

        Returns:
            Query result

        Raises:
            Exception: If query fails
        """
        try:
            result = self.graph.query(query)
            return result
        except Exception as e:
            raise RuntimeError(f"Migration {self.VERSION} query failed: {str(e)}")

    def escape_string(self, s: str) -> str:
        """Escape string for safe Cypher inclusion.

        Args:
            s: String to escape

        Returns:
            Escaped string safe for Cypher
        """
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def record_migration(self, status: str, duration_ms: float, error: Optional[str] = None) -> None:
        """Record this migration execution in the graph.

        Args:
            status: "success" or "failed"
            duration_ms: Execution time in milliseconds
            error: Error message if failed
        """
        executed_at = datetime.now().isoformat()
        error_str = f'"{self.escape_string(error)}"' if error else "null"

        query = f"""
        CREATE (m:SchemaVersion {{
            version: "{self.VERSION}",
            executed_at: "{executed_at}",
            duration_ms: {duration_ms},
            status: "{status}",
            error: {error_str},
            description: "{self.escape_string(self.DESCRIPTION)}"
        }})
        RETURN m
        """

        try:
            self.execute_query(query)
            # Update snapshot after recording migration
            self._write_schema_snapshot()
        except Exception as e:
            self.log(f"Warning: Could not record migration: {str(e)}")

    def _write_schema_snapshot(self) -> None:
        """Write SchemaVersion snapshot to docs."""
        try:
            query = """
            MATCH (sv:SchemaVersion)
            RETURN sv.version, sv.status, sv.executed_at, sv.description
            ORDER BY sv.executed_at DESC
            """
            result = self.graph.query(query)
            rows = result.result_set if hasattr(result, "result_set") else []

            lines = []
            lines.append("# SchemaVersion Snapshot")
            lines.append("")
            lines.append("Generated from FalkorDB.")
            lines.append("")
            lines.append("| Version | Status | Executed At | Description |")
            lines.append("|---|---|---|---|")
            for row in rows:
                version, status, executed_at, description = row
                lines.append(f"| {version} | {status} | {executed_at} | {description} |")

            content = "\n".join(lines) + "\n"
            path = Path(__file__).resolve().parents[3] / "docs" / "SCHEMAVERSION_SNAPSHOT.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self.log(f"Warning: Could not write schema snapshot: {str(e)}")
