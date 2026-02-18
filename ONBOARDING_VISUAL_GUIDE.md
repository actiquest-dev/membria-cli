# Onboarding Screens - Visual Examples & Usage Guide

## Quick Start

When you launch Membria for the first time:

```bash
$ membria
```

Instead of the normal CLI, you'll see the interactive onboarding wizard.

## Screen Walkthrough

### Screen 1/8: Welcome

```
╭─────────────────────────────────────────────────────────────────╮
│                     Welcome to Membria                          │
│                      Step 1 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Your Decision Intelligence Platform                            │
│                                                                 │
│ Membria captures your AI decisions, tracks outcomes, and       │
│ improves future choices through continuous calibration.        │
│                                                                 │
│ What you'll build:                                             │
│   ✓ A council of AI experts                                    │
│   ✓ Decision memory graph                                      │
│   ✓ Calibration system                                         │
│   ✓ Context injection                                          │
│                                                                 │
│ How it works:                                                  │
│   Decision → Code → Outcome → Calibration → Better Context    │
│                                                                 │
│ Let's set up your workspace!                                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**User Action**: Click [Next] → Advance to Provider Setup

---

### Screen 2/8: Provider Setup

```
╭─────────────────────────────────────────────────────────────────╮
│                    Provider Setup                               │
│                      Step 2 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Select your AI providers:                                      │
│                                                                 │
│ ( ) Anthropic (Claude)                                         │
│ (●) OpenAI (GPT-4)                                             │
│ ( ) Ollama (Local)                                             │
│ ( ) OpenRouter                                                 │
│                                                                 │
│                                                                 │
│ API Key:                                                       │
│ [sk-org-abc123............................... ]               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**Behind the scenes**:
```python
# When [Next] is clicked:
config_manager.set("providers.openai.api_key", "sk-org-...")
config_manager.save()

# Updated ~/.membria/config.toml:
[providers.openai]
api_key = "sk-org-..."
enabled = true
```

---

### Screen 3/8: Role Assignment

```
╭─────────────────────────────────────────────────────────────────╮
│                   Role Assignment                               │
│                      Step 3 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Build your expert council:                                     │
│                                                                 │
│ (●) Full Power (Claude 3.5 + GPT-4)                            │
│ ( ) Budget Friendly (Haiku + GPT-mini)                         │
│ ( ) Local Only (Ollama)                                        │
│ ( ) Custom                                                     │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**Config saved**:
```toml
[interactive]
role_preset = "full"
```

---

### Screen 4/8: Graph Database

```
╭─────────────────────────────────────────────────────────────────╮
│                   Graph Database                                │
│                      Step 4 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Store your decision memory:                                    │
│                                                                 │
│ (●) Docker (Recommended)                                       │
│ ( ) Binary                                                     │
│ ( ) Managed Service                                            │
│ ( ) Skip (In-memory)                                           │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**Expected**: If user chooses Docker, system will verify Docker is installed.

---

### Screen 5/8: Monitoring Level

```
╭─────────────────────────────────────────────────────────────────╮
│                   Monitoring Level                              │
│                      Step 5 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ How verbose should logging be?                                 │
│                                                                 │
│ ( ) 🤐 L0: Silent (production)                                 │
│ (●) 📝 L1: Decisions (default)                                 │
│ ( ) 🧠 L2: Reasoning                                           │
│ ( ) 🔍 L3: Debug (verbose)                                     │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**Levels Explained**:
- **L0**: No logs, production only
- **L1**: Decision statements + outcomes (default)
- **L2**: + reasoning chains, context used
- **L3**: + debug info, API calls, timings

---

### Screen 6/8: Theme Selection

```
╭─────────────────────────────────────────────────────────────────╮
│                   Color Theme                                   │
│                      Step 6 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Personalize your CLI:                                          │
│                                                                 │
│ (●) Nord                          ( ) Tokyo Night              │
│ ( ) Gruvbox                        ( ) Solarized Light         │
│ ( ) Dracula                        ( ) Solarized Dark          │
│ ( ) One Dark                       ( ) Monokai                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]                [Next]│
╰─────────────────────────────────────────────────────────────────╯
```

**Color Preview** (live update):
- **Nord** (Arctic colors):  [Primary: #5AA5FF] [Secondary: #FFB84D]
- **Gruvbox** (Retro): [Primary: #FB4934] [Secondary: #FE8019]
- **Tokyo Night** (Cyberpunk): [Primary: #7AA2F7] [Secondary: #BB9AF7]

---

### Screen 7/8: First Decision

```
╭─────────────────────────────────────────────────────────────────╮
│                  First Decision                                 │
│                      Step 7 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Experience Membria in action:                                  │
│                                                                 │
│ Your decision:                                                 │
│ [Use JWT tokens instead of session cookies........... ]       │
│                                                                 │
│ How confident? (0-100):                                        │
│ [85................................                   ]        │
│                                                                 │
│ Domain:                                                        │
│ [security, authentication.......................... ]        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]  [Skip]               [Finish]│
╰─────────────────────────────────────────────────────────────────╯
```

**Behind scenes**:
```python
config_manager.set("first_decision", {
    "statement": "Use JWT tokens instead of session cookies",
    "confidence": 85,
    "domain": "security, authentication"
})
```

---

### Screen 8/8: Summary

```
╭─────────────────────────────────────────────────────────────────╮
│                   Setup Complete!                               │
│                      Step 8 of 8                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ✅ You've configured:                                          │
│                                                                 │
│ 📦 Providers: Anthropic, OpenAI                               │
│ 👥 Roles: Full Power preset                                   │
│ 🗄️  Graph Database: Docker                                    │
│ 📊 Monitoring: L1 (Decisions)                                 │
│ 🎨 Theme: nord                                                │
│ 📝 First Decision: Recorded                                   │
│                                                                 │
│ Next steps:                                                    │
│   1. Type /help for all commands                               │
│   2. Use /plan to start delegating                             │
│   3. Check /settings to adjust config                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Back]                      [Start!]│
╰─────────────────────────────────────────────────────────────────╯
```

**User clicks [Start!]** → Main app interface appears

---

## Main App After Onboarding

```
╭─────────────────────────────────────────────────────────────────╮
│ Membria CLI                                          12:34 PM  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ╭─ Membria CLI ─╮                                              │
│ Council Context: architecture/security                         │
│ ✓ Expert roles: Architect, Security, Database, Moderator      │
│ Type /help for available commands                              │
│ ╰──────────────────╯                                            │
│                                                                 │
│ › /help                                                        │
│                                                                 │
│                                  │ 🏛️  📊  ⚙️  │               │
│                                  │ 🔍  💾  ❓  │               │
│                                  │             │               │
│                                  │____________ │               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ › |                                                             │
├─────────────────────────────────────────────────────────────────┤
│ pipeline │ ✓0 ⊙0 ○0 │ 📊 0 tokens │ 85%                        │
╰─────────────────────────────────────────────────────────────────╯
```

## Keyboard Navigation

### Within Each Screen

| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Move between buttons |
| Space / Enter | Select/click button |
| Arrow Keys | Scroll content if needed |
| Escape | Exit onboarding (saves partial config) |

### Quick Examples

**Skip to Summary Directly**
```
Screen 2: [Skip] →
Screen 3: [Skip] →
Screen 4: [Skip] →
Screen 5: [Skip] →
Screen 6: [Skip] →
Screen 7: [Skip] →
Screen 8: Summary (shown)
```

Result: Provider setup partially done, other steps skipped.

**Go Back to Step 2**
```
Screen 5: [Back] →
Screen 4: [Back] →
Screen 3: [Back] →
Screen 2: Modify provider again
```

Result: Re-enter API key, config updated.

## Configuration File After Onboarding

Full `~/.membria/config.toml` after completing all steps:

```toml
[providers.anthropic]
type = "anthropic"
model = "claude-3-5-sonnet-latest"
api_key = "sk-ant-..."
endpoint = "https://api.anthropic.com/v1"
enabled = true

[providers.openai]
type = "openai"
model = "gpt-4-turbo"
api_key = "sk-org-..."
endpoint = "https://api.openai.com/v1"
enabled = true

[providers.ollama]
type = "ollama"
model = "llama2"
api_key = ""
endpoint = "http://localhost:11434"
enabled = false

[interactive]
role_preset = "full"

[falkordb]
host = "localhost"
port = 6379
password = ""
db = 0
mode = "docker"

[monitoring]
level = "L1"

[display]
theme = "nord"
compact = false

[first_decision]
statement = "Use JWT tokens instead of session cookies"
confidence = 85
domain = "security, authentication"

[onboarding]
completed = true
timestamp = "2024-01-15T12:34:56"

[cache]
enabled = true
max_age = "24h"
max_size_mb = 100

[daemon]
port = 3117
auto_start = true
log_level = "info"
```

## User Scenarios

### Scenario 1: Quick Setup (All Defaults)

```
Screen 1: [Next] → Welcome skip
Screen 2: Anthropic key entered, [Next]
Screen 3: Select "Full Power", [Next]
Screen 4: Select "Docker", [Next]
Screen 5: L1 (already selected), [Next]
Screen 6: Nord (already selected), [Next]
Screen 7: Skip decision, [Skip]
Screen 8: [Start!]

⏱️ Time: ~1-2 minutes
✅ Result: Fully configured with all recommended options
```

### Scenario 2: Local Development Only

```
Screen 1: [Next]
Screen 2: Ollama key (empty), [Next]
Screen 3: Select "Local Only", [Next]
Screen 4: Select "Skip", [Next]
Screen 5: Select "L3" (Debug), [Next]
Screen 6: Change to "Dracula", [Next]
Screen 7: Enter decision, [Finish]
Screen 8: [Start!]

✅ Result: Local setup without Docker/cloud providers
```

### Scenario 3: Partial Setup (Skip Remaining)

```
Screen 1: [Next]
Screen 2: [Skip] → Skips to Summary without provider setup
Screen 8: [Back] → Return to add provider later
Screen 8: [Start!]

⚠️  Warning: App will warn about missing providers
💡 Fix: Use /settings providers to add later
```

## Common Tasks After Onboarding

### Change Theme Later

```bash
$ /theme gruvbox
✓ Theme changed to gruvbox
```

### Adjust Monitoring

```bash
$ /monitor L3
✓ Monitoring level set to L3 (verbose)
```

### Add Another Provider

```bash
$ /settings add-provider openrouter
Enter API key: sk-or-...
✓ OpenRouter added
```

### View Current Config

```bash
$ /settings
Available providers:
  anthropic  ✓ enabled
  openai     ✓ enabled
  ollama     ✗ disabled
  openrouter ✓ enabled

Current theme: gruvbox
Current level: L1
Role preset: full
```

## Troubleshooting

### Onboarding Doesn't Appear

Usually means configuration already exists:
```bash
# Check if first_run flag exists
grep "onboarding.completed" ~/.membria/config.toml

# Reset to first-run state
rm ~/.membria/config.toml
# Next app launch shows onboarding
```

### Changes Not Saving

Check file permissions:
```bash
ls -la ~/.membria/config.toml
# Should be read/write for user
chmod 644 ~/.membria/config.toml
```

### Theme Color Issues

Verify terminal supports 24-bit color:
```bash
# Check terminal capabilities
echo $TERM
# Should show something like: xterm-256color or screen-256color
```

## Summary

The onboarding experience:
- ✅ Takes 2-5 minutes
- ✅ Guides through 8 well-explained steps
- ✅ Persists all config immediately
- ✅ Allows back-navigation and skipping
- ✅ Results in fully functional Membria setup
- ✅ Can be modified anytime with /settings commands
