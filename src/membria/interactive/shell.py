import asyncio
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PromptStyle

from .splash import show_splash, show_status_panel
from .onboarding import OnboardingWizard
from .commands import CommandHandler
from .executor import AgentExecutor
from membria.task_router import TaskRouter
from .ui import MembriaUI

console = Console()

class MembriaShell:
    """Main interactive REPL shell for Membria."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.history_file = Path.home() / ".membria" / "shell_history"
        
        # Ensure history directory exists
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            style=PromptStyle.from_dict({
                'prompt': 'ansicyan bold',
                'bottom-toolbar': 'noreverse noinherit #888888',
                'cyan': 'ansicyan',
                'green': 'ansigreen',
                'red': 'ansired',
                'dim': '#888888',
            })
        )
        self.command_handler = CommandHandler(self)
        self.executor = AgentExecutor(config_manager)
        self.router = TaskRouter()
        self.ui = MembriaUI()
        self.executor.set_ui(self.ui)

        
    async def run(self):
        """Start the interactive session."""
        try:
            show_splash()
            
            # Check first run
            if self.config_manager.is_first_run():
                wizard = OnboardingWizard(self.config_manager)
                wizard.run()
            
            # Show status panel with real graph status
            show_status_panel(self.config_manager.config, graph_connected=self.executor.graph_client.connected)
            
            # Context Detection (Council)
            from .context_detector import ContextDetector
            detector = ContextDetector()
            ctx_mode = detector.detect()
            roles = detector.get_expert_roles(ctx_mode)
            console.print(f"[bold magenta]Council Context:[/bold magenta] {ctx_mode.value}")
            console.print(f"[dim]Expert roles for this workspace: {', '.join(roles)}[/dim]\n")
            console.print("[dim]Type /help for commands, @agent to speak to specific agent[/dim]")
            
            while True:
                try:
                    # Get footer for bottom_toolbar
                    def get_footer():
                        return self.ui.get_footer()
                    
                    text = await self.session.prompt_async(
                        "› ", 
                        bottom_toolbar=get_footer
                    )
                    
                    if not text.strip():
                        continue
                    
                    should_continue = await self.process_input(text)
                    if not should_continue:
                        break
                
                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted. Exiting...[/dim]")
                    break
                except EOFError:
                    break
                except Exception as e:
                    import traceback
                    console.print(f"\n[red]Error during input processing: {e}[/red]")
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        except Exception as e:
            import traceback
            console.print(f"\n[red bold]Fatal shell error:[/red bold]")
            console.print(f"[red]{str(e)}[/red]")
            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
            raise
        
        finally:
            # Save session on exit
            try:
                self.executor.save_session()
                console.print("[bold cyan]Goodbye![/bold cyan]")
            except:
                pass

    async def process_input(self, text: str) -> bool:
        """
        Route input to appropriate handler.
        Returns False to signal exit the loop.
        """
        stripped = text.strip()
        
        # Double-check: should never be empty at this point
        if not stripped:
            return True
        
        if stripped.startswith("/"):
            return await self.command_handler.handle_command(stripped)
            
        elif stripped.startswith("@"):
            console.print(f"[magenta]Direct agent communication not implemented in Phase 1.[/magenta]")
            console.print(f"You tried to reach: {stripped.split()[0]}")
            return True
            
        else:
            # Phase 2: Task routing and execution
            console.print("[dim]Classifying task...[/dim]")
            classification = self.router.classify(stripped)
            
            # Map classification to agent role
            role_map = {
                "TACTICAL": "implementer",
                "DECISION": "architect",
                "LEARNING": "architect"
            }
            
            target_role = role_map.get(classification.task_type.name, "implementer")
            
            console.print(f"[dim]Routing to [bold]{target_role}[/bold] (Type: {classification.task_type.name}, Conf: {classification.confidence:.2f})[/dim]")
            
            result = await self.executor.run_task(stripped, role=target_role)
            
            if result:
                result_text = f"\n[bold {target_role}]{target_role.upper()}[/bold {target_role}]\n{result}"
                console.print(result_text)
            else:
                console.print("[red]Agent execution failed.[/red]")
                
            return True
