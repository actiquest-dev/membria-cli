# Onboarding Screens Integration Guide

## Overview

The Textual-based onboarding system provides an interactive first-run experience for Membria users. When users launch the app for the first time, they're guided through 8 mandatory setup steps using Textual screens (modal dialogs).

## Architecture

### File Structure

```
src/membria/interactive/
├── onboarding_screens.py          # NEW: 8 Textual screen classes
├── textual_shell.py               # UPDATED: Integrates onboarding flow
├── commands.py                    # Command handlers (/theme, /monitor, /settings)
├── menus.py                       # Interactive menu widgets
└── onboarding_enhanced.py         # Text-based fallback wizard
```

### Key Classes

#### `OnboardingScreen` (Base Class)
Base class for all onboarding screens. Provides:
- Progress tracking (current_step / total_steps)
- Navigation handlers (Back, Skip, Next buttons)
- State persistence via `save_step_state()` method
- Keyboard shortcuts (Escape to exit)

**CSS Layout:**
```css
┌────────────────────────────────────┐
│           TITLE BAR                │
│      Progress: Step 2/8            │
├────────────────────────────────────┤
│                                    │
│         CONTENT AREA               │
│    (Labels, Input fields,          │
│     RadioButtons, etc)             │
│                                    │
├────────────────────────────────────┤
│  [Back]  [Skip]                [Next]  │
└────────────────────────────────────┘
```

#### 8 Screen Classes

| Screen | Purpose | Config Keys |
|--------|---------|-------------|
| `WelcomeScreen` | Concept explanation | N/A |
| `ProviderSetupScreen` | API key authentication | `providers.{name}.api_key` |
| `RoleAssignmentScreen` | Expert role selection | `interactive.role_preset` |
| `GraphDatabaseScreen` | FalkorDB backend choice | `falkordb.mode` |
| `MonitoringLevelScreen` | Logging verbosity | `monitoring.level` |
| `ThemeSelectionScreen` | Color theme selection | `display.theme` |
| `FirstDecisionScreen` | Tutorial decision capture | `first_decision` |
| `SummaryScreen` | Setup completion summary | N/A |

#### `OnboardingFlow` (State Manager)
Orchestrates the 8-step flow:

```python
flow = OnboardingFlow(app, config_manager)
flow.start()              # Show step 1
flow.next_screen()        # Advance to next step
flow.prev_screen()        # Go back
flow.mark_complete()      # Mark onboarding done
```

## Integration Points

### 1. App Startup (textual_shell.py)

When `MembriaApp.on_mount()` runs:

```python
async def on_mount(self) -> None:
    # Check if first run
    if self.config_manager.is_first_run():
        from .onboarding_screens import OnboardingFlow
        
        # Create and start onboarding flow
        flow = OnboardingFlow(self, self.config_manager)
        flow.start()  # Pushes WelcomeScreen
        
        # Wait for onboarding to complete
        await self._wait_for_onboarding()
    
    # Then show welcome message
    self.messages_area.add_message("Welcome to Membria...")
```

### 2. First Run Detection

The `ConfigManager.is_first_run()` method checks:

```python
def is_first_run(self) -> bool:
    """True if no providers configured yet."""
    return not self.config.providers
```

### 3. State Persistence

Each screen's `save_step_state()` method persists data:

```python
class ProviderSetupScreen(OnboardingScreen):
    def save_step_state(self) -> None:
        provider = self.query_one("#provider-select").pressed_button.value
        api_key = self.query_one("#api-key-input").value
        
        # Save to ~/.membria/config.toml
        self.config_manager.set(f"providers.{provider}.api_key", api_key)
        self.config_manager.save()
```

### 4. Screen Navigation

Button handlers in `OnboardingScreen.on_button_pressed()`:

```
[Back]  → flow.prev_screen()       # Go to previous step
[Skip]  → flow.mark_complete()     # Skip remaining steps
[Next]  → save_step_state() + flow.next_screen()
```

Special case: `FirstDecisionScreen` has `[Finish]` button.

## Configuration Storage

### Config File Structure

After onboarding, `~/.membria/config.toml` contains:

```toml
[providers.anthropic]
type = "anthropic"
api_key = "sk-ant-..."
enabled = true

[providers.openai]
type = "openai"
api_key = "sk-org-..."
enabled = true

[display]
theme = "nord"

[monitoring]
level = "L1"

[interactive]
role_preset = "full"

[falkordb]
mode = "docker"

[onboarding]
completed = true

[first_decision]
statement = "Use JWT for authentication"
confidence = 85
domain = "security"
```

## User Flow Diagram

```
START (is_first_run = True)
  ↓
[1. Welcome Screen] ← User learns about Membria
  ↓ [Next]
[2. Provider Setup] ← Enter API keys
  ↓ [Next]
[3. Role Assignment] ← Choose expert council
  ↓ [Next]
[4. Graph Database] ← FalkorDB configuration
  ↓ [Next]
[5. Monitoring Level] ← Set verbosity
  ↓ [Next]
[6. Theme Selection] ← Pick colors
  ↓ [Next]
[7. First Decision] ← Capture tutorial decision
  ↓ [Finish]
[8. Summary Screen] ← Show what was configured
  ↓ [Start!]
Main App Interface
  (with welcome message)
```

## Extending the Onboarding Flow

### Adding a New Screen

1. Create a new class inheriting from `OnboardingScreen`:

```python
class DatabaseSchemaScreen(OnboardingScreen):
    """Configure database schema."""
    
    def on_mount(self) -> None:
        title = self.query_one("#title", Label)
        title.update("[bold cyan]Database Schema[/bold cyan]")
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("[bold cyan]Database Schema[/bold cyan]", id="title")
            yield Label(f"Step {self.step}/{self.total_steps}", id="progress")
            
            with Vertical(classes="content"):
                yield Label("Connect to your database:")
                yield Input(id="db-host", placeholder="localhost")
                yield Input(id="db-port", placeholder="5432")
                yield Input(id="db-name", placeholder="membria")
            
            with Horizontal(classes="actions"):
                yield Button("Back", id="btn-back")
                yield Button("Skip", id="btn-skip")
                yield Button("Next", id="btn-next", variant="primary")
    
    def save_step_state(self) -> None:
        """Persist database config."""
        host = self.query_one("#db-host", Input).value
        port = self.query_one("#db-port", Input).value
        
        self.config_manager.set("database", {
            "host": host,
            "port": int(port) if port else 5432,
        })
        self.config_manager.save()
```

2. Register in `OnboardingFlow.screens`:

```python
class OnboardingFlow:
    def __init__(self, app, config_manager):
        self.screens = [
            WelcomeScreen,
            ProviderSetupScreen,
            RoleAssignmentScreen,
            GraphDatabaseScreen,
            MonitoringLevelScreen,
            ThemeSelectionScreen,
            DatabaseSchemaScreen,      # NEW
            FirstDecisionScreen,
            SummaryScreen,
        ]
```

### Customizing Screen Appearance

Use Textual CSS in `DEFAULT_CSS`:

```python
class CustomScreen(OnboardingScreen):
    DEFAULT_CSS = """
    CustomScreen Container {
        width: 100;        # Wider screen
        border: double;    # Double border
    }
    
    CustomScreen Input {
        margin: 1 1;       # More spacing
    }
    """
```

## Testing the Onboarding Flow

### Reset First-Run Flag

```python
import toml
from pathlib import Path

config_file = Path.home() / ".membria" / "config.toml"
with open(config_file) as f:
    config = toml.load(f)

# Remove all providers to trigger onboarding
config['providers'] = {}

with open(config_file, 'w') as f:
    toml.dump(config, f)

# Next app launch will show onboarding
```

### Test Navigation

1. **Forward flow**: Click Next on each screen (saves config at each step)
2. **Backward flow**: Click Back to return to previous screens
3. **Skip flow**: Click Skip to jump to Summary
4. **Exit flow**: Press Escape to quit setup (config partial)

### Verify Config Save

After completing onboarding:

```bash
cat ~/.membria/config.toml
# Should show all configured values
```

## Migration from Text-Based Wizard

The old `OnboardingWizard` (text-based, in `onboarding_enhanced.py`) is still available as a fallback. The Textual version (`onboarding_screens.py`) is preferred.

### Key Differences

| Feature | Text-Based | Textual |
|---------|-----------|---------|
| UI | Rich Prompt/Input | Textual Screens |
| Navigation | Linear | Non-linear (Back button) |
| Visual Polish | Console text | Styled widgets |
| Integration | Standalone | App-native |
| Skip Support | Limited | Full (skip to Summary) |

## Troubleshooting

### Onboarding Not Triggering

Check `is_first_run()` logic:

```python
def is_first_run(self) -> bool:
    return not self.config.providers  # Empty dict = True
```

Force reset:
```bash
rm ~/.membria/config.toml
```

### Screens Not Saving State

Verify `save_step_state()` implementation:

```python
def save_step_state(self) -> None:
    try:
        widget = self.query_one("#widget-id", InputType)
        value = widget.value
        self.config_manager.set("config.key", value)
        self.config_manager.save()
    except Exception as e:
        print(f"Failed to save: {e}")
```

### Navigation Issues

Check `OnboardingFlow` screen stack:

```python
# In on_mount, after flow.start():
print(f"Screens: {len(self.app.screen_stack)}")  # Should be > 1
```

### CSS Layout Problems

Textual CSS is strict about dimensions. Ensure:
- Container width <= terminal width
- All widgets have sensible `width`/`height` (or `auto`)
- Use `layout: horizontal` or `layout: vertical` explicitly

## Best Practices

1. **Always implement `save_step_state()`** to persist user input
2. **Handle exceptions gracefully** in state saving (don't crash)
3. **Provide meaningful placeholders** in Input fields
4. **Use consistent color markup** (#5AA5FF, #FFB84D, #21C93A, #E8E8E8)
5. **Keep screens under 80 characters wide** (terminal-friendly)
6. **Test with `config_manager.save()`** to verify TOML format

## API Reference

### OnboardingScreen

```python
class OnboardingScreen(Screen):
    # Properties
    step: int                         # Current step number
    total_steps: int                  # Total steps (8)
    config_manager: ConfigManager     # Config persistence
    flow: OnboardingFlow              # Parent flow manager
    
    # Methods
    def save_step_state(self) -> None:  # Override to save config
    def on_button_pressed(event) -> None:  # Handle buttons
```

### OnboardingFlow

```python
class OnboardingFlow:
    # Methods
    def start(self) -> None:          # Show first screen
    def show_screen(step: int) -> None:  # Jump to step
    def next_screen(self) -> None:    # Advance 1 step
    def prev_screen(self) -> None:    # Go back 1 step
    def mark_complete(self) -> None:  # Finish onboarding
```

### ConfigManager Integration

```python
config_manager.is_first_run() -> bool  # Check if new user
config_manager.set(key, value)         # Save config value
config_manager.save()                  # Write to config.toml
config_manager.get(key) -> Any         # Read config value
```

## Future Enhancements

1. **Validation**: Test API keys during ProviderSetupScreen
2. **Docker Check**: Verify Docker is installed for FalkorDB setup
3. **Progress Persistence**: Resume from last step if interrupted
4. **Skipped Step Indicator**: Show which steps were skipped
5. **Help Integration**: Link to /help from each screen
6. **Post-Onboarding Survey**: Satisfaction check after completion

## Files Modified/Created

- ✅ **NEW**: `src/membria/interactive/onboarding_screens.py` (600+ lines)
- ✅ **UPDATED**: `src/membria/interactive/textual_shell.py` (on_mount method)
- ✅ **UNCHANGED**: `src/membria/config.py` (already has is_first_run)
- ✅ **REFERENCE**: `src/membria/interactive/onboarding_enhanced.py` (text-based backup)

## Summary

The Textual-based onboarding system provides:
- ✅ Native integration with Textual app
- ✅ Interactive screens with state persistence
- ✅ Easy extensibility (add new screens)
- ✅ Robust config storage (TOML format)
- ✅ Complete user onboarding experience
- ✅ Accessible navigation (Back/Skip buttons)
