# Membria CLI - New UI Layout

## Architecture Overview

The Membria CLI interface has been redesigned with a modern, information-dense layout optimized for power users.

### Screen Layout

```
┌────────────────────────────────────────────────────────────────┐
│                        HEADER (Clock)                          │
├─────────────────────────────────────┬──────────────────────────┤
│                                     │    ⚙ STATUS              │
│          MESSAGES AREA              │    ✓ Connected           │
│          (Scrollable)               │                          │
│          - Commands                 │    🎯 MODEL              │
│          - Responses                │    Claude 3.5 Sonnet     │
│          - Context                  │                          │
│                                     │    📊 USAGE              │
│                                     │    Tokens: 8.5K          │
│                                     │    Context: 85%          │
│                                     │┌─────────────────────────┤
│                                     ││ 🏛️  📊  ⚙️           │
│                                     ││ Skills Stats Config    │
│                                     │├─────────────────────────┤
│                                     ││ 🔍  💾  ❓           │
│                                     ││ Audit Session Help    │
│                                     │└─────────────────────────┘
├─────────────────────────────────────┴──────────────────────────┤
│ membria ▸ /help                                                │
├─────────────────────────────────────────────────────────────────┤
│ 📁 10 files +2 -4 │ pipeline | ✓2 ⊙1 ○3 | 📊 8.5K │ 85% ✓ Connected │
├─────────────────────────────────────────────────────────────────┤
│ Ctrl+D: Quit   Alt+C: Copy   Alt+P: Paste   Alt+H: Help      │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Header (Top)
- Shows current time
- Membria logo/title

### 2. Main Container (Middle - Horizontal Split)

#### Left: Messages Area
- **Scrollable** chat/log display
- Rich text with colors and formatting
- Shows all command outputs and responses
- Built-in scrollbar

#### Right: Quick Panel (28 characters wide)
Contains two sections:

**A. Info Section**
- **STATUS**: Connected/Disconnected indicator
- **MODEL**: Current LLM model being used
- **USAGE**: Token count and context percentage
  - Context % color-coded:
    - 🟢 > 50% = Green
    - 🟡 20-50% = Yellow
    - 🔴 < 20% = Red

**B. Icon Grid (3×2)**
Six quick-access buttons in two rows:

| Row 1 | Button | Command |
|-------|--------|---------|
| 🏛️ | Skills | `/skills` - List expert roles |
| 📊 | Stats | `/status` - System statistics |
| ⚙️ | Config | `/settings providers` - Provider config |

| Row 2 | Button | Command |
|-------|--------|---------|
| 🔍 | Audit | `/audit` - Decision audit log |
| 💾 | Session | `/session` - Session info |
| ❓ | Help | `/help` - Commands help |

Button behaviors:
- Hover: Highlight in blue
- Click: Auto-fill input with command
- Focus: Orange highlight

### 3. Input Area
- **Prompt**: `membria ▸ `
- **Placeholder**: "Type your message or /help"
- Single-line text input
- Command history with ↑/↓ arrows
- Auto-complete for `/` commands

### 4. Status Bar (NEW - Under Input)
Displays real-time information on one line:

**Format**: `[LEFT] [SPACER] [CENTER] [SPACER] [RIGHT]`

**Left**: File tracking
```
📁 10 files +2 -4
```
- 📁 Total files in workspace
- 🟢 `+2` Files added
- 🔴 `-4` Files removed

**Center**: Mode & tasks & tokens
```
pipeline | ✓2 ⊙1 ○3 | 📊 8.5K
```
- Mode: `pipeline` / `debate` / `diamond` / `auto`
- Tasks: Completed / In Progress / Open
- Tokens: Used in current session (K = thousands)

**Right**: Context & connection
```
Context: 85% | ✓ Connected
```
- Context %: Dynamically colored
- Status: ✓ Connected or ✗ Disconnected

### 5. Footer (Bottom)
Standard Textual footer with key bindings:
- `Ctrl+D`: Quit
- `Alt+C`: Copy last message
- `Alt+P`: Paste from clipboard
- `Alt+H`: Help

## Color Scheme

| Element | Color | Hex |
|---------|-------|-----|
| Primary | Blue | #5AA5FF |
| Accent | Orange | #FFB84D |
| Success | Green | #21C93A |
| Error | Red | #FF6B6B |
| Warning | Yellow | #FFB84D |
| Neutral | Gray | #E8E8E8 |
| Background | Dark | $surface |
| Panels | Darker | $panel |
| Boost | Lighter | $boost |

## Interaction Flow

### Typical User Session

```
1. Start CLI
   ↓ Shows splash screen (optional)
   ↓ Detects context (workspace type)
   ↓ Shows welcome message
   
2. User types message or command
   ↓ Appears in messages area with › prefix
   
3. If command (starts with /)
   ↓ Command handler processes it
   ↓ Result appears in messages area
   
4. Icon buttons always clickable
   ↓ Fill input with command
   ↓ User can modify or submit
   
5. Status bar updates
   ↓ File changes tracked
   ↓ Tokens counted
   ↓ Context usage shown
   ↓ Connection status monitored
```

## Quick Panel Icon Grid Styling

```css
#icon-grid Button {
    width: 1fr;           /* Equal share of 3 columns */
    height: 5;            /* 5 rows = 2 lines text + padding */
    border: solid #5AA5FF;
    background: $boost;
    color: #FFB84D;
    margin: 0 1 0 0;      /* Right margin between buttons */
}

#icon-grid Button:hover {
    background: #5AA5FF;  /* Blue background on hover */
    color: #1a1a1a;       /* Dark text */
}

#icon-grid Button:focus {
    background: #FFB84D;  /* Orange on focus */
    color: #1a1a1a;
}
```

## Responsive Behavior

- **Messages Area**: Expands to fill available space
- **Quick Panel**: Fixed 28 character width
- **Input Area**: Full width, auto-height
- **Status Bar**: Full width, fixed 1 line
- **Icon Grid**: Responsive - 3 columns always

## Performance Notes

- Status bar updates every second
- Icons are instant (client-side)
- Messages area scrolls efficiently
- No lag on input typing
- Minimal re-renders

## Future Enhancements

- [ ] Customizable icon layout
- [ ] Draggable columns
- [ ] Minimize/expand quick panel
- [ ] Custom color themes
- [ ] Status bar time display
- [ ] Real-time file sync indicator
- [ ] Model switching in status bar
