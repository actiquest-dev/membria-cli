"""
Splash Screen for Membria Interactive Shell
Displays logo and system status during startup
"""

import asyncio
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.screen import Screen
from rich.panel import Panel


class SplashScreen(Screen):
    """Membria startup splash screen"""
    
    DEFAULT_CSS = """
    Screen {
        background: $panel;
        color: $text;
        align: center middle;
    }
    
    #splash_container {
        height: auto;
        width: 60;
        layout: vertical;
        align: center middle;
        background: $panel;
    }
    
    #logo_widget {
        width: 60;
        height: auto;
        text-align: center;
        color: #5AA5FF;
    }
    
    #status_widget {
        width: 60;
        height: auto;
        text-align: center;
        color: #E8E8E8;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.frame = 0
    
    def compose(self) -> ComposeResult:
        with Container(id="splash_container"):
            yield Static(self._render_logo(), id="logo_widget")
            yield Static("", id="status_widget")
    
    def _render_logo(self) -> str:
        """Render Membria logo in bright blue"""
        logo = """
[#5AA5FF]╔════════════════════════════════╗
║                                ║
║    [bold]█  █  █  █  █  █  █[/bold]       ║
║    [bold]█  █  █  █  █  █  █[/bold]       ║
║    [bold]M E M B R I A[/bold]          ║
║    [bold]█  █  █  █  █  █  █[/bold]       ║
║    [bold]█  █  █  █  █  █  █[/bold]       ║
║                                ║
║  [#FFB84D]Decision Memory Engine[/#FFB84D]     ║
║                                ║
╚════════════════════════════════╝[/#5AA5FF]
"""
        return logo
    
    def _render_status(self) -> str:
        """Render initialization status (animated)"""
        # Animated spinner frames
        spinner_frames = ["◐", "◓", "◑", "◒"]
        spinner = spinner_frames[self.frame % len(spinner_frames)]
        
        status_text = f"[#FFB84D]{spinner}[/#FFB84D] [#E8E8E8]Initializing...[/#E8E8E8]"
        
        # Show component status based on frame
        if self.frame > 5:
            status_text += "\n[#21C93A]✓ Graph Database[/#21C93A]"
        if self.frame > 10:
            status_text += "\n[#21C93A]✓ Agent Registry[/#21C93A]"
        if self.frame > 15:
            status_text += "\n[#21C93A]✓ Calibration[/#21C93A]"
        
        return status_text
    
    async def on_mount(self) -> None:
        """Start animation and auto-dismiss after 2 seconds"""
        # Animate the status widget by updating every 0.1 seconds
        while self.frame < 20:
            self.frame += 1
            try:
                status_widget = self.query_one("#status_widget", Static)
                status_widget.update(self._render_status())
            except Exception:
                break
            await asyncio.sleep(0.1)
        
        # Auto-dismiss after all frames rendered or 2 seconds
        self.dismiss()
    
    def on_key(self, _) -> None:
        """Dismiss on any key press"""
        self.dismiss()


class ExitSplashScreen(Screen):
    """Exit splash screen with session summary"""
    
    DEFAULT_CSS = """
    Screen {
        background: $panel;
        color: $text;
        align: center middle;
    }
    
    #exit_container {
        height: auto;
        width: 60;
        layout: vertical;
        align: center middle;
        background: $panel;
    }
    
    #exit_message {
        width: 60;
        height: auto;
        text-align: center;
        color: $text;
    }
    """
    
    def __init__(self, session_stats: dict = None):
        super().__init__()
        self.session_stats = session_stats or {}
    
    def compose(self) -> ComposeResult:
        with Container(id="exit_container"):
            yield Static(self.render_exit_message(), id="exit_message")
    
    def render_exit_message(self):
        """Render exit splash screen content"""
        lines = [
            "[#5AA5FF][bold]Membria[/bold][/#5AA5FF]",
            "",
            "[#FFB84D]Session Summary[/#FFB84D]",
            f"[#21C93A]✓ Tasks completed: {self.session_stats.get('tasks_completed', 0)}[/#21C93A]",
            f"[#21C93A]✓ Decisions recorded: {self.session_stats.get('decisions_recorded', 0)}[/#21C93A]",
            f"[#FFB84D]📊 Tokens used: {self.session_stats.get('tokens_used', 0):,}[/#FFB84D]",
            f"[#E8E8E8]📈 Calibration updates: {self.session_stats.get('calibration_updates', 0)}[/#E8E8E8]",
            "",
            "[#999999]Graph is learning...[/#999999]",
        ]
        content = "\n".join(lines)
        return Panel(
            content, 
            border_style="#5AA5FF", 
            padding=(1, 2),
            title="[#5AA5FF][bold]Membria[/bold][/#5AA5FF]"
        )
    
    def on_mount(self) -> None:
        """Auto-close after 3 seconds"""
        self.set_timer(self._auto_dismiss, 3.0, count=1)
    
    def _auto_dismiss(self) -> None:
        """Remove exit screen"""
        self.dismiss()
    
    def on_key(self, _) -> None:
        """Dismiss on any key press"""
        self.dismiss()

