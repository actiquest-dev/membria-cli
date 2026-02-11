# FalkorDB Schema - Membria Causal Memory Graph

**Версия:** 0.1
**Статус:** DESIGN (не реализовано!)
**Цель:** Полное описание как должна храниться причинно-следственная связь решений

---

## Проблема

Текущий код в `graph.py` создаёт только **Decision nodes**, это недостаточно для:
- Tracking decision → outcome correlation
- Finding patterns (какие решения ломаются)
- Rework analysis (когда код переделывается)
- Negative knowledge (что не работает)

---

## Архитектура Графа

```
Developer Session (MCP)
    ↓
    ├─ Decision Node
    │  (explicit decision)
    │
    ├─ Engram Node
    │  (session checkpoint)
    │
    ├─ CodeChange Node
    │  (commit that implemented decision)
    │
    ├─ Outcome Node
    │  (success or failure)
    │
    └─ AntiPattern Node
       (if antipattern found)
```

### Relationships (Рёбра)

```
Decision --[MADE_IN]--> Engram
Decision --[IMPLEMENTED_IN]--> CodeChange
CodeChange --[RESULTED_IN]--> Outcome
CodeChange --[TRIGGERED]--> AntiPattern
Outcome --[CAUSED]--> NegativeKnowledge
NegativeKnowledge --[PREVENTED]--> Decision (next time)
Decision --[REWORKED_BY]--> CodeChange (if reverted)
Decision --[SIMILAR_TO]--> Decision (vector similarity)
```

---

## Node Types & Properties

### 1. Decision Node

```cypher
(:Decision {
  id: "dec_abc123",                    # Unique ID
  statement: "Use PostgreSQL for...",  # What was decided
  alternatives: ["MongoDB", "SQLite"], # Considered options
  confidence: 0.85,                    # Developer's confidence (0-1)

  # Decision context
  module: "database",                  # auth|db|api|frontend|backend
  created_at: 1707500000,              # Unix timestamp
  created_by: "claude-code",           # Who made the decision

  # Outcome tracking
  outcome: "success|failure|pending",  # Later filled in
  resolved_at: 1708000000,             # When outcome known

  # Calibration data
  actual_success_rate: 0.9,            # Measured outcome rate

  # Reference
  engram_id: "eng_def456",             # Session where decided
  commit_sha: "abc123def456"           # Commit that implemented it
})
```

**Example:**
```cypher
(:Decision {
  id: "dec_001_falkordb_choice",
  statement: "Use FalkorDB instead of Neo4j for graph storage",
  alternatives: ["Neo4j", "Amazon Neptune", "ArangoDB"],
  confidence: 0.85,
  module: "database",
  created_at: 1707500000,
  created_by: "claude-code",
  outcome: "success",
  resolved_at: 1708000000,
  actual_success_rate: 1.0,
  engram_id: "eng_phase2_start",
  commit_sha: "9b842ce"
})
```

---

### 2. Engram Node (Session Checkpoint)

```cypher
(:Engram {
  id: "eng_xyz789",                    # Unique ID
  session_id: "sess_phase2_work",      # Claude Code session ID

  # Git context
  commit_sha: "9b842ce",               # What was committed
  commit_message: "Build Phase 1 foundation",
  branch: "main",

  # Timing
  created_at: 1707500000,              # When session ended
  session_duration_sec: 3600,

  # AI context
  agent_type: "claude-code",           # Who made changes
  agent_model: "claude-sonnet-4-5",

  # Summary
  decisions_extracted: 3,              # How many decisions found
  files_changed: 12,                   # How many files modified
  lines_added: 456,
  lines_removed: 123
})
```

---

### 3. CodeChange Node

```cypher
(:CodeChange {
  id: "change_123",

  # What changed
  commit_sha: "9b842ce",
  files_changed: ["src/graph.py", "src/models.py"],
  diff_stat: {added: 456, removed: 123, modified: 5},

  # When
  timestamp: 1707500000,
  author: "claude-code",

  # Why (linked to decision)
  decision_id: "dec_001_falkordb_choice",

  # Did it work?
  outcome: "success|failure|reverted",
  reverted_by: "change_456",  # if outcome=reverted
  days_to_revert: 14
})
```

---

### 4. Outcome Node

```cypher
(:Outcome {
  id: "outcome_123",

  # Result
  status: "success|failure|partial",

  # Evidence
  evidence: "Graph performs well, no errors in 2 weeks",
  measured_at: 1708000000,

  # Metrics
  performance_impact: 0.95,     # 1.0 = no impact, <1 = slower, >1 = faster
  reliability: 0.99,            # Uptime/error rate
  maintenance_cost: 0.8,        # Developer time to maintain

  # Link
  code_change_id: "change_123"
})
```

---

### 5. NegativeKnowledge Node

```cypher
(:NegativeKnowledge {
  id: "nk_custom_jwt_fail",

  # What failed
  hypothesis: "Custom JWT implementation is safe",
  conclusion: "Custom JWT has 89% removal rate",

  # Evidence
  evidence: "20,470 repos, removed within 97 days avg",
  source: "CodeDigger analysis",

  # Context
  domain: "auth",
  severity: "high",  # high|medium|low

  # Timing
  discovered_at: 1707500000,
  expires_at: null,  # Can expire (avoid permanent blocking)

  # Prevention
  blocks_pattern: "custom-jwt",
  recommendation: "Use passport-jwt instead"
})
```

---

### 6. AntiPattern Node

```cypher
(:AntiPattern {
  id: "ap_foreach_async",

  # What
  name: "forEach with async callback",
  category: "async",
  severity: "high",

  # Statistics
  repos_affected: 15642,
  occurrence_count: 234567,
  removal_rate: 0.76,
  avg_days_to_removal: 42,

  # Detection
  keywords: ["forEach", "async"],
  regex_pattern: "\.forEach\\s*\\(\\s*async",

  # Evidence
  example_bad: "items.forEach(async item => await process(item))",
  example_good: "for (const item of items) { await process(item) }",

  # Discovery
  first_seen: 1707500000,
  found_by: "CodeDigger",
  source: "GitHub mining"
})
```

---

## Relationships (Рёбра графа)

### [MADE_IN] - Решение принято в сессии

```cypher
(Decision)-[MADE_IN {
  at_timestamp: 1707500000,
  confidence_given: 0.85,
  alternatives_considered: 3
}]->(Engram)
```

**Query:**
```cypher
MATCH (d:Decision)-[r:MADE_IN]->(e:Engram)
RETURN d.statement, e.session_id, r.at_timestamp
```

---

### [IMPLEMENTED_IN] - Решение реализовано в коммите

```cypher
(Decision)-[IMPLEMENTED_IN {
  implemented_at: 1707500000,
  commit_sha: "9b842ce",
  files_affected: ["src/graph.py"]
}]->(CodeChange)
```

**Query:** Найти какой код реализовал какое решение
```cypher
MATCH (d:Decision)-[r:IMPLEMENTED_IN]->(c:CodeChange)
WHERE d.module = "database"
RETURN d.statement, c.commit_sha, c.timestamp
```

---

### [RESULTED_IN] - Код привёл к результату

```cypher
(CodeChange)-[RESULTED_IN {
  outcome: "success",
  measured_at: 1708000000,
  days_to_outcome: 14
}]->(Outcome)
```

**Query:** Найти все изменения и их результаты
```cypher
MATCH (c:CodeChange)-[r:RESULTED_IN]->(o:Outcome)
RETURN c.commit_sha, o.status, o.reliability
```

---

### [TRIGGERED] - Код содержит антипаттерн

```cypher
(CodeChange)-[TRIGGERED {
  found_at: 1707500000,
  severity: "high",
  line_numbers: [42, 58, 123]
}]->(AntiPattern)
```

**Query:** Какие антипаттерны были добавлены?
```cypher
MATCH (c:CodeChange)-[r:TRIGGERED]->(ap:AntiPattern)
WHERE c.commit_sha = "9b842ce"
RETURN ap.name, ap.severity, ap.recommendation
```

---

### [CAUSED] - Результат привёл к negative knowledge

```cypher
(Outcome)-[CAUSED {
  when: 1708000000,
  confidence: 0.95
}]->(NegativeKnowledge)
```

**Query:** Какие знания получены из неудачных исходов?
```cypher
MATCH (o:Outcome)-[r:CAUSED]->(nk:NegativeKnowledge)
WHERE o.status = "failure"
RETURN nk.hypothesis, nk.evidence, nk.recommendation
```

---

### [PREVENTED] - Negative knowledge блокирует решение

```cypher
(NegativeKnowledge)-[PREVENTED {
  blocked_at: 1708500000
}]->(Decision)
```

**Query:** Было ли решение заблокировано negative knowledge?
```cypher
MATCH (nk:NegativeKnowledge)-[r:PREVENTED]->(d:Decision)
WHERE nk.severity = "high"
RETURN nk.hypothesis, d.statement, r.blocked_at
```

---

### [REWORKED_BY] - Решение переделано в другом коммите

```cypher
(Decision)-[REWORKED_BY {
  reworked_at: 1708500000,
  new_commit_sha: "abc456def789",
  reason: "performance issues"
}]->(CodeChange)
```

**Query:** Какие решения переделывались? (Failure rate)
```cypher
MATCH (d:Decision)-[r:REWORKED_BY]->(c:CodeChange)
RETURN d.statement, count(*) as rework_count
ORDER BY rework_count DESC
```

---

### [SIMILAR_TO] - Похожие решения (Vector similarity)

```cypher
(Decision)-[SIMILAR_TO {
  similarity_score: 0.92,
  computed_at: 1708500000
}]->(Decision)
```

**Query:** Найти похожие решения с лучшим исходом
```cypher
MATCH (d1:Decision)-[r:SIMILAR_TO]->(d2:Decision)
WHERE d1.id = "dec_001" AND r.similarity_score > 0.8
RETURN d2.statement, d2.outcome, d2.actual_success_rate
```

---

## Key Queries (Analytic Queries)

### 1. Decision Success Rate by Module

```cypher
MATCH (d:Decision {outcome: "success"})
RETURN d.module,
       count(*) as successes,
       count(DISTINCT d.id) as total,
       100.0 * count(*) / count(DISTINCT d.id) as success_rate
ORDER BY success_rate DESC
```

**Expected Output:**
```
module      | successes | total | success_rate
database    | 8         | 10    | 80%
auth        | 9         | 10    | 90%
api         | 5         | 8     | 62.5%
```

---

### 2. Decision Rework Pattern

```cypher
MATCH (d:Decision)-[r:REWORKED_BY]->(c:CodeChange)
RETURN d.statement,
       count(r) as rework_count,
       avg(r.days_to_revert) as avg_days_to_revert
WHERE d.confidence < 0.7
ORDER BY rework_count DESC
```

**Expected Output:**
```
statement                              | rework_count | avg_days
"Use custom JWT for auth"              | 5            | 97
"Implement N+1 query optimization"     | 3            | 42
```

---

### 3. Confidence Calibration

```cypher
MATCH (d:Decision {outcome: "success"})
RETURN
  round(d.confidence * 10) / 10 as confidence_bucket,
  count(*) as successful,
  avg(d.actual_success_rate) as actual_rate,
  100.0 * avg(d.actual_success_rate) / avg(d.confidence) as calibration_ratio
ORDER BY confidence_bucket DESC
```

**Expected Output:**
```
confidence_bucket | successful | actual_rate | calibration_ratio
0.9               | 15         | 0.87        | 96%  (well-calibrated)
0.7               | 8          | 0.45        | 64%  (overconfident)
0.5               | 3          | 0.92        | 184% (underconfident)
```

---

### 4. Antipattern Prevention Value

```cypher
MATCH (ap:AntiPattern {removal_rate: r}),
      (d:Decision)-[x:PREVENTED]-(ap)
WHERE r > 0.7
RETURN ap.name,
       ap.removal_rate,
       count(d) as decisions_prevented,
       ap.recommendation
ORDER BY r DESC
```

**Expected Output:**
```
name                           | removal_rate | prevented | recommendation
"Custom JWT Implementation"    | 0.89         | 23        | "Use passport-jwt"
"forEach with async callback" | 0.76         | 15        | "Use for...of loop"
"N+1 Query Problem"           | 0.82         | 18        | "Use batch loading"
```

---

### 5. Negative Knowledge Effectiveness

```cypher
MATCH (nk:NegativeKnowledge),
      (nk)-[r:PREVENTED]->(d:Decision)
RETURN nk.hypothesis,
       count(r) as times_prevented,
       nk.severity,
       nk.recommendation
ORDER BY times_prevented DESC
```

**Expected Output:**
```
hypothesis                             | prevented | severity | recommendation
"Custom JWT fails 89% of the time"    | 45        | high     | Use passport-jwt
"N+1 queries cause slowdowns"         | 32        | high     | Use eager loading
```

---

## Data Flow: How It Should Work

### Scenario: Decision → Implementation → Rework

```
1. DECISION MADE
   Developer (or Claude Code): "I'll use PostgreSQL"
   → CREATE (:Decision {id: "dec_001", statement: "...", confidence: 0.85})

2. SESSION CAPTURED (Engram)
   → CREATE (:Engram {id: "eng_001"})
   → CREATE (dec_001)-[MADE_IN]->(eng_001)

3. CODE COMMITTED
   → CREATE (:CodeChange {commit_sha: "abc123"})
   → CREATE (dec_001)-[IMPLEMENTED_IN]->(change_001)

4. RUNNING FOR 2 WEEKS
   → CREATE (:Outcome {status: "success", reliability: 0.99})
   → CREATE (change_001)-[RESULTED_IN]->(outcome_001)

5. UPDATE DECISION WITH OUTCOME
   → MATCH (d:Decision {id: "dec_001"})
      SET d.outcome = "success", d.resolved_at = 1708000000

6. LATER: REWORK NEEDED
   → CREATE (:CodeChange {commit_sha: "def456"})
   → CREATE (dec_001)-[REWORKED_BY]->(change_002)
   → UPDATE (dec_001) SET outcome = "reworked"

7. EXTRACT NEGATIVE KNOWLEDGE
   → CREATE (:NegativeKnowledge {
       hypothesis: "PostgreSQL was wrong choice for this",
       evidence: "Took 2 weeks to discover scaling issues"
     })
   → CREATE (change_002)-[CAUSED]->(nk_001)

8. NEXT SIMILAR DECISION
   → Developer considers PostgreSQL again
   → QUERY finds nk_001 via [PREVENTED]
   → Show: "You learned 2 weeks ago this doesn't work"
```

---

## Implementation Priority

### Phase 0 (THIS WEEK)
- [x] Decision node creation (working)
- [ ] Engram node creation
- [ ] [MADE_IN] relationship

### Phase 1 (NEXT WEEK)
- [ ] CodeChange node + [IMPLEMENTED_IN]
- [ ] Outcome node + [RESULTED_IN]
- [ ] Decision outcome tracking

### Phase 2 (WEEK 3)
- [ ] NegativeKnowledge nodes
- [ ] AntiPattern nodes
- [ ] Prevention queries

### Phase 3 (WEEK 4)
- [ ] Analytics queries
- [ ] Calibration dashboard
- [ ] Rework pattern detection

---

## Current Gap

**What exists:** Decision nodes only
**What's missing:**
- ❌ Engram nodes
- ❌ CodeChange nodes
- ❌ Outcome nodes
- ❌ NegativeKnowledge nodes
- ❌ AntiPattern nodes
- ❌ All relationships
- ❌ All analytics queries

**This must be implemented before Phase 1 validation!**

---

## Example Graph State (After 2 months)

```
Nodes: 245 Decisions, 180 Engrams, 240 CodeChanges, 180 Outcomes, 45 NegativeKnowledge
Relationships: 890

Sample Query Results:
- Success rate by module: 75% average
- Rework rate: 22% of decisions
- Confidence calibration: 85% accurate
- Antipattern prevention: 156 decisions blocked
```

---

## Code Changes Required

**New files:**
- `src/membria/graph_schema.py` - Node/relationship definitions
- `src/membria/graph_queries.py` - Analytics queries

**Modified files:**
- `src/membria/graph.py` - Add node creation methods
- `src/membria/mcp_daemon.py` - Track outcomes on code changes

**New commands:**
- `membria decisions update <id> --outcome success` - Mark decision resolved
- `membria negative-knowledge list` - Show learned failures
- `membria graph stats` - Show causal memory stats

---

Это то, что должно быть в FalkorDB!

Сейчас - только Decision nodes.
Нужно - полный причинно-следственный граф.
