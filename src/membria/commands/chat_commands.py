"""Interactive Chat commands for Membria CLI."""

import asyncio
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text
from rich.align import Align
from typing import Optional

from membria.interactive.executor import AgentExecutor
from membria.config import ConfigManager

console = Console()

MEMBRIA_ART = r"""[bold cyan]
             ░░░░░░░░                            ░░░░░░░░░            
            ░░░░░░░░░░░                         ░░░░░░░░░░░           
           ░░░░░░░░░░░░                         ░░░░░░░░░░░           
           ░░░░░░░░░░░░                         ░░░░░░░░░░░           
            ░░░░░░░░░░░░                       ░░░░░░░░░░░░           
              ░░░░░░░░░░░                    ░░░░░░░░░░░░             
               ░░░░░░░░░░░░                 ░░░░░░░░░░░░              
               ░░░░░ ░░░░░░░░             ░░░░░░░  ░░░░░              
               ░░░░░   ░░░░░░░          ░░░░░░░░   ░░░░░              
               ░░░░░     ░░░░░░░       ░░░░░░░     ░░░░░              
               ░░░░░      ░░░░░░░░   ░░░░░░░       ░░░░░              
               ░░░░░        ░░░░░░░░░░░░░░         ░░░░░              
               ░░░░░          ░░░░░░░░░░░          ░░░░░              
               ░░░░░           ░░░░░░░░            ░░░░░              
               ░░░░░             ░░░░              ░░░░░              
               ░░░░░                               ░░░░░              
             ░░░░░░░░░                           ░░░░░░░░░            
            ░░░░░░░░░░░                         ░░░░░░░░░░░           
           ░░░░░░░░░░░░                        ░░░░░░░░░░░░           
           ░░░░░░░░░░░░                        ░░░░░░░░░░░░           
            ░░░░░░░░░░░                         ░░░░░░░░░░░           
             ░░░░░░░░                             ░░░░░░░             
[/bold cyan]"""

class ChatCommands:
    """Handles an interactive chat session in the terminal."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.executor = AgentExecutor(self.config_manager)

    async def _chat_loop(self, mode: str = "auto"):
        """Main interaction loop."""
        console.print(Align.center(MEMBRIA_ART))
        
        console.print(Panel(
            f"🏛️ [bold cyan]Membria Interactive Council[/bold cyan]\n"
            f"Mode: [yellow]{mode.upper()}[/yellow]\n"
            f"Type [bold red]'exit'[/bold red] to end, or [bold blue]'mode <new_mode>'[/bold blue] to switch.",
            border_style="cyan"
        ))

        while True:
            try:
                user_input = Prompt.ask("\n[bold green]Principal[/bold green]")
                
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("[dim]Council adjourned.[/dim]")
                    break
                
                if user_input.lower().startswith("mode "):
                    new_mode = user_input.split(" ", 1)[1].strip().lower()
                    mode = new_mode
                    console.print(f"[dim]Switched to orchestration mode: {mode}[/dim]")
                    continue

                with Live(Panel("[bold yellow]Council is deliberating...[/bold yellow]", title="Membria"), refresh_per_second=4) as live:
                    if mode == "auto" or mode in ["pipeline", "debate", "consensus", "diamond"]:
                        response = await self.executor.run_orchestration(user_input, mode=mode)
                    else:
                        response = await self.executor.run_task(user_input, role=mode)

                    live.update(Panel(Markdown(response or "No response."), title="Council Response", subtitle=f"Mode: {mode}", border_style="green"))

            except KeyboardInterrupt:
                console.print("\n[dim]Council adjourned.[/dim]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

def chat_command(
    mode: str = typer.Option("auto", "--mode", "-m", help="Orchestration mode (auto, pipeline, debate, consensus, or a specific expert role)")
):
    """Start an interactive chat session with the Membria Council."""
    chat = ChatCommands()
    asyncio.run(chat._chat_loop(mode=mode))
