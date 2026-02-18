"""Database migrations module.

This module contains:
- Migration base class (membria.migrations.base.Migration)
- Migrator runner (membria.migrations.migrator.Migrator)
- Individual migration versions (membria.migrations.versions.*)

Usage:
    from membria.migrations.migrator import Migrator
    from membria.storage import Storage

    storage = Storage()
    storage.connect()
    migrator = Migrator(storage.db)

    # Run pending migrations
    migrator.migrate_to()

    # Check current version
    current = migrator.get_current_version()
"""

from membria.migrations.base import Migration, MigrationRecord
from membria.migrations.migrator import Migrator

__all__ = [
    "Migration",
    "MigrationRecord",
    "Migrator",
]
