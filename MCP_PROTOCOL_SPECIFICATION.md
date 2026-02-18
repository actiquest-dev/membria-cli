# Membria MCP Protocol Specification

**Version:** 1.0
**Status:** Design Document
**Last Updated:** 2026-02-12

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Protocol Specification](#protocol-specification)
4. [Tools](#tools)
5. [Resources](#resources)
6. [Data Models](#data-models)
7. [Message Formats](#message-formats)
8. [Error Handling](#error-handling)
9. [Integration Examples](#integration-examples)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Overview

### Purpose

Membria MCP Protocol defines how Claude Code and other LLM-based tools interact with the Membria decision memory and calibration system.

**Key Goals:**
- Expose Membria capabilities through standard MCP interface
- Enable Claude to capture decisions with full context
- Provide real-time calibration feedback
- Inject contextual skills and warnings
- Create closed-loop learning system

### Architecture Pattern

```
Claude Code / IDE
      ↓
   MCP Client
      ↓
MCP Protocol (JSON-RPC over stdio)
      ↓
Membria MCP Server
      ↓
Decision Capture ↔ Outcome Tracker ↔ Calibration System
            ↓
      FalkorDB Graph
```

### Design Principles

1. **Composable** - Each tool is independent, can be used separately
2. **Incremental** - Start with core decisions, add outcomes, then skills
3. **Real-time** - Immediate feedback on confidence/calibration
4. **Extensible** - Easy to add new tools and resources
5. **Safe** - Graceful degradation if graph unavailable

---

## Architecture

### Server Components

```
┌─────────────────────────────────────────────────────────┐
│                  Membria MCP Server                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tools Layer (Callable from Claude)                    │
│  ├─ Decision Management                               │
│  ├─ Outcome Recording                                 │
│  ├─ Calibration Analysis                              │
│  └─ Skill/Warning Injection                           │
│                                                         │
│  Resources Layer (Query/Subscribe)                    │
│  ├─ Decision Resources                                │
│  ├─ Calibration Resources                             │
│  ├─ Skills Resources                                  │
│  └─ Anomaly Resources                                 │
│                                                         │
│  State Management                                      │
│  ├─ Session Management                                │
│  ├─ Context Caching                                   │
│  └─ Error Recovery                                    │
│                                                         │
│  Backend Integration                                   │
│  ├─ OutcomeTracker                                    │
│  ├─ CalibrationUpdater                                │
│  ├─ GraphClient (FalkorDB)                            │
│  └─ CausalAgent                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Decision Capture Flow:
   Claude → membria.capture_decision()
   → DecisionCapture (Phase 1)
   → FalkorDB Graph
   → Return decision_id

2. Outcome Recording Flow:
   Claude/GitHub → membria.record_outcome()
   → OutcomeTracker
   → CalibrationUpdater
   → FalkorDB Graph
   → Return calibration_update

3. Context Injection Flow:
   Claude → membria.get_decision_context()
   → GraphAnalyzer
   → (Calibration + Skills + Warnings)
   → Return context injection

4. Skill Generation Flow:
   CalibrationUpdater → TeamCalibration
   → Skill Generator (Phase 3.2)
   → FalkorDB Graph
   → Available via membria.get_skills()
```

---

## Protocol Specification

### MCP Version & Requirements

```
MCP Version: 1.0+
Protocol: JSON-RPC 2.0
Transport: stdio (can be extended to HTTP, WebSocket)
Required Fields: jsonrpc, method, params, id
Optional Fields: result, error
```

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call" | "resources/read" | "resources/subscribe",
  "params": {
    "name": "tool_or_resource_name",
    "arguments": {
      // tool-specific arguments
    }
  }
}
```

### Response Format - Success

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "content": [
      {
        "type": "text" | "json" | "error",
        "data": "response data"
      }
    ],
    "isError": false
  }
}
```

### Response Format - Error

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {
      "details": "Optional detailed error info",
      "suggestion": "Recommended action"
    }
  }
}
```

### Server Initialization

```json
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-25",
    "capabilities": {
      "tools": true,
      "resources": true,
      "sampling": false
    },
    "clientInfo": {
      "name": "claude-code",
      "version": "1.0"
    }
  }
}
```

---

## Tools

### 1. Decision Management

#### 1.1 membria.capture_decision

**Purpose:** Capture a new decision with full context.

**Arguments:**
```json
{
  "statement": "string (required)",
  "alternatives": "string[] (required, min 1)",
  "confidence": "float (required, 0-1)",
  "assumptions": "string[] (optional)",
  "risk_level": "low|medium|high (optional)",
  "context": {
    "module": "string (database|auth|api|frontend|backend|infra)",
    "session_id": "string (optional, for Claude Code sessions)",
    "file_path": "string (optional, path to relevant code)",
    "reasoning": "string (optional, why this decision)"
  }
}
```

**Returns:**
```json
{
  "decision_id": "dec_abc123def",
  "created_at": "2026-02-12T10:30:00Z",
  "status": "pending",
  "confidence": 0.75,
  "message": "Decision captured successfully"
}
```

**Example Call:**
```json
{
  "jsonrpc": "2.0",
  "id": "cap-1",
  "method": "tools/call",
  "params": {
    "name": "membria.capture_decision",
    "arguments": {
      "statement": "Use PostgreSQL for user database instead of MongoDB",
      "alternatives": ["MongoDB", "SQLite", "MySQL"],
      "confidence": 0.82,
      "assumptions": [
        "PostgreSQL can handle 10k+ req/s",
        "Team has PostgreSQL experience"
      ],
      "risk_level": "medium",
      "context": {
        "module": "database",
        "session_id": "sess_phase3_work",
        "file_path": "src/db/schema.ts",
        "reasoning": "ACID guarantees needed for transactions"
      }
    }
  }
}
```

**Error Cases:**
- `confidence_out_of_range`: confidence not in 0-1
- `missing_alternatives`: < 1 alternative provided
- `graph_unavailable`: FalkorDB not connected
- `invalid_module`: module not recognized

---

#### 1.2 membria.update_decision

**Purpose:** Update decision status or metadata after implementation.

**Arguments:**
```json
{
  "decision_id": "string (required, dec_*)",
  "status": "pending|executed|completed|failed|reworked (optional)",
  "confidence_update": "float (optional, 0-1)",
  "notes": "string (optional)",
  "linked_pr": "string (optional, GitHub PR URL)",
  "linked_commit": "string (optional, commit SHA)"
}
```

**Returns:**
```json
{
  "decision_id": "dec_abc123def",
  "previous_status": "pending",
  "new_status": "executed",
  "updated_at": "2026-02-12T10:35:00Z"
}
```

---

#### 1.3 membria.get_decision

**Purpose:** Get full details of a decision.

**Arguments:**
```json
{
  "decision_id": "string (required)"
}
```

**Returns:**
```json
{
  "decision_id": "dec_abc123def",
  "statement": "Use PostgreSQL for user database",
  "alternatives": ["MongoDB", "SQLite", "MySQL"],
  "confidence": 0.82,
  "module": "database",
  "created_at": "2026-02-12T10:30:00Z",
  "created_by": "claude-code",
  "status": "executed",
  "outcome": null,
  "assumptions": ["PostgreSQL can handle 10k+ req/s"],
  "similar_decisions": [
    {
      "statement": "Use PostgreSQL for analytics",
      "success_rate": 0.88,
      "confidence_difference": 0.06
    }
  ],
  "antipatterns_triggered": []
}
```

---

### 2. Outcome Recording

#### 2.1 membria.record_outcome

**Purpose:** Record outcome of a decision after 30-day period.

**Arguments:**
```json
{
  "decision_id": "string (required, dec_*)",
  "final_status": "success|partial|failure (required)",
  "final_score": "float (required, 0-1)",
  "signals": {
    "ci_passed": "boolean (optional)",
    "incident_found": "boolean (optional)",
    "performance_metrics": "object (optional)",
    "reliability_score": "float (optional, 0-1)"
  },
  "lessons_learned": "string[] (optional)",
  "decision_domain": "string (optional, auto-detect if not provided)"
}
```

**Returns:**
```json
{
  "outcome_id": "outcome_dec_abc123_xyz789",
  "decision_id": "dec_abc123def",
  "final_status": "success",
  "final_score": 0.87,
  "completed_at": "2026-02-12T10:45:00Z",
  "calibration_impact": {
    "domain": "database",
    "previous_success_rate": 0.78,
    "new_success_rate": 0.81,
    "sample_size": 12,
    "confidence_gap": 0.01
  },
  "recommendation": "Team is well-calibrated in database decisions"
}
```

**Triggers:**
- Automatic calibration update
- Skill generation (if enabled)
- Anomaly detection
- Graph update

---

#### 2.2 membria.record_signal

**Purpose:** Record intermediate signal/event for a decision (before final outcome).

**Arguments:**
```json
{
  "decision_id": "string (required)",
  "signal_type": "pr_created|pr_merged|ci_passed|ci_failed|incident|performance (required)",
  "valence": "positive|negative|neutral (required)",
  "description": "string (optional)",
  "metrics": "object (optional)"
}
```

**Returns:**
```json
{
  "signal_id": "sig_abc123",
  "decision_id": "dec_abc123def",
  "recorded_at": "2026-02-12T10:40:00Z",
  "estimated_success": 0.72
}
```

---

### 3. Calibration Analysis

#### 3.1 membria.get_calibration

**Purpose:** Get calibration metrics for domain.

**Arguments:**
```json
{
  "domain": "string (optional, database|auth|api|etc.)",
  "include_trend": "boolean (optional, default true)",
  "include_credible_interval": "boolean (optional, default true)"
}
```

**Returns:**
```json
{
  "domain": "database",
  "sample_size": 12,
  "success_rate": 0.817,
  "mean_confidence": 0.806,
  "confidence_gap": 0.011,
  "status": "well-calibrated",
  "alpha": 9.8,
  "beta": 2.2,
  "variance": 0.0124,
  "trend": "stable",
  "credible_interval_95": [0.748, 0.873],
  "recommendation": "Keep doing what you're doing - well calibrated!"
}
```

---

#### 3.2 membria.get_confidence_guidance

**Purpose:** Get personalized confidence guidance.

**Arguments:**
```json
{
  "domain": "string (required)",
  "decision_confidence": "float (optional, 0-1)",
  "context": "string (optional, decision statement for analysis)"
}
```

**Returns:**
```json
{
  "domain": "auth",
  "status": "data_available|no_data",
  "sample_size": 8,
  "actual_success_rate": 0.625,
  "your_confidence": 0.80,
  "confidence_gap": 0.175,
  "calibration_status": "underconfident",
  "adjustment": 0.10,
  "recommendation": "You're underconfident by 17.5%! Trust your decisions more in auth domain.",
  "credible_interval_95": [0.45, 0.78],
  "similar_patterns": [
    {
      "pattern": "Auth decisions when feature-flagged",
      "success_rate": 0.92,
      "confidence": 0.75,
      "recommendation": "Use feature flags - boosts success by 30%"
    }
  ]
}
```

---

#### 3.3 membria.get_all_calibrations

**Purpose:** Get calibration for all domains.

**Arguments:**
```json
{
  "min_sample_size": "integer (optional, default 3)",
  "sort_by": "success_rate|trend|variance (optional)"
}
```

**Returns:**
```json
{
  "domains": [
    {
      "domain": "database",
      "sample_size": 12,
      "success_rate": 0.817,
      "trend": "stable",
      "status": "well-calibrated"
    },
    {
      "domain": "auth",
      "sample_size": 8,
      "success_rate": 0.625,
      "trend": "improving",
      "status": "underconfident"
    }
  ],
  "overall_calibration": "good",
  "last_updated": "2026-02-12T10:45:00Z"
}
```

---

### 4. Context & Decision Support

#### 4.1 membria.get_decision_context

**Purpose:** Get full context for a decision (for Claude injection).

**Arguments:**
```json
{
  "statement": "string (required, proposed decision)",
  "module": "string (optional, database|auth|etc.)",
  "confidence": "float (optional, proposed confidence)",
  "depth": "minimal|standard|full (optional, default standard)"
}
```

**Returns:**
```json
{
  "decision_statement": "Use PostgreSQL for user database",
  "calibration_context": {
    "domain": "database",
    "team_success_rate": 0.82,
    "team_confidence": 0.81,
    "status": "well-calibrated",
    "your_confidence": 0.75,
    "gap": -0.07,
    "recommendation": "You're slightly underconfident - consider 0.80"
  },
  "similar_decisions": [
    {
      "statement": "Use PostgreSQL for analytics",
      "success_rate": 0.88,
      "lessons": ["Set up connection pooling", "Monitor query performance"]
    },
    {
      "statement": "Use MongoDB for user data",
      "success_rate": 0.62,
      "antipattern": "Avoid - lack of ACID guarantees caused issues"
    }
  ],
  "applicable_skills": [
    {
      "skill": "PostgreSQL scales to 50k+ req/s with proper tuning",
      "confidence": 0.91,
      "source": "12 successful decisions"
    }
  ],
  "warnings": [
    {
      "type": "antipattern",
      "description": "Database migration without testing",
      "severity": "high"
    }
  ],
  "causal_context": {
    "previous_failed_decisions": [
      "Chose MongoDB without evaluation"
    ],
    "lessons_learned": ["Always benchmark alternatives"]
  }
}
```

**Depth Levels:**
- `minimal`: Just calibration + top warning
- `standard`: Calibration + 3 similar + 2 skills + warnings (default)
- `full`: Everything + causal chains + related decisions

---

#### 4.2 membria.analyze_decision

**Purpose:** Deep analysis of a specific decision.

**Arguments:**
```json
{
  "decision_id": "string (required)"
}
```

**Returns:**
```json
{
  "decision_id": "dec_abc123def",
  "statement": "Use PostgreSQL for user database",
  "analysis": {
    "causal_chain": {
      "decision": "PostgreSQL",
      "implementation": "CodeChange: Schema migration",
      "outcome": "Success (0.87 score)",
      "lesson": "ACID guarantees important for user data",
      "skill_generated": "PostgreSQL maintains consistency"
    },
    "prevention_effectiveness": {
      "prevented_decisions": 2,
      "prevented_issue": "Attempted MongoDB switch (would fail)"
    },
    "similar_decisions": [...],
    "antipatterns_avoided": [...]
  }
}
```

---

### 5. Skills & Recommendations

#### 5.1 membria.get_skills

**Purpose:** Get applicable skills for a domain or decision.

**Arguments:**
```json
{
  "domain": "string (required)",
  "decision_statement": "string (optional, for relevance scoring)",
  "min_confidence": "float (optional, default 0.70)",
  "limit": "integer (optional, default 10)"
}
```

**Returns:**
```json
{
  "domain": "database",
  "skills": [
    {
      "skill_id": "sk_pg_perf_001",
      "statement": "PostgreSQL scales to 50k+ req/s with connection pooling",
      "confidence": 0.91,
      "evidence": {
        "successes": 8,
        "total_outcomes": 9
      },
      "applicability_score": 0.95,
      "recommendation": "Use connection pooling (PgBouncer) for high throughput"
    },
    {
      "skill_id": "sk_pg_acid_001",
      "statement": "PostgreSQL ACID guarantees critical for transaction consistency",
      "confidence": 0.88,
      "evidence": {
        "successes": 7,
        "total_outcomes": 8
      },
      "applicability_score": 0.92,
      "when_to_use": "When data consistency is critical"
    }
  ],
  "antipatterns": [
    {
      "pattern": "Using SQLite for production >1 concurrent connection",
      "severity": "high",
      "success_rate": 0.15,
      "recommendation": "Use PostgreSQL or MySQL instead"
    }
  ]
}
```

---

#### 5.2 membria.get_warnings

**Purpose:** Get red flags and warnings for a proposed decision.

**Arguments:**
```json
{
  "statement": "string (required)",
  "module": "string (required)",
  "confidence": "float (optional)",
  "alternatives": "string[] (optional)",
  "context": "object (optional)"
}
```

**Returns:**
```json
{
  "warnings": [
    {
      "type": "antipattern",
      "severity": "high",
      "message": "forEach with async callbacks detected",
      "evidence": "Found in 3 failed decisions",
      "recommendation": "Use map() with Promise.all() instead"
    },
    {
      "type": "overconfidence",
      "severity": "medium",
      "message": "Your confidence (0.90) is above team average (0.75) for auth domain",
      "recommendation": "Consider 0.82 (more realistic)"
    }
  ],
  "firewall_status": "caution",
  "risk_score": 0.65
}
```

---

## Resources

### Resource Format

Resources are queryable/subscribable data that Claude can access without calling tools.

**Protocol:**
```json
{
  "method": "resources/read" | "resources/subscribe",
  "params": {
    "uri": "membria://resource-path",
    "arguments": {}
  }
}
```

---

### Available Resources

#### membria://decisions/all
List all decisions.

**Arguments:**
```json
{
  "module": "string (optional, filter by module)",
  "status": "string (optional, pending|executed|completed)",
  "limit": "integer (optional, default 20)"
}
```

---

#### membria://decisions/{decision_id}
Get specific decision.

---

#### membria://calibrations/all
Get all calibration profiles.

---

#### membria://calibrations/{domain}
Get calibration for specific domain.

---

#### membria://skills/{domain}
Get skills for domain.

---

#### membria://graph/causal-chain/{decision_id}
Get full causal chain for decision.

---

#### membria://graph/similar-decisions/{decision_id}
Get similar decisions from graph.

---

#### membria://anomalies/current
Get current anomalies/issues detected.

---

## Data Models

### Decision Model

```typescript
interface MembrinDecision {
  decision_id: string;                    // dec_*
  statement: string;                      // The decision statement
  alternatives: string[];                 // Alternative options
  confidence: float;                      // 0-1
  module: string;                         // database, auth, api, etc.
  created_at: ISO8601;
  created_by: string;                     // claude-code, human
  status: "pending" | "executed" | "completed" | "failed" | "reworked";
  outcome?: string;                       // success, partial, failure
  assumptions: string[];
  reasoning: string;
  linked_pr?: string;                     // GitHub PR URL
  linked_commit?: string;                 // Commit SHA
  context_hash: string;                   // SHA256 of immutable context
}
```

### Outcome Model

```typescript
interface MembrinOutcome {
  outcome_id: string;
  decision_id: string;
  final_status: "success" | "partial" | "failure";
  final_score: float;                     // 0-1
  completed_at: ISO8601;
  signals: Signal[];
  lessons_learned: string[];
  metrics: {
    performance_impact?: float;
    reliability?: float;
    maintenance_cost?: float;
  };
}
```

### Calibration Model

```typescript
interface MembrinCalibration {
  domain: string;
  sample_size: integer;
  alpha: float;                           // Successes + prior
  beta: float;                            // Failures + prior
  mean_success_rate: float;               // α/(α+β)
  variance: float;
  confidence_gap: float;                  // team_confidence - actual_success
  trend: "improving" | "stable" | "declining";
  credible_interval_95: [float, float];
  last_updated: ISO8601;
}
```

### Skill Model

```typescript
interface MembrinSkill {
  skill_id: string;
  domain: string;
  statement: string;                      // The skill/best practice
  confidence: float;                      // 0-1
  evidence: {
    successes: integer;
    total_outcomes: integer;
  };
  when_to_use: string;
  examples: string[];
  antipattern?: string;                   // What not to do
  source: "outcomes" | "analysis";
  generated_at: ISO8601;
}
```

---

## Message Formats

### Context Injection Prompt (for Claude System Prompt)

```
## Membria Decision Context

**Domain:** database
**Team Success Rate:** 82% (12 decisions)
**Your Confidence:** 75% vs Team Average: 81%
**Status:** Well-calibrated (gap: 0.01)

### Applicable Skills:
1. PostgreSQL scales 50k+ req/s with connection pooling (91% confidence)
2. Always add ACID guarantees for transaction consistency (88% confidence)

### Similar Decisions:
- ✅ PostgreSQL for analytics (88% success)
- ❌ MongoDB without evaluation (62% success)

### Warnings:
- ⚠️ Database migrations need testing (high severity)
```

### Error Response Format

```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "field": "confidence",
      "problem": "Must be between 0 and 1",
      "received": 1.5,
      "suggestion": "Use confidence: 0.75"
    }
  }
}
```

### Batch Response Format

```json
{
  "results": [
    { "id": "req-1", "result": {...} },
    { "id": "req-2", "result": {...} },
    { "id": "req-3", "error": {...} }
  ]
}
```

---

## Error Handling

### Standard Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| -32700 | Parse error | Retry with valid JSON |
| -32600 | Invalid Request | Check method name and params |
| -32601 | Method not found | Verify tool/resource exists |
| -32602 | Invalid params | Check argument types and ranges |
| -32603 | Internal error | Retry or check server logs |
| -32001 | Graph unavailable | Retry when graph is online |
| -32002 | Calibration insufficient | Need more outcomes (min 3) |
| -32003 | Decision not found | Check decision_id format |

### Graceful Degradation

If graph is unavailable:
- ✅ Decision capture still works (in-memory)
- ✅ Calibration returns cached data
- ⚠️ Context injection limited to local data
- ❌ Graph queries fail (return 503)

```json
{
  "error": {
    "code": -32001,
    "message": "Graph unavailable",
    "data": {
      "suggestion": "Using cached calibration data from 2 hours ago",
      "retry_after": 30
    }
  }
}
```

---

## Integration Examples

### Example 1: Claude Capturing Decision

```
User: "Should we use PostgreSQL or MongoDB for user database?"

Claude (via MCP):
{
  "method": "tools/call",
  "params": {
    "name": "membria.capture_decision",
    "arguments": {
      "statement": "Use PostgreSQL for user database",
      "alternatives": ["MongoDB", "SQLite"],
      "confidence": 0.82,
      "assumptions": ["ACID guarantees needed", "Team knows PostgreSQL"],
      "context": { "module": "database" }
    }
  }
}

Server returns:
{
  "decision_id": "dec_pg_user_001",
  "status": "pending",
  "confirmation": "Decision captured. I've recorded this decision with 82% confidence."
}

Claude (with context):
"Great! I've captured this decision. Our database team has 82% success rate with PostgreSQL
(12 decisions, well-calibrated). Similar decision: PostgreSQL for analytics had 88% success.
Let me implement this with connection pooling (key skill from previous success)."
```

### Example 2: Recording Outcome

```
(30 days later, PR merged, tests passed, in production)

Claude/Webhook triggers:
{
  "method": "tools/call",
  "params": {
    "name": "membria.record_outcome",
    "arguments": {
      "decision_id": "dec_pg_user_001",
      "final_status": "success",
      "final_score": 0.89,
      "signals": {
        "ci_passed": true,
        "incident_found": false
      },
      "lessons_learned": [
        "Connection pooling critical at 8k req/s",
        "Monitoring saved us from N+1 queries"
      ]
    }
  }
}

Server returns:
{
  "outcome_id": "out_pg_user_001",
  "calibration_impact": {
    "domain": "database",
    "new_success_rate": 0.84,
    "recommendation": "Keep using PostgreSQL - working well!"
  },
  "skill_generated": {
    "skill": "PostgreSQL connection pooling critical above 5k req/s",
    "confidence": 0.89
  }
}
```

### Example 3: Context Injection During Decision

```
User: "I'm thinking of using MongoDB for cache layer"

Claude requests context:
{
  "method": "tools/call",
  "params": {
    "name": "membria.get_decision_context",
    "arguments": {
      "statement": "Use MongoDB for cache layer",
      "module": "database",
      "depth": "standard"
    }
  }
}

Server returns rich context:
{
  "calibration_context": {
    "status": "overconfident",
    "gap": 0.15,
    "recommendation": "MongoDB has lower success in our database domain"
  },
  "similar_decisions": [
    {
      "statement": "MongoDB for user data",
      "success_rate": 0.62,
      "antipattern": "Should use PostgreSQL for consistency"
    }
  ],
  "warnings": [
    {
      "type": "overconfidence",
      "message": "MongoDB success rate 62% < your estimated confidence"
    }
  ]
}

Claude (with injected context):
"Wait - I see MongoDB has only 62% success in our database decisions vs your confidence.
Let me reconsider: PostgreSQL for primary (84% success), Redis for cache (88% success)
would be better. Updating confidence from 0.80 → 0.65 for MongoDB approach."
```

---

## Implementation Roadmap

### Phase 3.1: Core MCP Server (Weeks 1-2)

**Sprint 1.1: Infrastructure**
- [ ] Create MCP server skeleton
- [ ] Implement stdio transport
- [ ] JSON-RPC 2.0 handler
- [ ] Error handling framework
- [ ] Tests for protocol layer

**Sprint 1.2: Core Tools**
- [ ] membria.capture_decision
- [ ] membria.get_decision
- [ ] membria.record_outcome
- [ ] membria.get_calibration
- [ ] Integration tests

**Sprint 1.3: Integration**
- [ ] Claude Code MCP client
- [ ] System prompt injection
- [ ] Context caching
- [ ] E2E tests

### Phase 3.2: Advanced Features (Weeks 3-4)

**Sprint 2.1: Context Tools**
- [ ] membria.get_decision_context
- [ ] membria.get_skills
- [ ] membria.get_warnings
- [ ] Skill injection prompt generation

**Sprint 2.2: Resources**
- [ ] Resource API implementation
- [ ] Caching layer
- [ ] Subscription support
- [ ] Real-time updates

### Phase 3.3: Skill Generation (Weeks 5-6)

**Sprint 3.1: Skill Generator**
- [ ] Mine outcomes for patterns
- [ ] Generate skills from causal chains
- [ ] Score skill confidence
- [ ] Store in graph

**Sprint 3.2: Continuous Learning**
- [ ] Skill maturation tracking
- [ ] Skill retirement (old skills)
- [ ] A/B testing for skills
- [ ] Performance metrics

---

## Security & Safety

### Authentication

```
Option 1: API Key
- Each Claude Code instance has unique key
- Key rotated monthly
- Revokable

Option 2: OAuth 2.0 (future)
- GitHub OAuth for team accounts
- Scope: membria-cli
```

### Data Privacy

- Decisions stored locally unless explicitly synced
- No external API calls except to graph
- GDPR compliance for decision deletion
- Audit log for all operations

### Rate Limiting

```
Default limits:
- 100 requests/minute per client
- 10 capture_decision calls/minute
- 1000 resource reads/minute

Soft limits:
- Warnings at 80% of limit
- Backoff: exponential retry
```

### Validation

All inputs validated:
```
- confidence: 0 ≤ x ≤ 1
- statement: length 10-500 chars, no injection
- decision_id: matches pattern ^dec_[a-z0-9]+$
- module: in whitelist [database, auth, api, frontend, backend, infra]
```

---

## Monitoring & Observability

### Metrics to Track

```
Server Health:
- Request latency (p50, p95, p99)
- Error rate by tool
- Graph connection status
- Cache hit rate

Usage:
- Decisions captured/day
- Outcomes recorded/day
- Context injections/day
- Most used tools

Calibration:
- Domains tracked
- Average success rate
- Overconfident/underconfident count
```

### Logging

```
LEVEL: DEBUG | INFO | WARN | ERROR | FATAL

Events to log:
- All tool calls (with anonymized args)
- Graph operations
- Cache operations
- Errors with full traceback
- Performance slowdowns (>1s)
```

---

## Version & Compatibility

**Current Version:** 1.0

**Backwards Compatibility:**
- Tools are versioned (v1, v2, etc.)
- Deprecated tools marked with ⚠️
- Minimum 1 quarter notice before removal
- Clients can specify version in params

**Future Roadmap:**
- v1.1: Skill subscriptions
- v1.2: Multi-user teams
- v2.0: Performance optimizations

---

## Appendix: Quick Start

### Start MCP Server

```bash
membria mcp start --port 9090
```

### Test Tool Call

```bash
curl -X POST http://localhost:9090 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tools/call",
    "params": {
      "name": "membria.capture_decision",
      "arguments": {
        "statement": "Test decision",
        "alternatives": ["Alt 1"],
        "confidence": 0.75
      }
    }
  }'
```

### Claude Code Integration

```json
// In Claude Code settings:
{
  "mcp_servers": {
    "membria": {
      "command": "membria",
      "args": ["mcp", "serve"],
      "env": {
        "MEMBRIA_GRAPH_URL": "http://localhost:7687",
        "MEMBRIA_LOG_LEVEL": "info"
      }
    }
  }
}
```

---

**End of Specification**

