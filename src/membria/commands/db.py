"""Database commands: migration, versioning, and schema management."""

import typer
from typing import Optional
from membria.migrations.migrator import Migrator
from membria.graph import GraphClient

app = typer.Typer(help="Database operations (migrations, versioning, validation)")


@app.command()
def version() -> None:
    """Show current database schema version.

    Displays the version of the database schema currently applied.
    """
    try:
        graph_client = GraphClient()
        graph_client.connect()

        db = graph_client.db_instance
        migrator = Migrator(db)

        current_version = migrator.get_current_version()

        if current_version == "0.0.0":
            typer.echo("📊 No migrations applied (schema version: 0.0.0)")
        else:
            typer.echo(f"📊 Current schema version: {current_version}")

        # Show migration history
        try:
            graph = graph_client.graph
            query = """
            MATCH (sv:SchemaVersion)
            RETURN sv.version, sv.executed_at, sv.status, sv.duration_ms
            ORDER BY sv.executed_at DESC
            LIMIT 10
            """
            result = graph.query(query)

            if result:
                typer.echo("\n📋 Recent migrations:")
                for row in result:
                    version = row[0]
                    executed_at = row[1]
                    status = row[2]
                    duration_ms = row[3]
                    status_icon = "✓" if status == "success" else "✗"
                    typer.echo(f"  {status_icon} {version} ({duration_ms:.0f}ms) - {executed_at}")
        except Exception as e:
            pass  # Don't fail if we can't show history

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def migrate(target: Optional[str] = typer.Option(None, "--to", help="Target version to migrate to")) -> None:
    """Run pending migrations.

    Applies all pending migrations in order, bringing the schema up to date.
    Migrations are automatically validated after execution.

    Args:
        target: Optional target version (e.g., "0.1.0"). If not specified, migrates to latest.

    Examples:
        membria db migrate                    # Migrate to latest
        membria db migrate --to 0.1.0         # Migrate to specific version
    """
    try:
        graph_client = GraphClient()
        graph_client.connect()

        db = graph_client.db_instance
        migrator = Migrator(db)

        # Check for pending migrations
        pending = migrator.get_pending_migrations()
        current = migrator.get_current_version()

        if not pending:
            typer.echo(f"✓ Already at latest version ({current})")
            graph_client.disconnect()
            return

        typer.echo(f"Current version: {current}")
        typer.echo(f"Pending migrations: {len(pending)}")

        if target:
            typer.echo(f"Target: {target}")

        # Run migrations
        success = migrator.migrate_to(target)

        if success:
            new_version = migrator.get_current_version()
            typer.echo(f"✓ Migrations completed. New version: {new_version}")

            # Validate
            typer.echo("\n🔍 Validating schema...")
            if migrator.validate_migrations():
                typer.echo("✓ Schema is valid")
            else:
                typer.echo("⚠️  Schema validation warnings detected")
                raise typer.Exit(1)
        else:
            typer.echo("❌ Migration failed", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def rollback(to: str = typer.Argument(..., help="Version to rollback to (e.g., 0.1.0)")) -> None:
    """Rollback database to a specific version.

    Undoes all migrations after the specified version, restoring the schema
    to that state.

    Args:
        to: Version to rollback to (e.g., "0.1.0")

    Examples:
        membria db rollback 0.1.0
        membria db rollback 0.0.0
    """
    try:
        graph_client = GraphClient()
        graph_client.connect()

        db = graph_client.db_instance
        migrator = Migrator(db)

        current = migrator.get_current_version()

        if current == to:
            typer.echo(f"✓ Already at version {to}")
            return

        typer.echo(f"Current version: {current}")
        typer.echo(f"Rolling back to: {to}")

        # Confirm rollback
        confirm = typer.confirm("⚠️  This will undo migrations. Continue?", default=False)
        if not confirm:
            typer.echo("Rollback cancelled")
            return

        # Run rollback
        success = migrator.rollback_to(to)

        if success:
            new_version = migrator.get_current_version()
            typer.echo(f"✓ Rollback completed. Version: {new_version}")

            # Validate
            typer.echo("\n🔍 Validating schema...")
            if migrator.validate_migrations():
                typer.echo("✓ Schema is valid")
            else:
                typer.echo("⚠️  Schema validation warnings detected")
        else:
            typer.echo("❌ Rollback failed", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


@app.command()
def validate() -> None:
    """Validate database schema integrity.

    Checks that all applied migrations are in a valid state.
    Useful for diagnosing schema issues.
    """
    try:
        graph_client = GraphClient()
        graph_client.connect()

        db = graph_client.db_instance
        migrator = Migrator(db)

        current = migrator.get_current_version()
        typer.echo(f"Checking schema version {current}...\n")

        is_valid = migrator.validate_migrations()

        if is_valid:
            typer.echo("\n✓ Schema is valid")
        else:
            typer.echo("\n❌ Schema validation failed", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {str(e)}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
