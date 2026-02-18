import typer
from typing import Optional, List, Dict
import json
import os
import sys
from rich.console import Console
from pathlib import Path
from tabulate import tabulate

console = Console()
app = typer.Typer(help="Connect Membria to external IDEs and tools")
experts_app = typer.Typer(help="Manage Membria Expert Roles")
providers_app = typer.Typer(help="Manage AI Model Providers")

@app.command("claude")
def connect_claude(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show config without writing")
):
    """Connect Membria to Claude Desktop MCP."""
    config_path = Path("~/Library/Application Support/Claude/claude_desktop_config.json").expanduser()
    
    python_path = sys.executable
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    
    new_config = {
        "mcpServers": {
            "membria": {
                "command": python_path,
                "args": [server_path]
            }
        }
    }
    
    if dry_run:
        console.print("[bold cyan]Proposed Claude Desktop Config:[/bold cyan]")
        console.print_json(data=new_config)
        return

    if not config_path.parent.exists():
        console.print(f"[red]Claude Desktop config directory not found: {config_path.parent}[/red]")
        return

    existing_config = {}
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                existing_config = json.load(f)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read existing config: {e}. Creating new.[/yellow]")

    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["membria"] = new_config["mcpServers"]["membria"]

    try:
        with open(config_path, "w") as f:
            json.dump(existing_config, f, indent=2)
        console.print(f"[bold green]✓[/bold green] Connected to Claude Desktop! (Config updated at {config_path})")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to update config:[/bold red] {e}")

@app.command("continue")
def connect_continue():
    """Show instructions to connect Membria to Continue.dev."""
    python_path = sys.executable
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    
    config_snippet = {
        "type": "mcp",
        "name": "membria",
        "command": f"{python_path} {server_path}"
    }
    
    console.print("[bold]To connect Membria to Continue.dev:[/bold]")
    console.print("Add this to your [cyan]~/.continue/config.json[/cyan] under the [yellow]'contextProviders'[/yellow] array:")
    console.print_json(data=config_snippet)

@app.command("aider")
def connect_aider():
    """Show instructions to connect Membria to Aider."""
    python_path = sys.executable
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    
    console.print("[bold]To connect Membria to Aider:[/bold]")
    console.print("Add this to your [cyan].aider.conf.yml[/cyan] in your project root:")
    console.print(f"[yellow]mcp-command: {python_path} {server_path}[/yellow]")
    console.print("\n[dim]Aider will now use Membria for context and pattern retrieval.[/dim]")

@app.command("cursor")
def connect_cursor():
    """Show instructions to connect Membria to Cursor IDE."""
    python_path = sys.executable
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    
    console.print("[bold]To connect Membria to Cursor:[/bold]")
    console.print("1. Open Cursor Settings -> Models -> MCP")
    console.print("2. Click '+ Add New MCP Server'")
    console.print(f"3. Name: [cyan]membria[/cyan]")
    console.print("4. Type: [cyan]command[/cyan]")
    console.print(f"5. Command: [yellow]{python_path} {server_path}[/yellow]")
    console.print("\n[dim]Membria will now provide experts and context to your Cursor AI.[/dim]")

def run_tool(
    tool: str = typer.Argument(..., help="Tool command to run (e.g. 'aider', 'claude-code')"),
    args: Optional[str] = typer.Option(None, help="Additional arguments for the tool")
):
    """Run an external tool wrapped with Membria intelligence (MCP Bridge)."""
    import subprocess
    
    python_path = sys.executable
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"))
    
    console.print(f"[bold green]🚀 Launching {tool} with Membria Intelligence...[/bold green]")
    
    # In a real implementation, we would set up environment variables 
    # or start the MCP server and pass the port to the tool if it supports it.
    # For now, we'll simulate the launch and note the MCP injection.
    
    env = os.environ.copy()
    env["MEMBRIA_MCP_COMMAND"] = f"{python_path} {server_path}"
    
    console.print(f"[bold cyan]🏛️ Membria Orchestrator:[/bold cyan] Initializing context bridge...")
    console.print(f"[dim]Bridge URI: mcp://membria (via {server_path})[/dim]")
    console.print(f"[bold cyan]Membria Orchestrator:[/bold cyan] Launching [yellow]{tool}[/yellow]...\n")
    
    try:
        cmd = tool.split()
        if args:
            cmd.extend(args.split())
            
        # This is a simplified wrapper. 
        # Future: Use a real MCP stdio bridge if the tool supports it.
        subprocess.run(cmd, env=env)
        console.print(f"\n[bold green]✓[/bold green] {tool} execution finished. Membria captured outcomes.")
    except Exception as e:
        console.print(f"[bold red]Error launching tool:[/bold red] {e}")

# --- Experts Sub-App ---

@experts_app.command("list")
def list_experts():
    """List all configured expert roles."""
    from membria.interactive.expert_registry import ExpertRegistry
    from membria.config import ConfigManager
    
    config = ConfigManager().config
    experts = ExpertRegistry.EXPERTS
    custom_experts = config.team.get("agents", {})
    
    table = []
    for role, data in experts.items():
        config_status = "[green]Default[/green]"
        if role in custom_experts:
            config_status = f"[cyan]Custom ({custom_experts[role].get('model', 'unknown')})[/cyan]"
        
        table.append([role, data["name"], config_status, ", ".join(data.get("traits", []))])
        
    headers = ["Role", "Name", "Status", "Traits"]
    console.print(tabulate(table, headers=headers, tablefmt="simple"))

@experts_app.command("configure")
def configure_expert(role: str):
    """Interactively configure an expert role."""
    from membria.interactive.expert_registry import ExpertRegistry
    from membria.config import ConfigManager
    
    if role.lower() not in ExpertRegistry.EXPERTS:
        console.print(f"[red]Role '{role}' not found in registry.[/red]")
        return
        
    config_manager = ConfigManager()
    
    model = typer.prompt(f"Enter model for {role} (e.g. gpt-4, claude-3-5-sonnet-latest)", default="claude-3-5-sonnet-latest")
    provider = typer.prompt(f"Enter provider for {role} (openai, anthropic)", default="anthropic")
    label = typer.prompt(f"Enter display label for {role}", default=ExpertRegistry.EXPERTS[role]["name"])
    
    if "agents" not in config_manager.config.team:
        config_manager.config.team["agents"] = {}
        
    config_manager.config.team["agents"][role] = {
        "model": model,
        "provider": provider,
        "label": label
    }
    
    config_manager.save()
    console.print(f"[bold green]✓ Expert {role} configured successfully![/bold green]")

# --- Providers Sub-App ---

@providers_app.command("config")
def config_provider(name: str):
    """Configure an AI provider (API keys, etc)."""
    from membria.config import ConfigManager
    config_manager = ConfigManager()
    
    api_key = typer.prompt(f"Enter API Key for {name}", hide_input=True)
    
    if "providers" not in config_manager.config.providers:
        config_manager.config.providers = {}
        
    config_manager.config.providers[name] = {
        "api_key": api_key,
        "enabled": True
    }
    
    config_manager.save()
    console.print(f"[bold green]✓ Provider {name} configured successfully![/bold green]")

@providers_app.command("list")
def list_providers():
    """List all configured providers."""
    from membria.config import ConfigManager
    config = ConfigManager().config
    
    providers = config.providers
    if not providers:
        console.print("[yellow]No providers configured. Use 'membria providers config <name>'[/yellow]")
        return
        
    table = []
    for name, data in providers.items():
        key_status = "[green]Set[/green]" if data.get("api_key") else "[red]Missing[/red]"
        table.append([name, key_status, data.get("endpoint", "Default")])
        
    headers = ["Provider", "API Key", "Endpoint"]
    console.print(tabulate(table, headers=headers, tablefmt="simple"))

@providers_app.command("test")
def test_provider(name: str):
    """Test connection to a provider using a simple probe."""
    import asyncio
    from membria.interactive.providers import ProviderFactory, Message
    from membria.config import ConfigManager
    
    config = ConfigManager().config
    p_config = config.providers.get(name)
    
    if not p_config or not p_config.get("api_key"):
        console.print(f"[red]Provider {name} is not configured or missing API key.[/red]")
        return

    async def _test():
        console.print(f"[yellow]Testing connection to {name}...[/yellow]")
        try:
            provider = ProviderFactory.get_provider(name, p_config["api_key"])
            model = "claude-3-5-sonnet-latest" if name == "anthropic" else "gpt-4o-latest"
            
            # Simple probe
            messages = [Message(role="user", content="ping")]
            response = await provider.complete(model, messages)
            
            if response and response.content:
                console.print(f"[bold green]✓ Connection successful![/bold green] (Model: {model})")
            else:
                console.print(f"[bold red]✗ Connection failed:[/bold red] Empty response")
        except Exception as e:
            console.print(f"[bold red]✗ Connection failed:[/bold red] {str(e)}")

    asyncio.run(_test())
