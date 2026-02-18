## Membria CLI Interactive Menus

**Complete navigation & configuration system built with Textual **

---

## 📺 Menu Architecture

```
Membria CLI (Textual App)
├── Command Dispatcher (/commands.py)
│   ├── /theme          → ThemeMenu widget
│   ├── /settings       → SettingsMenu widget
│   ├── /monitor        → MonitorMenu widget
│   └── /settings providers → ProviderManagerMenu
│
├── Interactive Widgets (menus.py)
│   ├── ThemeMenu       - Select from 8 color themes with preview
│   ├── SettingsMenu    - Main config hub (providers, roles, display)
│   ├── MonitorMenu     - Set logging level (L0-L3) 
│   └── ProviderManagerMenu - Add/remove/configure LLM providers
│
└── Message-driven updates
    ├── ThemeSelected(theme_name)
    ├── SettingChanged(setting, value)
    ├── MonitorLevelChanged(level)
    └── ProviderAction(action, provider)
```

---

## 🎨 Theme Menu (`/theme`)

**Interactive theme selector with live color preview**

### Usage
```bash
/theme              # Show all available themes
/theme <name>       # Set theme immediately
```

### Available Themes

| Theme | Style | Colors |
|-------|-------|--------|
| **nord** | Arctic | Cool blues + greens |
| **gruvbox** | Retro groove | Warm oranges + reds |
| **tokyo-night** | Cyberpunk | Purple + cyan neon |
| **solarized-light** | Classic light | High contrast |
| **solarized-dark** | Classic dark | High contrast |
| **dracula** | Vampire | Pink + purple |
| **one-dark** | Atom-like | Warm palette |
| **monokai** | High contrast | Bold colors |

### Features

✅ **Live Preview** - Color swatches update as you browse  
✅ **Grid Layout** - 2×4 button grid (Textual Grid)  
✅ **Keyboard Navigation** - Tab through themes, Enter to select  
✅ **Persistent** - Setting saved to config  
✅ **CSS Integrated** - Uses `$primary`, `$secondary`, `$accent` variables  

### Implementation (ThemeMenu)

```python
# Theme selector using Grid layout with 8 buttons
class ThemeMenu(Static):
    THEMES = {
        "nord": {"colors": [...], "description": "..."},
        # ... 7 more themes
    }
    
    # Reactive state for current theme
    current_theme = reactive("nord")
    
    # Messages when user selects
    class ThemeSelected(Message):
        def __init__(self, theme_name: str): ...
    
    # Grid layout: 2 columns × 4 rows
    def compose(self) -> ComposeResult:
        with Grid(id="theme-grid"):  # grid-size: 2 4
            for theme_name in self.THEMES:
                yield Button(...)  # .theme-button class
        
        # Color swatches in Horizontal container
        with Horizontal(id="color-preview"):
            for color in current_colors:
                color_box = Static("")
                color_box.styles.background = color
```

---

## ⚙️ Settings Menu (`/settings`)

**Central hub for all configuration**

### Main Menu
```bash
/settings                      # Show settings menu
```

### Sub-commands

#### 📦 Provider Management
```bash
/settings providers                    # List all providers
/settings toggle <name>                # Enable/disable
/settings set-key <name> <api_key>     # Set API key
/settings set-model <name> <model>     # Change default model
/settings test-provider <name>         # Test connection
/settings add-provider <n> <t> <m>     # Add new provider
/settings remove <name>                # Delete provider
```

#### 👥 Roles & Agents
```bash
/settings roles                        # List available roles
/settings assign-role <role> <prov>    # Assign role to provider
/settings calibrate <role> <acc>       # Set accuracy (0-1)
```

### Features

✅ **Provider Config** - Add/remove/toggle LLM providers  
✅ **Model Selection** - Choose from available models per provider  
✅ **API Key Management** - Secure credential storage  
✅ **Role Assignment** - Bind experts to specific providers  
✅ **Calibration** - Set expected accuracy for each role  

### Implementation (SettingsMenu)

```python
class SettingsMenu(Static):
    # Custom message for changes
    class SettingChanged(Message):
        def __init__(self, setting_name: str, value: str): ...
    
    def compose(self) -> ComposeResult:
        with Vertical():
            # 📦 Provider section
            yield Label("[yellow]Providers[/yellow]")
            with Vertical(classes="setting-group"):
                yield Button("➕ Add Provider", id="btn-add-provider")
                yield Button("⚙️  Manage Providers", id="btn-manage-providers")
            
            # 👥 Roles section
            yield Label("[yellow]Roles & Agents[/yellow]")
            with Vertical(classes="setting-group"):
                yield Button("👥 Assign Roles", id="btn-assign-roles")
                yield Button("📊 View Calibration", id="btn-view-calibration")
            
            # Display settings
            yield Label("[yellow]Display[/yellow]")
            # ... theme, monitor level buttons ...
```

---

## 📊 Monitor Menu (`/monitor`)

**Set logging & debug output level**

### Usage
```bash
/monitor              # Show available levels
/monitor <L0|L1|L2|L3>  # Set level
```

### Levels

| Level | Name | Logs | Use When |
|-------|------|------|----------|
| **L0** | Silent | Nothing | Production mode |
| **L1** | Decisions | Decisions + outcomes | Default, normal use |
| **L2** | Reasoning | L1 + agent traces | Debugging logic |
| **L3** | Debug | L2 + all tool calls | Deep troubleshooting |

### Features

✅ **Visual Level Selector** - Buttons with descriptions  
✅ **Toggle Display** - Show current selection with checkmark  
✅ **Configurable Verbosity** - Control output noise  
✅ **State Persistence** - Saved to config  

### Implementation (MonitorMenu)

```python
class MonitorMenu(Static):
    LEVELS = {
        "L0": {"name": "Silent", "description": "...", "shows": []},
        "L1": {"name": "Decisions", "shows": ["decision_made", ...]},
        "L2": {"name": "Reasoning", "shows": [...]},
        "L3": {"name": "Debug", "shows": [...]},
    }
    
    current_level = reactive("L1")
    
    # Message when level changes
    class MonitorLevelChanged(Message):
        def __init__(self, level: str): ...
```

---

## 🏢 Provider Manager (`/settings providers`)

**Detailed provider configuration interface**

### Features

✅ **Visual Status** - Green ✓ for enabled, red ✗ for disabled  
✅ **Quick Actions** - Toggle/Key/Remove buttons per provider  
✅ **Type Display** - Shows provider type (anthropic/openai/etc)  
✅ **Key Status** - ✓ if configured, ⚠ if missing  

### Implementation (ProviderManagerMenu)

```python
class ProviderManagerMenu(Static):
    # Message when action taken
    class ProviderAction(Message):
        def __init__(self, action: str, provider_name: str = None):
            # action: "add", "remove", "toggle", "set_key", "set_model"
    
    def compose(self) -> ComposeResult:
        with Vertical():
            for prov_name, prov_config in self.providers_config.items():
                # Show status box for each provider
                with Vertical(classes="provider-item"):
                    # Status line (enabled/disabled)
                    yield Label(f"[status] {prov_name} ({type})")
                    
                    # Actions (toggles, key, remove)
                    with Horizontal():
                        yield Button("Toggle", id=f"btn-toggle-{prov_name}")
                        yield Button("Key", id=f"btn-key-{prov_name}")
                        yield Button("Remove", id=f"btn-remove-{prov_name}")
```

---

## 🔌 Integration with App

### Command Handler Flow

```
User Input: "/theme nord"
    ↓
CommandHandler.handle_command()
    ↓
_handle_theme("nord")
    ↓
Update config.display.theme = "nord"
    ↓
Return formatted success message
    ↓
Display in messages_area
```

### Message-Driven Updates

When menus are embedded as Textual widgets (not just CLI):

```python
# In app compose():
yield ThemeMenu(id="theme-selector")

# ThemeMenu posts messages:
def on_button_pressed(self, event):
    self.post_message(ThemeSelected(theme_name))

# App listens:
def on_theme_menu_theme_selected(self, message: ThemeMenu.ThemeSelected):
    theme_name = message.theme_name
    self.app.theme = theme_name
    # Update color scheme live
```

---

## 🎛️ CSS Structure

### Theme Variables (textual_shell.py)
```tcss
/* Light palette */
$primary:    #5AA5FF    /* Bright blue */
$secondary:  #FFB84D    /* Orange */
$accent:     #21C93A    /* Green */
$surface:    #1a1a1a    /* Dark bg */
$error:      #FF6B6B    /* Red */
$success:    #51CF66    /* Green */
```

### Menu Button Styles
```tcss
Button {
    margin: 0 1;
    width: 100%;
}

Button:focus {
    background: $accent 20%;
    border: solid $accent;
}

Button.toggle-button.enabled {
    background: $success 30%;
}

Button.toggle-button.disabled {
    background: $error 30%;
}
```

---

## 🚀 Usage Examples

### Change Theme
```bash
> /theme
[shows all 8 theme options]

> /theme tokyo-night
✓ Theme set to: tokyo-night (Cyberpunk vibes)
```

### Configure Provider
```bash
> /settings providers
Configured Providers:

✓ anthropic
   Type: anthropic | Model: claude-3-5-sonnet | Auth: ✓ Configured

✗ openai
   Type: openai | Model: gpt-4-turbo | Auth: ⚠ Missing API key

> /settings set-key openai sk-xxx...
✓ API key configured for openai

> /settings test-provider openai
Testing provider: openai
  Status: ENABLED
  Type: openai
  Model: gpt-4-turbo
  Auth: ✓ Configured
✓ Provider configuration valid
```

### Set Monitoring
```bash
> /monitor
Monitoring Level:

  ✓ L0: Silent - No logging
   L1: Decisions - Show decisions + outcomes (default)
   L2: Reasoning - L1 + agent reasoning traces
   L3: Debug - L2 + all tool calls & graph queries

> /monitor L2
✓ Monitoring set to: L2 - Reasoning - L1 + agent reasoning traces
```

---

## 📋 Command Reference

| Command | Function | Menu Widget |
|---------|----------|-------------|
| `/theme` | Select color theme | ThemeMenu |
| `/settings` | Main config hub | SettingsMenu |
| `/settings providers` | Manage providers | ProviderManagerMenu |
| `/monitor` | Set log level | MonitorMenu |
| `/mode` | Orchestration mode | Text-based |
| `/agents` | Show calibration | Text-based |

---

## 🔄 State Management

### Reactive Properties
- `ThemeMenu.current_theme` - Updates color preview
- `MonitorMenu.current_level` - Updates button highlights
- `SettingsMenu` - Posts messages for state changes

### Persistence
All settings saved to `~/.membria/config.json`:
```json
{
  "display": {
    "theme": "tokyo-night"
  },
  "monitoring": {
    "level": "L2"
  },
  "orchestration": {
    "mode": "pipeline"
  },
  "providers": {
    "anthropic": {
      "enabled": true,
      "model": "claude-3-5-sonnet",
      "api_key": "sk-..."
    }
  }
}
```

---

## 🧪 Testing

### Commands to test
```bash
pytest tests/test_menus.py

# Manual testing in shell:
/theme                    # Browse themes
/theme gruvbox           # Set theme
/settings                # Show menu
/settings providers      # List providers
/monitor L3              # Set debug level
```

---

## 🔮 Future Enhancements

1. **Interactive Input** - Inline Input widgets for API keys
2. **Validation** - Real-time key validation
3. **Presets** - Save/load configuration profiles
4. **Dashboard Integration** - Visual analytics for decisions
5. **Hotkeys** - Quick theme/monitor switching (Ctrl+T, Ctrl+L)
