"""
Interactive menu widgets for Membria CLI.
Implements theme selection, settings, and monitoring configuration.
"""

from typing import List, Callable, Optional
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.widgets import Static, Button, Label, Input
from textual.containers import Grid, Vertical, Horizontal
from textual.reactive import reactive
from textual.message import Message


class MenuBase(Static):
    """Base class for all interactive menus with keyboard navigation."""
    
    DEFAULT_CSS = """
    MenuBase {
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }
    
    MenuBase > Vertical {
        height: auto;
    }
    
    MenuBase Button {
        margin: 0 1;
    }
    
    MenuBase Button:focus {
        background: $accent 20%;
    }
    """
    
    selected_index = reactive(0)
    
    def __init__(self, title: str = "", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.menu_items: List[tuple] = []  # (label, value, callback)
    
    def add_item(self, label: str, value: str, callback: Optional[Callable] = None):
        """Add a menu item."""
        self.menu_items.append((label, value, callback))


class ThemeMenu(Static):
    """Interactive theme selector with color preview."""
    
    class ThemeSelected(Message):
        """Posted when theme is selected."""
        def __init__(self, theme_name: str):
            self.theme_name = theme_name
            super().__init__()
    
    DEFAULT_CSS = """
    ThemeMenu {
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    
    ThemeMenu > Vertical {
        height: auto;
    }
    
    ThemeMenu #theme-title {
        width: 100%;
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    ThemeMenu #theme-grid {
        width: 100%;
        height: auto;
        grid-size: 2 4;
        grid-gutter: 1 2;
    }
    
    ThemeMenu .theme-button {
        width: 100%;
        height: 5;
    }
    
    ThemeMenu .theme-button:focus {
        background: $accent 30%;
        border: solid $accent;
    }
    
    ThemeMenu #color-preview {
        width: 100%;
        height: 3;
        margin-top: 1;
        border: solid $accent;
        padding: 1;
    }
    
    ThemeMenu .color-swatch {
        width: 10;
        height: 1;
        margin: 0 1;
    }
    """
    
    THEMES = {
        "nord": {
            "colors": ["#2E3440", "#88C0D0", "#81A1C1", "#A3BE8C"],
            "description": "Nord - Arctic palette"
        },
        "gruvbox": {
            "colors": ["#282828", "#FB4934", "#B8BB26", "#FABD2F"],
            "description": "Gruvbox - Retro groove"
        },
        "tokyo-night": {
            "colors": ["#1A1B26", "#0DB9D7", "#BB9AF7", "#7AA2F7"],
            "description": "Tokyo Night - Cyberpunk"
        },
        "solarized-light": {
            "colors": ["#FDF6E3", "#DC322F", "#859900", "#268BD2"],
            "description": "Solarized Light"
        },
        "solarized-dark": {
            "colors": ["#002B36", "#DC322F", "#859900", "#268BD2"],
            "description": "Solarized Dark"
        },
        "dracula": {
            "colors": ["#282A36", "#FF79C6", "#50FA7B", "#F1FA8C"],
            "description": "Dracula - Vampire theme"
        },
        "one-dark": {
            "colors": ["#282C34", "#E06C75", "#98C379", "#E5C07B"],
            "description": "One Dark - Atom inspired"
        },
        "monokai": {
            "colors": ["#272822", "#F92672", "#A6E22E", "#FD971F"],
            "description": "Monokai - High contrast"
        },
    }
    
    current_theme = reactive("nord")
    
    def compose(self) -> ComposeResult:
        """Build theme selector UI."""
        with Vertical():
            yield Label("[cyan]╭─ Theme Selector ─╮[/cyan]", id="theme-title")
            
            with Grid(id="theme-grid"):
                for theme_name, theme_info in self.THEMES.items():
                    btn = Button(
                        f"[{theme_name.upper()}]\n{theme_info['description']}",
                        id=f"btn-theme-{theme_name}",
                        classes="theme-button"
                    )
                    if theme_name == self.current_theme:
                        btn.styles.background = "$accent"
                    yield btn
            
            # Color preview
            yield Label("Color Palette:", id="theme-preview-label")
            with Horizontal(id="color-preview"):
                for color in self.THEMES[self.current_theme]["colors"]:
                    color_box = Static("", classes="color-swatch")
                    color_box.styles.background = color
                    yield color_box
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle theme button press."""
        button_id = event.button.id
        if button_id and button_id.startswith("btn-theme-"):
            theme_name = button_id.replace("btn-theme-", "")
            self.current_theme = theme_name
            self.post_message(self.ThemeSelected(theme_name))
            # Update UI
            self._refresh_colors()
    
    def _refresh_colors(self) -> None:
        """Refresh color preview display."""
        # Reset all buttons
        for button in self.query("Button.theme-button"):
            button.styles.background = "transparent"
        
        # Highlight current theme
        selected_btn = self.query_one(f"#btn-theme-{self.current_theme}", Button)
        selected_btn.styles.background = "$accent"
        
        # Update color swatches
        colors = self.THEMES[self.current_theme]["colors"]
        for idx, swatch in enumerate(self.query(".color-swatch")):
            if idx < len(colors):
                swatch.styles.background = colors[idx]


class SettingsMenu(Static):
    """Interactive settings configuration menu."""
    
    class SettingChanged(Message):
        """Posted when a setting is changed."""
        def __init__(self, setting_name: str, value: str):
            self.setting_name = setting_name
            self.value = value
            super().__init__()
    
    DEFAULT_CSS = """
    SettingsMenu {
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    
    SettingsMenu > Vertical {
        height: auto;
    }
    
    SettingsMenu #settings-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    SettingsMenu .setting-group {
        height: auto;
        margin-bottom: 1;
    }
    
    SettingsMenu .setting-label {
        color: $secondary;
        width: 30;
    }
    
    SettingsMenu .setting-value {
        color: $accent;
        width: 40;
    }
    
    SettingsMenu Button {
        margin: 0 1;
    }
    
    SettingsMenu .toggle-button {
        width: 12;
        margin: 0 1;
    }
    
    SettingsMenu .toggle-button.enabled {
        background: $success 30%;
    }
    
    SettingsMenu .toggle-button.disabled {
        background: $error 30%;
    }
    """
    
    def __init__(self, config_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.config_manager = config_manager
        self.providers = {}  # {name: {type, model, enabled, key}}
    
    def compose(self) -> ComposeResult:
        """Build settings menu UI."""
        with Vertical():
            yield Label("[cyan]╭─ Settings Menu ─╮[/cyan]", id="settings-title")
            
            # Provider Configuration Section
            yield Label("[yellow]Providers[/yellow]")
            with Vertical(classes="setting-group"):
                yield Button("➕ Add Provider", id="btn-add-provider")
                yield Button("⚙️  Manage Providers", id="btn-manage-providers")
            
            # Roles & Agents Section
            yield Label("[yellow]Roles & Agents[/yellow]")
            with Vertical(classes="setting-group"):
                yield Button("👥 Assign Roles", id="btn-assign-roles")
                yield Button("📊 View Calibration", id="btn-view-calibration")
            
            # Display Settings
            yield Label("[yellow]Display[/yellow]")
            with Horizontal(classes="setting-group"):
                yield Label("Color Theme:", classes="setting-label")
                yield Button("Change 🎨", id="btn-change-theme")
            
            with Horizontal(classes="setting-group"):
                yield Label("Monitor Level:", classes="setting-label")
                yield Button("L1", id="btn-monitor-l1", classes="toggle-button enabled")
                yield Button("L2", id="btn-monitor-l2", classes="toggle-button")
                yield Button("L3", id="btn-monitor-l3", classes="toggle-button")
            
            # Experimental
            yield Label("[yellow]Experimental[/yellow]")
            with Vertical(classes="setting-group"):
                yield Button("✨ Auto-Routing", id="btn-auto-routing", classes="toggle-button enabled")
                yield Button("🔍 RAG Context", id="btn-rag-context", classes="toggle-button enabled")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle settings button press."""
        button_id = event.button.id
        
        if button_id == "btn-add-provider":
            self.post_message(self.SettingChanged("action", "add_provider"))
        elif button_id == "btn-manage-providers":
            self.post_message(self.SettingChanged("action", "manage_providers"))
        elif button_id == "btn-assign-roles":
            self.post_message(self.SettingChanged("action", "assign_roles"))
        elif button_id == "btn-view-calibration":
            self.post_message(self.SettingChanged("action", "view_calibration"))
        elif button_id == "btn-change-theme":
            self.post_message(self.SettingChanged("action", "change_theme"))
        elif button_id and button_id.startswith("btn-monitor-"):
            level = button_id.replace("btn-monitor-", "").upper()
            self._set_monitor_level(level)
        elif button_id == "btn-auto-routing":
            self._toggle_feature("auto_routing", event.button)
        elif button_id == "btn-rag-context":
            self._toggle_feature("rag_context", event.button)
    
    def _set_monitor_level(self, level: str) -> None:
        """Set monitoring level (L1, L2, L3)."""
        buttons = self.query("Button[id*='btn-monitor']")
        for btn in buttons:
            btn.remove_class("enabled")
            btn.add_class("disabled")
        
        selected_btn = self.query_one(f"#btn-monitor-{level.lower()}")
        selected_btn.remove_class("disabled")
        selected_btn.add_class("enabled")
        
        self.post_message(self.SettingChanged("monitor_level", level))
    
    def _toggle_feature(self, feature: str, button: Button) -> None:
        """Toggle a feature on/off."""
        if button.has_class("enabled"):
            button.remove_class("enabled")
            button.add_class("disabled")
            enabled = False
        else:
            button.remove_class("disabled")
            button.add_class("enabled")
            enabled = True
        
        self.post_message(self.SettingChanged(feature, "on" if enabled else "off"))


class MonitorMenu(Static):
    """Monitoring level and debug settings."""
    
    class MonitorLevelChanged(Message):
        """Posted when monitor level changes."""
        def __init__(self, level: str):
            self.level = level
            super().__init__()
    
    DEFAULT_CSS = """
    MonitorMenu {
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    
    MonitorMenu > Vertical {
        height: auto;
    }
    
    MonitorMenu .monitor-option {
        height: auto;
        margin-bottom: 1;
        padding-left: 2;
    }
    
    MonitorMenu Button {
        margin: 0 1;
    }
    """
    
    LEVELS = {
        "L0": {
            "name": "Silent",
            "description": "No logging. Fire and forget.",
            "shows": []
        },
        "L1": {
            "name": "Decisions",
            "description": "Show decisions + outcomes",
            "shows": ["decision_made", "outcome_recorded"]
        },
        "L2": {
            "name": "Reasoning",
            "description": "L1 + agent reasoning traces",
            "shows": ["decision_made", "outcome_recorded", "reasoning_trace"]
        },
        "L3": {
            "name": "Debug",
            "description": "L2 + all tool calls & graph queries",
            "shows": ["decision_made", "outcome_recorded", "reasoning_trace", "tool_call", "graph_query"]
        },
    }
    
    current_level = reactive("L1")
    
    def compose(self) -> ComposeResult:
        """Build monitoring menu."""
        with Vertical():
            yield Label("[cyan]╭─ Monitoring Level ─╮[/cyan]")
            
            for level, info in self.LEVELS.items():
                with Vertical(classes="monitor-option"):
                    is_selected = level == self.current_level
                    mark = "[#21C93A]✓[/#21C93A]" if is_selected else " "
                    yield Button(
                        f"{mark} {level}: {info['name']}\n    {info['description']}",
                        id=f"btn-level-{level}",
                        classes="monitor-level-button"
                    )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle level selection."""
        button_id = event.button.id
        if button_id and button_id.startswith("btn-level-"):
            level = button_id.replace("btn-level-", "")
            self.current_level = level
            self.post_message(self.MonitorLevelChanged(level))
            self._update_display()
    
    def _update_display(self) -> None:
        """Update the display to show selected level."""
        buttons = self.query("Button.monitor-level-button")
        for btn in buttons:
            btn_level = btn.id.replace("btn-level-", "")
            if btn_level == self.current_level:
                # Get fresh button text with checkmark
                info = self.LEVELS[btn_level]
                btn.label = f"[#21C93A]✓[/#21C93A] {btn_level}: {info['name']}\n    {info['description']}"
                btn.styles.background = "$accent 20%"
            else:
                info = self.LEVELS[btn_level]
                btn.label = f"  {btn_level}: {info['name']}\n    {info['description']}"
                btn.styles.background = "transparent"


class ProviderManagerMenu(Static):
    """Interactive provider configuration menu."""
    
    class ProviderAction(Message):
        """Posted when provider action is taken."""
        def __init__(self, action: str, provider_name: str = None):
            self.action = action  # "add", "remove", "toggle", "set_key", "set_model"
            self.provider_name = provider_name
            super().__init__()
    
    DEFAULT_CSS = """
    ProviderManagerMenu {
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    
    ProviderManagerMenu > Vertical {
        height: auto;
    }
    
    ProviderManagerMenu #provider-title {
        color: $primary;
        text-style: bold;
        margin-bottom: 1;
    }
    
    ProviderManagerMenu .provider-item {
        height: auto;
        margin-bottom: 1;
        padding-left: 2;
        border-left: solid $secondary;
    }
    
    ProviderManagerMenu .provider-status-on {
        color: $success;
    }
    
    ProviderManagerMenu .provider-status-off {
        color: $error;
    }
    """
    
    def __init__(self, providers_config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.providers_config = providers_config or {}
    
    def compose(self) -> ComposeResult:
        """Build provider manager UI."""
        with Vertical():
            yield Label("[cyan]╭─ Provider Manager ─╮[/cyan]", id="provider-title")
            
            # List providers
            if self.providers_config:
                for prov_name, prov_config in self.providers_config.items():
                    enabled = prov_config.get("enabled", False)
                    status_color = "$success" if enabled else "$error"
                    status_text = "✓ ON" if enabled else "✗ OFF"
                    
                    with Vertical(classes="provider-item"):
                        yield Label(
                            f"[{status_color}]{status_text}[/{status_color}] {prov_name} ({prov_config.get('type', 'unknown')})"
                        )
                        with Horizontal():
                            yield Button(
                                "Toggle" if enabled else "Enable",
                                id=f"btn-toggle-{prov_name}",
                                classes="provider-button"
                            )
                            yield Button(
                                "Key", id=f"btn-key-{prov_name}",
                                classes="provider-button"
                            )
                            yield Button(
                                "Remove",
                                id=f"btn-remove-{prov_name}",
                                classes="provider-button"
                            )
            else:
                yield Label("[yellow]No providers configured[/yellow]")
            
            # Add new provider button
            yield Button("➕ Add Provider", id="btn-add-new-provider")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle provider button actions."""
        button_id = event.button.id
        
        if button_id == "btn-add-new-provider":
            self.post_message(self.ProviderAction("add"))
        elif button_id.startswith("btn-toggle-"):
            provider = button_id.replace("btn-toggle-", "")
            self.post_message(self.ProviderAction("toggle", provider))
        elif button_id.startswith("btn-key-"):
            provider = button_id.replace("btn-key-", "")
            self.post_message(self.ProviderAction("set_key", provider))
        elif button_id.startswith("btn-remove-"):
            provider = button_id.replace("btn-remove-", "")
            self.post_message(self.ProviderAction("remove", provider))
