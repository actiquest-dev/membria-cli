# Claude Code + Membria Integration Examples

## Example 1: Get Calibration Data

**User:** "How confident is the team with database decisions?"

**Behind the Scenes:**
```python
Claude calls: membria.get_calibration("database")

Response:
{
  "domain": "database",
  "sample_size": 22,
  "success_rate": 0.89,
  "confidence_gap": 0.12,  # Team is 12% overconfident!
  "trend": "improving",
  "note": "Team is overconfident by 12% - Pad time estimates significantly"
}
```

**Claude Responds:**
```
Your team has made 22 database decisions with 89% success rate.
However, you're 12% overconfident - meaning you think decisions will
succeed more often than they actually do.

Recommendation: When estimating time for database work, add 15-20%
buffer to account for this bias.

Recent trend: Improving (getting better over time!)
```

---

## Example 2: Validate a Plan (Mid-Plan)

**User:** "I'm planning to: 1) Set up PostgreSQL 2) Add Prisma ORM 3) Run migrations"

**Behind the Scenes:**
```python
Claude calls: membria.validate_plan(
  steps=[
    "Set up PostgreSQL",
    "Add Prisma ORM",
    "Run migrations"
  ],
  domain="database"
)

Response:
{
  "total_steps": 3,
  "warnings_count": 1,
  "high_severity": 0,
  "medium_severity": 1,
  "can_proceed": true,
  "warnings": [
    {
      "step": 3,
      "type": "past_failure",
      "severity": "medium",
      "message": "Similar migration approach failed before",
      "suggestion": "Consider versioning and rollback strategy"
    }
  ]
}
```

**Claude Responds:**
```
Good plan! One thing to watch:

⚠️ MEDIUM: Step 3 (migrations) - Similar migration approach
   failed before. The team had issues with versioning.

   Suggestion: Make sure you have a clear migration strategy,
   including rollback procedures. Consider using Prisma's
   migration tooling which handles this well.

Overall: ✅ Can proceed with caution on migrations
```

---

## Example 3: Get Plan Context (Pre-Plan)

**User:** "Help me plan a complete authentication system"

**Behind the Scenes:**
```python
Claude calls: membria.get_plan_context(
  domain="auth",
  scope="JWT implementation with refresh tokens and rate limiting"
)

Response includes:
{
  "past_plans": [
    {
      "domain": "auth",
      "steps_count": 5,
      "duration_estimate": "3h",
      "actual_duration": "7h",
      "reworks": 2,
      "completion_rate": "100%"
    }
  ],
  "failed_approaches": [
    {
      "approach": "Custom JWT implementation",
      "failure_count": 2,
      "recommendation": "Use Auth0 or Passport-JWT instead"
    }
  ],
  "successful_patterns": [
    {
      "pattern": "Auth0 integration",
      "success_count": 12,
      "success_rate": 1.0
    },
    {
      "pattern": "JWT + Redis sessions",
      "success_count": 5,
      "success_rate": 0.88
    }
  ],
  "calibration": {
    "confidence_gap": 0.15,
    "note": "⚠️ OVERCONFIDENT by 15% - Add 20-25% buffer"
  }
}
```

**Claude Responds:**
```
# Auth System Plan

Based on team history, here's what I found:

## Past Experience
- Last auth plan: 5 steps, took 7 hours (estimated 3h)
- Team reworks: 2 times before getting it right
- Pattern: Team is 15% OVERCONFIDENT - tends to underestimate

## What Works Well ✅
- Auth0: 12 successful uses (100%)
- JWT + Redis: 5 successful uses (88%)

## What to Avoid ❌
- Custom JWT: Failed 2 times
- Recommendation: Use Auth0 or Passport-JWT

## My Plan (Informed by History)
1. Choose Auth0 (proven 12 times) - 30 min
2. Set up environment variables - 15 min
3. Create login/logout endpoints - 1.5 hours
4. Add token refresh - 1 hour (⚠️ past failure point)
5. Add rate limiting - 1 hour
6. Test and debug - 2 hours (⚠️ team underestimates this)

**Estimated Time: 6.5 hours** (padded 20% for overconfidence)
**High Risk Areas:** Token refresh, testing
```

---

## Example 4: Capture and Record Decision

**Day 1 - Capture:**
```
User: "I'm going to use Prisma ORM for the database layer"

Claude (internally):
  membria.capture_decision(
    statement="Use Prisma ORM",
    alternatives=["TypeORM", "Sequelize", "Raw SQL"],
    confidence=0.85,
    context={"module": "database"}
  )

  Returns: decision_id = "dec_a1b2c3d4..."
```

**Day 30 - Record Outcome:**
```
User: "Prisma worked great for our project"

Claude (internally):
  membria.record_outcome(
    decision_id="dec_a1b2c3d4...",
    final_status="success",
    final_score=0.95,
    decision_domain="database"
  )

  Calibration updated:
  - Database decisions: 23 samples
  - Success rate: 0.91
  - Team getting better!
```

---

## Example 5: Full Plan Mode Cycle (PRE → MID → POST)

### Step 1: PRE-PLAN - Get Context

```
User: "Let's plan the API layer"

Claude (internally):
  get_plan_context(domain="api", scope="REST API with OpenAPI")

  Returns: Rich context with past plans, failures, patterns, calibration
```

### Step 2: Generate Informed Plan

```
Claude: "Based on team history, here's the API plan:
1. Express.js setup - 30 min
2. OpenAPI/Swagger setup - 45 min
3. Error handling middleware - 1 hour
4. Rate limiting - 1 hour
5. Logging - 45 min

Estimated: 4 hours (padded for team overconfidence)

Wait, let me validate this plan..."
```

### Step 3: MID-PLAN - Validate Plan

```
Claude (internally):
  validate_plan(
    steps=["Express setup", "OpenAPI", "Error handling", ...],
    domain="api"
  )

  Returns: 1 medium warning about error handling
```

### Step 4: Refine Plan

```
Claude: "I found one concern: Error handling.
Let me adjust step 3 to use established libraries instead.

Final plan approved. Recording in Membria..."
```

### Step 5: POST-PLAN - Record Decisions

```
Claude (internally):
  record_plan(
    plan_steps=["Express setup", "OpenAPI", "Error handling", ...],
    domain="api",
    plan_confidence=0.88,
    duration_estimate="4 hours",
    warnings_shown=1,
    warnings_heeded=1
  )

  Returns: engram_id = "eng_xyz789..."
  All decisions captured and linked in graph
```

### Result: Full Closed-Loop Learning

```
├─ PRE-PLAN:  Rich context injected
├─ Generation: Informed by history
├─ MID-PLAN:  Validated against failures
├─ Refinement: Issues identified and fixed
└─ POST-PLAN: All decisions captured for future learning

Next API decision will benefit from THIS learning!
```

---

## Example 6: Continuous Improvement Loop

### Week 1
```
Decision 1: Use Auth0
  → Captured with 80% confidence
  → Outcome: SUCCESS

Decision 2: Use Prisma ORM
  → Captured with 75% confidence
  → Outcome: SUCCESS
```

### Week 2
```
Calibration Update:
  Database: 23 decisions, 91% success, 7% overconfident
  Auth: 25 decisions, 92% success, 5% overconfident

Claude notices: Team getting better at estimates!
```

### Week 3
```
Next database decision:
  Claude: "Based on team history..."
  (More accurate context, tighter estimates, aware of patterns)

Result: Better planning, better execution, less rework
```

---

## Example 7: Team Learning

### Scenario: Reduce Over-Confidence

**Day 1:**
```
Team estimates: Database setup = 2 hours
Actual time: 5 hours
Confidence gap recorded: +60% overconfident

Claude gets this signal!
```

**Day 8:**
```
Next database decision:
Claude: "Your team is typically 12% overconfident with database
         work. Estimate: 4 hours → I'd pad to 4h 45min

Result: More realistic planning
```

**Day 15:**
```
Decision outcome: Took exactly as estimated!
Calibration refined: Gap narrowing (60% → 55%)

System learning: Team self-corrects
```

---

## How to Use These Examples

1. **Copy patterns** to your own projects
2. **Adjust domains** (auth, database, api, cache, etc.)
3. **Let Claude learn** over time
4. **Watch team improve** as calibration refines
5. **Share results** - team gets smarter together

## Real Benefits After 30 Days

- ✅ More accurate time estimates (reduce overconfidence)
- ✅ Avoid known failure patterns (capture and learn)
- ✅ Reuse successful approaches (green zone)
- ✅ Better decisions (informed by 100+ past decisions)
- ✅ Less rework (validated plans before execution)
- ✅ Team knows what works (calibration shows it)

---

## Pro Tips

1. **Always capture** before implementing big decisions
2. **Record outcomes** within 30 days to update calibration
3. **Use Plan Mode** when tackling new domains
4. **Check warnings** - they come from real failures
5. **Trust green zones** - those patterns are proven
6. **Ask Claude** for context - it'll give you history
