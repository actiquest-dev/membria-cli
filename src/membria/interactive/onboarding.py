import os
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
from typing import List, Dict, Any
from .models import ProviderConfig, TeamConfig, AgentConfig

console = Console()

class OnboardingWizard:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.providers = {}
        self.team = {}
        
    def run(self):
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Welcome to Membria CLI[/bold cyan]\n"
            "[dim]Let's orchestrate your AI workforce.[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        if Confirm.ask("Would you like to configure your AI providers now?", default=True):
            from .auth import AuthManager
            auth = AuthManager()
            token = auth.get_token()
            
            use_browser = False
            if token:
                console.print("[green]ℹ Found active Membria Plus/Pro session.[/green]")
                use_browser = Confirm.ask("Use account-based authentication for all models?", default=True)
            else:
                console.print("\n[bold cyan]NEW:[/bold cyan] You can now sign in via browser for Membria Plus/Pro (no API keys needed).")
                if Confirm.ask("Sign in via browser now?", default=False):
                    if asyncio.run(auth.login()):
                        use_browser = True
            
            if not use_browser:
                self.setup_providers()
            else:
                # Mock: configured via proxy
                self.providers = {"membria_proxy": {"enabled": True}}
                self.config_manager.config.providers = self.providers
            
        if Confirm.ask("Would you like to assemble your agent team?", default=True):
            self.setup_team()
            
        self._save_config()
        
        console.print("\n[bold green]✅ Setup Complete![/bold green]")
        console.print("Starting your interactive session...\n")
        
    def setup_providers(self):
        console.print("\n[bold]Step 1: Provider Setup[/bold]")
        console.print("Supported providers: Anthropic (Claude), OpenAI, KiloCode, Ollama, OpenRouter")
        
        # Simple interactive setup
        if Confirm.ask("Configure Anthropic (Claude)?"):
            key = Prompt.ask("Enter ANTHROPIC_API_KEY (or leave empty to check env)", password=True)
            if key:
                # In real app, we'd validate. For now, just store it if user wants (or rely on env)
                # But actually, we prefer env vars. 
                # Let's just ask if they have it in env or want to store it in .env
                pass 
            self.providers["anthropic"] = {"enabled": True}

        if Confirm.ask("Configure OpenAI?"):
            self.providers["openai"] = {"enabled": True}
            
        if Confirm.ask("Configure others (KiloCode/Ollama)?"):
            # Placeholder for minimal onboarding
            self.providers["other"] = {"enabled": True}
            
        # Update config object in memory (as dicts, matching config.py structure)
        self.config_manager.config.providers = self.providers

    def setup_team(self):
        console.print("\n[bold]Step 2: Team Assembly[/bold]")
        console.print("Choose a team preset:")
        console.print("1. [bold]Full Power[/bold] (Claude 3.5 Sonnet + GPT-4o)")
        console.print("2. [bold]Budget Friendly[/bold] (Haiku + GPT-4o-mini)")
        console.print("3. [bold]Local only[/bold] (Ollama/Llama3)")
        
        choice = IntPrompt.ask("Select preset", choices=["1", "2", "3"], default=1)
        
        agents = {}
        
        if choice == 1:
            agents = {
                "architect": {"role": "architect", "provider": "anthropic", "model": "claude-3-5-sonnet-20240620", "label": "Archie"},
                "implementer": {"role": "implementer", "provider": "anthropic", "model": "claude-3-5-sonnet-20240620", "label": "Coder"},
                "reviewer": {"role": "reviewer", "provider": "openai", "model": "gpt-4o", "label": "Reviewer"}
            }
        elif choice == 2:
            agents = {
                "architect": {"role": "architect", "provider": "anthropic", "model": "claude-3-haiku-20240307", "label": "Archie (Lite)"},
                "implementer": {"role": "implementer", "provider": "openai", "model": "gpt-4o-mini", "label": "Coder (Mini)"},
            }
        elif choice == 3:
            agents = {
                "architect": {"role": "architect", "provider": "ollama", "model": "llama3", "label": "LocalArch"},
                "implementer": {"role": "implementer", "provider": "ollama", "model": "llama3", "label": "LocalCoder"},
            }
            
        self.config_manager.config.team = {"agents": agents}
        console.print(f"[green]Assembled team with {len(agents)} agents.[/green]")

    def _save_config(self):
        # We need to ensure config relies on primitives for toml serialization
        # The ConfigManager.save() handles the dataclass -> dict conversion via asdict
        # Our providers and team fields are Dict[str, Any], so they serialize fine.
        self.config_manager.save()
