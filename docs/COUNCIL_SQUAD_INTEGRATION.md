# Multi-LLM Council ↔ Squad Integration

## Executive Summary

**Squad** and **Council** are complementary, not to be merged:

| Aspect | Council | Squad |
|--------|---------|-------|
| **What** | Orchestration modes (pipeline/debate/consensus/diamond) | Repeated team processes with presets |
| **Roles** | Hardcoded in code (9 roles) | Dynamic from FalkorDB (unlimited) |
| **Memory** | Stateless | Stores decisions in graph |
| **Use Case** | Ad-hoc brainstorming from shell | Repeatable processes (RCA, migrations, reviews) |
| **Scaling** | Limited by code changes | Scales via CLI (no code) |

## Architecture Decision

**Don't combine at code level.** Instead:
- Squad = main user-facing orchestration system
- Council = low-level executor that Squad uses internally
- ExpertRegistry = unified interface with graph fallback

## How ExpertRegistry Bridges Them

```
User calls Squad preset (e.g., incident-rca)
  ↓
Squad roles = ["investigator", "skeptic", "arbiter"]
  ↓
executor.run_task(task, role="investigator")
  ↓
ExpertRegistry.get_expert("investigator")
  → Check hardcoded EXPERTS dict
  → Check config.team.agents
  → Check FalkorDB graph ← NEW FALLBACK
  → Return expert config with system prompt
  ↓
AgentExecutor uses prompt for LLM call
```

## Squad Roles (FalkorDB-managed)

These roles are created via `squad role-set` and stored in graph:

- **incident-rca:** investigator, skeptic, arbiter
- **security-fix:** fixer, red_team
- **migration-plan:** migrator, ops, arbiter
- **api-contract:** backend, frontend
- **perf-regression:** perf, reviewer
- **release-gate:** release_manager, qa

**None of these are hardcoded.** They're defined in graph with `prompt_path` pointing to markdown files.

## Practical Workflow

```bash
# 1. Define prompt for new role
cat > ~/.membria/prompts/investigator.md << 'EOF'
You are an Incident Investigator...
EOF

# 2. Register in graph (one-time per project)
membria squad role-set investigator --prompt-path ~/.membria/prompts/investigator.md

# 3. Use in squad (multiple times)
membria squad create-from-preset incident-rca --project-id proj_123
membria squad run sqd_xxx --task "diagnose prod outage" --record-decisions

# Next time incident happens:
membria squad run sqd_xxx --task "diagnose new outage"
  → ExpertRegistry fetches "investigator" role from graph
  → Loads prompt from ~/.membria/prompts/investigator.md
  → AgentExecutor calls LLM with cached prompt
  → Decisions recorded to FalkorDB
  → Future RCAs use the same role definition + previous decision context
```

## Key Design Principles

1. **No hardcoded domain roles** — Only 9 generic roles in code (architect, implementer, etc.)
2. **Graph is source of truth for squad roles** — Managed via CLI, not code
3. **Fallback gracefully** — If role not in graph, use implementer as fallback
4. **Prompt-as-file** — Store role system prompts in markdown, load at runtime
5. **Context per role** — DocShots/Skills/NK linked per role in graph, injected at LLM call time

## Implementation Details

### ExpertRegistry Changes

**Before:**
```python
def get_expert(role):
    return EXPERTS.get(role, EXPERTS["implementer"])  # Only hardcoded roles
```

**After:**
```python
def get_expert(role):
    # 1. Check hardcoded EXPERTS
    default = EXPERTS.get(role, ...)

    # 2. Check config
    custom = _get_custom_experts()
    merged = {**default, **custom}

    # 3. NEW: Check graph for unknown roles
    if role not in EXPERTS:
        graph_role = _get_graph_role(role)
        if graph_role:
            merged["name"] = graph_role["name"]
            merged["description"] = graph_role["description"]
            if graph_role["prompt_path"]:
                merged["prompt"] = _load_prompt_from_path(graph_role["prompt_path"])

    return merged
```

### GraphClient Enhancement

**New method:**
```python
def get_role(self, role_name: str) -> Optional[Dict[str, Any]]:
    """Fetch role from graph with name, description, prompt_path."""
    # Parameterized query (safe from injection)
    # Returns role properties
```

## Migration Path: From Council to Squad

If you have ad-hoc Council debates today:

```bash
# Create squad preset from your debate workflow
membria squad create \
  --name "Architecture Decision" \
  --project-id proj_123 \
  --strategy lead_review \
  --role architect \
  --role reviewer \
  --profile default \
  --profile default

# Run it once
membria squad run sqd_xxx --task "Design new API" --record-decisions

# Reuse many times with context from previous decisions
membria squad run sqd_xxx --task "Design new endpoint"
```

Result: You now have repeatable, recorded, context-aware architecture reviews.

## Testing

Tests in `tests/test_expert_registry_graph_fallback.py` cover:
- Hardcoded roles work
- Graph fallback works
- Prompt loading from files
- Graceful fallback on graph connection failure
- Custom config overrides
