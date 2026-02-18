from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from typing import List, Dict, Any, Optional

class MembriaUI:
    """
    Manages the Claude-style premium terminal UI layout.
    """
    
    def __init__(self):
        self.active_tasks = []
        self.stats = {
            "files": {"changed": 0, "added": 0, "removed": 0},
            "context": 0,
            "tasks": {"done": 0, "in_progress": 0, "open": 0},
            "tokens": 0,
            "context_percent": 99
        }
        self.last_log_messages = []

    def update_stats(self, **kwargs):
        """Update UI statistics."""
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value

    def add_task(self, name: str, status: str = "in_progress"):
        """Add a task to the live list."""
        self.active_tasks.append({"name": name, "status": status})
        self._recalculate_tasks()

    def set_task_status(self, name: str, status: str):
        """Update status of a specific task."""
        for task in self.active_tasks:
            if task["name"] == name:
                task["status"] = status
                break
        self._recalculate_tasks()

    def _recalculate_tasks(self):
        """Sync internal stats with task list."""
        self.stats["tasks"] = {
            "done": len([t for t in self.active_tasks if t["status"] == "done"]),
            "in_progress": len([t for t in self.active_tasks if t["status"] == "in_progress"]),
            "open": len([t for t in self.active_tasks if t["status"] == "open"])
        }

    def generate_layout(self) -> Layout:
        """Construct the Rich layout for the live display."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=None),
            Layout(name="main", size=None),
            Layout(name="footer", size=1)
        )
        
        # 1. Header: Task List
        task_table = Table.grid(expand=True)
        task_table.add_column(ratio=1)
        
        t_stats = self.stats["tasks"]
        header_text = f"[bold white]{t_stats['done']} tasks[/bold white] [dim]({t_stats['done']} done, {t_stats['in_progress']} in progress, {t_stats['open']} open)[/dim]"
        task_table.add_row(header_text)
        
        for task in self.active_tasks:
            icon = " [green]✔[/green] " if task["status"] == "done" else " [red]■[/red] "
            style = "bold white" if task["status"] == "in_progress" else "dim"
            task_table.add_row(f"{icon} [{style}]{task['name']}[/{style}]")
        
        layout["header"].update(task_table)
        
        # 2. Main: Spacer (REPL output goes here naturally, or we can use it for live agent logs)
        layout["main"].update("")
        
        # 3. Footer: Status Bar
        f_stats = self.stats["files"]
        status_line = Text.assemble(
            (f"{self.stats['context']} files", "cyan"),
            (" +", "green"), (str(f_stats['added']), "green"),
            (" -", "red"), (str(f_stats['removed']), "red"),
            (" · ", "dim"),
            ("ctrl+t to hide tasks", "dim"),
            (" " * 50), # Spacer
            ("Context left until auto-compact: 99%", "dim")
        )
        layout["footer"].update(status_line)
        
        return layout

    def get_header(self) -> Optional[RenderableType]:
        """Get just the task tracking header if tasks are active."""
        if not self.active_tasks:
            return None
            
        t_stats = self.stats["tasks"]
        grid = Table.grid(expand=True)
        # Match screenshot format exactly
        grid.add_row(f"[dim]{len(self.active_tasks)} tasks ({t_stats['done']} done, {t_stats['in_progress']} in progress, 0 open)[/dim]")
        
        # Only show the last 3 tasks to keep it compact
        for task in self.active_tasks[-3:]:
            if task["status"] == "in_progress":
                icon = "[#ff79c6]■[/#ff79c6]"  # Pinkish square
                style = "bold white"
            elif task["status"] == "done":
                icon = "[green]✔[/green]"
                style = "dim"
            else:
                icon = "[dim]○[/dim]"
                style = "dim"
            grid.add_row(f" {icon} [{style}]{task['name']}[/{style}]")
        
        return grid

    def get_footer(self) -> list:
        """Get the footer status bar as list of (style, text) tuples for bottom_toolbar."""
        import shutil
        f_stats = self.stats["files"]
        cols = shutil.get_terminal_size().columns
        
        # Build left side
        left_parts = [
            ('dim', f" {self.stats['context']} files "),
            ('green', f"+{f_stats['added']}"),
            ('dim', " "),
            ('red', f"-{f_stats['removed']}"),
            ('dim', " · ctrl+t to hide tasks"),
        ]
        
        # Calculate left text length  
        left_text_len = sum(len(text) for _, text in left_parts)
        
        # Right side
        right_text = f"Context: {self.stats.get('context_percent', 99)}% "
        right_parts = [('dim', right_text)]
        
        # Calculate padding
        padding_len = max(1, cols - left_text_len - len(right_text))
        
        # Combine all
        result = left_parts + [('', ' ' * padding_len)] + right_parts
        
        return result
