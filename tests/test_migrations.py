"""Tests for database migrations."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from membria.migrations.base import Migration, MigrationRecord
from membria.migrations.versions.v0_1_0_initial import V0_1_0_Initial
from membria.migrations.versions.v0_2_0_engrams import V0_2_0_Engrams
from membria.migrations.migrator import Migrator


class TestMigrationBase:
    """Test the Migration base class."""

    def test_migration_has_version(self):
        """Test that migrations have VERSION defined."""
        assert V0_1_0_Initial.VERSION == "0.1.0"
        assert V0_2_0_Engrams.VERSION == "0.2.0"

    def test_migration_has_description(self):
        """Test that migrations have DESCRIPTION defined."""
        assert V0_1_0_Initial.DESCRIPTION == "Create initial Decision node type and schema tracking"
        assert V0_2_0_Engrams.DESCRIPTION == "Add Engram node type and MADE_IN relationships"

    def test_migration_has_dependencies(self):
        """Test that migrations have DEPENDENCIES defined."""
        assert V0_1_0_Initial.DEPENDENCIES == []
        assert V0_2_0_Engrams.DEPENDENCIES == ["0.1.0"]

    def test_escape_string(self):
        """Test string escaping for Cypher safety."""
        mock_db = Mock()
        migration = V0_1_0_Initial(mock_db)

        # Test backslash escaping
        assert migration.escape_string("foo\\bar") == "foo\\\\bar"

        # Test quote escaping
        assert migration.escape_string('foo"bar') == 'foo\\"bar'

        # Test combined
        assert migration.escape_string('foo\\"bar') == 'foo\\\\\\"bar'


class TestV0_1_0_Initial:
    """Test v0.1.0 initial migration."""

    def test_v0_1_0_migrate(self):
        """Test that v0.1.0 migration runs without error."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("test",)]

        migration = V0_1_0_Initial(mock_db)
        migration.migrate()

        # Should have called query multiple times
        assert mock_graph.query.call_count > 0

    def test_v0_1_0_validate_success(self):
        """Test v0.1.0 validation passes when schema exists."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph

        # Mock successful query responses
        mock_graph.query.side_effect = [
            [("test_decision_id",)],  # Create test node
            [],  # Cleanup query
        ]

        migration = V0_1_0_Initial(mock_db)
        result = migration.validate()

        assert result is True

    def test_v0_1_0_validate_failure(self):
        """Test v0.1.0 validation fails when schema is broken."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.side_effect = Exception("Query failed")

        migration = V0_1_0_Initial(mock_db)
        result = migration.validate()

        assert result is False

    def test_v0_1_0_rollback(self):
        """Test v0.1.0 rollback removes Decision nodes."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = []

        migration = V0_1_0_Initial(mock_db)
        migration.rollback()

        # Should have called query to delete nodes
        assert mock_graph.query.call_count > 0


class TestV0_2_0_Engrams:
    """Test v0.2.0 engrams migration."""

    def test_v0_2_0_migrate(self):
        """Test that v0.2.0 migration runs without error."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("test",)]

        migration = V0_2_0_Engrams(mock_db)
        migration.migrate()

        # Should have called query multiple times
        assert mock_graph.query.call_count > 0

    def test_v0_2_0_dependencies(self):
        """Test that v0.2.0 has correct dependencies."""
        assert "0.1.0" in V0_2_0_Engrams.DEPENDENCIES
        assert len(V0_2_0_Engrams.DEPENDENCIES) == 1

    def test_v0_2_0_validate_success(self):
        """Test v0.2.0 validation passes when schema exists."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph

        # Mock successful query responses
        mock_graph.query.side_effect = [
            [("test_decision",)],  # Create decision
            [("test_engram",)],    # Create engram
            [["1"]],               # Create relationship
            [],                    # Cleanup
        ]

        migration = V0_2_0_Engrams(mock_db)
        result = migration.validate()

        assert result is True


class TestMigrator:
    """Test the Migrator class."""

    def test_migrator_init(self):
        """Test Migrator initialization."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph

        migrator = Migrator(mock_db)

        assert migrator.db == mock_db
        assert migrator.graph == mock_graph

    def test_compare_versions_less_than(self):
        """Test version comparison: v1 < v2."""
        assert Migrator._compare_versions("0.1.0", "0.2.0") < 0
        assert Migrator._compare_versions("0.1.0", "1.0.0") < 0

    def test_compare_versions_equal(self):
        """Test version comparison: v1 == v2."""
        assert Migrator._compare_versions("0.1.0", "0.1.0") == 0

    def test_compare_versions_greater_than(self):
        """Test version comparison: v1 > v2."""
        assert Migrator._compare_versions("0.2.0", "0.1.0") > 0
        assert Migrator._compare_versions("1.0.0", "0.9.0") > 0

    def test_get_current_version_none(self):
        """Test getting current version when no migrations applied."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = []  # No migrations

        migrator = Migrator(mock_db)
        version = migrator.get_current_version()

        assert version == "0.0.0"

    def test_get_current_version_exists(self):
        """Test getting current version when migrations applied."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("0.1.0",)]

        migrator = Migrator(mock_db)
        version = migrator.get_current_version()

        assert version == "0.1.0"

    def test_filename_to_classname(self):
        """Test conversion of filename to class name."""
        migrator = Migrator.__new__(Migrator)

        # Test v0_1_0_initial -> V0_1_0_Initial
        classname = migrator._filename_to_classname("v0_1_0_initial")
        assert classname == "V0_1_0_Initial"

        # Test v0_2_0_engrams -> V0_2_0_Engrams
        classname = migrator._filename_to_classname("v0_2_0_engrams")
        assert classname == "V0_2_0_Engrams"

    def test_get_pending_migrations_empty(self):
        """Test getting pending migrations when none exist."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("0.2.0",)]  # All migrations applied

        migrator = Migrator(mock_db)
        migrator.migrations = [
            ("0.1.0", Mock),
            ("0.2.0", Mock),
        ]

        pending = migrator.get_pending_migrations()

        assert len(pending) == 0

    def test_get_pending_migrations_with_pending(self):
        """Test getting pending migrations when some exist."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("0.1.0",)]  # Only 0.1.0 applied

        migrator = Migrator(mock_db)
        migrator.migrations = [
            ("0.1.0", Mock),
            ("0.2.0", Mock),
        ]

        pending = migrator.get_pending_migrations()

        assert len(pending) == 1
        assert pending[0][0] == "0.2.0"

    def test_validate_migrations_all_valid(self):
        """Test validation when all migrations are valid."""
        mock_db = Mock()
        mock_graph = Mock()
        mock_db.select_graph.return_value = mock_graph
        mock_graph.query.return_value = [("0.1.0",)]

        # Create mock migration that validates
        mock_migration_class = Mock()
        mock_migration_instance = Mock()
        mock_migration_instance.validate.return_value = True
        mock_migration_class.return_value = mock_migration_instance

        migrator = Migrator(mock_db)
        migrator.migrations = [
            ("0.1.0", mock_migration_class),
        ]

        result = migrator.validate_migrations()

        assert result is True

    def test_migration_record_dataclass(self):
        """Test MigrationRecord dataclass."""
        now = datetime.now()
        record = MigrationRecord(
            version="0.1.0",
            executed_at=now,
            duration_ms=100.5,
            status="success",
        )

        assert record.version == "0.1.0"
        assert record.executed_at == now
        assert record.duration_ms == 100.5
        assert record.status == "success"
        assert record.error is None

    def test_migration_record_with_error(self):
        """Test MigrationRecord with error."""
        now = datetime.now()
        record = MigrationRecord(
            version="0.1.0",
            executed_at=now,
            duration_ms=50.0,
            status="failed",
            error="Database connection failed",
        )

        assert record.status == "failed"
        assert record.error == "Database connection failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
