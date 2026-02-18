# Membria Complete Integration Guide

This guide shows how to integrate Membria across **Claude Code**, **VSCode Tasks**, and the **VSCode Extension** for a complete decision intelligence workflow.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      DEVELOPER                               │
└─────────────────────────────────────────────────────────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
            ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
            │  Claude │  │ VSCode  │  │ VSCode  │
            │   Code  │  │  Tasks  │  │Extension│
            └────┬────┘  └────┬────┘  └────┬────┘
                 │            │            │
                 └────────────┼────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  MCP Server        │
                    │  (Flask, port 6379)│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Decision System   │
                    │  - Decisions       │
                    │  - Outcomes        │
                    │  - Calibration     │
                    │  - Plans           │
                    │  - Skills          │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  FalkorDB Graph    │
                    │  (Persistent)      │
                    └────────────────────┘
```

## Quick Start (5 minutes)

### 1. Start MCP Server
```bash
cd membria-cli
python src/membria/start_mcp_server.py
# Output: "✅ MCP Server running on port 6379"
```

### 2. Configure VSCode Extension
```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to test in debug mode
```

### 3. Configure Claude Code
Add to your project's `.claude/claude.json`:
```json
{
  "mcp_servers": {
    "membria": {
      "command": "python",
      "args": ["-m", "membria.start_mcp_server"],
      "env": {
        "MEMBRIA_PORT": "6379"
      }
    }
  }
}
```

## Three Integration Points

### 1️⃣ Claude Code Integration

**When to use:** During planning, decision capture, and context review

**Setup:**
```bash
# In membria-cli/.claude/
cat << 'EOF' > claude.json
{
  "mcp_servers": {
    "membria": {
      "command": "python",
      "args": ["src/membria/start_mcp_server.py"]
    }
  }
}
EOF
```

**Available Tools in Claude:**
- `capture_decision` - Record decision with alternatives and confidence
- `record_outcome` - Update decision with result
- `get_calibration` - View team calibration by domain
- `get_decision_context` - Get context for statement
- `validate_plan` - Check plan steps for issues
- `record_plan` - Save plan to database
- `get_plan_context` - Get plan-specific context

**Workflow Example:**
```
User: "I'm planning to redesign the auth system. What should I consider?"

Claude: [Tool] get_decision_context("Auth system redesign")
→ Returns: Recent decisions, calibration gaps, warnings

Claude: "Based on team history, JWT + Redis has 92% success rate.
         But you're overconfident by 15% in auth domain."

User: [Decides to use JWT + Redis]

Claude: [Tool] capture_decision(
  "Use JWT + Redis for session management",
  ["OAuth2", "Custom JWT", "Sessions DB"],
  0.85
)
→ Decision saved to database
```

**See also:** [`docs/CLAUDE_INTEGRATION.md`](../docs/CLAUDE_INTEGRATION.md)

### 2️⃣ VSCode Tasks Integration

**When to use:** Automating recurring Membria operations

**Setup:**
Configuration is in `.vscode/tasks.json`:
```json
{
  "label": "Membria: Generate Skills",
  "type": "shell",
  "command": "python -m membria.commands.skill generate ${input:domain}"
}
```

**Available Tasks:**
| Task | Command | Use Case |
|------|---------|----------|
| List Plans | `membria plans list` | Review team plans |
| Show Plan Stats | `membria plans accuracy` | Check plan accuracy |
| Validate Plan | `membria plans validate` | Check new plan |
| Generate Skill | `membria skills generate` | Create skill from outcomes |
| List Skills | `membria skills list` | Browse available skills |
| Check Readiness | `membria skills readiness` | See if domains ready |
| Run Tests | `pytest tests/` | Verify system |
| Start MCP Server | `python start_mcp_server.py` | Launch server |

**Keyboard Shortcuts:**
- `Ctrl+Shift+M P` - List Plans
- `Ctrl+Shift+M V` - Validate Plan
- `Ctrl+Shift+M G` - Generate Skill
- `Ctrl+Shift+M L` - List Skills

**Example Workflow:**
```
1. User presses Ctrl+Shift+M V
2. VSCode prompts for plan steps
3. Runs: membria plans validate
4. Shows results in output panel
5. Creates annotations for warnings
```

**See also:** [`.vscode/tasks.json`](../.vscode/tasks.json)

### 3️⃣ VSCode Extension Integration

**When to use:** Real-time decision support while coding

**Setup:**
```bash
cd vscode-extension
npm install
npm run compile
npm run vsce-package  # Creates .vsix file

# Install in VSCode:
# Extensions → Install from VSIX
```

**Features:**
- **Sidebar Views**
  - Decisions: Browse all decisions
  - Calibration: Team metrics by domain
  - Skills: Available skills and zones
  - Plans: Team plans and status

- **Commands**
  - `Ctrl+Shift+M D` - Capture Decision
  - `Ctrl+Shift+M C` - Get Context
  - `Ctrl+Shift+M V` - Validate Plan
  - `Ctrl+Shift+M O` - Record Outcome
  - `Ctrl+Shift+M B` - View Calibration

- **Hover Context**
  - Hover over code → See decision context
  - Shows recent outcomes, warnings, calibration

- **Inline Decorations**
  - Green underline = Confident, good history
  - Yellow underline = Review carefully
  - Red underline = Known failures, antipatterns

**Example Workflow:**
```
1. Developer opens Python file
2. Types: "database_type = use_postgresql()"
3. Hovers over "use_postgresql"
4. VSCode shows:
   - Success rate: 89%
   - Recent outcomes: success, success, failure
   - Calibration: Team is overconfident by 12%

5. Developer runs: Ctrl+Shift+M V
6. Validates plan for database migration
7. Gets warnings about past failures
8. Sees recommendation: "Review carefully"

9. Developer clicks "Record Outcome" in sidebar
10. Selects decision and outcome status
11. VSCode refreshes calibration data
```

**See also:** [`README.md`](README.md), [`DEVELOPMENT.md`](DEVELOPMENT.md)

## Complete Workflow Example

**Scenario:** Team needs to redesign caching strategy

### Phase 1: Plan Creation (Claude Code)
```
User: "Help me plan a caching redesign"

Claude: [Tool] get_decision_context("caching strategy")
→ Returns: 23 past decisions, success rate 71%, confidence gap -8%

Claude: "Your team is underconfident in caching. Past successes:
        - Redis cluster: 94% success
        - Memcached: 65% success
        - In-memory cache: 48% success"

User: "Let's use Redis with fallback to Memcached"

Claude: [Tool] record_plan(
  steps=["Design Redis schema", "Setup cluster", "Implement fallback", "Load test"],
  domain="cache",
  confidence=0.8
)
```

### Phase 2: Implementation (VSCode)

**A. Sidebar Planning**
1. Open Membria sidebar
2. Click "Plans" view
3. See new plan with 4 steps
4. Start working through steps

**B. Real-time Context**
1. Start coding fallback logic
2. Type: `if redis_timeout: use_memcached()`
3. Hover over `use_memcached` → See 65% success rate

**C. Validation**
1. Complete initial implementation
2. Press `Ctrl+Shift+M V`
3. Validate full caching plan
4. Warnings: "Fallback not tested with load"
5. Recommendation: "Add load testing step"

### Phase 3: Outcome Tracking (VSCode Extension)
1. After deployment, record outcomes
2. Command: `Ctrl+Shift+M O`
3. Select: `use_redis_cluster`
4. Choose: `success`
5. Extension updates calibration data in real-time

### Phase 4: Skill Generation (VSCode Tasks)
1. Collect 30+ caching decisions with outcomes
2. Run task: `Ctrl+Shift+M G` → "cache" domain
3. System generates skill: "cache_strategy_recommendation"
4. Skill shows: Redis (94%), Memcached (65%), In-memory (48%)
5. Next time team plans caching, get evidence-based guidance

## Configuration Reference

### Claude Integration
File: `membria-cli/.claude/claude.json`
```json
{
  "mcp_servers": {
    "membria": {
      "command": "python",
      "args": ["src/membria/start_mcp_server.py"],
      "timeout": 30000
    }
  }
}
```

### VSCode Extension Settings
File: `.vscode/settings.json`
```json
{
  "membria.serverHost": "localhost",
  "membria.serverPort": 6379,
  "membria.autoValidatePlans": true,
  "membria.showHoverContext": true,
  "membria.showInlineWarnings": true,
  "membria.debounceMs": 500
}
```

### VSCode Tasks
File: `.vscode/tasks.json` (see [full file](../.vscode/tasks.json))
- 11 tasks configured
- All use Ctrl+Shift+M prefix
- Linked to keybindings for quick access

## Troubleshooting

### MCP Server Won't Start
```bash
# Check port availability
lsof -i :6379

# Kill existing process if needed
kill -9 <PID>

# Verify Python environment
python -m membria.start_mcp_server --version
```

### VSCode Extension Not Connecting
1. Verify MCP server running: `curl http://localhost:6379/health`
2. Check firewall: Port 6379 must be accessible
3. Review extension logs: Output → Membria
4. Restart VSCode: `Ctrl+Shift+P` → "Reload Window"

### Claude Code Integration Issues
1. Verify `.claude/claude.json` syntax (valid JSON)
2. Check paths are absolute or relative to workspace
3. Test MCP server directly: `python src/membria/start_mcp_server.py`
4. Check Claude Code logs for errors

### Tasks Not Running
1. Verify VSCode tasks.json format
2. Check problem matchers for correct paths
3. Run task with verbose: `Terminal → Run Task (with Debug)`
4. Review Output terminal for error messages

## Performance Tips

### Cache Decisions
```typescript
// Extension caches decisions per domain
const cache = new Map<string, Decision[]>();
if (cache.has(domain)) return cache.get(domain);
```

### Debounce Updates
```typescript
// Decorations update 500ms after user stops typing
private updateTimer: NodeJS.Timeout;
```

### Batch Operations
```bash
# CLI: Process multiple plans at once
membria plans list --limit 100 | membria plans validate --batch
```

## Security Considerations

### API Keys
Never commit `.env` files containing API keys:
```bash
echo ".env" >> .gitignore
```

### Data Privacy
- Decisions stored in local FalkorDB (not cloud)
- MCP server runs locally (port 6379)
- VSCode extension communicates via localhost only
- Claude integration uses local MCP protocol

### Access Control
- Restrict FalkorDB access by network
- Use firewall rules for port 6379
- Disable remote connections if not needed

## Next Steps

1. **Start MCP Server**: `python src/membria/start_mcp_server.py`
2. **Setup VSCode Extension**: `cd vscode-extension && npm install && npm run compile`
3. **Configure Claude**: Add `.claude/claude.json` to project
4. **Create First Decision**: Use VSCode Command `Ctrl+Shift+M D`
5. **Capture Outcome**: Use `Ctrl+Shift+M O` after decision result
6. **Generate Skill**: Use task `Ctrl+Shift+M G` after 30+ outcomes
7. **Use in Claude**: Reference skills in planning via MCP tools

## Additional Resources

- [Membria CLI Documentation](../README.md)
- [Claude Integration Details](../docs/CLAUDE_INTEGRATION.md)
- [VSCode Tasks Configuration](../.vscode/tasks.json)
- [VSCode Extension README](README.md)
- [Extension Development Guide](DEVELOPMENT.md)
