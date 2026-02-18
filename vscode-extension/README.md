# Membria VSCode Extension

Membria decision intelligence integration for VSCode. Brings decision context, plan validation, and skill recommendations directly into your editor.

## Features

### 📋 Decision Management
- **Capture Decisions**: Record decisions with alternatives and confidence levels
- **Record Outcomes**: Track decision results to build calibration data
- **Decision Tree**: Browse all decisions organized by status (Recent, Success, Failed, Pending)

### 🎯 Plan Validation
- **Validate Plans**: Get real-time feedback on plan steps
- **Detection**: Identifies conflicts with negative knowledge and antipatterns
- **Warnings**: Shows calibration gaps and debiasing suggestions

### ⭐ Skills & Recommendations
- **List Skills**: Browse domain-specific skills with quality scores
- **Generate Skills**: Create skills from outcomes and patterns
- **Zones**: See patterns categorized as Green (use confidently), Yellow (review carefully), Red (avoid)

### 📊 Team Calibration
- **View Calibration**: Track confidence vs success rates by domain
- **Gaps**: See where team is overconfident/underconfident
- **Trends**: Monitor improvement over time

### 🔍 Inline Features
- **Hover Context**: Hover over code to see decision context and warnings
- **Decorations**: Visual indicators for detected decision patterns and warnings
- **Syntax Highlighting**: Color-coded zones and pattern quality

## Installation

### Prerequisites
- VSCode 1.60 or later
- Node.js 14+
- Python 3.8+ (for Membria CLI)
- MCP Server running (see [Claude Integration](../docs/CLAUDE_INTEGRATION.md))

### Steps

1. Clone the repository:
```bash
cd vscode-extension
npm install
```

2. Install and start the MCP server:
```bash
# In membria-cli directory
pip install -e .
python src/membria/start_mcp_server.py
```

3. Build the extension:
```bash
npm run compile
```

4. Press `F5` to open the Debug session and test the extension

### Package for Distribution
```bash
npm install -g @vscode/vsce
vsce package
```

This creates a `.vsix` file you can share or publish to the VSCode Marketplace.

## Configuration

Add to `.vscode/settings.json`:

```json
{
  "membria.serverHost": "localhost",
  "membria.serverPort": 6379,
  "membria.autoValidatePlans": true,
  "membria.showHoverContext": true,
  "membria.showInlineWarnings": true
}
```

## Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| `membria.captureDecision` | `Ctrl+Shift+M D` | Capture a decision |
| `membria.getContext` | `Ctrl+Shift+M C` | Get decision context |
| `membria.validatePlan` | `Ctrl+Shift+M V` | Validate plan steps |
| `membria.showPlans` | `Ctrl+Shift+M P` | Show all plans |
| `membria.showSkills` | `Ctrl+Shift+M S` | Show all skills |
| `membria.generateSkill` | `Ctrl+Shift+M G` | Generate skill for domain |
| `membria.recordOutcome` | `Ctrl+Shift+M O` | Record decision outcome |
| `membria.viewCalibration` | `Ctrl+Shift+M B` | View team calibration |
| `membria.togglePanel` | `Ctrl+Shift+M T` | Toggle sidebar panel |

## Sidebar Views

### 📌 Decisions
Browse decisions organized by status and outcome type. Click to view details.

### 📊 Calibration
Team calibration metrics by domain showing:
- Success Rate: Historical success percentage
- Sample Size: Number of decisions observed
- Confidence Gap: Team calibration (overconfident/underconfident)
- Trend: Improving/Stable/Declining

### ⭐ Skills
Skills generated from outcomes and patterns. Shows:
- Skill ID and domain
- Quality Score: Evidence-based (success_rate × √sample_size / √n)
- Success Rate: Empirical success rate
- Zones: Green (>75%), Yellow (50-75%), Red (<50%)

### 📋 Plans
Team plans organized by status (Completed, In Progress, Pending). Shows:
- Plan ID and domain
- Step count and accuracy
- Last updated timestamp

## How It Works

### Decision Capture Flow
1. Run command: `membria.captureDecision`
2. Enter decision statement, alternatives, and confidence
3. Decision is sent to MCP server
4. Stored in FalkorDB with timestamp
5. Immediately appears in Decisions panel

### Plan Validation Flow
1. Run command: `membria.validatePlan`
2. Enter plan steps (one per line)
3. MCP server checks against:
   - Negative Knowledge (known failures)
   - AntiPatterns (common mistakes)
   - Past Failures (team history)
   - Calibration (confidence gaps)
4. Returns warnings with severity levels
5. Can proceed if no high-severity issues

### Skill Generation Flow
1. Sufficient outcomes collected in domain (≥30)
2. Patterns extracted from outcomes
3. Skill procedure generated with evidence
4. Quality score calculated: `success_rate × (1 - 1/√sample_size)`
5. Available via `membria.generateSkill` command

## Architecture

### Components
- **membriaClient.ts**: HTTP client to MCP server
- **providers/**: Tree data providers for sidebar views
- **hoverProvider.ts**: Hover context display
- **decorationProvider.ts**: Inline warnings and indicators
- **extension.ts**: Main activation and command registration

### Data Flow
```
VSCode Extension → MCP Server (HTTP) → FalkorDB
                                    ↓
                    CalibrationUpdater, PatternExtractor, SkillGenerator
```

## Troubleshooting

### MCP Server Connection Failed
- Check server is running: `python src/membria/start_mcp_server.py`
- Verify port matches settings (default: 6379)
- Check firewall if running on different machine

### No Skills Generated
- Need ≥30 outcomes per domain (sample size requirement)
- Run: `membria skills generate <domain>` via CLI
- Check calibration data exists for domain

### Hover Context Not Showing
- Enable in settings: `"membria.showHoverContext": true`
- Check server connectivity
- File must be Python/TypeScript/JavaScript

### Plan Validation Takes Too Long
- Server may be querying graph database
- First query is slower, subsequent queries are cached
- Adjust timeout in membriaClient.ts if needed

## Contributing

Contributions welcome! Areas for enhancement:
- Additional hover information (related decisions, evidence)
- Decision timeline visualization
- Skill comparison charts
- Integration with source control (git)
- Webview panels improvements

## License

MIT

## Related

- [Membria CLI](../README.md) - Command-line interface
- [Claude Integration](../docs/CLAUDE_INTEGRATION.md) - Claude Code integration
- [VSCode Tasks Integration](../docs/VSCODE_INTEGRATION.md) - Task automation
