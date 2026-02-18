# Membria Skills Architecture: Comprehensive Ecosystem Research

**Date:** February 12, 2026
**Author:** Claude Code Research
**Status:** Complete Analysis & Specifications

---

## EXECUTIVE SUMMARY

This research analyzes how LLM dev tools manage Claude's behavior across 8 different systems, then positions Membria's unique Skills architecture as the missing piece: a system that generates reusable procedures from lived experience, feeding them back to Claude through calibrated feedback loops.

**Key Finding:** Membria's differentiation is not in context injection (everyone does this) but in **Decision → Outcome → Calibration → Skills → Behavior**, a closed-loop learning system that turns team history into procedures.

---

# PART 1: ECOSYSTEM ANALYSIS - HOW TOOLS MANAGE CLAUDE

## 1. GSD (Get Shit Done)

### What It Does
Structural workflow framework for Claude Code that fights context rot through meta-prompting and phase-based planning.

### How It Manages Claude
- **Architecture:** Phase-based (DISCUSS → PLAN → EXECUTE → VERIFY)
- **Context Strategy:** CLAUDE.md files injected at project root + recursive discovery up to filesystem root
- **Knowledge Format:** Markdown specs, PLAN.md (phase design), STATE.md (audit trail), VERIFICATION.md (quality check)
- **Feedback Loop:** Manual verification step with human sign-off per phase

### Decision Capture
- User intent captured via interactive discussion phase
- Alternatives explored during planning phase
- Decisions not explicitly recorded—implicit in PLAN.md content

### Outcome Tracking
- VERIFICATION.md tracks success/failure
- No automated outcome signal ingestion
- Human decides when phase is "complete"

### How Feedback Reaches Claude
- Via VERIFICATION.md content injected into next phase context
- Essentially: human reads verification → updates PLAN.md → Claude sees it

### Knowledge Generation & Storage
- Knowledge stored as Markdown specs (human-written or AI-drafted)
- No automated skill generation from outcomes
- Team learns through documented patterns, not procedural extraction

### Strengths
- Phase-based structure prevents context rot
- Works well with existing Claude Code workflow
- Minimal disruption to human developer

### Weaknesses
- Requires manual verification (human bottleneck)
- No procedural knowledge extraction
- No quantified outcome metrics
- Can't auto-adjust based on historical success/failure patterns
- Decisions not structured for querying or aggregation

---

## 2. Aider (AI Pair Programming)

### What It Does
Terminal-based AI coding assistant that maintains a map of your repo and provides context-aware suggestions.

### How It Manages Claude
- **Architecture:** Repo map + conversation memory
- **Context Strategy:** Automatic code signature map of entire repository
- **Knowledge Format:** Implicit in the map—function signatures, file structure
- **Feedback Loop:** User approval/rejection of suggestions; LLM sees diffs and accepts/rejects based on feedback

### Decision Capture
- Implicit: when user asks "should we refactor X", Aider maintains context
- No formal decision recording

### Outcome Tracking
- Tracks: code changes (diffs)
- Does NOT track: whether the change worked, metrics, incidents

### How Feedback Reaches Claude
- Via git diffs shown in next conversation
- Claude Code sees: "I just created file X and it compiled"
- But not: "3 days later, this caused a bug in production"

### Knowledge Generation & Storage
- Knowledge implicit in repo map
- Re-generates the map each session (stateless)
- No long-term learning across projects

### Strengths
- Simple, effective context injection via code signatures
- Real-time feedback on compilation/syntax errors
- Works immediately without setup

### Weaknesses
- **Massive gap:** No connection between short-term code outcomes (does it compile?) and long-term quality (is it maintainable?)
- Stateless—can't learn from team patterns
- No decision tracking
- No calibration of developer confidence vs. actual success

---

## 3. Cursor IDE

### What It Does
VS Code fork with built-in LLM integration (Claude, GPT, etc.) as an IDE-first editing experience.

### How It Manages Claude
- **Architecture:** VS Code extension with LLM service layer
- **Context Strategy:** Hierarchical CLAUDE.md discovery (walks up from CWD to root), .cursorignore filtering
- **Knowledge Format:** CLAUDE.md (plain text rules, coding standards), project rules in Settings
- **Feedback Loop:** User approval of inline suggestions; visual diffs for manual review

### Decision Capture
- None. Cursor is transaction-based (suggestion → accept/reject)
- No temporal record of why a decision was made

### Outcome Tracking
- None explicit. Only: did the user accept the suggestion?
- No tracking of whether accepted code later caused issues

### How Feedback Reaches Claude
- Next suggestion uses: previous conversation context + updated CLAUDE.md
- But no quantified feedback ("this pattern failed 3 times in the past week")

### Knowledge Generation & Storage
- Static CLAUDE.md files (human-maintained)
- Pre-commit hooks available but no automatic skill generation

### Strengths
- IDE-first means context is naturally available
- CLAUDE.md is simple and intuitive
- Lifecycle hooks (PreToolUse, PostToolUse) enable deterministic automation

### Weaknesses
- CLAUDE.md is static—doesn't evolve from outcomes
- No temporal tracking of decisions
- Suggestions are ephemeral (no historical record)
- Cannot distinguish: "Cursor suggested this and it failed twice" from "Cursor suggested this and we never tried it"

---

## 4. Devin AI (Autonomous Agent)

### What It Does
Autonomous software engineer that maintains long-running context across multi-day tasks and learns from mistakes.

### How It Manages Claude
- **Architecture:** Continuous agent with memory, planning, and tool use (shell, editor, browser)
- **Context Strategy:** Long-term context window (maintains 1000s of decisions across days)
- **Knowledge Format:** Implicit in planner (mapping of task → steps), memory of failed attempts
- **Feedback Loop:** Real-time: tool execution → success/failure → plan adjustment

### Decision Capture
- Planner breaks tasks into steps with reasoning
- Records: "tried approach A → failed with error X → learned Y → trying approach B"

### Outcome Tracking
- Real-time: CI failures, runtime errors, test failures
- Long-term: task completion metrics
- Learning example: "First week saw errors; by end of week, error patterns recognized and avoided"

### How Feedback Reaches Claude
- Synchronous: tool fails immediately → error msg → planner adjusts
- Asynchronous: pattern recognition ("I've seen this error 3 times today")

### Knowledge Generation & Storage
- Implicit: Planner becomes better at task mapping
- No extraction of portable skills
- Knowledge trapped in Devin's session—not reusable by other agents or humans

### Strengths
- **Best-in-class** real-time feedback loop
- Learns within a session (error pattern recognition)
- Maintains context across 1000s of decisions
- Compounding advantage: sees examples → avoids rabbit holes

### Weaknesses
- Learning is session-local (not persistent across projects)
- **Critical gap:** No way to extract lessons as reusable procedures
- Can't share what it learned with other agents or team members
- No calibration—confidence not adjusted based on outcomes

---

## 5. Continue.dev (IDE Extension)

### What It Does
VS Code extension for local or cloud LLM integration with pluggable context providers.

### How It Manages Claude
- **Architecture:** LLM abstraction layer + context provider ecosystem
- **Context Strategy:** Pluggable context sources (documentation, Git commits, Discord channels, custom integrations)
- **Knowledge Format:** YAML/JSON config (context_providers section defines sources)
- **Feedback Loop:** User chat feedback injected into next prompt

### Decision Capture
- Implicit in chat history
- Can link to GitHub issues/commits

### Outcome Tracking
- Limited. Tracks: chat → code changes
- Optional: integration with documentation sites

### How Feedback Reaches Claude
- Via context providers that pull fresh data
- Example: "User feedback → stored in Discord → Continue pulls → LLM sees in next session"

### Knowledge Generation & Storage
- Knowledge in config YAML (static)
- Context providers are programmatic (can fetch fresh data)
- No automatic skill extraction

### Strengths
- Extensible context provider model
- Supports local/private LLMs
- Config-driven (version-controllable)

### Weaknesses
- Still manual configuration (requires engineer to think about what context matters)
- No automatic learning from outcomes
- Context providers are pre-defined—can't generate new providers from experience
- No temporal tracking of decisions

---

## 6. GitHub Copilot Ecosystem

### What It Does
Integrated LLM assistant across GitHub, IDE, CLI with context routing and model selection.

### How It Manages Claude
- **Architecture:** Model routing engine + context window management
- **Context Strategy:** Repository custom instructions (.github/copilot-instructions.md), @workspace/@project participants, file links
- **Knowledge Format:** Markdown instructions (static)
- **Feedback Loop:** Model selection (user can pick different model per conversation)

### Decision Capture
- None explicit

### Outcome Tracking
- Limited. GitHub has data (PR metrics, review comments) but Copilot doesn't consume it for learning

### How Feedback Reaches Claude
- Via PR review comments in next session
- Via model switching (human decides "this task needs GPT-5, not Sonnet")

### Knowledge Generation & Storage
- Static .github/copilot-instructions.md
- Organization-level knowledge bases (GitHub-hosted docs)
- No automatic learning from PR/issue outcomes

### Strengths
- Native integration with GitHub (where all historical data lives)
- Model routing (human chooses right tool)
- Instruction file is discoverable and version-controlled

### Weaknesses
- **Tragic disconnect:** GitHub has 3+ years of PR/issue/review history, but Copilot can't access it for learning
- No automated feedback from PR metrics → prompt adjustment
- Static instructions don't evolve
- No calibration mechanism

---

## 7. LangGraph (Agent Framework)

### What It Does
Production orchestration framework for multi-agent workflows with persistent state and time-travel debugging.

### How It Manages Claude
- **Architecture:** Graph nodes + state objects + persistence layer
- **Context Strategy:** State accumulation (grows as it flows through nodes)
- **Knowledge Format:** Graph structure (nodes define behavior)
- **Feedback Loop:** Real-time node execution → state update → next node uses updated state

### Decision Capture
- Implicit in state object
- Can be serialized for replay

### Outcome Tracking
- Excellent: Every node writes success/failure to state
- Can checkpoint and resume from any point

### How Feedback Reaches Claude
- Via state object (contains all decisions + outcomes so far)
- Time-travel: can replay from checkpoint with modified decisions

### Knowledge Generation & Storage
- Knowledge implicit in graph structure
- Can be exported as graph definition (YAML/JSON)
- No skill generation—graph structure is hand-coded

### Strengths
- **Best production system:** Persistent state, checkpointing, time-travel debugging
- Excellent for complex, long-running tasks
- State is queryable and loggable

### Weaknesses
- Requires explicit graph design (not generative)
- No automatic skill extraction from outcomes
- Knowledge is in graph topology, not in portable procedures
- No calibration

---

## 8. MCP (Model Context Protocol)

### What It Does
Open protocol for connecting LLMs to external tools, data sources, and services.

### How It Manages Claude
- **Architecture:** Standardized server/client protocol
- **Context Strategy:** Tools/resources/prompts streamed to LLM from MCP servers
- **Knowledge Format:** Tool definitions (capabilities, schema), prompt templates
- **Feedback Loop:** MCP servers can request LLM sampling (server asks LLM for context generation)

### Decision Capture
- Implicit in tool use (which tools called, in what order)

### Outcome Tracking
- Limited. Tool calls are logged but not connected to outcomes

### How Feedback Reaches Claude
- Via prompt templates (static)
- Via Sampling: MCP server can ask Claude to generate context on-demand

### Knowledge Generation & Storage
- Tools are pre-defined in MCP manifest
- No skill generation
- Prompts are static (though servers can generate them dynamically)

### Strengths
- Standardized, composable (tools from different vendors work together)
- Sampling feature enables bidirectional communication
- Emerging ecosystem (many servers being built)

### Weaknesses
- Still early (skills architecture not yet standardized)
- No automatic skill generation
- No feedback loop from tool outcomes to prompt adjustment
- Tool catalog is static (can't generate new tools from experience)

---

# PART 2: COMPARISON TABLE

| Tool | Context Injection | Decision Capture | Outcome Tracking | Feedback to Claude | Skill Generation | Learning | Calibration |
|------|------------------|------------------|------------------|--------------------|------------------|----------|------------|
| **GSD** | CLAUDE.md (static) | Implicit (PLAN.md) | Manual verification | Via PLAN.md edit | None | Manual | None |
| **Aider** | Repo map (auto) | None | Implicit (diffs) | Via git context | None | Per-session only | None |
| **Cursor** | CLAUDE.md (static) | None | Implicit (accept/reject) | Via CLAUDE.md | None | None | None |
| **Devin** | Long-term memory | Implicit (planner) | Real-time (errors) | Via planner adjustment | None (session-local) | Within session | None |
| **Continue** | Context providers | Implicit (chat) | Limited | Via providers | None | None | None |
| **Copilot** | Instructions (static) | None | Implicit (PR metrics unused) | Static instructions | None | None | None |
| **LangGraph** | State object | State snapshots | State-tracked | Via state updates | None (graph-coded) | None | None |
| **MCP** | Tool definitions | Tool calls | Limited | Prompt templates | None | None | None |
| **Membria** | Context injection | Decision nodes | Signal-based | Calibration loop | **YES - procedural** | **Yes - continuous** | **Yes - Beta distribution** |

---

# PART 3: MEMBRIA'S UNIQUE POSITION

## What's Missing Across All 8 Tools

Every tool above does ONE of these well:
- Context injection (GSD, Cursor, Copilot, Continue, MCP)
- Real-time feedback (Devin, LangGraph)
- Long-term memory (Devin)
- Outcome tracking (LangGraph)

**But NONE do the complete loop:**

```
Decision → Outcome Signal → Calibration → Skill Generation → Claude Behavior Adjustment
```

## Membria's Differentiation

### 1. Structured Decision Capture (Already Implemented)
Membria records decisions with:
- Statement + alternatives + assumptions + predicted_outcome
- Context hash (immutable record of what was known)
- Decision ID for tracking

**How it's different:**
- Other tools: decisions are implicit (in chat, in PLAN.md, in code)
- Membria: decisions are first-class nodes in the graph

### 2. Multi-Signal Outcome Tracking (Already Implemented)
Membria captures signals from:
- PR lifecycle (created → merged)
- CI/test results (passing/failing)
- Runtime events (incidents, performance)
- Manual feedback (30-day review)

**How it's different:**
- Aider: only sees immediate diffs
- Devin: only sees immediate errors
- Copilot: ignores PR metrics entirely
- Membria: connects decision → code → CI → production → incident

### 3. Calibration Loop (Already Implemented)
Membria uses Beta distributions to track:
- Decision success rate per domain
- Confidence gap (am I too confident or too uncertain?)
- Confidence adjustment recommendations

**How it's different:**
- No other tool adjusts their own confidence based on outcomes
- Membria: when you say "90% confident" but only succeed 60% of the time, Membria tells you to lower your confidence to 75%

### 4. Skill Generation from Experience (DESIGNED, NOT YET BUILT)
Membria will generate reusable procedures:
- From patterns in outcomes (e.g., "When architecture decision involves HTTP server, Fastify has succeeded 85% of the time")
- From negative knowledge (e.g., "Custom JWT implementations have failed 8 times; use Auth0")
- From decision reworks (e.g., "Task X requires Y pre-decision; we did 5 reworks before learning this")

**How it's different:**
- Devin learns within a session but doesn't export
- GSD stores knowledge as static specs
- Membria: auto-generates procedures from outcomes and feeds them back to Claude

### 5. Feedback Pipeline to Claude Management (DESIGNED, PARTIALLY BUILT)
Membria feeds back to Claude Code via:
- MCP context injection (decision history)
- Negative knowledge blocks (do NOT do X)
- Confidence-adjusted suggestions (be cautious with Y, be bold with Z)
- Skills/procedures (here's the 15-step procedure for Z based on our experience)

**How it's different:**
- GSD: requires manual PLAN.md updates
- Cursor: static CLAUDE.md
- Copilot: ignores all outcomes
- Membria: automatically calibrated feedback based on team history

---

# PART 4: MEMBRIA SKILLS ARCHITECTURE

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MEMBRIA FULL PIPELINE                         │
└─────────────────────────────────────────────────────────────────────┘

PHASE 1: DECISION & CONTEXT INJECTION
  ┌──────────────────────────────────────────────────────────┐
  │ Developer makes decision in Claude Code / IDE             │
  │                                                           │
  │ MCP Daemon intercepts:                                   │
  │ • Decision intent detection (decision vs tactical)       │
  │ • Context injection from Reasoning Graph:               │
  │   - Similar past decisions (vector search)              │
  │   - Antipatterns that triggered before (Engrams)       │
  │   - Team calibration scores for this domain            │
  │   - Negative knowledge blocks                           │
  │                                                           │
  │ Claude Code receives injected context:                  │
  │ "You're choosing an auth strategy. Your team has been  │
  │  60% successful with Auth0 (9/15 times). Custom JWT    │
  │  has failed 80% (8/10 times). Recommend Auth0."        │
  └──────────────────────────────────────────────────────────┘
                           ↓
PHASE 2: DECISION CAPTURE
  ┌──────────────────────────────────────────────────────────┐
  │ Decision made: "Use Auth0"                               │
  │                                                           │
  │ DecisionCapture records:                                │
  │ • Statement: "Implement OAuth 2.0 with Auth0"          │
  │ • Alternatives: Custom JWT, Firebase Auth, Keycloak    │
  │ • Assumptions: Auth0 free tier sufficient               │
  │ • Predicted outcome: "Production auth in 1 week"        │
  │ • Confidence: 0.85 (adjusted from team calibration)    │
  │ • Context hash: sha256(decision_state)                 │
  │                                                           │
  │ Stored in FalkorDB as Decision node                    │
  └──────────────────────────────────────────────────────────┘
                           ↓
PHASE 3: OUTCOME SIGNALS (30-day observation window)
  ┌──────────────────────────────────────────────────────────┐
  │ Real-world events are captured as Signals:              │
  │                                                           │
  │ T+0:   PR_CREATED (decision → code)                     │
  │ T+1:   CI_PASSED (compiles, tests pass)                 │
  │ T+2:   PR_MERGED (approved)                             │
  │ T+3:   PERFORMANCE_OK (latency 45ms vs 100ms assumed)   │
  │ T+8:   STABILITY_OK (no errors in 1 week)              │
  │ T+30:  OUTCOME_COMPLETE (success | partial | failure)   │
  │                                                           │
  │ Signals stored in FalkorDB as Signal nodes              │
  │ Outcome node aggregates all signals + metrics           │
  │                                                           │
  │ Final metrics:                                           │
  │ • Time to production: 2 days (vs 7 predicted)           │
  │ • P99 latency: 45ms (vs 100ms predicted)                │
  │ • Uptime: 99.98% (vs 99.9% assumed)                    │
  │ • Bug count: 1 (vs 0 assumed)                           │
  │ • Incidents: 0                                           │
  └──────────────────────────────────────────────────────────┘
                           ↓
PHASE 4: CALIBRATION UPDATE
  ┌──────────────────────────────────────────────────────────┐
  │ CalibrationUpdater processes outcome:                   │
  │                                                           │
  │ Decision: "Use Auth0"                                   │
  │ Confidence: 0.85                                        │
  │ Outcome: SUCCESS                                        │
  │ Domain: auth_strategy                                   │
  │                                                           │
  │ Update Beta distribution:                               │
  │ • Previous: Beta(α=7, β=2) [mean=0.78]                │
  │ • Signal: SUCCESS → α += 1                              │
  │ • New: Beta(α=8, β=2) [mean=0.80]                      │
  │                                                           │
  │ Calculate confidence gap:                               │
  │ • Predicted: 0.85                                       │
  │ • Actual: 1.0 (success)                                │
  │ • Gap: +0.15 (slightly underconfident)                 │
  │                                                           │
  │ Update calibration:                                     │
  │ • Trend: improving (8 successes in last 10)            │
  │ • Recommendation: confidence can increase to 0.90      │
  └──────────────────────────────────────────────────────────┘
                           ↓
PHASE 5: SKILL GENERATION
  ┌──────────────────────────────────────────────────────────┐
  │ SkillGenerator looks at patterns across domain:         │
  │                                                           │
  │ Query Reasoning Graph:                                 │
  │ MATCH (d:Decision)-[:RESULTED_IN]->(o:Outcome)        │
  │ WHERE d.statement CONTAINS "auth_strategy"             │
  │ AND o.final_status IN ["success", "failure"]          │
  │ RETURN d.statement, o.final_status, d.confidence      │
  │                                                           │
  │ Results:                                                │
  │ • Auth0 approach: 8 successes / 9 attempts (89%)       │
  │ • Custom JWT: 2 successes / 10 attempts (20%)          │
  │ • Firebase Auth: 7 successes / 8 attempts (87%)        │
  │                                                           │
  │ Generate Skill:                                         │
  │ ┌──────────────────────────────────────┐              │
  │ │ SKILL: auth_strategy_recommendation   │              │
  │ ├──────────────────────────────────────┤              │
  │ │ Domain: authentication                │              │
  │ │ Success Rate: 88% (8 successes/9)    │              │
  │ │ Confidence: 0.88                      │              │
  │ │ Sample Size: 9 decisions              │              │
  │ │                                      │              │
  │ │ PROCEDURE:                           │              │
  │ │ IF need_auth_strategy THEN:          │              │
  │ │   PREFER Auth0 (89% success)         │              │
  │ │   AVOID Custom JWT (20% success)     │              │
  │ │   CONSIDER Firebase Auth (87%)       │              │
  │ │                                      │              │
  │ │ REASONING:                           │              │
  │ │ - Auth0 scaled well in production    │              │
  │ │ - Custom JWT had 8 failures:         │              │
  │ │   * 4: token refresh issues          │              │
  │ │   * 3: scope management problems     │              │
  │ │   * 1: performance degradation       │              │
  │ │ - Firebase Auth simpler but not     │              │
  │ │   flexible enough for custom scopes │              │
  │ │                                      │              │
  │ │ WHEN APPLY:                          │              │
  │ │ - Green: Apply when confidence      │              │
  │ │   requirements are low/medium       │              │
  │ │ - Yellow: Review if custom scopes   │              │
  │ │   needed (Firebase limitation)      │              │
  │ │ - Red: BLOCK custom JWT until      │              │
  │ │   issues from past failures solved  │              │
  │ └──────────────────────────────────────┘              │
  │                                                         │
  │ Skill stored in FalkorDB + exported to Skills DB      │
  └──────────────────────────────────────────────────────────┘
                           ↓
PHASE 6: FEEDBACK TO CLAUDE
  ┌──────────────────────────────────────────────────────────┐
  │ When new developer makes decision in Claude Code:       │
  │                                                           │
  │ MCP Context Injector fetches:                          │
  │ • Skill: auth_strategy_recommendation                  │
  │ • Current calibration for auth_strategy domain         │
  │ • Similar past decisions with outcomes                 │
  │                                                           │
  │ Prompts Claude:                                        │
  │                                                           │
  │ "SKILL AVAILABLE: auth_strategy_recommendation         │
  │                                                           │
  │  Your team's experience (9 decisions, 30 days tracking):│
  │  - Auth0: 89% success (8/9)                            │
  │  - Custom JWT: 20% success (2/10)                      │
  │  - Firebase Auth: 87% success (7/8)                    │
  │                                                           │
  │  TEAM CONFIDENCE CALIBRATION:                          │
  │  For auth_strategy decisions:                          │
  │  - Your team is typically 78% confident               │
  │  - Your team achieves 80% success                      │
  │  - Gap: -2% (slightly underconfident, that's good!)   │
  │                                                           │
  │  NEGATIVE KNOWLEDGE:                                   │
  │  - Custom JWT failed 8 times:                          │
  │    * Token refresh issues (4x)                         │
  │    * Scope management (3x)                             │
  │    * Performance (1x)                                  │
  │                                                           │
  │  RECOMMENDATION:                                       │
  │  IF your use case matches past scenarios:             │
  │    STRONGLY RECOMMEND Auth0 (89% team success)        │
  │    AVOID Custom JWT (flagged by negative knowledge)   │
  │    CONSIDER Firebase Auth if simpler scope needed     │
  │                                                           │
  │  If you proceed with Custom JWT despite warnings:     │
  │  - Your confidence will be reduced to 0.65            │
  │  - You may need lead approval                         │
  │  - Document assumptions (could become future lesson)  │
  │ "                                                       │
  │                                                         │
  │ Claude Code now makes auth decision with:             │
  │ • Team's lived experience                            │
  │ • Calibrated confidence levels                       │
  │ • Negative knowledge warnings                        │
  │ • Procedural guidance (the skill)                    │
  └──────────────────────────────────────────────────────────┘
```

---

## Core Data Structures

### Decision Node
```
Decision:
  decision_id: str
  statement: str                    # "Use Auth0 for OAuth"
  alternatives: List[str]          # ["Custom JWT", "Firebase Auth", "Keycloak"]
  alternatives_with_reasons: Dict  # {"Custom JWT": "Faster to code but complex to maintain"}
  assumptions: List[str]           # ["Auth0 free tier sufficient", "Latency < 100ms acceptable"]
  predicted_outcome: Dict          # {"timeline": "1 week", "success_criteria": ["Prod auth", "No major bugs"]}

  # Metadata
  confidence: float                # 0.0-1.0 (calibrated from team history)
  context_hash: str                # immutable hash of decision state
  created_at: datetime
  created_by: str
  domain: str                       # "auth_strategy" for querying

  # Status
  status: str                       # "pending" → "executed" → "completed"
  linked_pr: str                    # GitHub PR URL
  linked_commit: str                # Git commit SHA
```

### Outcome Node
```
Outcome:
  outcome_id: str
  decision_id: str                 # Link back to decision

  # Timeline
  status: str                       # "pending" → "merged" → "completed" → "failed"
  created_at: datetime
  submitted_at: datetime            # PR created
  merged_at: datetime               # PR merged
  completed_at: datetime            # 30 days after merge

  # Signals
  signals: List[Signal]            # Each event during observation window
    - Signal:
        type: str                    # "PR_CREATED", "CI_PASSED", "INCIDENT"
        valence: str                 # "positive", "negative", "neutral"
        timestamp: datetime
        description: str             # "PR #123 merged"
        severity: str                # For negative: "low", "medium", "high"
        metrics: Dict                # {"latency_ms": 45, "uptime": 99.98}

  # Final evaluation
  final_status: str                 # "success", "partial", "failure"
  final_score: float                # 0.0-1.0 aggregate
  lessons_learned: List[str]        # ["Auth0 scaled better than expected", "UX issues from scope changes"]

  # Measured metrics
  metrics: Dict                      # {"p99_latency": 45, "uptime": 99.98, "bugs": 1, "incidents": 0}
```

### Calibration Profile
```
CalibrationProfile:
  domain: str                       # "auth_strategy", "db_migration", etc.

  # Beta distribution for Bayesian calibration
  distribution: BetaDistribution
    - alpha: float                   # Successes + prior
    - beta: float                    # Failures + prior
    - mean: float                    # α/(α+β) = success rate
    - variance: float                # distribution spread
    - sample_size: int               # total decisions observed
    - confidence_interval: (lower, upper)  # 95% credible interval

  # Calibration gap
  confidence_gap: float              # avg_predicted_confidence - actual_success_rate
  trend: str                         # "improving", "stable", "declining"
  recommendations: List[str]         # ["Reduce confidence for X", "Team is good at Y"]
  last_evaluation: datetime
```

### Skill (Generated from Patterns)
```
Skill:
  skill_id: str
  domain: str                       # "auth_strategy"
  name: str                         # "auth_strategy_recommendation"
  version: int                       # Updated as new data arrives

  # Evidence
  success_rate: float               # 0.89 (8 successes / 9 total)
  confidence: float                 # 0.88 (derived from Beta distribution)
  sample_size: int                  # 9 decisions
  last_updated: datetime

  # Decision procedure
  procedure: str                    # Structured steps (Markdown)
    "IF choosing auth strategy:
       STRONGLY_PREFER Auth0 (89% success)
       AVOID Custom JWT (20% success)
       CONSIDER Firebase Auth (87%)"

  # Negative knowledge
  antipatterns: List[Dict]          # What failed and why
    - pattern: "Custom JWT for OAuth"
      failure_rate: 0.80            # 8 failures / 10 attempts
      root_causes:
        - "Token refresh edge cases" (4 instances)
        - "Scope management complexity" (3 instances)
        - "Performance degradation under load" (1 instance)
      recommendation: "BLOCK unless all issues addressed in code review"

  # When to apply
  applicability: Dict               # Green/Yellow/Red zones
    green:
      - "Standard OAuth 2.0 flows"
      - "Team familiar with Auth0"
      confidence: 0.89
    yellow:
      - "Custom scopes needed"
      - "Complex multi-tenant requirements"
      confidence: 0.72
    red:
      - "Custom JWT implementation"
      - "Without addressing past failures"
      confidence: 0.00  # Block

  # Traceability
  generated_from: List[str]         # Decision IDs that led to this skill
  conflicts_with: List[str]         # Contradictory skills
  related_skills: List[str]         # Complementary skills
```

---

## System Components

### 1. Decision Surface
**Purpose:** Show developer what context was injected and why

**Input:** Decision intent + Reasoning Graph

**Output:** Structured context card with:
- Similar past decisions (+ outcomes)
- Team calibration score (confidence guidance)
- Antipatterns that triggered (negative knowledge)
- Applicable skills

**Example Output:**
```
┌─────────────────────────────────────────────────────────┐
│ DECISION CONTEXT: "Implement authentication"            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ TEAM EXPERIENCE (9 auth decisions, 30 days tracking):  │
│ ├─ Auth0: 89% success (8/9)                            │
│ ├─ Custom JWT: 20% success (2/10)                      │
│ └─ Firebase Auth: 87% success (7/8)                    │
│                                                         │
│ YOUR CONFIDENCE CALIBRATION:                           │
│ ├─ Team avg confidence: 78%                            │
│ ├─ Team actual success: 80%                            │
│ └─ Gap: -2% (good! you're slightly cautious)          │
│                                                         │
│ 🚫 NEGATIVE KNOWLEDGE (Custom JWT):                   │
│ ├─ Failed 8/10 times                                  │
│ ├─ Common failures:                                   │
│ │  • Token refresh issues (40%)                       │
│ │  • Scope management (30%)                           │
│ │  • Performance (10%)                                │
│ └─ Recommendation: BLOCK without mitigation plan      │
│                                                         │
│ 💡 RECOMMENDED SKILL:                                 │
│ └─ auth_strategy_recommendation (88% success)         │
│                                                         │
│ 📋 SIMILAR DECISIONS:                                 │
│ ├─ Decision D-001: "Use Auth0 for SPA" → SUCCESS     │
│ ├─ Decision D-005: "Custom JWT for mobile" → FAILED  │
│ └─ Decision D-012: "Firebase Auth for admin" → SUCCESS│
│                                                         │
│ ⚖️ DECISION FIREWALL LEVEL: [WARN] Can override     │
└─────────────────────────────────────────────────────────┘
```

### 2. Outcome Tracker
**Purpose:** Capture signals from real-world execution

**Inputs:**
- Webhook from GitHub (PR created, merged, code review)
- CI/CD pipeline (test results, build failures)
- Monitoring systems (incidents, performance metrics)
- Manual review (after 30 days)

**Outputs:**
- Signal nodes in Reasoning Graph
- Outcome aggregation (success/partial/failure)
- Lessons learned extraction

**Implementation:**
- `outcome_tracker.py` - Core logic
- `webhook_handler.py` - GitHub/CI integration
- `outcome_models.py` - Data structures

### 3. Calibration Updater
**Purpose:** Learn team confidence patterns

**Process:**
1. For each completed outcome:
   - Extract decision confidence
   - Compare to actual success (1.0 if success, 0.0 if failure)
   - Update Beta distribution for domain
2. Calculate confidence gap (predicted - actual)
3. Generate recommendations

**Output:** CalibrationProfile with trend analysis

**Example:**
```
Domain: auth_strategy
Sample size: 9
Success rate: 80%
Confidence gap: -2% (team is slightly underconfident)
Trend: improving (last 3 decisions all succeeded)
Recommendations:
  - "Team is well-calibrated for this domain"
  - "Can increase confidence from 78% to 82%"
  - "Especially good at evaluating auth0 vs custom JWT tradeoff"
```

### 4. Skill Generator
**Purpose:** Extract procedural knowledge from patterns

**Triggers:**
- After every 5 outcomes in a domain (incremental)
- Once per week (batch processing)
- Manual request

**Process:**
1. Query all decisions in domain with outcomes
2. Group by decision type (e.g., "choosing auth strategy")
3. Calculate success rates for each alternative
4. Extract failure patterns (root causes)
5. Generate decision procedure (if/then rules)
6. Mark antip

atterns (high-failure alternatives)

**Output:** Skill node + exported to Skills registry

**Example Skill Generation:**
```python
# Query: All auth_strategy decisions
MATCH (d:Decision)-[:RESULTED_IN]->(o:Outcome)
WHERE d.domain = "auth_strategy"
AND o.final_status IN ["success", "failure"]
RETURN d.statement, o.final_status, d.created_at

# Results analysis:
{
  "Auth0": {"success": 8, "total": 9, "rate": 0.89},
  "Custom JWT": {"success": 2, "total": 10, "rate": 0.20},
  "Firebase Auth": {"success": 7, "total": 8, "rate": 0.87}
}

# Generate skill:
Skill(
  domain="auth_strategy",
  success_rate=0.88,  # Average across all auth decisions
  procedure="""
  IF need_auth_strategy THEN:
    IF simple_oauth_flow:
      STRONGLY_RECOMMEND Auth0 (89% success)
    ELIF custom_scopes_needed:
      CONSIDER Firebase Auth (87% success)
    ELSE:
      AVOID Custom JWT (20% success)
  """,
  antipatterns=[
    {
      "pattern": "Custom JWT",
      "failure_rate": 0.80,
      "root_causes": ["token refresh", "scope mgmt", "perf"]
    }
  ]
)
```

### 5. Context Injector (MCP Integration)
**Purpose:** Feed skills and calibration back to Claude

**Triggered:** When new decision is being made

**Process:**
1. Detect decision intent (Task Router)
2. Query Reasoning Graph for:
   - Applicable skills
   - Team calibration score
   - Similar past decisions
   - Negative knowledge warnings
3. Construct context injection
4. Stream to Claude Code via MCP

**Example Injection:**
```
MEMBRIA_CONTEXT = {
  "decision_intent": "Implement authentication",
  "skills": [
    {
      "skill_id": "auth_strategy_recommendation",
      "success_rate": 0.88,
      "procedure": "IF simple_oauth: USE Auth0...",
      "confidence": 0.88
    }
  ],
  "calibration": {
    "domain": "auth_strategy",
    "team_success_rate": 0.80,
    "team_confidence": 0.78,
    "gap": -0.02,
    "adjustment": "Team is well-calibrated; confidence okay at 0.78-0.82"
  },
  "negative_knowledge": [
    {
      "pattern": "Custom JWT for OAuth",
      "failed": 8,
      "total": 10,
      "firewall_level": "BLOCK",
      "reason": "Token refresh and scope management issues in past 8 attempts"
    }
  ],
  "similar_decisions": [
    {
      "decision_id": "D-001",
      "statement": "Use Auth0 for SPA",
      "outcome": "SUCCESS",
      "time_to_prod": "2 days",
      "uptime_30d": "99.98%"
    }
  ]
}
```

---

## Integration with Claude Code

### MCP Server Implementation
```
MCP Server (Membria MCP Daemon)
├── /resources
│   ├── decision_history: Lists all decisions with outcomes
│   ├── team_calibration: Beta distribution profiles
│   ├── antipatterns: Negative knowledge database
│   └── skills: Generated procedural knowledge
│
├── /prompts
│   ├── decision_context: "Here's what your team experienced..."
│   ├── skill_application: "Apply skill X because..."
│   └── confidence_guidance: "Your team's calibration shows..."
│
└── /tools
    ├── record_decision: Capture new decision
    ├── lookup_similar: Find past decisions in domain
    └── query_skills: Find applicable skills
```

### Lifecycle
1. **Developer types decision intent** in Claude Code
2. **Task Router detects** it's a DECISION task (not tactical)
3. **MCP daemon fetches context**:
   - Query Reasoning Graph for domain
   - Get applicable skills
   - Get calibration profile
   - Get antipatterns
4. **Context injected as MCP resources**
5. **Claude Code sees**:
   ```
   You're implementing authentication.
   Your team's 9 auth decisions succeeded 80% of the time.
   Recommended skill: auth_strategy_recommendation (88% success)

   Based on team experience:
   - Auth0: 89% success (8/9)
   - Custom JWT: 20% success (2/10)  [⚠️ AVOID]
   - Firebase Auth: 87% success (7/8)
   ```
6. **Claude makes decision** with team context
7. **Decision captured** in graph
8. **Outcome signals** captured over 30 days
9. **Calibration updated**
10. **Skills regenerated** incrementally
11. **Loop continues** for next developer

---

## Comparison: Before vs After Membria Skills

### Before (Current Dev Practice)
```
Developer needs auth strategy
  ↓
Searches GitHub issues/PRs for auth discussion
  ↓
Finds scattered context ("we used Auth0 once", "custom JWT failed")
  ↓
Asks team lead (bottleneck)
  ↓
Makes decision (maybe 70% informed)
  ↓
Codes, ships, observes
  ↓
If it fails, learns the hard way
  ↓
Knowledge lost when developer leaves
```

**Problems:**
- Inefficient (manual research)
- Incomplete (can't find all past decisions)
- Unquantified (no success rates)
- Non-transferable (knowledge not codified)

### After (Membria Skills)
```
Developer needs auth strategy
  ↓
MCP daemon auto-detects decision intent
  ↓
Claude Code receives context:
  "Your team succeeded 80% of the time with auth decisions.
   Skill: auth_strategy_recommendation (88% success).
   Auth0: 89% success (8/9)
   Custom JWT: 20% success (2/10) [⚠️ AVOID]
   Firefox Auth: 87% success (7/8)"
  ↓
Claude makes informed decision (90%+ accuracy)
  ↓
Decision captured + outcomes tracked
  ↓
If fails, becomes input to skill refinement
  ↓
Skills auto-improve as more data arrives
  ↓
Knowledge persists and transfers to new team members
```

**Benefits:**
- Efficient (automatic injection)
- Complete (all past decisions queryable)
- Quantified (success rates + confidence intervals)
- Transferable (skills are procedures)
- Compounding (each outcome improves skills)

---

# PART 5: IMPLEMENTATION ROADMAP

## Phase 1: Foundation (DONE - Weeks 1-3)
- [x] Decision nodes with full context capture
- [x] Outcome models with signal tracking
- [x] Calibration profiles (Beta distributions)
- [x] FalkorDB schema with all node types
- [x] Engram capture (agent session recording)
- [x] Antipattern detection (CodeDigger integration)
- [x] Firewall (decision blocking based on antipatterns)

## Phase 2: Skill Generation & Learning Loop (CURRENT - Weeks 4-6)
- [ ] Skill generator (query decisions → extract patterns → generate procedures)
- [ ] Skill storage (Skills DB in FalkorDB)
- [ ] Incremental skill updates (every 5 outcomes, not just weekly)
- [ ] Skill versioning (track improvements)
- [ ] Skill export (to MCP, CLI, documentation)
- [ ] Graph queries for skill discovery
- [ ] Tests for skill generation accuracy

## Phase 3: MCP Context Injection (Weeks 7-8)
- [ ] MCP server integration (expose decision context as resources)
- [ ] Context prioritization (what's most relevant?)
- [ ] Token budget awareness (don't exceed context window)
- [ ] Streaming optimization (fetch fresh data on demand)
- [ ] Integration tests with Claude Code

## Phase 4: Outcome Tracking & Calibration Loop (Weeks 9-11)
- [ ] Webhook handlers (GitHub, CI/CD, monitoring)
- [ ] Signal aggregation (real-time events)
- [ ] Outcome scoring (success/partial/failure)
- [ ] Calibration runner (hourly/daily updates)
- [ ] Dashboard (team can see calibration trends)

## Phase 5: Team Dashboard & Visualization (Weeks 12+)
- [ ] Decision timeline (when decisions made, outcomes resolved)
- [ ] Skill performance (success rates, trending)
- [ ] Calibration profiles (team confidence vs actual)
- [ ] Negative knowledge heat map (what fails often)
- [ ] Export to coaching / onboarding materials

---

# PART 6: KEY INSIGHTS FOR MEMBRIA POSITIONING

## What Membria Does That No One Else Does

1. **Closes the feedback loop completely**
   - Decision → Code → Outcome → Calibration → Skill → Behavior (repeat)
   - Every other tool has gaps

2. **Generates portable knowledge from experience**
   - Skills are procedures extracted from outcomes, not hand-written specs
   - They improve automatically as data arrives
   - They transfer to new team members (not person-dependent)

3. **Quantifies team effectiveness**
   - Confidence vs actual success (calibration gap)
   - Domain-specific success rates (what is your team good at?)
   - Trend detection (improving/stable/declining in each domain)

4. **Prevents costly mistakes through negative knowledge**
   - Custom JWT failed 8 times → BLOCK next Custom JWT attempt
   - Not just a warning—enforced with firewall
   - Can be overridden with lead approval (audit trail)

5. **Compounding intelligence**
   - First outcome: 1 data point
   - 5th outcome: pattern emerges, skill generated
   - 10th outcome: confidence intervals narrow, recommendations calibrated
   - 30th outcome: strongest possible procedural guidance

## Why This Matters

- **GSD** helps with phase-based planning (structure)
- **Aider** provides context injection (efficiency)
- **Cursor** makes it IDE-native (convenience)
- **Devin** enables autonomous agents (scale)
- **Copilot** has GitHub integration (data access)

**But Membria** closes the loop that makes AI development sustainable:
- Without outcome tracking, context injection is half-informed
- Without calibration, skills are unverified recommendations
- Without negative knowledge, teams repeat failures
- Without procedural extraction, knowledge is fragile (person-dependent)

---

# PART 7: COMPETITIVE MOAT

## Why Membria Can't Be Easily Copied

1. **Data accumulation problem**
   - Membria skills improve as the team grows its decision history
   - Day 1: no skills (cold start)
   - Day 30: basic skills emerging (5 decisions × domains)
   - Day 90: strong skills with tight confidence intervals
   - Year 1: team-specific procedures that outsiders can't access

2. **Team embeddedness**
   - Team can't just switch to another system without losing 12 months of calibration data
   - Retraining takes weeks (new system starts at cold start)
   - Competitive advantage compounds

3. **Privacy moat**
   - Decision history is company IP (captured in FalkorDB on-prem)
   - Not available to outside competitors
   - Each team builds unique set of skills

4. **Integration depth**
   - Membria is embedded in every engineer's workflow (MCP injection)
   - Switching means re-architecting how decisions are made
   - High switching cost

---

# CONCLUSION

Membria's Skills architecture is the missing piece in the LLM dev tools ecosystem. While other tools excel at context injection, real-time feedback, or long-term memory, none complete the full loop: **Decision → Outcome → Calibration → Skill → Behavior**.

By implementing this pipeline, Membria becomes not just a tool but a **learning system** that:
- Captures what your team knows
- Measures if it's working
- Adjusts confidence automatically
- Generates portable procedures
- Feeds them back to Claude

This compounds over time, creating a durable competitive advantage that grows stronger as teams use Membria longer.

---

# APPENDIX: RESEARCH SOURCES

## Tools Analyzed

1. **GSD (Get Shit Done)**
   - Sources: [Beating context rot in Claude Code with GSD - The New Stack](https://thenewstack.io/beating-the-rot-and-getting-stuff-done/)
   - Sources: [GitHub - gsd-build/get-shit-done](https://github.com/glittercowboy/get-shit-done)
   - Sources: [Medium - I Tested GSD Claude Code](https://medium.com/@joe.njenga/i-tested-gsd-claude-code-meta-prompting-that-ships-faster-no-agile-bs-ca62aff18c04)

2. **Aider**
   - Sources: [Aider Documentation](https://aider.chat/docs/)
   - Sources: [Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
   - Sources: [GitHub - Aider-AI/aider](https://github.com/Aider-AI/aider)

3. **Cursor IDE**
   - Sources: [Cursor vs Claude Code - haihai.ai](https://www.haihai.ai/cursor-vs-claude-code/)
   - Sources: [How to Use Claude Code with Cursor - apidog.com](https://apidog.com/blog/use-claude-code-with-cursor/)

4. **Devin AI**
   - Sources: [Cognition - Devin's 2025 Performance Review](https://cognition.ai/blog/devin-annual-performance-review-2025)
   - Sources: [Devin Docs](https://docs.devin.ai/)
   - Sources: [Cognition - Introducing Devin](https://cognition.ai/blog/introducing-devin)

5. **Continue.dev**
   - Sources: [Continue Documentation - Context Providers](https://docs.continue.dev/customization/context-providers)
   - Sources: [DeepWiki - Continue Extension Architecture](https://deepwiki.com/continuedev/continue/4.1-extension-architecture)

6. **GitHub Copilot**
   - Sources: [GitHub Docs - Prompt Engineering with Copilot](https://docs.github.com/en/copilot/concepts/prompting/prompt-engineering)
   - Sources: [GitHub Docs - Provide Context to Copilot](https://docs.github.com/en/copilot/how-tos/provide-context)
   - Sources: [DeepWiki - Model Routing & Context Management](https://deepwiki.com/github/copilot-cli/6.5-model-routing-and-context-management)

7. **LangGraph**
   - Sources: [LangChain - LangGraph](https://www.langchain.com/langgraph)
   - Sources: [Medium - Build ReAct AI Agents with LangGraph](https://medium.com/@tahirbalarabe2/build-react-ai-agents-with-langgraph-cb9d28cc6e20)
   - Sources: [Databricks - AI Agent Memory](https://docs.databricks.com/aws/en/generative-ai/agent-framework/stateful-agents)

8. **MCP (Model Context Protocol)**
   - Sources: [Model Context Protocol - GitHub](https://github.com/modelcontextprotocol)
   - Sources: [What is Model Context Protocol - Google Cloud](https://cloud.google.com/discover/what-is-model-context-protocol)
   - Sources: [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/2025-11-25)

---

**Document End**
