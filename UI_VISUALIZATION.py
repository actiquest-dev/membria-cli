#!/usr/bin/env python3
"""
Membria CLI - New UI Layout Visualization

This file shows the new interface structure with ASCII art and descriptions.
"""

UI_LAYOUT = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                    MEMBRIA CLI - NEW INTERFACE LAYOUT                          ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  ┌──────────────────────────────────────────────────────┬─────────────────┐  ║
║  │ HEADER: Membria | 14:35:42                          │                 │  ║
║  ├──────────────────────────────────────────────────────┼─────────────────┤  ║
║  │                                                      │  ⚙ STATUS      │  ║
║  │                                                      │  ✓ Connected   │  ║
║  │    MESSAGES AREA (Scrollable)                       │                 │  ║
║  │                                                      │  🎯 MODEL      │  ║
║  │    › /plan Setup authentication                     │  Claude 3.5    │  ║
║  │      [#5AA5FF]pipeline[/#5AA5FF] | ✓1 ⊙2 ○3       │                 │  ║
║  │                                                      │  📊 USAGE      │  ║
║  │    [#21C93A]✓[/#21C93A] Plan ready                 │  Tokens: 8.5K  │  ║
║  │    7-Step Execution Flow...                         │  Context: 85%  │  ║
║  │                                                      │┌───────────────┤  ║
║  │    › /settings providers                           ││  🏛️   📊   ⚙️ │  ║
║  │      Configure Providers:                          ││ Skills Stats Cfg││  ║
║  │                                                      │├───────────────┤  ║
║  │    [#21C93A]✓[/#21C93A] anthropic (ENABLED)        ││  🔍   💾   ❓ │  ║
║  │           Type: anthropic                          ││ Audit Sess Help││  ║
║  │           Model: claude-3-5-sonnet-latest          │└───────────────┘  ║
║  │                                                      │                 │  ║
║  │    Quick Commands:                                  │                 │  ║
║  │      /settings toggle openai                        │                 │  ║
║  │      /settings set-key anthropic sk-ant-...         │                 │  ║
║  │      /settings test-provider openai                 │                 │  ║
║  ├──────────────────────────────────────────────────────┴─────────────────┤  ║
║  │ Input: membria ▸ Type your message or /help                            │  ║
║  ├──────────────────────────────────────────────────────────────────────────┤  ║
║  │ 📁 10 files +2 -4 │ pipeline | ✓2 ⊙1 ○3 | 📊 8.5K │ Context: 85% ✓ Ok║  ║
║  ├──────────────────────────────────────────────────────────────────────────┤  ║
║  │ ^O: Open  Ctrl+D: Quit  Alt+C: Copy  Alt+P: Paste  Alt+H: Help          │  ║
║  └──────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

QUICK_PANEL_DETAIL = """
╔═══════════════════════════╗
║    QUICK PANEL (3×2)     ║
╠═══════════════════════════╣
║                           ║
║  ⚙ STATUS                ║
║  ✓ Connected             ║
║                           ║
║  🎯 MODEL                ║
║  Claude 3.5 Sonnet       ║
║                           ║
║  📊 USAGE                ║
║  Tokens: 8.5K            ║
║  Context: 85%            ║
║                           ║
╠═════════════╤═════════════╣
║  🏛️  Skills  │ 📊  Stats │ ║
║  /skills    │ /status   │ ║
╠═════════════┼═════════════╣
║  ⚙️  Config  │ 🔍  Audit │ ║
║  /settings  │ /audit    │ ║
╠═════════════┼═════════════╣
║  💾 Session │ ❓  Help   │ ║
║  /session   │ /help     │ ║
╚═════════════╧═════════════╝

Button Behavior:
• Click any icon → Auto-fills input with command
• Hover → Blue highlight (#5AA5FF)
• Focus → Orange highlight (#FFB84D)
"""

STATUS_BAR_DETAIL = """
═══════════════════════════════════════════════════════════════════════════════════

STATUS BAR FORMAT (One Line):

[LEFT]          [SPACER]        [CENTER]                [SPACER]     [RIGHT]

LEFT:     📁 10 files +2 -4
          └─ File tracking (added/removed)

CENTER:   pipeline | ✓2 ⊙1 ○3 | 📊 8.5K
          └─ Mode │ Tasks (done/in-progress/open) │ Tokens used

RIGHT:    Context: 85% | ✓ Connected
          └─ Context % (color-coded) │ Connection status

═══════════════════════════════════════════════════════════════════════════════════

COLORS:
┌────────────────────────────────────────────────────────┐
│ Element         │ Color    │ Hex      │ Meaning        │
├────────────────────────────────────────────────────────┤
│ Mode            │ Blue     │ #5AA5FF  │ Primary info   │
│ Tasks-Done      │ Green    │ #21C93A  │ Success        │
│ Tasks-Progress  │ Orange   │ #FFB84D  │ In progress    │
│ Tasks-Open      │ Blue     │ #5AA5FF  │ Waiting        │
│ Tokens          │ Orange   │ #FFB84D  │ Used           │
│ Context >50%    │ Green    │ #21C93A  │ Healthy        │
│ Context 20-50%  │ Orange   │ #FFB84D  │ Warning        │
│ Context <20%    │ Red      │ #FF6B6B  │ Critical       │
│ Connected       │ Green    │ #21C93A  │ OK             │
│ Disconnected    │ Red      │ #FF6B6B  │ Error          │
└────────────────────────────────────────────────────────┘
"""

INTERACTION_EXAMPLES = """
═══════════════════════════════════════════════════════════════════════════════════

EXAMPLE 1: Getting Help
─────────────────────────────────────────────────────────────────────────────────

1. User clicks ❓ (Help icon)
   → Input auto-fills: membria ▸ /help
   
2. User presses Enter
   → Help text appears in messages area
   → Status bar shows: Tasks updated to ✓1 ⊙1 ○2
   → Context % might decrease (due to API call)


EXAMPLE 2: Switching Providers
─────────────────────────────────────────────────────────────────────────────────

1. User clicks ⚙️ (Config icon)
   → Input auto-fills: membria ▸ /settings providers
   
2. User presses Enter or types first few chars
   → Provider list appears in messages
   → Shows: ✓ anthropic (ENABLED), ✓ openai (ENABLED), ✗ kilo (DISABLED)
   
3. User types: /settings toggle kilo
   → Status updates: kilo now ENABLED
   
4. User types: /settings test-provider kilo
   → Connection test runs
   → Result: ✓ Provider configuration valid


EXAMPLE 3: Monitoring Session
─────────────────────────────────────────────────────────────────────────────────

1. Status bar shows: 📁 12 files +3 -1 | pipeline | ✓5 ⊙2 ○1 | 📊 15.3K | Context: 72% ✓ Ok

2. Files are being tracked in real-time (+3 new files)

3. Tasks are progressing (5 done, 2 in progress, 1 waiting)

4. Tokens accumulating (15.3K = 15,300 tokens used)

5. Context consumption: 72% remaining (28% used)
   - Color is orange (#FFB84D) because 20% < 72% < 50% is false
   - Actually 72% > 50% so GREEN (#21C93A)

═══════════════════════════════════════════════════════════════════════════════════
"""

KEYBOARD_SHORTCUTS = """
═══════════════════════════════════════════════════════════════════════════════════

COMMAND INPUT:
  ↑ / ↓           Cycle through command history
  Tab             Auto-complete command (future)
  Ctrl+A          Select all
  Ctrl+K          Clear line

NAVIGATION:
  Ctrl+Home       Jump to top of messages
  Ctrl+End        Jump to bottom of messages
  Page Up/Down     Scroll messages area

QUICK COMMANDS (from icons):
  🏛️ Skills       /skills                  List expert roles
  📊 Stats        /status                  Show system status
  ⚙️ Config       /settings providers      Manage LLM providers
  🔍 Audit        /audit                   Show decision audit log
  💾 Session      /session                 Show session info
  ❓ Help         /help                    Show command help

INPUT MODES:
  /keyword        Slash commands
  plain text      Send to agents for processing

═══════════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(UI_LAYOUT)
    print("\n")
    print(QUICK_PANEL_DETAIL)
    print("\n")
    print(STATUS_BAR_DETAIL)
    print("\n")
    print(INTERACTION_EXAMPLES)
    print("\n")
    print(KEYBOARD_SHORTCUTS)
