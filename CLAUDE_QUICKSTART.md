# Claude Code Integration - Quick Start (5 minutes)

## Step 1: Verify Installation ✓

```bash
cd /Users/miguelaprossine/membria-cli
python -m membria.mcp_server --help
```

Should show: MCP Server ready

## Step 2: Configure Claude Code

### Option A: Claude Code GUI (Easiest)

1. Open Claude Code
2. Go to **Settings** → **MCP Servers**
3. Click **Add New Server**
4. Fill in:
   ```
   Name: membria
   Type: stdio
   Command: python
   Args: -m membria.mcp_server
   CWD: /Users/miguelaprossine/membria-cli
   ```
5. Click **Save** and **Restart Claude**

### Option B: Edit settings.json (Advanced)

```bash
# Open your Claude settings
nano ~/.claude/settings.json
```

Add:
```json
{
  "mcp_servers": {
    "membria": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "membria.mcp_server"],
      "cwd": "/Users/miguelaprossine/membria-cli"
    }
  }
}
```

Save and restart Claude Code.

## Step 3: Test the Connection

In Claude Code, ask:

```
"What do we know about database decisions?"
```

Claude should respond with calibration data (if available).

## Step 4: Start Using

### Capture a Decision
```
Claude: "I'm going to use PostgreSQL for the user database"
Claude (behind the scenes): Automatically calls membria.capture_decision()
```

### Get Context Before Planning
```
User: "Help me plan the authentication system"
Claude: Calls get_plan_context() → gives you rich context
```

### Validate Your Plan
```
User: "Here's my plan: [steps]"
Claude: Validates against failures → suggests improvements
```

---

## Common Prompts to Try

### 1. Understand Team Bias
```
"What's our team's track record with [database/auth/api] decisions?
Are we overconfident or underconfident?"
```

**Claude will show:**
- Success rate
- Confidence gap
- Recommendations
- Trends

### 2. Get Historical Context
```
"What have we tried before with [topic]?
What worked and what failed?"
```

**Claude will show:**
- Successful patterns
- Failed approaches
- Past plans
- Lessons learned

### 3. Validate Before Starting
```
"I'm about to do: [your plan steps].
Are there any known issues with this approach?"
```

**Claude will check against:**
- Negative Knowledge (known failures)
- AntiPatterns (bad practices)
- Past failures
- Team overconfidence

### 4. Full Plan Mode
```
"Plan a complete [feature/system] for [domain]"
```

**Claude will:**
1. Get rich context (PRE-PLAN)
2. Generate informed plan
3. Validate each step (MID-PLAN)
4. Record decisions (POST-PLAN)

---

## What Happens Behind the Scenes

```
┌─────────────────────────────────────────────────────┐
│ You ask Claude a question                           │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Claude calls Membria MCP Tool                       │
│ (e.g., get_calibration, validate_plan, etc.)      │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Membria:                                             │
│ 1. Connects to FalkorDB (if running)                │
│ 2. Queries decision graph                           │
│ 3. Extracts patterns, calibration, history          │
│ 4. Returns contextualized response                  │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Claude uses this context to respond                 │
│ (Much better answers because informed by history)  │
└─────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### "Membria is not responding"

**Check 1: Is the MCP server started?**
```bash
python /Users/miguelaprossine/membria-cli/start_mcp_server.py
```

**Check 2: Is Claude configured correctly?**
- Verify settings.json has correct path
- Verify command is `python -m membria.mcp_server`
- Verify CWD is `/Users/miguelaprossine/membria-cli`

**Check 3: Restart Claude**
- Close Claude Code completely
- Reopen it

### "Tools are not available"

- Check that MCP server started without errors
- Check Claude logs: `~/.claude/logs/`
- Verify FalkorDB connection (if needed): `redis-cli ping`

### "Getting connection errors"

**If FalkorDB not running:**
```bash
# Start FalkorDB with Docker (if installed)
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest

# Check connection
redis-cli ping
# Should respond: PONG
```

If you don't have Docker:
- Some tools may fail (those needing graph queries)
- Basic tools still work (get_calibration with empty data, etc.)

---

## Next Steps

1. ✅ **Now:** Claude can access Membria tools
2. 📋 **Make decisions** with Claude and capture them
3. 📊 **Record outcomes** after 30 days
4. 📈 **Watch calibration improve** as team learns
5. 🚀 **Use Plan Mode** for big architectural decisions

---

## Features by Tool

| Tool | What it does | When to use |
|------|-------------|-----------|
| `get_calibration` | Team bias metrics | Before big decisions |
| `capture_decision` | Record a choice | When committing to approach |
| `record_outcome` | Track result | 30 days after decision |
| `get_plan_context` | Rich planning context | Starting to plan (PRE) |
| `validate_plan` | Check for issues | After generating plan (MID) |
| `record_plan` | Save all decisions | When plan approved (POST) |

---

## Success Indicator

After **2 weeks of use**, you should see:

✅ Claude gives more context-aware answers
✅ Fewer "I don't know" responses
✅ Better pattern recognition
✅ More accurate recommendations
✅ Team learns from past mistakes

After **1 month of use**:

✅ Calibration data visible and improving
✅ Team starts trusting the recommendations
✅ Overconfidence bias visible (and correctable)
✅ Fewer surprises (better estimates)
✅ Closed-loop learning kicks in

---

## Support

- 📖 Full docs: `docs/CLAUDE_INTEGRATION.md`
- 💡 Examples: `examples/claude_usage_examples.md`
- 🔧 Configuration: Edit `.claude/settings.json`
- 🐛 Debug: Check `~/.claude/logs/mcp.log`

---

**Ready? Go ask Claude about your next decision!** 🚀
