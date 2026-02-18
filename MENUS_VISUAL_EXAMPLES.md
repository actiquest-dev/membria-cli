# 🎪 Membria Menus - Visual Examples

## Example 1: Theme Selector

### Command: `/theme`

```
╭─ Theme Selector ─╮

┌──────────────────┐  ┌──────────────────┐
│   [NORD]         │  │  [GRUVBOX]       │
│ Arctic palette   │  │ Retro groove     │
└──────────────────┘  └──────────────────┘
┌──────────────────┐  ┌──────────────────┐
│ [TOKYO-NIGHT]    │  │ [SOLARIZED-L]    │
│ Cyberpunk vibes  │  │ Light background │
└──────────────────┘  └──────────────────┘
┌──────────────────┐  ┌──────────────────┐
│ [SOLARIZED-D]    │  │   [DRACULA]      │
│ Dark background  │  │ Vampire theme    │
└──────────────────┘  └──────────────────┘
┌──────────────────┐  ┌──────────────────┐
│   [ONE-DARK]     │  │   [MONOKAI]      │
│ Atom inspired    │  │ High contrast    │
└──────────────────┘  └──────────────────┘

Color Palette:
▓▓ ▓▓ ▓▓ ▓▓  (nord colors)
$2E3440 #88C0D0 #81A1C1 #A3BE8C
```

### Command: `/theme tokyo-night`

```
[#21C93A]✓ Theme set to:[/#21C93A] [#5AA5FF]tokyo-night[/#5AA5FF] (Cyberpunk vibes)
```

---

## Example 2: Settings Menu (Text-based)

### Command: `/settings`

```
╭─ Settings Menu ─╮

📦 Providers
  /settings providers              List all providers
  /settings toggle <name>          Enable/disable provider
  /settings set-key <name> <key>   Set API key
  /settings set-model <n> <model>  Change default model
  /settings test-provider <name>   Test provider connection
  /settings add-provider <n> <t>   Add new provider
  /settings remove <name>          Remove provider

👥 Roles & Agents
  /settings roles                  List available roles
  /settings assign-role <r> <p>    Assign role to provider
  /settings calibrate <r> <acc>    Set role accuracy (0-1)

🎨 Display
  /theme                           Show theme options
  /monitor                         Show monitoring levels

╰──────────────────────────────╯
```

### Sub-command: `/settings providers`

```
Configured Providers:

✓ anthropic
   Type: anthropic | Model: claude-3-5-sonnet | Auth: ✓

✗ openai
   Type: openai | Model: gpt-4-turbo | Auth: ⚠

✓ kilo
   Type: ollama | Model: llama2 | Auth: ✓

Use /settings set-key <name> <key> to configure API keys
```

### Sub-command: `/settings roles`

```
Available Expert Roles:

  ✓ Architect
     System design & architecture decisions
     Provider: anthropic:claude-3-5-sonnet

  ✓ Security Engineer
     Security & auth review
     Provider: anthropic:claude-3-opus

  ✓ Database Expert
     Schema & query optimization
     Provider: openai:gpt-4-turbo

  ✓ Moderator
     Conflict resolution & consensus
     Provider: anthropic:claude-3-5-sonnet

Use /settings assign-role <role> <provider> to configure
```

---

## Example 3: Monitoring Level Menu

### Command: `/monitor`

```
╭─ Monitoring Level ─╮

  ✓ L0: Silent
    No logging. Fire and forget.

  L1: Decisions  
    Show decisions + outcomes (default)

  L2: Reasoning
    L1 + agent reasoning traces

  L3: Debug
    L2 + all tool calls & graph queries

Use /monitor <L0|L1|L2|L3> to change
```

#### After selecting: `/monitor L3`

```
[#21C93A]✓ Monitoring set to:[/#21C93A] L3 - Debug - L2 + all tool calls & graph queries
```

---

## Example 4: Provider Manager Menu

### Command: `/settings test-provider anthropic`

```
Testing provider: anthropic

  Status: ✓ ENABLED
  Type: anthropic
  Model: claude-3-5-sonnet
  Endpoint: default (https://api.anthropic.com/v1)
  Auth: ✓ Configured

✓ Provider configuration valid
```

### Detailed Provider Setup Flow

```
User: /settings providers
      ↓
System: ✓ anthropic  | ✗ openai  | ✓ kilo
      ↓
User: /settings set-key openai sk-proj-xxx...
      ↓
System: ✓ API key configured for openai
      ↓
User: /settings toggle openai
      ↓
System: ✓ Provider enabled
      ↓
User: /settings test-provider openai
      ↓
System: ✓ Provider configuration valid
```

---

## Example 5: Help Menu

### Command: `/help`

```
╭─ Membria CLI Commands ─╮

📦 Navigation & System
  /help              Show this help message
  /status            Show system and team status
  /context           Show detected workspace context
  /session           Show session statistics
  /settings          Configure providers, roles, agents

📦 Planning & Execution
  /plan <task>       Generate a multi-agent plan
  /diff [file]       Show pending changes
  /apply [file]      Apply validated changes
  
📦 Analysis & Decision History
  /decisions [n]     Show last N decisions (default: 5)
  /calibration [d]   Show calibration stats for domain
  /cost              Show current session cost
  /audit             Show reasoning audit log

📦 Configuration
  /agents            List agents and calibration
  /skills            List all expert roles
  /mode [name]       Show or switch orchestration mode
  /theme [name]      Show themes or set theme
  /monitor [L0-L3]   Show monitoring levels or set level
  /settings          Main settings menu
  /settings providers            Interactive provider manager
  /settings toggle <name>        Enable/disable provider
  /settings set-key <name> <key> Set API key
  /settings test-provider <name> Test provider

📦 Control & Clipboard
  /exit              Exit the shell
  /copy              Copy last message to clipboard
  /paste             Paste from clipboard
  /export [file]     Save all messages to file
  /view              View all messages in less (for text selection)
  /dashboard [host port]  Open analytics dashboard in browser

📦 Navigation
  ↑↓        Command history
  Ctrl+Home Jump to top
  Ctrl+End  Jump to bottom
  Click     Click commands or /export button

╰──────────────────────────────╯
```

---

## Example 6: Full Interactive Session

```
╭─ Membria CLI ─╮
Council Context: data-processing
✓ Expert roles: Architect, Database Expert

Type /help for available commands
╰──────────────────╯

› /settings
╭─ Settings Menu ─╮
📦 Providers
  /settings providers              List all providers
  /settings toggle <name>          Enable/disable provider
...
╰──────────────────────────────╯

› /settings providers
Configured Providers:

✓ anthropic
   Type: anthropic | Model: claude-3-5-sonnet | Auth: ✓

✗ openai
   Type: openai | Model: gpt-4-turbo | Auth: ⚠

› /settings set-key openai sk-proj-12345...
✓ API key configured for openai

› /settings toggle openai
✓ Provider enabled: openai

› /theme
Available Themes:

  🎨 nord: Arctic palette
    solarized-light: Light background
    …(6 more themes)

Current: nord
Usage: /theme <name>

› /theme tokyo-night
✓ Theme set to: tokyo-night (Cyberpunk vibes)

› /monitor
Monitoring Level:

  ✓ L0: Silent - No logging
    L1: Decisions - Show decisions + outcomes (default)
    L2: Reasoning - L1 + agent reasoning traces
    L3: Debug - L2 + all tool calls & graph queries

› /monitor L2
✓ Monitoring set to: L2 - Reasoning - L1 + agent reasoning traces

(All subsequent commands now use L2 verbosity)
```

---

## Example 7: Widget Rendering (Textual Grid Layout)

### ThemeMenu as embedded Textual widget:

```
┌─────────────────────────────────────────┐
│ ╭─ Theme Selector ─╮                    │
│ ┌───────────────┬───────────────┐       │
│ │  ▶ NORD       │   GRUVBOX     │       │
│ │  Arctic       │   Retro       │       │
│ └───────────────┴───────────────┘       │
│ ┌───────────────┬───────────────┐       │
│ │  TOKYO-NIGHT  │ SOLARIZED-L   │       │
│ │  Cyberpunk    │  Light        │       │
│ └───────────────┴───────────────┘       │
│ ┌───────────────┬───────────────┐       │
│ │  SOLARIZED-D  │    DRACULA    │       │
│ │  Dark         │   Vampire     │       │
│ └───────────────┴───────────────┘       │
│ ┌───────────────┬───────────────┐       │
│ │   ONE-DARK    │    MONOKAI    │       │
│ │   Atom        │  High contrast│       │
│ └───────────────┴───────────────┘       │
│                                         │
│ Color Palette:                          │
│ ██ ██ ██ ██                             │
│ #2E3440 #88C0D0 #81A1C1 #A3BE8C       │
└─────────────────────────────────────────┘
```

---

## Example 8: Settings Menu as Textual Widget

```
┌─────────────────────────────────────────┐
│ ╭─ Settings Menu ─╮                     │
│                                         │
│ Providers                               │
│ ┌──────────────────────────────────┐   │
│ │ ➕ Add Provider                   │   │
│ │ ⚙️  Manage Providers              │   │
│ └──────────────────────────────────┘   │
│                                         │
│ Roles & Agents                          │
│ ┌──────────────────────────────────┐   │
│ │ 👥 Assign Roles                  │   │
│ │ 📊 View Calibration              │   │
│ └──────────────────────────────────┘   │
│                                         │
│ Display                                 │
│ ┌──────────────────────────────────┐   │
│ │ Change 🎨                         │   │
│ │ [✓][L2][L3] Monitor Level        │   │
│ └──────────────────────────────────┘   │
│                                         │
│ Experimental                            │
│ ┌──────────────────────────────────┐   │
│ │ [✓] Auto-Routing                 │   │
│ │ [✓] RAG Context                  │   │
│ └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## Color Scheme Reference

Used throughout all menus:

```
[#5AA5FF] - Primary Blue    (headers, titles)
[#FFB84D] - Secondary Orange (section labels, icons)
[#21C93A] - Accent Green     (checkmarks, success)
[#E8E8E8] - Light Gray       (body text, descriptions)
[red]     - Error Red        (disabled, errors)
[yellow]  - Warning Yellow   (warnings, missing config)
```

---

## Keyboard Shortcuts (Built-in Textual)

```
Tab              - Next menu item / button
Shift+Tab        - Previous menu item
Enter / Space    - Activate button / select item
Escape           - Close menu (when embedded)
↑↓               - Navigate list items
Home             - First item
End              - Last item
```

All menus follow standard Textual widget behavior ✨
