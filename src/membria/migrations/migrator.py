"""Migrator: Runs and manages database schema migrations."""

import importlib
import time
from datetime import datetime
from typing import List, Optional, Tuple
from falkordb import FalkorDB
from membria.migrations.base import Migration


class Migrator:
    """Manages database migrations.

    Responsibilities:
    - Discover available migrations
    - Detect current schema version
    - Run pending migrations in order
    - Handle rollback to previous versions
    - Validate migration state
    """

    def __init__(self, db: FalkorDB):
        """Initialize migrator.

        Args:
            db: FalkorDB connection instance
        """
        self.db = db
        self.graph = db.select_graph("membria")
        self.migrations: List[Tuple[str, type]] = []
        self._discover_migrations()

    def _discover_migrations(self) -> None:
        """Discover all available migrations in versions/ directory.

        Migrations are expected to be in membria/migrations/versions/
        File naming: v{MAJOR}_{MINOR}_{PATCH}_{name}.py
        Class naming: V{MAJOR}_{MINOR}_{PATCH}_{Name}

        Raises:
            ImportError: If migration cannot be imported
        """
        import os
        from pathlib import Path

        migrations_dir = Path(__file__).parent / "versions"
        self.migrations = []

        if not migrations_dir.exists():
            print("⚠️  Migrations directory not found")
            return

        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.startswith("v") and f.endswith(".py")])

        for filename in migration_files:
            module_name = filename[:-3]  # Remove .py extension
            # Parse semantic version from filename: v0_1_0_name -> 0.1.0
            parts = module_name.split("_")
            if parts and parts[0].startswith("v"):
                parts[0] = parts[0][1:]  # strip leading 'v'
            version = ".".join(parts[0:3]) if len(parts) >= 3 else module_name.replace("_", ".")

            try:
                module = importlib.import_module(f"membria.migrations.versions.{module_name}")

                # Convert filename to class name
                # v0_1_0_initial -> V0_1_0_Initial
                class_name = self._filename_to_classname(module_name)

                if hasattr(module, class_name):
                    migration_class = getattr(module, class_name)
                    self.migrations.append((version, migration_class))
                else:
                    print(f"⚠️  Migration class {class_name} not found in {module_name}")

            except ImportError as e:
                print(f"⚠️  Could not import migration {module_name}: {str(e)}")

        print(f"📦 Discovered {len(self.migrations)} migrations")

    def _filename_to_classname(self, filename: str) -> str:
        """Convert migration filename to class name.

        v0_1_0_initial -> V0_1_0_Initial
        v0_2_0_engrams -> V0_2_0_Engrams

        Args:
            filename: Migration filename without .py extension

        Returns:
            Expected class name
        """
        # Remove leading 'v' if present
        if filename.startswith('v'):
            filename = filename[1:]

        parts = filename.split("_")
        # Format is: {major}_{minor}_{patch}_{name...}
        # So parts = ['0', '1', '0', 'name', ...]
        if len(parts) < 3:
            return f"V{filename}"

        # Extract version and name parts
        version_part = "_".join(parts[0:3])  # "0_1_0"
        name_parts = parts[3:]  # ['initial'] or ['engrams']

        name_part = "_".join([p.capitalize() for p in name_parts]) if name_parts else ""

        class_name = f"V{version_part}"
        if name_part:
            class_name += f"_{name_part}"

        return class_name

    def get_current_version(self) -> str:
        """Get the current schema version.

        Queries SchemaVersion nodes to find the latest executed migration.

        Returns:
            Current version string (e.g., "0.1.0"), or "0.0.0" if no migrations
        """
        try:
            query = """
            MATCH (sv:SchemaVersion)
            WHERE sv.status = "success"
            RETURN sv.version
            ORDER BY sv.executed_at DESC
            LIMIT 1
            """
            result = self.graph.query(query)

            if result and hasattr(result, "result_set") and len(result.result_set) > 0:
                return result.result_set[0][0]
            return "0.0.0"

        except Exception as e:
            print(f"⚠️  Could not determine current version: {str(e)[:100]}")
            return "0.0.0"

    def get_pending_migrations(self) -> List[Tuple[str, type]]:
        """Get list of migrations that haven't been executed yet.

        Returns:
            List of (version, migration_class) tuples
        """
        current = self.get_current_version()
        pending = []

        for version, migration_class in self.migrations:
            if self._compare_versions(version, current) > 0:
                pending.append((version, migration_class))

        return pending

    def migrate_to(self, target_version: Optional[str] = None) -> bool:
        """Run all pending migrations up to target version.

        Args:
            target_version: Target version to migrate to. If None, migrate to latest.

        Returns:
            True if successful, False otherwise
        """
        if not self.migrations:
            print("⚠️  No migrations found")
            return False

        pending = self.get_pending_migrations()

        if not pending:
            current = self.get_current_version()
            print(f"✓ Already at latest version: {current}")
            return True

        print(f"🚀 Running {len(pending)} pending migrations...")

        for version, migration_class in pending:
            if target_version and self._compare_versions(version, target_version) > 0:
                break

            success = self._run_migration(version, migration_class)
            if not success:
                print(f"❌ Migration {version} failed")
                return False

        print("✓ All migrations completed successfully")
        return True

    def rollback_to(self, target_version: str) -> bool:
        """Rollback to a specific version.

        Executes rollback() in reverse order for all migrations after target.

        Args:
            target_version: Version to rollback to

        Returns:
            True if successful, False otherwise
        """
        current = self.get_current_version()

        if self._compare_versions(target_version, current) >= 0:
            print(f"✓ Already at or before version {target_version}")
            return True

        # Get migrations to rollback in reverse order
        to_rollback = []
        for version, migration_class in reversed(self.migrations):
            if self._compare_versions(version, current) <= 0 and self._compare_versions(version, target_version) > 0:
                to_rollback.append((version, migration_class))

        if not to_rollback:
            print(f"⚠️  No migrations to rollback")
            return True

        print(f"🔄 Rolling back {len(to_rollback)} migrations...")

        for version, migration_class in to_rollback:
            success = self._run_rollback(version, migration_class)
            if not success:
                print(f"❌ Rollback {version} failed")
                return False

        print(f"✓ Rolled back to version {target_version}")
        return True

    def _run_migration(self, version: str, migration_class: type) -> bool:
        """Execute a single migration.

        Args:
            version: Migration version
            migration_class: Migration class to instantiate and run

        Returns:
            True if successful, False otherwise
        """
        print(f"\n📌 Running migration {version}...")
        start_time = time.time()

        try:
            migration = migration_class(self.db)

            # Check dependencies
            if hasattr(migration, "DEPENDENCIES") and migration.DEPENDENCIES:
                for dep in migration.DEPENDENCIES:
                    if self._compare_versions(dep, self.get_current_version()) > 0:
                        print(f"❌ Dependency {dep} not satisfied")
                        return False

            # Run migration
            migration.migrate()

            # Validate
            if not migration.validate():
                print(f"❌ Validation failed for {version}")
                migration.record_migration("failed", 0, "validation failed")
                return False

            # Record success
            duration_ms = (time.time() - start_time) * 1000
            migration.record_migration("success", duration_ms)

            print(f"✓ Migration {version} completed in {duration_ms:.0f}ms")
            return True

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)[:100]
            print(f"❌ Migration {version} failed: {error_msg}")

            try:
                migration.record_migration("failed", duration_ms, error_msg)
            except Exception:
                pass

            return False

    def _run_rollback(self, version: str, migration_class: type) -> bool:
        """Execute rollback for a single migration.

        Args:
            version: Migration version
            migration_class: Migration class to instantiate and run

        Returns:
            True if successful, False otherwise
        """
        print(f"\n🔄 Rolling back migration {version}...")
        start_time = time.time()

        try:
            migration = migration_class(self.db)
            migration.rollback()
            duration_ms = (time.time() - start_time) * 1000
            print(f"✓ Rollback {version} completed in {duration_ms:.0f}ms")
            return True

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"❌ Rollback {version} failed: {error_msg}")
            return False

    def validate_migrations(self) -> bool:
        """Validate current schema state.

        Runs validate() on all executed migrations.

        Returns:
            True if all migrations are valid, False otherwise
        """
        current = self.get_current_version()
        print(f"🔍 Validating migrations (current: {current})...")

        all_valid = True
        for version, migration_class in self.migrations:
            if self._compare_versions(version, current) > 0:
                break

            try:
                migration = migration_class(self.db)
                if not migration.validate():
                    print(f"❌ Validation failed for {version}")
                    all_valid = False
                else:
                    print(f"✓ {version} valid")
            except Exception as e:
                print(f"❌ Could not validate {version}: {str(e)[:100]}")
                all_valid = False

        if all_valid:
            print("✓ All migrations are valid")
        else:
            print("❌ Some migrations failed validation")

        return all_valid

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two semantic versions.

        Args:
            v1: First version (e.g., "0.1.0")
            v2: Second version (e.g., "0.2.0")

        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        try:
            parts1 = tuple(map(int, v1.split(".")))
            parts2 = tuple(map(int, v2.split(".")))

            if parts1 < parts2:
                return -1
            elif parts1 > parts2:
                return 1
            else:
                return 0
        except Exception:
            return 0  # Default: versions are equal if parsing fails
