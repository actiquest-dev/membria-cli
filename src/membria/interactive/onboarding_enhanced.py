"""
Comprehensive onboarding wizard for Membria CLI.
Runs on first launch to set up providers, roles, graph DB, and initial settings.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.progress import Progress
from rich.table import Table

console = Console()


class EnhancedOnboardingWizard:
    """
    Comprehensive setup wizard that guides users through:
    1. Welcome & Concept explanation
    2. Provider authentication (Anthropic, OpenAI, Ollama, etc)
    3. Role assignment (Architect, Security, DB Expert, Moderator)
    4. Graph Database setup (FalkorDB optional)
    5. Monitoring level selection (L0-L3)
    6. Theme selection
    7. First decision capture (tutorial)
    8. Summary and next steps
    """
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.step = 0
        self.total_steps = 8
        self.completed = {
            "providers": False,
            "roles": False,
            "graph_db": False,
            "monitoring": False,
            "theme": False,
            "first_decision": False,
        }
    
    def run(self):
        """Run the complete onboarding wizard."""
        try:
            self.show_welcome()
            self.step_providers_setup()
            self.step_roles_assignment()
            self.step_graph_database()
            self.step_monitoring_level()
            self.step_theme_selection()
            self.step_first_decision()
            self.show_summary()
            
            self._save_all()
            
            console.print("\n[bold green]✅ Setup Complete![/bold green]")
            console.print("Starting your interactive session...\n")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Setup interrupted[/yellow]")
            if Confirm.ask("Save partial configuration?", default=True):
                self._save_all()
            raise
    
    def show_welcome(self):
        """Step 0: Welcome and concept explanation."""
        self.step = 1
        
        console.clear()
        
        welcome_text = """
[bold cyan]╭─ Welcome to Membria ─╮[/bold cyan]

[#FFB84D]Your Decision Intelligence Platform[/#FFB84D]

Membria is a middleware that captures your AI decisions,
tracks their outcomes, and improves future choices through
continuous calibration.

[#21C93A]What you'll build:[/#21C93A]
  ✓ A council of AI experts (Architect, Security, Database, Moderator)
  ✓ Decision memory graph (who decided what, when, outcome)
  ✓ Calibration system (know when you're overconfident)
  ✓ Context injection (learn from past decisions)

[#5AA5FF]How it works:[/#5AA5FF]
  1. You make a decision → Membria captures it
  2. Decision → Code → Outcome (tracked via GitHub webhooks)
  3. Outcome recorded → Calibration updates
  4. Next similar decision gets context from past outcomes

[#E8E8E8]Right now:[/#E8E8E8]
  Let's set up your AI providers, assemble your team,
  and configure your workspace.

[bold cyan]╰──────────────────────╯[/bold cyan]
"""
        console.print(welcome_text)
        
        if not Confirm.ask("[yellow]Ready to get started?[/yellow]", default=True):
            raise KeyboardInterrupt()
    
    def step_providers_setup(self):
        """Step 1: Set up AI providers."""
        self.step = 2
        self._show_step_header("Provider Setup", "Connect your AI models")
        
        providers = {}
        
        console.print("\n[#FFB84D]Available Providers:[/#FFB84D]\n")
        
        # Anthropic (Claude)
        if Confirm.ask("  ✓ Anthropic (Claude 3.5 Sonnet, Haiku)?", default=True):
            console.print("\n[#5AA5FF]Enter your Anthropic API key:[/#5AA5FF]")
            console.print("[dim]Get it from: https://console.anthropic.com/[/dim]")
            
            key = Prompt.ask("  API Key", password=True, default="")
            if key:
                providers["anthropic"] = {
                    "type": "anthropic",
                    "api_key": key,
                    "model": "claude-3-5-sonnet-20241022",
                    "enabled": True
                }
                console.print("[#21C93A]  ✓ Anthropic configured[/#21C93A]")
            else:
                console.print("[yellow]  ⚠ Skipped (check env var ANTHROPIC_API_KEY)[/yellow]")
                providers["anthropic"] = {
                    "type": "anthropic",
                    "api_key": "",
                    "model": "claude-3-5-sonnet-20241022",
                    "enabled": True
                }
        
        # OpenAI
        if Confirm.ask("\n  ✓ OpenAI (GPT-4o, GPT-4o-mini)?", default=True):
            console.print("\n[#5AA5FF]Enter your OpenAI API key:[/#5AA5FF]")
            console.print("[dim]Get it from: https://platform.openai.com/api-keys[/dim]")
            
            key = Prompt.ask("  API Key", password=True, default="")
            if key:
                providers["openai"] = {
                    "type": "openai",
                    "api_key": key,
                    "model": "gpt-4-turbo",
                    "enabled": True
                }
                console.print("[#21C93A]  ✓ OpenAI configured[/#21C93A]")
            else:
                console.print("[yellow]  ⚠ Skipped (check env var OPENAI_API_KEY)[/yellow]")
                providers["openai"] = {
                    "type": "openai",
                    "api_key": "",
                    "model": "gpt-4-turbo",
                    "enabled": True
                }
        
        # Ollama (local)
        if Confirm.ask("\n  ✓ Ollama (Local models - llama2, mistral)?", default=False):
            console.print("\n[#5AA5FF]Ollama configuration:[/#5AA5FF]")
            endpoint = Prompt.ask("  Endpoint", default="http://localhost:11434")
            model = Prompt.ask("  Default model", default="llama2")
            
            providers["ollama"] = {
                "type": "ollama",
                "endpoint": endpoint,
                "model": model,
                "enabled": True
            }
            console.print("[#21C93A]  ✓ Ollama configured[/#21C93A]")
        
        if not providers:
            console.print("\n[red]✗ No providers configured![/red]")
            if Confirm.ask("Continue without providers (you'll need to add them later)?", default=False):
                pass
            else:
                raise KeyboardInterrupt()
        
        self.config_manager.config.providers = providers
        self.completed["providers"] = True
    
    def step_roles_assignment(self):
        """Step 2: Assign roles to providers."""
        self.step = 3
        self._show_step_header("Role Assignment", "Build your expert council")
        
        console.print("\n[#FFB84D]Available Roles:[/#FFB84D]\n")
        
        roles = {
            "architect": {
                "title": "Architect",
                "description": "System design & high-level decisions",
                "recommended_provider": "anthropic"
            },
            "security": {
                "title": "Security Engineer",
                "description": "Security & authentication review",
                "recommended_provider": "anthropic"
            },
            "database": {
                "title": "Database Expert",
                "description": "Schema design & query optimization",
                "recommended_provider": "openai"
            },
            "moderator": {
                "title": "Moderator",
                "description": "Conflict resolution & consensus",
                "recommended_provider": "anthropic"
            }
        }
        
        providers = self.config_manager.config.providers or {}
        available_providers = list(providers.keys())
        
        assigned_roles = {}
        
        for role_key, role_info in roles.items():
            console.print(f"  [#5AA5FF]✓ {role_info['title']}[/#5AA5FF]")
            console.print(f"    {role_info['description']}")
            
            if available_providers:
                console.print(f"\n    Available: {', '.join(available_providers)}")
                provider = Prompt.ask(
                    f"    Assign to provider",
                    default=role_info["recommended_provider"]
                    if role_info["recommended_provider"] in available_providers
                    else available_providers[0]
                )
                
                assigned_roles[role_key] = {
                    "title": role_info["title"],
                    "provider": provider,
                    "model": providers.get(provider, {}).get("model", ""),
                    "enabled": True
                }
                console.print(f"    [#21C93A]✓ Assigned to {provider}[/#21C93A]\n")
        
        self.config_manager.config.roles = assigned_roles
        self.completed["roles"] = True
    
    def step_graph_database(self):
        """Step 3: Set up FalkorDB (optional but recommended)."""
        self.step = 4
        self._show_step_header("Graph Database", "Store your decision history")
        
        console.print("""
[#FFB84D]FalkorDB - Decision Memory Graph[/#FFB84D]

Membria stores all your decisions, outcomes, and relationships
in a graph database. This enables:
  ✓ Query: "Show me similar past decisions"
  ✓ Calibrate: "Am I overconfident in this domain?"
  ✓ Learn: "What patterns led to success?"

[#5AA5FF]Setup Options:[/#5AA5FF]
  1. Docker (recommended) - Auto-launch container
  2. Local Binary - Download binary + run
  3. Managed Service - Use cloud-hosted FalkorDB
  4. Skip - Use in-memory storage (no persistence)
""")
        
        choice = IntPrompt.ask("  Choose setup method", choices=["1", "2", "3", "4"], default=1)
        
        if choice == 1:
            if self._setup_docker_falkor():
                self.completed["graph_db"] = True
        elif choice == 2:
            if self._setup_binary_falkor():
                self.completed["graph_db"] = True
        elif choice == 3:
            endpoint = Prompt.ask("  FalkorDB endpoint", default="https://api.falkordb.com")
            api_key = Prompt.ask("  API Key", password=True, default="")
            self.config_manager.config.graph_db = {
                "type": "managed",
                "endpoint": endpoint,
                "api_key": api_key
            }
            self.completed["graph_db"] = True
        else:
            console.print("[yellow]  ⚠ Skipping FalkorDB (decisions won't persist)[/yellow]")
    
    def _setup_docker_falkor(self) -> bool:
        """Set up FalkorDB via Docker."""
        console.print("\n[#5AA5FF]Docker Setup:[/#5AA5FF]")
        
        if not Confirm.ask("  Docker installed?", default=True):
            console.print("  [yellow]Install Docker: https://docker.com[/yellow]")
            return False
        
        console.print("\n  [dim]Running: docker run -d -p 6379:6379 falkordb/falkordb[/dim]")
        
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "run", "-d", "-p", "6379:6379", "falkordb/falkordb"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                console.print("  [#21C93A]✓ FalkorDB running on localhost:6379[/#21C93A]")
                self.config_manager.config.graph_db = {
                    "type": "docker",
                    "host": "localhost",
                    "port": 6379
                }
                return True
            else:
                console.print(f"  [red]✗ Docker failed: {result.stderr.decode()}[/red]")
                return False
        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")
            return False
    
    def _setup_binary_falkor(self) -> bool:
        """Set up FalkorDB via binary."""
        console.print("\n[#5AA5FF]Binary Setup:[/#5AA5FF]")
        console.print("  Download: https://github.com/FalkorDB/FalkorDB/releases")
        console.print("  Extract and run the binary, then provide path:")
        
        path = Prompt.ask("  FalkorDB binary path", default="/usr/local/bin/falkordb")
        
        if Path(path).exists():
            console.print(f"  [#21C93A]✓ Found at {path}[/#21C93A]")
            self.config_manager.config.graph_db = {
                "type": "binary",
                "path": path
            }
            return True
        else:
            console.print(f"  [yellow]⚠ Not found at {path}[/yellow]")
            return False
    
    def step_monitoring_level(self):
        """Step 4: Choose monitoring/logging level."""
        self.step = 5
        self._show_step_header("Monitoring Level", "Set logging verbosity")
        
        console.print("\n[#FFB84D]What should Membria log?[/#FFB84D]\n")
        
        levels = {
            "L0": {
                "name": "Silent",
                "description": "No logging (production mode)",
                "emoji": "🤐"
            },
            "L1": {
                "name": "Decisions",
                "description": "Show decisions + outcomes (default)",
                "emoji": "📝"
            },
            "L2": {
                "name": "Reasoning",
                "description": "L1 + agent thinking traces",
                "emoji": "🧠"
            },
            "L3": {
                "name": "Debug",
                "description": "L2 + tool calls + graph queries",
                "emoji": "🔍"
            },
        }
        
        for level, info in levels.items():
            console.print(f"  {info['emoji']} {level}: {info['name']}")
            console.print(f"     {info['description']}\n")
        
        choice = Prompt.ask("  Choose level", default="L1")
        
        if choice not in levels:
            console.print("[yellow]  Invalid choice, using L1[/yellow]")
            choice = "L1"
        
        self.config_manager.config.monitoring = {"level": choice}
        self.completed["monitoring"] = True
        console.print(f"  [#21C93A]✓ Set to {choice}[/#21C93A]")
    
    def step_theme_selection(self):
        """Step 5: Choose color theme."""
        self.step = 6
        self._show_step_header("Color Theme", "Personalize your CLI")
        
        console.print("\n[#FFB84D]Available Themes:[/#FFB84D]\n")
        
        themes = [
            ("nord", "Arctic palette", "Cool blues + greens"),
            ("gruvbox", "Retro groove", "Warm oranges + reds"),
            ("tokyo-night", "Cyberpunk", "Purple + cyan neon"),
            ("solarized-light", "Light mode", "High contrast"),
            ("solarized-dark", "Dark mode", "High contrast"),
            ("dracula", "Vampire theme", "Pink + purple"),
            ("one-dark", "Atom-like", "Warm palette"),
            ("monokai", "High contrast", "Bold colors"),
        ]
        
        for idx, (name, style, desc) in enumerate(themes, 1):
            console.print(f"  {idx}. [bold]{name}[/bold] - {style}")
            console.print(f"     {desc}\n")
        
        choice = IntPrompt.ask("  Choose theme (1-8)", default=1)
        
        if 1 <= choice <= len(themes):
            theme_name = themes[choice - 1][0]
            self.config_manager.config.display = {"theme": theme_name}
            self.completed["theme"] = True
            console.print(f"  [#21C93A]✓ Theme set to {theme_name}[/#21C93A]")
        else:
            console.print("[yellow]  Invalid choice, using nord[/yellow]")
            self.config_manager.config.display = {"theme": "nord"}
    
    def step_first_decision(self):
        """Step 6: Capture first decision (tutorial)."""
        self.step = 7
        self._show_step_header("First Decision", "Experience Membria in action")
        
        console.print("""
[#FFB84D]Let's capture your first decision![/#FFB84D]

This is a tutorial to show how Membria works:
  1. You make a decision
  2. Membria records it with confidence
  3. Later: outcome is tracked
  4. System learns from the result

[#E8E8E8]Example:[/#E8E8E8]
  Decision: "Use JWT for authentication"
  Confidence: 0.92 (quite confident)
  Domain: authentication
"
)
        
        if Confirm.ask("  Ready to capture your first decision?", default=True):
            statement = Prompt.ask("  Your decision statement")
            confidence = IntPrompt.ask("  How confident? (0-100)", default=80) / 100.0
            domain = Prompt.ask("  Domain (architecture, database, auth, etc)", default="general")
            
            first_decision = {
                "statement": statement,
                "confidence": confidence,
                "domain": domain,
                "timestamp": "2026-02-16T12:00:00Z"  # Will be set by app
            }
            
            self.config_manager.config.first_decision = first_decision
            self.completed["first_decision"] = True
            
            console.print(f"\n[#21C93A]✓ Decision recorded![/#21C93A]")
            console.print(f"  \"{statement}\"")
            console.print(f"  Confidence: {confidence:.0%} | Domain: {domain}")
    
    def show_summary(self):
        """Step 7: Show summary of what was configured."""
        self.step = 8
        self._show_step_header("Setup Summary", "Configuration complete")
        
        console.print("\n[#FFB84D]✅ You've configured:[/#FFB84D]\n")
        
        # Providers
        providers = self.config_manager.config.providers or {}
        console.print(f"  📦 Providers: {len(providers)}")
        for name in providers:
            console.print(f"     ✓ {name}")
        
        # Roles
        roles = self.config_manager.config.roles or {}
        console.print(f"\n  👥 Roles: {len(roles)}")
        for name in roles:
            console.print(f"     ✓ {roles[name].get('title', name)}")
        
        # Graph DB
        if self.config_manager.config.graph_db:
            console.print(f"\n  🗄️  Graph Database: Configured")
        
        # Monitoring
        monitoring = self.config_manager.config.monitoring or {}
        level = monitoring.get("level", "L1")
        console.print(f"\n  📊 Monitoring: {level}")
        
        # Theme
        display = self.config_manager.config.display or {}
        theme = display.get("theme", "nord")
        console.print(f"\n  🎨 Theme: {theme}")
        
        # First decision
        if self.config_manager.config.first_decision:
            console.print(f"\n  📝 First Decision: Recorded")
        
        console.print("\n[#E8E8E8]Next steps:[/#E8E8E8]")
        console.print("  1. Type /help for all commands")
        console.print("  2. Use /plan to start delegating tasks")
        console.print("  3. Set API keys: /settings set-key <provider> <key>")
        console.print("  4. View decisions: /decisions")
        console.print("  5. Check calibration: /calibration")
    
    def _save_all(self):
        """Save all configuration to file."""
        try:
            self.config_manager.save()
            console.print("[#21C93A]✓ Configuration saved[/#21C93A]")
        except Exception as e:
            console.print(f"[red]✗ Save failed: {e}[/red]")
    
    def _show_step_header(self, title: str, subtitle: str):
        """Display a step header."""
        progress_text = f"({self.step}/{self.total_steps})"
        header = Panel.fit(
            f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim] {progress_text}",
            border_style="cyan"
        )
        console.print(f"\n{header}")


def run_onboarding_wizard(config_manager):
    """Entry point for onboarding wizard."""
    wizard = EnhancedOnboardingWizard(config_manager)
    wizard.run()
