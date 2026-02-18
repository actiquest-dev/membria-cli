"""
Real-time progress bar for long-running operations in Textual UI.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.progress import Progress, BarColumn, TextColumn, PercentageColumn, TimeRemainingColumn
from rich.text import Text
from typing import Optional, Callable
import asyncio


class ProgressBar(Static):
    """Interactive progress bar widget."""
    
    progress = reactive(0.0)  # 0.0-1.0
    is_active = reactive(False)
    status_text = reactive("Initializing...")
    
    def __init__(self, title: str = "Processing...", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.start_time = None
        self.eta_seconds = None
    
    def render(self) -> Text:
        """Render the progress bar."""
        if not self.is_active:
            return Text("", style="dim")
        
        # Create bar
        bar_length = 30
        filled = int(bar_length * self.progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Format output
        percentage = f"{int(self.progress * 100)}%"
        output = (
            f"[#5AA5FF]{self.title}[/#5AA5FF]\n"
            f"[#21C93A]│{bar}│[/#21C93A] {percentage}\n"
            f"[#FFB84D]{self.status_text}[/#FFB84D]"
        )
        
        return Text.from_markup(output)
    
    def start(self, title: str = None):
        """Start the progress bar."""
        if title:
            self.title = title
        self.is_active = True
        self.progress = 0.0
        self.status_text = "Starting..."
        self.refresh()
    
    def update(self, progress: float, status: str = None):
        """Update progress (0.0-1.0)."""
        self.progress = max(0.0, min(1.0, progress))
        if status:
            self.status_text = status
        self.refresh()
    
    def complete(self, message: str = "Done!"):
        """Mark as complete."""
        self.progress = 1.0
        self.status_text = message
        self.is_active = True
        self.refresh()
    
    def finish(self):
        """Hide the progress bar."""
        self.is_active = False
        self.refresh()


class StepProgress(Static):
    """Multi-step progress indicator."""
    
    class Step:
        def __init__(self, name: str, status: str = "pending"):
            self.name = name
            self.status = status  # pending, running, done, error
            self.message = ""
    
    def __init__(self, steps: list, **kwargs):
        super().__init__(**kwargs)
        self.steps = [self.Step(s) if isinstance(s, str) else s for s in steps]
        self.current_step = 0
    
    def render(self) -> Text:
        """Render step progress."""
        output = Text()
        
        for i, step in enumerate(self.steps):
            if step.status == "done":
                icon = "[#21C93A]✓[/#21C93A]"
            elif step.status == "running":
                icon = "[#FFB84D]⊙[/#FFB84D]"
            elif step.status == "error":
                icon = "[red]✗[/red]"
            else:
                icon = "[#999999]○[/#999999]"
            
            line = f"{icon} {step.name}"
            if step.message:
                line += f" - {step.message}"
            
            output.append(line + "\n")
        
        return output
    
    def start_step(self, step_idx: int, message: str = ""):
        """Start a step."""
        if 0 <= step_idx < len(self.steps):
            self.steps[step_idx].status = "running"
            self.steps[step_idx].message = message
            self.refresh()
    
    def complete_step(self, step_idx: int, message: str = ""):
        """Complete a step."""
        if 0 <= step_idx < len(self.steps):
            self.steps[step_idx].status = "done"
            if message:
                self.steps[step_idx].message = message
            self.refresh()
    
    def error_step(self, step_idx: int, message: str = ""):
        """Mark step as error."""
        if 0 <= step_idx < len(self.steps):
            self.steps[step_idx].status = "error"
            if message:
                self.steps[step_idx].message = message
            self.refresh()


async def long_operation_with_progress(
    progress_bar: ProgressBar,
    operation: Callable,
    steps: int = 10,
    operation_name: str = "Processing"
) -> Optional[str]:
    """Run a long operation with progress updates.
    
    Args:
        progress_bar: ProgressBar widget to update
        operation: Async function that yields progress (0.0-1.0)
        steps: Number of steps for the operation
        operation_name: Name to display
    
    Returns:
        Result from operation, or None on error
    """
    progress_bar.start(operation_name)
    
    try:
        # Run operation - it should be an async generator that yields progress
        result = None
        async for progress in operation():
            progress_bar.update(progress, f"Step {int(progress * steps)}/{steps}")
            await asyncio.sleep(0.1)  # Allow UI updates
        
        progress_bar.complete("✓ Done!")
        await asyncio.sleep(1)  # Show completion briefly
        progress_bar.finish()
        return result
    
    except Exception as e:
        progress_bar.update(1.0, f"Error: {str(e)}")
        return None
