# Plan Mode Integration - Phase 5 Complete

## Summary

Successfully integrated Plan Mode support into Membria's MCP Server. This addresses the critical blind spot where Membria had zero visibility during plan creation - the most important architectural decisions.

## Three Integration Points

### 1. PRE-PLAN: Context Injection (~1500 tokens)

**Tool:** `membria.get_plan_context`

Builds rich context BEFORE planning starts:

```python
result = get_plan_context({
    "domain": "auth",
    "scope": "JWT implementation with refresh tokens"
})
```

Returns:
- **past_plans**: Similar plans with outcomes (if available)
- **failed_approaches**: What didn't work in this domain
- **successful_patterns**: Proven patterns with usage counts
- **calibration**: Team bias data (confidence_gap, success_rate, trend)
- **constraints**: Project constraints (TypeScript, Docker, GitHub CI/CD)
- **recommendations**: Actionable guidance based on history
- **formatted**: Markdown-formatted context for Claude injection
- **total_tokens**: Token estimate for budget tracking

### 2. MID-PLAN: Plan Validation

**Tool:** `membria.validate_plan`

Scans each plan step for conflicts:

```python
result = validate_plan({
    "steps": [
        "Set up PostgreSQL database",
        "Create API endpoints",
        "Implement authentication"
    ],
    "domain": "database"
})
```

Checks each step against:
1. **NegativeKnowledge** (semantic similarity threshold 0.7)
   - Example: "Use custom JWT" → Known failures exist for this
2. **AntiPatterns** (regex pattern matching)
   - Example: Detects patterns with high failure rates
3. **Past Failures** (keyword similarity)
   - Example: Similar step failed before in the graph
4. **Calibration** (overconfidence detection)
   - Example: Team is overconfident by 15% in this domain

Returns:
- **warnings**: List of PlanWarning objects
- **can_proceed**: Boolean (False if any HIGH severity warnings)
- **high_severity**: Count of high severity warnings
- **medium_severity**: Count of medium severity warnings
- **low_severity**: Count of low severity warnings
- **total_steps**: Number of steps validated

### 3. POST-PLAN: Decision Capture

**Tool:** `membria.record_plan`

Captures architectural decisions from approved plan:

```python
result = record_plan({
    "plan_steps": [
        "Step 1: Set up database",
        "Step 2: Create API",
        "Step 3: Add authentication"
    ],
    "domain": "auth",
    "plan_confidence": 0.85,
    "duration_estimate": "3 hours",
    "warnings_shown": 2,
    "warnings_heeded": 1
})
```

Records:
- **engram_id**: Unique ID for this plan session
- **decisions_recorded**: List of decision IDs (one per step)
- **warnings_impact**: Tracks how many warnings influenced the plan
  - This feedback helps calibrate future suggestions

## Implementation

### Files Created

1. **plan_context_builder.py** (NEW)
   - `PlanContextBuilder` class
   - Builds ~1500 token context for planning phase
   - Queries past plans, failures, patterns, calibration from graph
   - Formats as markdown for Claude injection

2. **plan_validator.py** (NEW)
   - `PlanValidator` class
   - Validates plan steps against NK/AP/past failures
   - Detects overconfidence signals from CalibrationProfile
   - Returns PlanWarning objects with severity levels

### Files Modified

1. **mcp_server.py** (MODIFIED)
   - Added imports for plan_context_builder, plan_validator, GraphClient
   - Added three new MCP tools to MembriaToolHandler
   - Registered tools in MembriaMCPServer.tools dictionary
   - All existing tools still work (capture_decision, record_outcome, etc.)

## Test Coverage

### New Tests: 55 total

**test_plan_validator.py** (12 tests)
- Warning data model tests
- Plan validation tests (empty, single, multiple steps)
- Domain context tests
- Async validation tests
- Keyword extraction tests
- Severity sorting tests

**test_plan_context_builder.py** (13 tests)
- Builder initialization
- Context building for different domains
- Token estimation
- Markdown formatting
- Constraint retrieval
- Recommendation generation
- Max tokens handling

**test_mcp_plan_mode.py** (30 tests)
- Tool handler initialization
- Parameter validation (required fields, types)
- Tool response structures
- MCP server integration
- Request/response handling
- Backward compatibility with existing tools

### Total Tests: 348 (↑ from 293)

```
293 existing tests: ✅ PASSING
55 new tests:      ✅ PASSING
348 total:         ✅ PASSING
```

## Key Metrics

### Plan Mode Integration Completeness

- ✅ PRE-PLAN context injection (PlanContextBuilder)
- ✅ MID-PLAN validation (PlanValidator)
- ✅ POST-PLAN decision capture (MCP tool)
- ✅ Three MCP tools integrated and tested
- ✅ 348 tests passing (100%)
- ✅ No breaking changes to existing tools

### Token Budget

- Target: ~1500 tokens per context
- Respects max_tokens parameter
- Truncates least important sections if needed
- Estimates: ~4 chars per token

## Next Steps

**Phase 6: CLI Commands + Complete Skills Integration**

Remaining work:
- [ ] CLI commands for plan mode (`membria plans list`, `membria plans show`, etc.)
- [ ] CLI commands for skills (`membria skills generate`, `membria skills list`, etc.)
- [ ] Skill generation for all domains
- [ ] End-to-end integration tests

## Critical Insight

Before this integration, the decision flow was:

```
User → Claude (planning) → Code generation
                  ↑
         Membria has NO visibility here (blind spot!)
```

After Plan Mode integration:

```
User → Membria context injection (PRE-PLAN)
          ↓
       Claude (planning with rich context)
          ↓
       Membria validation (MID-PLAN)
          ↓
       Claude (refined plan)
          ↓
       Code generation
          ↓
       Membria records decisions (POST-PLAN)
```

This closes the critical gap and enables closed-loop learning from planning decisions.
