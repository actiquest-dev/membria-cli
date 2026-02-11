# Membria Versioning Strategy

**Версия документа:** 1.0
**Статус:** DESIGN (не реализовано!)
**Цель:** Как поддерживать версионность кода, schema и данных

---

## Проблема

Сейчас:
- CLI версия: 0.1.0 (только строка)
- MCP daemon версия: 0.2.0 (hardcoded)
- FalkorDB schema версия: не существует
- Миграции: не существуют
- Rollback: не возможен
- Backward compatibility: не проверяется

**Если добавим новый node type в schema, старые данные сломаются!**

---

## Семантическое версионирование

### CLI Version (src/membria/__init__.py)

```python
__version__ = "MAJOR.MINOR.PATCH"

# Examples:
0.1.0  - Phase 1 MVP
0.2.0  - Phase 2 (Decision Extractor)
0.3.0  - Phase 3 (Cognitive Safety)
1.0.0  - Production ready
1.1.0  - New feature (backward compatible)
2.0.0  - Breaking change (schema incompatible)
```

**MAJOR:**
- 0 = Alpha (breaking changes expected)
- 1+ = Stable (semantic versioning)

**MINOR:**
- New features (backward compatible)
- New commands
- New nodes in schema

**PATCH:**
- Bug fixes
- Security patches
- No schema changes

### Schema Version (in FalkorDB graph)

```
schema_version = "0.1" (separate from CLI version!)

0.1 - Initial (Decision nodes only)
0.2 - Add Engram + MADE_IN relationship
0.3 - Add CodeChange + Outcome nodes
0.4 - Add NegativeKnowledge
0.5 - Add AntiPattern nodes
1.0 - Stable schema
```

---

## Version Metadata in Graph

### Store in FalkorDB

```cypher
(:SchemaVersion {
  version: "0.2.0",
  cli_version: "0.1.0",
  timestamp: 1707500000,
  migration_count: 2,
  notes: "Added Engram nodes and MADE_IN relationship"
})

(:Migration {
  id: "001_initial_schema",
  version_from: "0.1.0",
  version_to: "0.2.0",
  timestamp: 1707400000,
  status: "completed",
  description: "Initial Decision nodes only",
  rollback_script: "MATCH (n:Migration {id: '001'}) DELETE n"
})

(:Migration {
  id: "002_add_engram_nodes",
  version_from: "0.2.0",
  version_to: "0.3.0",
  timestamp: 1707500000,
  status: "completed",
  description: "Add Engram nodes and MADE_IN relationship"
})
```

---

## Migration System

### Directory Structure

```
src/membria/migrations/
├── __init__.py
├── migrator.py              # Migration runner
└── versions/
    ├── v0_1_0_initial.py    # Decision nodes
    ├── v0_2_0_engrams.py    # Engram nodes
    ├── v0_3_0_outcomes.py   # CodeChange + Outcome
    ├── v0_4_0_nk.py         # NegativeKnowledge
    └── v0_5_0_antipatterns.py  # AntiPattern nodes
```

### Migration File Format

```python
# src/membria/migrations/versions/v0_2_0_engrams.py

"""Add Engram nodes and MADE_IN relationship"""

VERSION = "0.2.0"
DESCRIPTION = "Add Engram nodes and MADE_IN relationship"
DEPENDENCIES = ["v0_1_0_initial"]

def migrate(graph):
    """Apply migration (0.1.0 → 0.2.0)"""
    try:
        # Create index for faster queries
        graph.query("CREATE INDEX ON :Engram(id)")

        # Add constraint
        graph.query(
            "CREATE CONSTRAINT FOR (e:Engram) "
            "REQUIRE e.id IS UNIQUE"
        )

        # Verify backward compat: existing Decisions still work
        result = graph.query("MATCH (d:Decision) RETURN count(d) as cnt")
        assert result[0]['cnt'] > 0, "Existing decisions missing!"

        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

def rollback(graph):
    """Rollback migration (0.2.0 → 0.1.0)"""
    try:
        # Drop Engram nodes
        graph.query("MATCH (e:Engram) DELETE e")

        # Drop index
        graph.query("DROP INDEX engram_id_idx")

        return True
    except Exception as e:
        print(f"Rollback failed: {e}")
        return False

def validate(graph):
    """Validate migration success"""
    # Check schema is correct
    engram_count = graph.query("MATCH (e:Engram) RETURN count(e)")
    decision_count = graph.query("MATCH (d:Decision) RETURN count(d)")

    assert engram_count > 0 or decision_count > 0, \
        "No nodes found after migration!"

    return True
```

### Migration Runner

```python
# src/membria/migrations/migrator.py

class Migrator:
    def __init__(self, graph):
        self.graph = graph
        self.current_version = self._get_version()

    def _get_version(self):
        """Get current schema version from graph"""
        try:
            result = self.graph.query(
                "MATCH (sv:SchemaVersion) "
                "RETURN sv.version "
                "ORDER BY sv.timestamp DESC LIMIT 1"
            )
            return result[0]['version'] if result else "0.1.0"
        except:
            return "0.1.0"

    def migrate_to(self, target_version):
        """Migrate from current to target version"""
        migrations = self._plan_migrations(
            self.current_version,
            target_version
        )

        for migration in migrations:
            print(f"Applying {migration.VERSION}...")

            # Run migration
            if not migration.migrate(self.graph):
                print(f"Failed! Rolling back...")
                migration.rollback(self.graph)
                return False

            # Validate
            if not migration.validate(self.graph):
                print(f"Validation failed! Rolling back...")
                migration.rollback(self.graph)
                return False

            # Record migration
            self._record_migration(migration)
            self.current_version = migration.VERSION

        return True

    def rollback_to(self, target_version):
        """Rollback from current to target version"""
        # Find migrations in reverse order
        migrations = self._plan_migrations_reverse(
            self.current_version,
            target_version
        )

        for migration in migrations:
            print(f"Rolling back {migration.VERSION}...")
            if not migration.rollback(self.graph):
                print(f"Rollback failed!")
                return False
            self.current_version = target_version

        return True

    def _record_migration(self, migration):
        """Record migration in graph"""
        query = f"""
        CREATE (:Migration {{
            id: '{migration.VERSION}',
            timestamp: {int(time.time())},
            status: 'completed',
            description: '{migration.DESCRIPTION}'
        }})
        UPDATE :SchemaVersion SET version = '{migration.VERSION}'
        """
        self.graph.query(query)
```

---

## CLI Versioning

### Package Version

```toml
# pyproject.toml
[project]
name = "membria"
version = "0.1.0"  # Single source of truth
```

### Version Check at Startup

```python
# src/membria/cli.py

from membria import __version__
from membria.migrations import Migrator

def main():
    # Check schema version matches CLI version
    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    graph.connect()

    migrator = Migrator(graph)
    schema_version = migrator.current_version
    cli_version = __version__

    # Auto-migrate if needed
    if schema_version != cli_version:
        print(f"Schema {schema_version} → CLI {cli_version}")
        print("Migrating...")

        if not migrator.migrate_to(cli_version):
            print("❌ Migration failed!")
            print("Run: membria db rollback")
            sys.exit(1)

        print("✅ Migration complete")

    # Now run normally
    ...
```

---

## Commands for Version Management

### New CLI Commands

```bash
# Show versions
membria version                    # Show CLI version
membria db version                 # Show schema version
membria db status                  # Show migration status

# Migration control
membria db migrate [--to VERSION]  # Migrate to version
membria db rollback [--to VERSION] # Rollback to version
membria db migrations list         # Show all migrations
membria db validate                # Validate schema integrity

# Compatibility check
membria db compat-check            # Check data compatibility
```

### Implementation

```python
# src/membria/commands/db.py (NEW FILE)

@db_app.command("version")
def version():
    """Show schema version"""
    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    graph.connect()

    migrator = Migrator(graph)
    current = migrator.current_version
    target = __version__

    console.print(f"Schema version: {current}")
    console.print(f"CLI version: {target}")

    if current != target:
        console.print(f"[yellow]⚠️  Mismatch! (schema {current} != CLI {target})[/yellow]")
        console.print("Run: membria db migrate")

@db_app.command("migrate")
def migrate(to: Optional[str] = None):
    """Migrate schema to target version"""
    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    graph.connect()

    migrator = Migrator(graph)
    target = to or __version__

    console.print(f"Migrating from {migrator.current_version} to {target}...")

    if migrator.migrate_to(target):
        console.print("[green]✅ Migration successful[/green]")
    else:
        console.print("[red]❌ Migration failed[/red]")
        raise typer.Exit(code=1)

@db_app.command("rollback")
def rollback(to: Optional[str] = None):
    """Rollback schema to previous version"""
    if not to:
        console.print("[red]❌ Must specify target version[/red]")
        raise typer.Exit(code=1)

    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    graph.connect()

    migrator = Migrator(graph)

    confirm = console.input(
        f"Rollback from {migrator.current_version} to {to}? [y/N]: "
    )

    if confirm.lower() == 'y':
        if migrator.rollback_to(to):
            console.print("[green]✅ Rollback successful[/green]")
        else:
            console.print("[red]❌ Rollback failed[/red]")
            raise typer.Exit(code=1)
```

---

## Backward Compatibility Guarantees

### Phase 1 (0.1.x)
- All 0.1.x versions compatible
- Can add new optional fields to Decision
- Can add new node types without breaking existing nodes

### Phase 2 (0.2.x)
- All 0.2.x versions compatible
- Can migrate from 0.1.x to 0.2.x
- Can rollback from 0.2.x to 0.1.x

### Phase 3 (0.3.x)
- All 0.3.x versions compatible
- Auto-migrate on startup if needed

### Phase 4+ (1.0.x)
- Stable API
- MUST maintain backward compatibility
- Deprecation warnings for breaking changes

---

## Breaking Changes Policy

**Breaking changes only in MAJOR versions:**

```
0.1.0 → 0.2.0: ✅ OK (new nodes, new relationships)
0.2.0 → 0.3.0: ✅ OK (new schema, auto-migrate)
0.3.0 → 1.0.0: ✅ OK (stabilization)

1.0.0 → 1.1.0: ❌ NOT OK (must be backward compatible)
1.0.0 → 2.0.0: ✅ OK (breaking changes allowed)
```

---

## Deployment Checklist

### Before Release

```bash
# 1. Update version
vi src/membria/__init__.py  # Bump version
git add src/membria/__init__.py

# 2. Create migration file (if schema changed)
touch src/membria/migrations/versions/vX_Y_Z_*.py
# Write migrate() + rollback() + validate()

# 3. Test migration
pytest tests/test_migrations.py

# 4. Test backward compat
pytest tests/test_compat.py

# 5. Update CHANGELOG
echo "## [X.Y.Z] - YYYY-MM-DD" > CHANGELOG.md.new

# 6. Commit and tag
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push --tags
```

---

## Testing Migrations

### Migration Tests

```python
# tests/test_migrations.py

@pytest.mark.integration
def test_migration_0_1_to_0_2(temp_graph):
    """Test migration from 0.1.0 to 0.2.0"""
    # Setup: start with 0.1.0
    setup_v0_1(temp_graph)

    # Migrate
    migrator = Migrator(temp_graph)
    assert migrator.migrate_to("0.2.0")

    # Verify
    assert migrator.current_version == "0.2.0"
    result = temp_graph.query("MATCH (e:Engram) RETURN count(e)")
    assert result[0]['count'] >= 0

@pytest.mark.integration
def test_rollback_0_2_to_0_1(temp_graph):
    """Test rollback from 0.2.0 to 0.1.0"""
    # Setup: start with 0.2.0
    setup_v0_2(temp_graph)

    # Rollback
    migrator = Migrator(temp_graph)
    assert migrator.rollback_to("0.1.0")

    # Verify old schema still works
    result = temp_graph.query("MATCH (d:Decision) RETURN count(d)")
    assert result[0]['count'] >= 0
```

### Compatibility Tests

```python
# tests/test_compat.py

def test_decision_backward_compat_v0_1_to_v0_2():
    """Old Decision nodes work in new schema"""
    # Create old-style Decision
    decision = Decision(
        decision_id="old_dec_001",
        statement="Old decision",
        alternatives=["A"],
        confidence=0.8
    )

    # Add to new schema
    graph = GraphClient()
    graph.connect()
    graph.add_decision(decision)

    # Can still query it
    results = graph.get_decisions()
    assert any(d['id'] == "old_dec_001" for d in results)
```

---

## Current Status

| Component | Version | Versioning |
|-----------|---------|-----------|
| CLI | 0.1.0 | ✅ Defined |
| MCP Daemon | 0.2.0 | ❌ Hardcoded, mismatched |
| FalkorDB Schema | ??? | ❌ Not tracked |
| Migrations | N/A | ❌ Not implemented |

---

## TODO for Phase 0

- [ ] Create migration system architecture
- [ ] Implement v0.1.0 initial migration
- [ ] Implement v0.2.0 (add Engram nodes)
- [ ] Add db commands (version, migrate, rollback)
- [ ] Version check on startup
- [ ] Migration tests
- [ ] Compatibility tests
- [ ] Documentation

---

## Rationale

**Why separate schema version from CLI version?**
- CLI can release patches without schema changes
- Schema changes might happen independent of CLI
- Allows fine-grained tracking of breaking changes

**Why store migrations in graph?**
- Single source of truth
- Can query migration history
- Enables rollback validation

**Why auto-migrate on startup?**
- User-friendly (no manual steps)
- Prevents "old schema" surprises
- Fail-safe (with rollback option)

**Why explicit rollback?**
- Dangerous operation, should require confirmation
- Prevents accidental data loss
- Gives time to reconsider

---

**Next step:** Implement migration system in Phase 0.0 (after schema design)
