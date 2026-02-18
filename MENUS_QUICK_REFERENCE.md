# 🎯 Membria CLI Menus - Quick Reference

## What Was Built

Interactive menu system with **4 Textual widgets** for configuration:

### 1️⃣ **Theme Selector** (`/theme`)
- 8 color themes with live preview
- Grid layout (2×4) with color swatches
- `ThemeMenu` widget with reactive state

**Usage:**
```
/theme              → Show all themes
/theme tokyo-night  → Set immediately
```

**Themes:** nord • gruvbox • tokyo-night • solarized-light • solarized-dark • dracula • one-dark • monokai

---

### 2️⃣ **Settings Hub** (`/settings`)
- Main configuration menu
- 7 sub-commands for providers, roles, calibration
- `SettingsMenu` widget

**Usage:**
```
/settings                           → Show menu
/settings providers                 → List providers  
/settings toggle <name>             → Enable/disable
/settings set-key <name> <key>      → Set API key
/settings assign-role <role> <prov> → Bind provider
```

**Features:**
- ✅ Add/remove LLM providers
- ✅ Manage API keys  
- ✅ Assign experts to providers
- ✅ Set calibration scores

---

### 3️⃣ **Monitor Level** (`/monitor`)
- Control logging verbosity (L0-L3)
- `MonitorMenu` widget with 4 button options

**Usage:**
```
/monitor     → Show levels
/monitor L2  → Set to Reasoning
```

**Levels:**
- **L0:** Silent (production)
- **L1:** Decisions (default - shows decisions + outcomes)
- **L2:** Reasoning (+ agent traces)
- **L3:** Debug (+ tool calls & graph queries)

---

### 4️⃣ **Provider Manager** (`/settings providers`)
- Add/remove/configure LLM providers
- `ProviderManagerMenu` widget

**Features:**
- ✅ Visual status (✓ enabled, ✗ disabled)
- ✅ Quick actions (Toggle/Key/Remove buttons)
- ✅ Type display (anthropic, openai, etc)
- ✅ Key status indicators

---

## 📊 File Changes

### ✏️ NEW FILES
```
src/membria/interactive/menus.py          (600 lines)  4 widgets
UI_MENUS.md                               (350 lines)  Full docs
MENUS_IMPLEMENTATION.md                   (400 lines)  Dev guide
```

### 🔄 UPDATED FILES  
```
src/membria/interactive/commands.py
├── _handle_theme()     ← IMPLEMENTED (was stub)
├── _handle_monitor()   ← IMPLEMENTED (was missing)
├── _handle_settings()  ← ENHANCED (added helpers)
├── _show_settings_menu()
├── _list_providers()
├── _list_roles()
└── /help text updated with new commands
```

---

## 🏗️ Architecture

```
CLI Input: "/theme"
    ↓
CommandHandler.handle_command()
    ↓
_handle_theme(args)
    ↓
Return: "Available Themes:\n nord (Arctic)\n gruvbox (Retro)..."
    ↓
Display in messages_area
```

**OR (embedded in Textual app):**

```
yield ThemeMenu()
    ↓
User clicks theme button
    ↓
ThemeMenu.on_button_pressed()
    ↓
post_message(ThemeSelected("gruvbox"))
    ↓
App listens: on_theme_menu_theme_selected()
    ↓
Update theme live
```

---

## 🎨 Rich Markup Formatting

All menus use Membria color scheme:
- `[#5AA5FF]` → Bright blue (primary)
- `[#FFB84D]` → Orange (secondary)
- `[#21C93A]` → Green (accent)
- `[#E8E8E8]` → Light gray (text)

Example output:
```
[#5AA5FF]╭─ Theme Selector ─╮[/#5AA5FF]

[#FFB84D]Available Themes:[/#FFB84D]

  [#5AA5FF]✓[/#5AA5FF] nord: Arctic palette
  [#5AA5FF] [/#5AA5FF] gruvbox: Retro groove
  [#5AA5FF] [/#5AA5FF] tokyo-night: Cyberpunk vibes
```

---

## 🧪 Test Commands

```bash
# Theme menu
/theme
/theme nord
/theme tokyo-night

# Settings menu
/settings
/settings providers
/settings toggle anthropic
/settings set-key anthropic sk-ant-xxx
/settings roles
/settings assign-role Architect anthropic

# Monitor levels
/monitor
/monitor L0
/monitor L1
/monitor L2
/monitor L3

# Full help
/help
```

---

## 💾 Configuration Storage

All settings saved to: `~/.membria/config.json`

```json
{
  "display": {
    "theme": "tokyo-night"
  },
  "monitoring": {
    "level": "L2"
  },
  "providers": {
    "anthropic": {
      "enabled": true,
      "model": "claude-3-5-sonnet",
      "api_key": "sk-ant-..."
    },
    "openai": {
      "enabled": false,
      "model": "gpt-4-turbo",
      "api_key": ""
    }
  }
}
```

---

## 🔌 Integration Ready

### For Textual App Embedding
```python
from membria.interactive.menus import ThemeMenu, SettingsMenu, MonitorMenu

class MembriaApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        
        # Embed theme selector
        yield ThemeMenu(id="theme-menu")
        
        # Embed settings
        yield SettingsMenu(config_manager=self.config_manager)
        
        # Embed monitor
        yield MonitorMenu(id="monitor-menu")
        
        yield Footer()
    
    def on_theme_menu_theme_selected(self, message: ThemeMenu.ThemeSelected):
        """Update app theme when user selects from menu"""
        self.app.theme = message.theme_name
        # Live theme switching! ✨
```

### For CLI Commands (Already Working)
```python
# In CommandHandler:
result = await self._handle_theme(["tokyo-night"])
# → "[#21C93A]✓ Theme set to: tokyo-night[/#21C93A]"

self.messages_area.add_message(result)
```

---

## 🎯 Complete Command List

### Theme
```
/theme              Show available themes
/theme <name>       Set theme immediately
```

### Settings
```
/settings                               Main menu
/settings providers                     List providers
/settings toggle <name>                 Enable/disable
/settings set-key <name> <key>         Set API key
/settings set-model <name> <model>     Change model
/settings test-provider <name>         Test connection
/settings add-provider <n> <t> <m>     Add provider
/settings remove <name>                Delete provider
/settings roles                        List roles
/settings assign-role <r> <p>         Bind role
/settings calibrate <r> <acc>         Set accuracy (0-1)
```

### Monitor
```
/monitor            Show levels
/monitor L0         Silent
/monitor L1         Decisions (default)
/monitor L2         Reasoning
/monitor L3         Debug
```

### Help
```
/help               Show all commands (updated)
```

---

## 📚 Full Documentation

- **UI_MENUS.md** - Complete feature documentation (350 lines)
- **MENUS_IMPLEMENTATION.md** - Developer guide (400 lines)
- **Commands in CLI** - All implemented with `/help` integration

---

## ✨ Features Implemented

| Feature | Status |
|---------|--------|
| Theme selector (8 themes) | ✅ |
| Live color preview | ✅ |
| Settings main menu | ✅ |
| Provider management | ✅ |
| Monitor level control | ✅ |
| Keyboard navigation | ✅ |
| Persistent storage | ✅ |
| Rich markup formatting | ✅ |
| Textual Grid layout | ✅ |
| Reactive state | ✅ |
| Custom messages | ✅ |
| CSS styling | ✅ |

---

## 🚀 Ready to Use!

All menus are fully implemented and ready for:
1. ✅ CLI text-based interaction (`/theme`, `/settings`, `/monitor`)
2. 🔄 Embedding in Textual app as widgets
3. 📊 Extending with additional features (hotkeys, animations, etc)

Everything follows Textual best practices from the documentation ✨
