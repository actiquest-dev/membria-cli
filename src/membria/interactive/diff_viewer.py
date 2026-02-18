"""
Diff viewer for displaying and navigating file changes.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button
from rich.syntax import Syntax
from rich.text import Text
from typing import List, Optional


class DiffLine:
    """Represents a single line in a diff."""
    
    def __init__(self, line_type: str, content: str, line_num: Optional[int] = None):
        """
        Args:
            line_type: '+' (added), '-' (removed), '=' (context), '!' (changed)
            content: The line content
            line_num: Optional line number
        """
        self.line_type = line_type
        self.content = content
        self.line_num = line_num
    
    def render(self) -> Text:
        """Render the line with appropriate styling."""
        if self.line_type == '+':
            return Text(f"[#21C93A]+ {self.content}[/#21C93A]")
        elif self.line_type == '-':
            return Text(f"[red]- {self.content}[/red]")
        elif self.line_type == '!':
            return Text(f"[#FFB84D]~ {self.content}[/#FFB84D]")
        else:
            return Text(f"  {self.content}")


class DiffViewer(Static):
    """Interactive diff viewer for file changes."""
    
    def __init__(self, file_path: str, diff_lines: List[DiffLine], **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.diff_lines = diff_lines
        self.current_index = 0
    
    def render(self) -> Text:
        """Render the diff view."""
        output = Text()
        
        # Header
        output.append(Text(f"[#5AA5FF]File: {self.file_path}[/#5AA5FF]\n", style="bold"))
        output.append(Text(f"[#FFB84D]{len(self.diff_lines)} lines changed[/#FFB84D]\n\n"))
        
        # Show lines with context
        start_idx = max(0, self.current_index - 5)
        end_idx = min(len(self.diff_lines), self.current_index + 10)
        
        for i in range(start_idx, end_idx):
            line = self.diff_lines[i]
            if i == self.current_index:
                output.append(Text(f"▶ {line.render()}\n"))
            else:
                output.append(Text(f"  {line.render()}\n"))
        
        return output
    
    def scroll_next(self):
        """Move to next change."""
        if self.current_index < len(self.diff_lines) - 1:
            self.current_index += 1
            self.refresh()
    
    def scroll_prev(self):
        """Move to previous change."""
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh()


class DiffPanel(Container):
    """Panel for displaying multiple file diffs with navigation."""
    
    def __init__(self, diffs: dict, **kwargs):
        """
        Args:
            diffs: Dict of {file_path: List[DiffLine]}
        """
        super().__init__(**kwargs)
        self.diffs = diffs
        self.current_file_idx = 0
        self.file_paths = list(diffs.keys())
        self.diff_viewer = None
    
    def compose(self) -> ComposeResult:
        """Compose the diff panel."""
        if not self.file_paths:
            yield Static(Text("[yellow]No changes to display[/yellow]"))
            return
        
        # Diff viewer
        self.diff_viewer = DiffViewer(
            self.file_paths[0],
            self.diffs[self.file_paths[0]],
            expand=True
        )
        yield self.diff_viewer
        
        # Controls
        with Horizontal(id="diff-controls"):
            yield Button("← Previous File", id="prev-file")
            yield Static(
                f" {self.current_file_idx + 1}/{len(self.file_paths)} ",
                id="diff-counter"
            )
            yield Button("Next File →", id="next-file")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "next-file":
            self.next_file()
        elif event.button.id == "prev-file":
            self.prev_file()
    
    def next_file(self):
        """Navigate to next file."""
        if self.current_file_idx < len(self.file_paths) - 1:
            self.current_file_idx += 1
            self._update_view()
    
    def prev_file(self):
        """Navigate to previous file."""
        if self.current_file_idx > 0:
            self.current_file_idx -= 1
            self._update_view()
    
    def _update_view(self):
        """Update the diff viewer to show current file."""
        file_path = self.file_paths[self.current_file_idx]
        self.diff_viewer.file_path = file_path
        self.diff_viewer.diff_lines = self.diffs[file_path]
        self.diff_viewer.current_index = 0
        self.diff_viewer.refresh()
