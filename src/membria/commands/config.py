"""Configuration management commands."""

import typer
from rich.console import Console
from rich.table import Table
from dataclasses import asdict

from membria.config import ConfigManager

config_app = typer.Typer(help="Manage Membria configuration")
console = Console()


@config_app.command("show")
def show() -> None:
    """Show current configuration."""
    manager = ConfigManager()
    config_dict = asdict(manager.config)

    table = Table(title="Membria Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    def flatten_dict(d: dict, parent_key: str = "") -> list:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key))
            else:
                items.append((new_key, str(v)))
        return items

    for key, value in flatten_dict(config_dict):
        table.add_row(key, value)

    console.print(table)


@config_app.command("get")
def get(key: str) -> None:
    """Get a configuration value."""
    manager = ConfigManager()
    value = manager.get(key)

    if value is not None:
        console.print(f"[cyan]{key}[/cyan] = [green]{value}[/green]")
    else:
        console.print(f"[red]✗[/red] Config key not found: {key}")


@config_app.command("set")
def set_config(key: str, value: str) -> None:
    """Set a configuration value."""
    try:
        manager = ConfigManager()
        manager.set(key, value)
        console.print(f"[bold green]✓[/bold green] Set {key} = {value}")
        console.print("[dim]Note: Changes will take effect after daemon restart[/dim]")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to set config: {e}")


@config_app.command("graph-remote")
def graph_remote(
    host: str = typer.Argument(..., help="FalkorDB host"),
    port: int = typer.Option(6379, "--port", "-p", help="FalkorDB port"),
    password: str = typer.Option(None, "--password", "-P", help="FalkorDB password"),
) -> None:
    """Configure remote FalkorDB connection."""
    try:
        manager = ConfigManager()
        manager.set_falkordb_remote(host, port, password)
        console.print(f"[bold green]✓[/bold green] Configured remote FalkorDB")
        console.print(f"  Host: {host}:{port}")
        console.print(f"  Password: {'set' if password else 'not set'}")
        console.print("\n[dim]Testing connection...[/dim]")

        # Test connection
        from membria.graph import GraphClient
        client = GraphClient()
        if client.connect():
            health = client.health_check()
            console.print(f"[bold green]✓[/bold green] Connection successful!")
            console.print(f"  Status: {health['status']}")
            client.disconnect()
        else:
            console.print("[yellow]⚠[/yellow] Connection failed - check credentials")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to configure: {e}")
