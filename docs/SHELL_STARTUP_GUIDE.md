# Membria Interactive Shell - Startup Guide

## Quick Start

### Standard Startup (with splash screen)
```bash
membria
# or
python src/membria/cli.py
```

The splash screen shows initialization progress and auto-dismisses after 2 seconds.

### Fallback Mode (no splash screen)
If you experience any display issues or want a faster startup:

```bash
membria --no-splash
# or
python src/membria/cli.py --no-splash
```

## Getting Help Inside Shell

Once in the shell, try:

```
/help              # Show all available commands
/status            # Show system status
/plan <task>       # Create a plan for a task
/diff              # Show changes pending
/apply             # Apply changes
```

## Troubleshooting

### White/Blank Screen Hangs
If the shell appears to freeze on a white screen:

1. **First try:** Press any key or Ctrl+C
   - The splash screen dismisses on any input
   
2. **If Ctrl+C doesn't work:**
   - Kill the terminal (Cmd+W on Mac, Alt+F4 on Windows)
   - Restart with `--no-splash` flag:
     ```bash
     membria --no-splash
     ```

3. **If still hanging:**
   - Check system logs: `tail -f logs.md`
   - Report issue with environment:
     ```bash
     python --version
     pip list | grep textual
     ```

### Terminal Rendering Issues
If text looks corrupted or doesn't render properly:

```bash
# Reset terminal
reset

# Then try again with explicit terminal
TERM=xterm-256color membria --no-splash
```

## Feature Status

### Phase 1 (Now Available) ✅
- Interactive REPL shell
- Command routing with `/commands`
- Real-time status display
- Graph query integration
- Splash screen with initialization status

### Phase 2 (Coming Soon) 🔜
- Multi-model orchestration
- Council of experts (5 roles)
- Parallel task execution
- Advanced diff viewer
- Skill generation

## Environment Notes

- **Python:** 3.11+
- **Terminal:** Supports 256-color terminals (xterm-256color, iTerm2, Windows Terminal)
- **Dependencies:** textual>=0.50.0, rich>=13.0.0

## Development Notes

### Running Tests
```bash
pytest tests/test_shell.py -v
```

### Debug Mode
```bash
# Run with debug output
TEXTUAL_DEBUG=1 membria
```

### Architecture
- **UI:** Built with [Textual](https://textual.textualize.io/) (TUI framework)
- **Rendering:** [Rich](https://rich.readthedocs.io/) for console output
- **State:** Managed via asyncio event loop

## Tips & Tricks

1. **Command History:** Use arrow keys (↑/↓) to navigate previous commands
2. **Exit gracefully:** Press `Ctrl+D` or type `/quit`
3. **View logs:** Check `~/.membria/shell.log`
4. **Performance:** Use `--no-splash` on slower terminals for faster startup
