# VSCode Integration Guide

## Overview

Membria integrates with VSCode through:
1. **Tasks** - Run Membria commands via Command Palette
2. **Keybindings** - Quick keyboard shortcuts for frequent tasks
3. **Settings** - Recommended extensions and Python configuration

## Quick Setup

### 1. Open Project in VSCode

```bash
cd /Users/miguelaprossine/membria-cli
code .
```

### 2. Install Recommended Extensions

VSCode will ask to install extensions. Click **Install All** to get:
- Python (ms-python.python)
- Pylance (type checking)
- Ruff (linting)
- Git Lens (git integration)
- GitHub Copilot (optional)

## Using Tasks

### View All Available Tasks

**Command Palette:** `Ctrl+Shift+P` → Type "Run Task"

Or use **Terminal** menu → **Run Task**

### Available Tasks

#### Plan Mode Tasks

**membria: List plans**
- Shows all plans with status
- Usage: See what plans exist

**membria: Show plan**
- Displays detailed plan information
- Usage: Review specific plan steps

**membria: Plan accuracy**
- Shows accuracy metrics (time, completion rate)
- Usage: Understand team estimate patterns

**membria: Validate plan**
- Validates plan steps against known issues
- Usage: Check plan before executing

#### Skills Tasks

**membria: Generate skill**
- Creates a skill for a domain
- Usage: Generate from 3+ patterns

**membria: List skills**
- Shows all generated skills
- Usage: Browse team expertise

**membria: Show skill**
- Displays skill with zones (green/yellow/red)
- Usage: See detailed skill info

**membria: Check skill readiness**
- Shows readiness per domain
- Usage: Know when you can generate next skill

#### Testing & Development

**membria: Run all tests**
- Runs pytest with all 365+ tests
- Usage: Full test suite

**membria: Run quick tests (no DB)**
- Runs only non-database tests
- Usage: Fast feedback without FalkorDB

#### Server

**membria: Start MCP server**
- Starts the MCP server for Claude
- Usage: Integration with Claude Code

---

## Using Keybindings

Press these key combinations to run tasks:

| Shortcut | Task |
|----------|------|
| `Ctrl+Shift+M Ctrl+Shift+P` | List plans |
| `Ctrl+Shift+M Ctrl+Shift+V` | Validate plan |
| `Ctrl+Shift+M Ctrl+Shift+S` | Generate skill |
| `Ctrl+Shift+M Ctrl+Shift+L` | List skills |
| `Ctrl+Shift+M Ctrl+Shift+R` | Check readiness |
| `Ctrl+Shift+M Ctrl+Shift+T` | Run quick tests |
| `Ctrl+Shift+M Ctrl+Shift+M` | Start MCP server |

### Custom Keybindings

Edit `.vscode/keybindings.json` to change shortcuts:

```json
{
  "key": "your+key+combo",
  "command": "workbench.action.tasks.runTask",
  "args": "membria: Task Name"
}
```

Common patterns:
- `ctrl+shift+k` - Control + Shift + K
- `alt+m` - Alt + M
- `cmd+shift+p` - Command + Shift + P (Mac)

---

## Settings & Extensions

### Recommended Extensions

Auto-installed when you click "Install All":

1. **Python** (ms-python.python)
   - Syntax highlighting
   - Debugging
   - Testing

2. **Pylance** (ms-python.vscode-pylance)
   - Type checking
   - Smart suggestions
   - Code analysis

3. **Ruff** (charliermarsh.ruff)
   - Fast Python linting
   - Code formatting

4. **Git Lens** (eamodio.gitlens)
   - Git blame/history
   - Commit info on hover

5. **GitHub Copilot** (GitHub.copilot)
   - AI-powered code suggestions
   - Pairs well with Membria

### Python Environment

VSCode uses `.vscode/settings.json` to configure:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.testing.pytestEnabled": true
}
```

If you see warnings about Python:
1. Open Command Palette: `Ctrl+Shift+P`
2. Type: "Python: Select Interpreter"
3. Choose the virtual environment in `venv/`

---

## Workflow Examples

### Example 1: Validate a Plan

1. You've written a plan for a new feature
2. Press: `Ctrl+Shift+M Ctrl+Shift+V`
3. Enter your plan description
4. VSCode shows validation results
5. Review warnings and adjust if needed

### Example 2: Generate Skills

1. After building something new in a domain
2. Press: `Ctrl+Shift+M Ctrl+Shift+S`
3. Select domain (auth, database, etc.)
4. VSCode generates skill with patterns

### Example 3: Quick Testing

1. You make code changes
2. Press: `Ctrl+Shift+M Ctrl+Shift+T`
3. VSCode runs fast tests (no DB needed)
4. See results in output panel
5. Continue coding with confidence

### Example 4: Full Development Loop

```
1. Open membria-cli project
   → Code opens, extensions install

2. Make changes to code
   → Edit files, use Copilot suggestions

3. Run quick tests
   → Ctrl+Shift+M Ctrl+Shift+T
   → See if changes work

4. Generate skills (if new patterns)
   → Ctrl+Shift+M Ctrl+Shift+S
   → Document team learning

5. Validate plans (if planning)
   → Ctrl+Shift+M Ctrl+Shift+V
   → Check against known issues

6. Start MCP for Claude
   → Ctrl+Shift+M Ctrl+Shift+M
   → Connect to Claude Code
```

---

## Troubleshooting

### Tasks don't show up

1. Check `.vscode/tasks.json` exists
2. Reload window: `Ctrl+Shift+P` → "Reload Window"
3. Try running task again

### Keybindings don't work

1. Check `.vscode/keybindings.json`
2. Make sure keys aren't already bound
3. Test with Command Palette instead
4. Edit keybindings.json and change conflict

### Python interpreter not found

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

2. Select interpreter:
   - Ctrl+Shift+P → "Python: Select Interpreter"
   - Choose `./venv/bin/python`

### Extensions not installing

1. Click "Install All" button
2. If button doesn't appear:
   - Click Extensions icon (left sidebar)
   - Search recommended extensions
   - Install individually

### Tests fail with import errors

1. Make sure you're in project root:
   ```bash
   cd /Users/miguelaprossine/membria-cli
   ```

2. Set PYTHONPATH in terminal:
   ```bash
   export PYTHONPATH=$(pwd)/src:$PYTHONPATH
   ```

3. Or: The `.vscode/settings.json` should handle this

---

## Pro Tips

### 1. Use Task Automation

Create a `.vscode/tasks.json` task that runs multiple steps:

```json
{
  "label": "membria: Full Workflow",
  "dependsOn": [
    "membria: Run quick tests",
    "membria: Generate skill",
    "membria: Start MCP server"
  ],
  "problemMatcher": []
}
```

### 2. Quick Access to Plans

Add to your `.vscode/settings.json`:

```json
{
  "terminal.integrated.env.osx": {
    "MEMBRIA_HOME": "${workspaceFolder}"
  }
}
```

Then access from terminal:
```bash
python -m membria.commands.plan_commands
```

### 3. Debugging with Breakpoints

Add breakpoints in Python files, then:
- F5 to start debugging
- Watch variables in Debug panel
- Great for understanding how Membria works

### 4. Git Integration with Membria Decisions

When committing, reference decisions:

```
git commit -m "Implement JWT auth (decision: dec_abc123)"
```

Git Lens will show the decision context.

---

## Performance Tips

### Make Tasks Faster

For large codebases:
- Run "quick tests" (Ctrl+Shift+M T) instead of "all tests"
- FalkorDB optional for most operations
- Most Membria operations work without database

### Optimize VSCode

- Disable extensions you don't use
- Update Python extension regularly
- Use Ruff instead of Pylint (much faster)

---

## Next Steps

1. ✅ **Now:** Use tasks from Command Palette
2. 📌 **Learn:** Keybindings for frequent tasks
3. 🚀 **Integrate:** Connect with Claude Code
4. 📊 **Automate:** Create custom task workflows

---

## Support

- 📖 Full docs: Read inline in `.vscode/` files
- 🔧 Troubleshoot: Check "Python: Show Output" panel
- 💬 Questions: Check examples in `examples/` folder

**Happy coding with Membria!** 🚀
