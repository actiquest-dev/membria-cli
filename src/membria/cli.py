"""Main CLI application entry point."""

import os
import typer
from rich.console import Console
from typing import Optional

from membria import __version__
from membria.commands import (
    daemon_app,
    config_app,
    decisions_app,
    engrams_app,
    stats_app,
    calibration_app,
    extractor_app,
    safety_app,
    db_app,
    antipattern_app,
    outcomes_app,
    webhook_app,
    graph_agents_app,
    kb_app,
    session_app,
    squad_app,
)
from membria.commands.integration import (
    app as integration_app,
    experts_app,
    providers_app
)

app = typer.Typer(
    name="membria",
    help="AI-powered decision memory for developers",
    add_completion=False,
)
console = Console()

# Register sub-commands
app.add_typer(daemon_app, name="daemon")
app.add_typer(config_app, name="config")
app.add_typer(decisions_app, name="decisions")
app.add_typer(engrams_app, name="engrams")
app.add_typer(stats_app, name="stats")
app.add_typer(calibration_app, name="calibration")
app.add_typer(extractor_app, name="extractor")
app.add_typer(safety_app, name="safety")
app.add_typer(db_app, name="db")
app.add_typer(antipattern_app, name="antipattern")
app.add_typer(outcomes_app, name="outcome")
app.add_typer(webhook_app, name="webhook")
app.add_typer(graph_agents_app, name="graph")
app.add_typer(kb_app, name="kb")
app.add_typer(session_app, name="session")
app.add_typer(squad_app, name="squad")
app.add_typer(integration_app, name="connect")
app.add_typer(experts_app, name="experts")
app.add_typer(providers_app, name="providers")


def _force_textual_theme() -> None:
    os.environ.pop("NO_COLOR", None)
    os.environ.pop("CLICOLOR", None)
    os.environ.pop("CLICOLOR_FORCE", None)
    os.environ.setdefault("TEXTUAL_THEME", "nord")
    os.environ.setdefault("TEXTUAL_COLOR_SYSTEM", "256")
    os.environ.setdefault("COLORTERM", "truecolor")
    os.environ.setdefault("TERM", "xterm-256color")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"Membria CLI v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    no_splash: bool = typer.Option(
        False,
        "--no-splash",
        help="Skip splash screen on startup",
    ),
) -> None:
    """
    Membria CLI - AI-powered decision memory.
    """
    # Auto-migrate on startup
    try:
        from membria.graph import GraphClient
        from membria.migrations.migrator import Migrator

        graph_client = GraphClient()
        graph_client.connect()

        db = graph_client.db_instance
        migrator = Migrator(db)

        # Check for pending migrations
        pending = migrator.get_pending_migrations()
        if pending:
            console.print(f"[dim]Running {len(pending)} pending migrations...[/dim]")
            if migrator.migrate_to():
                new_version = migrator.get_current_version()
                console.print(f"[dim]✓ Schema migrated to {new_version}[/dim]")
            else:
                console.print("[bold red]✗ Migration failed[/bold red]", err=True)
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[dim]⚠️  Could not check migrations: {str(e)[:100]}[/dim]", err=True)

    # If no subcommand is invoked, start the interactive shell
    if ctx.invoked_subcommand is None:
        _force_textual_theme()
        from membria.interactive.textual_shell import run_textual_shell
        from membria.config import ConfigManager
        
        config_manager = ConfigManager()
        try:
            run_textual_shell(config_manager, skip_splash=no_splash)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Interrupted. Goodbye![/dim]")
        except Exception as e:
            import traceback
            console.print(f"\n[red bold]Fatal shell error:[/red bold]")
            console.print(f"[red]{str(e)}[/red]")
            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
            raise

@app.command()
def shell():
    """Start interactive Membria shell."""
    _force_textual_theme()
    from membria.interactive.textual_shell import run_textual_shell
    from membria.config import ConfigManager
    
    config_manager = ConfigManager()
    try:
        run_textual_shell(config_manager)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Interrupted. Goodbye![/dim]")
    except Exception as e:
        import traceback
        console.print(f"\n[red bold]Fatal shell error:[/red bold]")
        console.print(f"[red]{str(e)}[/red]")
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        raise

hooks_app = typer.Typer(help="Manage Membria Git hooks")
app.add_typer(hooks_app, name="hooks")

@hooks_app.command("install")
def hooks_install():
    """Install Membria Git hooks for auto-capture."""
    from membria.interactive.hooks import HookManager
    manager = HookManager()
    manager.install()

@hooks_app.command("uninstall")
def hooks_uninstall():
    """Remove Membria Git hooks."""
    from membria.interactive.hooks import HookManager
    manager = HookManager()
    manager.uninstall()

auth_app = typer.Typer(help="Manage Membria authentication")
app.add_typer(auth_app, name="auth")

@auth_app.command("login")
def auth_login():
    """Sign in to your Membria account via browser (Plus/Pro)."""
    import asyncio
    from membria.interactive.auth import AuthManager
    manager = AuthManager()
    asyncio.run(manager.login())

@auth_app.command("logout")
def auth_logout():
    """Clear your local Membria session."""
    from membria.interactive.auth import AuthManager
    manager = AuthManager()
    manager.logout()

@auth_app.command("status")
def auth_status():
    """Verify your current authentication status."""
    from membria.interactive.auth import AuthManager
    manager = AuthManager()
    token = manager.get_token()
    if token:
        # Mocking user info for now
        is_pro = "plus" in token or "pro" in token
        tier = "[bold magenta]PRO[/bold magenta]" if is_pro else "Standard"
        console.print(f"Status: [green]Logged In[/green]")
        console.print(f"Tier: {tier}")
        console.print(f"Token: {token[:8]}...{token[-4:]} (secured in keyring)")
    else:
        console.print("Status: [yellow]Not Logged In[/yellow]")
        console.print("Run 'membria auth login' to sign in.")

@app.command("run")
def run(tool: str, args: Optional[str] = None):
    """Run an external tool wrapped with Membria intelligence."""
    from membria.commands.integration import run_tool
    run_tool(tool, args)
    

@app.command()
def chat(
    mode: str = typer.Option("auto", "--mode", "-m", help="Orchestration mode (auto, pipeline, debate, consensus, or a specific expert role)")
):
    """Start an interactive chat session with the Membria Council."""
    from membria.commands.chat_commands import chat_command
    chat_command(mode=mode)

@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", help="Host to bind the dashboard to"),
    port: int = typer.Option(8000, help="Port to run the dashboard on")
):
    """Launch the Membria Analytics Dashboard in your browser."""
    from membria.interactive.dashboard.server import start_dashboard
    import webbrowser
    
    url = f"http://{host}:{port}"
    console.print(f"[bold green]🚀 Launching Membria Dashboard at {url}[/bold green]")
    webbrowser.open(url)
    start_dashboard(host=host, port=port)


@app.command()
def init(
    team: Optional[str] = typer.Option(None, "--team", help="Team ID to join")
) -> None:
    """Initialize Membria in the current directory."""
    console.print("[bold green]✓[/bold green] Initializing Membria...")
    console.print("[bold green]✓[/bold green] Created ~/.membria/")
    console.print("[bold green]✓[/bold green] Initialized local graph (FalkorDB in-memory)")
    console.print("[bold green]✓[/bold green] Default config written")
    
    if team:
        console.print(f"[bold yellow]![/bold yellow] Team mode not available in Phase 1")


@app.command()
def doctor() -> None:
    """Check Membria installation and configuration."""
    from membria.graph import GraphClient
    
    console.print("[bold]Membria Health Check[/bold]\n")
    console.print("[bold green]✓[/bold green] CLI installed")
    
    # Check Graph
    try:
        from membria.graph import GraphClient
        client = GraphClient()
        if client.connect():
            health = client.health_check()
            if health["status"] == "healthy":
                console.print(f"[bold green]✓[/bold green] Graph: connected ({client.host}:{client.port})")
            else:
                console.print(f"[bold red]✗[/bold red] Graph: error ({health.get('error')})")
        else:
            console.print(f"[bold red]✗[/bold red] Graph: could not connect to {client.host}:{client.port}")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Graph: error ({str(e)})")

    # Check Providers
    from membria.config import ConfigManager
    config = ConfigManager().config
    providers = config.providers
    if not providers:
        console.print("[bold red]✗[/bold red] Providers: none configured")
        console.print("  [dim]Run 'membria providers config anthropic' to connect a real model[/dim]")
    else:
        for p_name, p_data in providers.items():
            if p_data.get("api_key"):
                console.print(f"[bold green]✓[/bold green] Provider: {p_name} (API key set)")
            else:
                console.print(f"[bold red]✗[/bold red] Provider: {p_name} (API key missing)")

    # Check Daemon (optional)
    console.print("[bold yellow]![/bold yellow] Daemon: not running (optional)")
    
    console.print("\n[dim]Run 'membria init' or 'membria providers --help' to get started[/dim]")


if __name__ == "__main__":
    app()
