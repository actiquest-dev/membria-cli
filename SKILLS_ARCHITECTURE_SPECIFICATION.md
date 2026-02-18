# Membria Skills Architecture: Detailed Specification

**Version:** 0.1.0
**Date:** February 12, 2026
**Status:** Design Complete - Ready for Implementation

---

## 1. OVERVIEW

Membria Skills is a procedural knowledge system that:
1. Captures decisions + context (Decision nodes)
2. Observes outcomes over 30 days (Outcome nodes + Signals)
3. Updates team calibration (Beta distributions by domain)
4. Generates reusable procedures from patterns (Skills)
5. Injects skills back to Claude via MCP (Context Injection)

This creates a **closed feedback loop** where experience turns into guidance.

---

## 2. DATA MODEL

### 2.1 Decision Node (FalkorDB)

```cypher
CREATE (:Decision {
  decision_id: string,           // "d-2026-02-12-001"
  statement: string,              // "Use Auth0 for OAuth 2.0"
  alternatives: [string],         // ["Custom JWT", "Firebase Auth", "Keycloak"]
  alternatives_with_reasons: map, // {"Custom JWT": "Faster coding but complex to maintain"}
  assumptions: [string],          // ["Auth0 free tier sufficient", "Latency < 100ms"]
  predicted_outcome: map,         // {"timeline": "1 week", "success_criteria": [...]}

  confidence: double,             // 0.0-1.0 (team calibration adjusted)
  context_hash: string,           // SHA256(decision_state) - immutable
  domain: string,                 // "auth_strategy" - for grouping/querying

  created_at: string,             // ISO8601 timestamp
  created_by: string,             // Developer name or "claude-code"
  created_in: string,             // "membria-cli" | "claude-code" | "cursor"

  status: string,                 // "pending" | "executed" | "completed" | "failed"
  linked_pr: string,              // GitHub PR URL (when available)
  linked_commit: string,          // Git commit SHA (when available)

  metadata: map                   // Custom fields per domain
})

// Relationships
(decision)-[:MADE_BY]->(team_member)
(decision)-[:HAS_DOMAIN]->(domain_node)
(decision)-[:RESULTED_IN]->(outcome)
(decision)-[:USED_SKILL]->(skill)
(decision)-[:TRIGGERED_ANTIPATTERN]->(antipattern)
```

**Indices:**
```cypher
CREATE INDEX decision_domain ON Decision(domain)
CREATE INDEX decision_status ON Decision(status)
CREATE INDEX decision_created_at ON Decision(created_at)
CREATE INDEX decision_context_hash ON Decision(context_hash)
```

### 2.2 Outcome Node (FalkorDB)

```cypher
CREATE (:Outcome {
  outcome_id: string,             // "o-2026-02-12-001"
  decision_id: string,            // Link back to decision

  status: string,                 // "pending" | "merged" | "completed" | "failed" | "abandoned"

  // Timeline
  created_at: string,             // When decision made
  submitted_at: string,           // When PR created (optional)
  merged_at: string,              // When PR merged (optional)
  completed_at: string,           // When 30 days passed (optional)

  // GitHub integration
  pr_url: string,                 // "https://github.com/org/repo/pull/123"
  pr_number: integer,             // 123
  commit_sha: string,             // First commit SHA
  repo: string,                   // "org/repo"

  // Signal aggregation
  signal_count: integer,          // Total signals observed
  positive_signals: integer,      // CI passed, perf ok, etc.
  negative_signals: integer,      // Bugs, incidents, perf poor

  // Final evaluation
  final_status: string,           // "success" | "partial" | "failure"
  final_score: double,            // 0.0-1.0 aggregate

  lessons_learned: [string],      // ["Fastify handles 15k RPS (vs 10k assumed)", ...]

  // Metrics (populated after 30 days)
  metrics: map {
    uptime_percent: double,       // 99.95
    avg_latency_ms: double,       // 45.2
    p99_latency_ms: double,       // 120.5
    throughput_rps: double,       // 12000
    bug_count: integer,           // 2
    incident_count: integer,      // 0
    rollback_count: integer,      // 0
    custom: map                   // Domain-specific metrics
  }
})

// Relationships
(outcome)-[:AGGREGATES]->(signal)  // Many signals per outcome
(outcome)-[:RESULTED_FROM]->(decision)
(outcome)-[:UPDATED]->(calibration_profile)
```

**Indices:**
```cypher
CREATE INDEX outcome_decision_id ON Outcome(decision_id)
CREATE INDEX outcome_status ON Outcome(status)
CREATE INDEX outcome_final_status ON Outcome(final_status)
CREATE INDEX outcome_created_at ON Outcome(created_at)
```

### 2.3 Signal Node (FalkorDB)

```cypher
CREATE (:Signal {
  signal_id: string,              // "sig-2026-02-12-001"
  outcome_id: string,             // Link to parent outcome

  signal_type: string,            // "PR_CREATED", "CI_PASSED", "BUG_FOUND", etc.
  valence: string,                // "positive" | "negative" | "neutral"
  timestamp: string,              // When signal occurred

  description: string,            // "PR #123 merged", "All tests pass", "Latency degradation"

  // For negative signals
  severity: string,               // "low" | "medium" | "high" | null

  // Context & metrics
  metrics: map,                   // {latency_ms: 45, uptime: 99.95, ...}
  source: string,                 // "github" | "circleci" | "datadog" | "manual"
  source_id: string,              // Unique ID in source system

  metadata: map                   // Custom per signal type
})

// Relationships
(signal)-[:PART_OF]->(outcome)
```

### 2.4 Calibration Profile (FalkorDB)

```cypher
CREATE (:CalibrationProfile {
  profile_id: string,             // "cal-auth_strategy"
  domain: string,                 // "auth_strategy"

  // Beta distribution
  alpha: double,                  // Successes + prior
  beta: double,                   // Failures + prior

  // Derived statistics
  success_rate: double,           // alpha / (alpha + beta)
  variance: double,
  sample_size: integer,           // Total decisions observed

  // Confidence gap analysis
  avg_predicted_confidence: double, // Team's average confidence for this domain
  actual_success_rate: double,    // What actually happened
  confidence_gap: double,         // predicted - actual (negative = underconfident)

  trend: string,                  // "improving" | "stable" | "declining"
  trend_window: string,           // "7d" | "30d" | "90d"

  // Recommendations
  recommended_adjustment: double, // -0.15 to +0.15 (adjust team confidence)

  last_updated: string,           // When last updated
  observations: integer           // Number of outcomes processed
})

// Relationships
(profile)-[:TRACKS_DOMAIN]->(domain)
(profile)-[:UPDATED_BY]->(outcome)
```

**Indices:**
```cypher
CREATE INDEX profile_domain ON CalibrationProfile(domain)
```

### 2.5 Skill Node (FalkorDB)

```cypher
CREATE (:Skill {
  skill_id: string,               // "sk-auth_strategy_recommendation-v1"
  domain: string,                 // "auth_strategy"
  name: string,                   // "auth_strategy_recommendation"

  // Versioning
  version: integer,               // 1, 2, 3, ...
  previous_version_id: string,    // sk-auth_strategy_recommendation-v0

  // Evidence
  success_rate: double,           // 0.89 (from 9 successes / 10 decisions)
  confidence: double,             // 0.88 (derived from Beta distribution)
  sample_size: integer,           // 10 decisions observed

  // Metadata
  created_at: string,             // When skill first generated
  last_updated: string,           // When last updated from outcomes
  next_review: string,            // When to re-evaluate

  // Content
  procedure: string,              // Markdown with decision procedure
  // Example:
  // "## Authentication Strategy
  //  ### Recommendation
  //  IF need_auth_strategy THEN:
  //    IF simple_oauth_flow:
  //      **STRONGLY_RECOMMEND** Auth0 (89% success, 9/10)
  //    ELIF custom_scopes_needed:
  //      **CONSIDER** Firebase Auth (87% success, 7/8)
  //    ELSE:
  //      **AVOID** Custom JWT (20% success, 2/10)
  //
  //  ### Reasoning
  //  Custom JWT failed 80% (8/10):
  //    - Token refresh edge cases (4 instances)
  //    - Scope management complexity (3 instances)
  //    - Performance degradation (1 instance)
  //
  //  Auth0 excels at OAuth flows and handles edge cases."

  // Applicability zones
  applicability: map {
    green: [string],              // Use confidently
    yellow: [string],             // Review carefully
    red: [string]                 // Block unless overridden
  },

  // Metadata
  generated_from_decisions: [string], // [d-001, d-005, d-012, ...]
  conflicts_with: [string],       // [sk-custom-jwt-safe-v1]
  related_skills: [string],       // [sk-token-refresh-patterns-v1]

  // Quality metrics
  quality_score: double,          // 0.0-1.0 (based on success rate and sample size)
  confidence_interval_lower: double, // 95% CI
  confidence_interval_upper: double
})

// Relationships
(skill)-[:GENERATED_FROM]->(decision)
(skill)-[:BASED_ON]->(calibration_profile)
(skill)-[:ANTIPATTERN]->(antipattern)
```

**Indices:**
```cypher
CREATE INDEX skill_domain ON Skill(domain)
CREATE INDEX skill_name ON Skill(name)
CREATE INDEX skill_version ON Skill(version)
```

### 2.6 Antipattern Node (FalkorDB)

```cypher
CREATE (:Antipattern {
  antipattern_id: string,         // "ap-custom_jwt_oauth"
  name: string,                   // "Custom JWT for OAuth 2.0"
  domain: string,                 // "auth_strategy"

  // Evidence
  failure_count: integer,         // 8
  total_count: integer,           // 10
  failure_rate: double,           // 0.80

  // Categorization
  severity: string,               // "low" | "medium" | "high"
  firewall_level: string,         // "allow" | "warn" | "block"

  // Root cause analysis
  root_causes: [map {
    cause: string,                // "Token refresh edge cases"
    instance_count: integer,      // 4
    pattern_description: string   // Details
  }],

  // Context
  description: string,            // Why this pattern fails
  remediation: string,            // How to fix if attempted

  // Metadata
  discovered_at: string,          // When first detected
  last_updated: string,           // Last outcome contributed
  source: string                  // "membria" | "codedigger" | "manual"
})

// Relationships
(antipattern)-[:TRIGGERED_BY]->(decision)
(antipattern)-[:RESULT_IN]->(failure_outcome)
```

---

## 3. QUERY PATTERNS

### 3.1 Find Applicable Skills (When Decision Intent Detected)

```cypher
// Input: domain = "auth_strategy"
// Output: List of skills sorted by success rate + sample size

MATCH (s:Skill)
WHERE s.domain = "auth_strategy"
AND s.version = (
  MATCH (s2:Skill)
  WHERE s2.domain = "auth_strategy"
  AND s2.name = s.name
  RETURN MAX(s2.version) AS max_v
)
RETURN s.skill_id, s.name, s.success_rate, s.confidence, s.sample_size
ORDER BY s.success_rate DESC, s.sample_size DESC
```

### 3.2 Get Team Calibration for Domain

```cypher
// Input: domain = "auth_strategy"
// Output: Team's success rate, confidence gap, recommendation

MATCH (cp:CalibrationProfile)
WHERE cp.domain = "auth_strategy"
RETURN {
  domain: cp.domain,
  success_rate: cp.success_rate,
  avg_predicted_confidence: cp.avg_predicted_confidence,
  actual_success_rate: cp.actual_success_rate,
  gap: cp.confidence_gap,
  recommendation: cp.recommended_adjustment,
  trend: cp.trend
} AS calibration
```

### 3.3 Find Similar Past Decisions

```cypher
// Input: new_decision = "Use Auth0"
// Output: Similar decisions with outcomes

MATCH (d:Decision)-[:RESULTED_IN]->(o:Outcome)
WHERE d.domain = "auth_strategy"
AND d.status IN ["completed", "executed"]
AND d.statement CONTAINS "Auth0"
RETURN {
  decision_id: d.decision_id,
  statement: d.statement,
  confidence: d.confidence,
  outcome_status: o.final_status,
  outcome_score: o.final_score,
  time_to_outcome: duration.between(datetime(d.created_at), datetime(o.completed_at))
} AS similar_decision
ORDER BY o.completed_at DESC
LIMIT 5
```

### 3.4 Get Antipatterns for Domain

```cypher
// Input: domain = "auth_strategy"
// Output: Patterns to avoid (negative knowledge)

MATCH (ap:Antipattern)
WHERE ap.domain = "auth_strategy"
AND ap.failure_rate > 0.50  // >50% failure rate
RETURN {
  name: ap.name,
  failure_rate: ap.failure_rate,
  firewall_level: ap.firewall_level,
  root_causes: ap.root_causes,
  remediation: ap.remediation
} AS antipattern
ORDER BY ap.failure_rate DESC
```

### 3.5 Update Calibration from Outcome

```cypher
// Triggered when outcome completed
// Input: outcome_id, final_status (success | failure)

MATCH (o:Outcome)-[:RESULTED_FROM]->(d:Decision)
MATCH (cp:CalibrationProfile {domain: d.domain})

// Update Beta distribution
SET cp.alpha = cp.alpha + (CASE WHEN o.final_status = "success" THEN 1 ELSE 0 END)
SET cp.beta = cp.beta + (CASE WHEN o.final_status = "failure" THEN 1 ELSE 0 END)
SET cp.success_rate = cp.alpha / (cp.alpha + cp.beta)
SET cp.last_updated = datetime()

// Calculate confidence gap
WITH cp, d, o, (d.confidence - (cp.alpha / (cp.alpha + cp.beta))) AS new_gap
SET cp.confidence_gap = new_gap
SET cp.observations = cp.observations + 1

RETURN cp
```

### 3.6 Generate Skill (Batch Query)

```cypher
// Triggered: every 5 outcomes, or weekly batch
// Input: domain = "auth_strategy"
// Output: Aggregated data for skill generation

MATCH (d:Decision {domain: "auth_strategy"})-[:RESULTED_IN]->(o:Outcome)
WHERE o.status = "completed"
WITH d.statement, o.final_status, COUNT(*) AS count
MATCH (cp:CalibrationProfile {domain: "auth_strategy"})

RETURN {
  patterns: COLLECT({
    decision: d.statement,
    successes: SUM(CASE WHEN o.final_status = "success" THEN 1 ELSE 0 END),
    total: COUNT(o),
    rate: SUM(CASE WHEN o.final_status = "success" THEN 1 ELSE 0 END) / CAST(COUNT(o) AS FLOAT)
  }),
  calibration: {
    success_rate: cp.success_rate,
    confidence_gap: cp.confidence_gap,
    sample_size: cp.sample_size,
    trend: cp.trend
  }
}
```

---

## 4. SKILL GENERATION ALGORITHM

### 4.1 Input Data

```python
class SkillGenerationInput:
    domain: str                          # "auth_strategy"
    decisions: List[Decision]            # All decisions in domain
    outcomes: List[Outcome]              # Outcomes for those decisions
    calibration: CalibrationProfile      # Domain's calibration
```

### 4.2 Pattern Extraction

```python
def extract_patterns(decisions, outcomes):
    """Group decisions by statement, calculate success rates."""

    patterns = {}

    for decision, outcome in zip(decisions, outcomes):
        stmt = decision.statement

        if stmt not in patterns:
            patterns[stmt] = {
                "successes": 0,
                "total": 0,
                "decisions": []
            }

        patterns[stmt]["total"] += 1
        if outcome.final_status == "success":
            patterns[stmt]["successes"] += 1
        patterns[stmt]["decisions"].append(decision.decision_id)

    # Calculate success rates
    for stmt, data in patterns.items():
        data["success_rate"] = data["successes"] / data["total"]
        data["count"] = data["total"]

    return patterns
```

### 4.3 Antip Pattern Analysis

```python
def extract_antipatterns(patterns):
    """Identify patterns with high failure rates."""

    antipatterns = []

    for stmt, data in patterns.items():
        if data["success_rate"] < 0.50:  # >50% failure
            # Query root causes (TODO: connect to CodeDigger)
            antipatterns.append({
                "pattern": stmt,
                "failure_rate": 1 - data["success_rate"],
                "count": data["count"],
                "root_causes": [],  # Extract from outcomes
                "firewall_level": "warn" if data["success_rate"] > 0.30 else "block"
            })

    return antipatterns
```

### 4.4 Procedure Generation

```python
def generate_procedure(domain, patterns, antipatterns, calibration):
    """Generate human-readable decision procedure."""

    # Sort patterns by success rate
    high_success = [p for p in patterns if p["success_rate"] > 0.75]
    medium_success = [p for p in patterns if 0.50 <= p["success_rate"] <= 0.75]
    low_success = [p for p in patterns if p["success_rate"] < 0.50]

    procedure = f"""
    # Decision Procedure: {domain}

    ## Team Experience
    - Decisions observed: {calibration.sample_size}
    - Success rate: {calibration.success_rate:.1%}
    - Confidence gap: {calibration.confidence_gap:+.1%}
    - Trend: {calibration.trend}

    ## Recommendation
    """

    if high_success:
        procedure += "\n### Strongly Recommend:\n"
        for p in high_success:
            procedure += f"- **{p['statement']}** ({p['success_rate']:.0%} success, {p['count']} decisions)\n"

    if medium_success:
        procedure += "\n### Consider:\n"
        for p in medium_success:
            procedure += f"- **{p['statement']}** ({p['success_rate']:.0%} success, {p['count']} decisions)\n"

    if low_success:
        procedure += "\n### Avoid:\n"
        for p in low_success:
            procedure += f"- **{p['statement']}** ({p['success_rate']:.0%} success, {p['count']} decisions)\n"

    return procedure
```

### 4.5 Skill Creation

```python
def create_skill(domain, patterns, antipatterns, calibration):
    """Create Skill node in FalkorDB."""

    procedure = generate_procedure(domain, patterns, antipatterns, calibration)

    # Calculate quality score (success rate + sample size confidence)
    success_rate = calibration.success_rate
    sample_size = calibration.sample_size

    # Quality increases with success rate and sample size
    # Quality = 0.5 if sample_size < 3
    #         = success_rate * (1 - 1/sqrt(sample_size)) if sample_size >= 3
    if sample_size < 3:
        quality_score = 0.5
    else:
        quality_score = success_rate * (1 - 1 / sqrt(sample_size))

    skill = Skill(
        skill_id=f"sk-{domain}-v{skill_version}",
        domain=domain,
        name=f"{domain}_recommendation",
        version=skill_version,
        success_rate=success_rate,
        confidence=calibration.success_rate,
        sample_size=sample_size,
        procedure=procedure,
        applicability={
            "green": [p["statement"] for p in patterns if p["success_rate"] > 0.75],
            "yellow": [p["statement"] for p in patterns if 0.50 <= p["success_rate"] <= 0.75],
            "red": [p["statement"] for p in patterns if p["success_rate"] < 0.50]
        },
        quality_score=quality_score
    )

    return skill
```

---

## 5. CONTEXT INJECTION TO CLAUDE

### 5.1 MCP Resources

```yaml
# mcp_resources.yaml

resources:

  - decision_history:
      type: text
      description: "All decisions in the detected domain with outcomes"
      request_schema:
        domain: string  # "auth_strategy"
      response:
        - decision_id: string
          statement: string
          confidence: float
          outcome_status: string
          final_score: float
          created_at: datetime

  - team_calibration:
      type: text
      description: "Team's success rate and confidence calibration"
      request_schema:
        domain: string
      response:
        success_rate: float
        avg_predicted_confidence: float
        actual_success_rate: float
        confidence_gap: float
        trend: string
        recommendation: string

  - applicable_skills:
      type: text
      description: "Skills relevant to the decision being made"
      request_schema:
        domain: string
      response:
        - skill_id: string
          name: string
          success_rate: float
          procedure: markdown
          quality_score: float

  - antipatterns:
      type: text
      description: "Patterns that failed frequently in this domain"
      request_schema:
        domain: string
      response:
        - name: string
          failure_rate: float
          root_causes: [string]
          firewall_level: string

  - similar_decisions:
      type: text
      description: "Past decisions similar to the current one"
      request_schema:
        domain: string
        statement: string
      response:
        - decision_id: string
          statement: string
          outcome_status: string
          outcome_score: float
          lessons_learned: [string]
```

### 5.2 Prompt Injection Template

```
# MEMBRIA DECISION CONTEXT

You are making a decision about **{domain}**.

Your team has experience with {sample_size} decisions in this domain over the past {time_period}.

## Team Success Rate
- **Success rate:** {success_rate}%
- **Team's typical confidence:** {avg_predicted_confidence}%
- **Actual outcomes:** {actual_success_rate}%
- **Confidence gap:** {confidence_gap:+.1%} (team is {underconfident|overconfident|well-calibrated})

## Recommended Skill
The skill **{skill_name}** has been generated from {skill_sample_size} decisions in this domain.
- Success rate: {skill_success_rate}%
- Quality: {quality_score}%
- Last updated: {skill_updated}

### Procedure
{skill_procedure}

## Antipatterns to Avoid
{antipatterns_list}

## Similar Past Decisions
Your team has made similar decisions before:
{similar_decisions_list}

## Confidence Adjustment
Based on team history, I recommend:
- If you feel {confidence_range_lower}% confident: You're in line with team experience
- If you feel {confidence_range_upper}% confident: You might be slightly overconfident
```

### 5.3 Context Filtering (Token Budget Awareness)

```python
def build_context_injection(
    domain: str,
    available_tokens: int,
    priorities: List[str] = None
) -> Dict[str, str]:
    """Build context injection respecting token limits.

    Args:
        domain: Decision domain
        available_tokens: Remaining tokens in context window
        priorities: ["skills", "calibration", "antipatterns", "similar_decisions"]

    Returns:
        Constructed context as dict with size estimates
    """

    if priorities is None:
        priorities = ["skills", "calibration", "antipatterns", "similar_decisions"]

    context = {}
    tokens_used = 0

    for priority in priorities:
        if priority == "skills":
            skill = fetch_best_skill(domain)
            skill_tokens = estimate_tokens(skill.procedure)

            if tokens_used + skill_tokens < available_tokens:
                context["skill"] = skill.procedure
                tokens_used += skill_tokens

        elif priority == "calibration":
            cal = fetch_calibration(domain)
            cal_tokens = 200  # Estimate

            if tokens_used + cal_tokens < available_tokens:
                context["calibration"] = format_calibration(cal)
                tokens_used += cal_tokens

        elif priority == "antipatterns":
            ap = fetch_antipatterns(domain)
            ap_tokens = estimate_tokens(format_antipatterns(ap))

            if tokens_used + ap_tokens < available_tokens:
                context["antipatterns"] = format_antipatterns(ap)
                tokens_used += ap_tokens

        elif priority == "similar_decisions":
            sim = fetch_similar_decisions(domain, limit=3)
            sim_tokens = estimate_tokens(format_similar_decisions(sim))

            if tokens_used + sim_tokens < available_tokens:
                context["similar_decisions"] = format_similar_decisions(sim)
                tokens_used += sim_tokens

    return context
```

---

## 6. IMPLEMENTATION PHASES

### Phase 2A: Skill Generator (1-2 weeks)
**Status:** To do

**Files to Create:**
- `src/membria/skill_generator.py` - Core generation logic
- `src/membria/skill_validator.py` - Validation before publishing
- `tests/test_skill_generator.py` - Comprehensive tests

**Files to Modify:**
- `src/membria/graph.py` - Add create_skill, update_skill methods
- `src/membria/models.py` - Add Skill dataclass (if not already present)
- `src/membria/graph_queries.py` - Add skill queries

**Key Functions:**
```python
class SkillGenerator:
    def generate_skills_for_domain(domain: str) -> List[Skill]
    def extract_patterns(decisions, outcomes) -> Dict
    def analyze_antipatterns(patterns) -> List[Antipattern]
    def generate_procedure(patterns, antipatterns) -> str
    def create_skill(domain, patterns, antipatterns) -> Skill
    def validate_skill(skill) -> bool
    def publish_skill(skill) -> bool
```

**Success Criteria:**
- [x] Queries all decisions in a domain
- [x] Calculates success rates per alternative
- [x] Generates Markdown procedure
- [x] Creates Skill nodes in FalkorDB
- [x] 85% test coverage
- [x] Can regenerate skills incrementally (fast)

### Phase 2B: MCP Context Injection (2 weeks)
**Status:** To do

**Files to Create:**
- `src/membria/mcp_context_builder.py` - Build context payloads
- `src/membria/context_prioritizer.py` - Token budget awareness
- `tests/test_mcp_context.py` - Injection tests

**Files to Modify:**
- `src/membria/mcp_server.py` - Add context injection resources
- `src/membria/decision_surface.py` - Use MCP context

**Key Endpoints:**
```
GET /mcp/resources/decision_history?domain=auth_strategy
GET /mcp/resources/team_calibration?domain=auth_strategy
GET /mcp/resources/applicable_skills?domain=auth_strategy
GET /mcp/resources/antipatterns?domain=auth_strategy
GET /mcp/resources/similar_decisions?domain=auth_strategy&statement=...
```

**Success Criteria:**
- [x] MCP server exposes all 5 context resource types
- [x] Context respects available token budget
- [x] Prioritizes highest-value context
- [x] Claude Code receives injection without errors
- [x] Integration tests with real Claude Code

### Phase 2C: Outcome Tracking (1-2 weeks)
**Status:** In Progress (partial)

**Files Already Exist:**
- `src/membria/outcome_tracker.py` - Core logic (partial)
- `src/membria/webhook_handler.py` - GitHub webhooks (partial)

**Files to Complete:**
- `src/membria/signal_detector.py` - Extract signals from webhooks
- `src/membria/metrics_collector.py` - Gather metrics from monitoring
- `tests/test_outcome_tracking.py` - End-to-end tests

**Key Functions:**
```python
class OutcomeTracker:
    def create_outcome(decision_id: str) -> Outcome
    def add_signal(outcome_id: str, signal: Signal) -> None
    def complete_outcome(outcome_id: str) -> Outcome
    def calculate_score(outcome: Outcome) -> float
```

**Webhook Integration:**
```
POST /webhooks/github/pull_request
  - On PR created: create Signal(PR_CREATED)
  - On PR merged: create Signal(PR_MERGED), update status

POST /webhooks/circleci/build
  - On build passed: create Signal(CI_PASSED)
  - On build failed: create Signal(CI_FAILED)

POST /webhooks/datadog/alert
  - On incident triggered: create Signal(INCIDENT)
  - On incident resolved: create Signal(INCIDENT_RESOLVED)
```

**Success Criteria:**
- [x] Signals captured from GitHub, CI, monitoring
- [x] Outcomes aggregated from signals
- [x] Final score calculated (0.0-1.0)
- [x] 30-day observation window enforced
- [x] Dashboard shows outcome trends

### Phase 2D: Calibration Loop (1 week)
**Status:** In Progress (partial)

**Files Already Exist:**
- `src/membria/calibration_models.py` - Beta distribution (complete)
- `src/membria/calibration_updater.py` - Update logic (partial)

**Files to Complete:**
- `src/membria/calibration_runner.py` - Scheduled updater
- `src/membria/confidence_adjuster.py` - Make recommendations
- `tests/test_calibration.py` - Statistical tests

**Key Functions:**
```python
class CalibrationUpdater:
    def update_from_outcome(outcome: Outcome) -> None
    def calculate_gap(predicted_conf, actual_success) -> float
    def recommend_adjustment(gap: float) -> float
    def detect_trend(recent_outcomes: List) -> str
```

**Scheduler:**
```python
# Run hourly (or on demand)
for domain in all_domains:
    outcomes = get_completed_outcomes_since_last_update(domain)
    for outcome in outcomes:
        calibration_updater.update_from_outcome(outcome)
```

**Success Criteria:**
- [x] Beta distribution updated from outcomes
- [x] Confidence gap calculated
- [x] Trends detected (improving/stable/declining)
- [x] Recommendations generated
- [x] Historical calibration data retained

---

## 7. INTEGRATION EXAMPLE: End-to-End Flow

### 7.1 Developer Makes Decision (T=0)

**In Claude Code:**
```
Developer: "We need to implement OAuth 2.0"

Claude Code detects: DECISION task (not tactical)
MCP daemon intercepts and injects context:

"MEMBRIA DECISION CONTEXT: auth_strategy

Your team's experience (9 auth decisions, 30 days tracking):
- Success rate: 80%
- Team's typical confidence: 78%
- Confidence gap: -2% (well-calibrated)

SKILL AVAILABLE: auth_strategy_recommendation
- Success rate: 88%
- Procedure:
  IF simple_oauth_flow:
    STRONGLY_RECOMMEND Auth0 (89% success, 8/9)
  ELIF custom_scopes_needed:
    CONSIDER Firebase Auth (87% success, 7/8)
  ELSE:
    AVOID Custom JWT (20% success, 2/10)

ANTIPATTERNS TO AVOID:
- Custom JWT: 80% failure rate
  Root causes: Token refresh (4x), Scope mgmt (3x), Perf (1x)
  Firewall: WARN (can override with justification)

SIMILAR DECISIONS:
- D-001: "Use Auth0 for SPA" → SUCCESS (99.98% uptime, 0 incidents)
- D-012: "Firebase Auth for admin" → SUCCESS (99.95% uptime, 2 minor bugs)
"

Claude Code: "Based on your team's experience, I recommend Auth0."
Developer: "Agreed. Let's use Auth0."
```

### 7.2 Decision Captured (T=0+1min)

**In Membria:**
```python
decision = Decision(
    decision_id="d-2026-02-12-001",
    statement="Implement OAuth 2.0 with Auth0",
    alternatives=["Custom JWT", "Firebase Auth", "Keycloak"],
    assumptions=["Auth0 free tier sufficient", "Latency < 100ms"],
    predicted_outcome={
        "timeline": "1 week",
        "success_criteria": ["Production auth", "No critical bugs"]
    },
    confidence=0.85,  # Adjusted from team calibration
    domain="auth_strategy",
    created_by="alice@company.com",
    created_in="claude-code",
    status="pending"
)

graph_client.add_decision(decision)
```

### 7.3 Code Implementation (T=0+2hours)

**GitHub:**
```
Developer pushes code
PR created: #123
```

**In Membria:**
```python
# Webhook from GitHub
outcome = graph_client.create_outcome(decision_id="d-2026-02-12-001")
signal = Signal(
    signal_type=SignalType.PR_CREATED,
    valence=SignalValence.NEUTRAL,
    description="PR #123 created for Auth0 implementation",
    source="github",
    source_id="github/pulls/123"
)
outcome.add_signal(signal)
```

### 7.4 Merge & Deploy (T=0+3days)

**GitHub:**
```
PR reviewed and merged
CI pipeline: all tests pass
Deploy to production
```

**In Membria:**
```python
outcome.add_signal(Signal(PR_MERGED, POSITIVE, "PR #123 merged"))
outcome.add_signal(Signal(CI_PASSED, POSITIVE, "All tests pass"))
outcome.add_signal(Signal(STABILITY_OK, POSITIVE, "No errors in first 24h"))

# Update status
outcome.status = "merged"
outcome.merged_at = datetime.now()
```

### 7.5 Production Observation (T=0+30days)

**Monitoring & Incidents:**
```
Day 3: "P99 latency 45ms (vs 100ms predicted)" → POSITIVE signal
Day 8: "Zero incidents, 99.98% uptime" → POSITIVE signal
Day 30: Outcome complete
```

**In Membria:**
```python
outcome.add_signal(Signal(
    PERFORMANCE_OK, POSITIVE,
    "P99 latency 45ms vs 100ms predicted"
))

outcome.status = "completed"
outcome.completed_at = datetime.now()
outcome.final_status = "success"
outcome.final_score = 0.95  # Exceeded expectations
outcome.metrics = {
    "uptime_percent": 99.98,
    "avg_latency_ms": 45.0,
    "p99_latency_ms": 120.0,
    "bug_count": 0,
    "incident_count": 0
}

graph_client.update_outcome(outcome)
```

### 7.6 Calibration Update (T=0+30days+1hour)

**Scheduled Task:**
```python
# CalibrationUpdater runs
outcomes = graph_client.get_completed_outcomes(domain="auth_strategy")
# outcomes = [o-001 (success), o-002 (success), o-003 (partial), ...]

for outcome in outcomes:
    decision = graph_client.get_decision(outcome.decision_id)

    # Update Beta distribution
    if outcome.final_status == "success":
        profile.alpha += 1  # 8 → 9

    profile.success_rate = 9 / (9 + 2)  # 0.818 → 0.81
    profile.last_updated = datetime.now()

    # Calculate gap
    gap = decision.confidence - outcome.final_score
    # gap = 0.85 - 0.95 = -0.10 (underconfident by 10%)

    profile.confidence_gap = gap
    profile.trend = detect_trend(outcomes[-7:])  # Last 7

    graph_client.update_calibration(profile)
```

### 7.7 Skill Regeneration (T=0+30days+2hours)

**Skill Generator (triggered after 5 new outcomes):**
```python
# Query all auth_strategy decisions
decisions = graph_client.get_decisions(domain="auth_strategy")
outcomes = graph_client.get_outcomes_for_decisions(decisions)

# Extract patterns
patterns = {
    "Auth0": {"success": 9, "total": 10, "rate": 0.90},
    "Custom JWT": {"success": 2, "total": 10, "rate": 0.20},
    "Firebase Auth": {"success": 7, "total": 8, "rate": 0.88}
}

# Generate skill
skill_v2 = Skill(
    skill_id="sk-auth_strategy_recommendation-v2",
    version=2,
    previous_version_id="sk-auth_strategy_recommendation-v1",
    success_rate=0.86,  # Average across domain
    sample_size=28,  # Total decisions observed
    procedure="""
    ## Authentication Strategy

    Based on 28 decisions over 90 days:

    ### Strongly Recommend
    - **Auth0** (90% success, 9/10)
    - **Firebase Auth** (88% success, 7/8)

    ### Avoid
    - **Custom JWT** (20% success, 2/10)
      Root causes: Token refresh (40%), Scope mgmt (30%), Perf (10%)
    """,
    quality_score=0.88,
    generated_from_decisions=[
        "d-2026-02-01-001", "d-2026-02-05-002", ..., "d-2026-02-12-001"
    ]
)

graph_client.create_skill(skill_v2)
graph_client.mark_previous_as_superseded(skill_v1)
```

### 7.8 Next Developer Benefits (T=0+35days)

**New developer in Claude Code:**
```
Developer: "We need auth for a new service"

MCP daemon injects:

"MEMBRIA DECISION CONTEXT: auth_strategy

Your team's experience (10 auth decisions, 90 days tracking):
- Success rate: 86%
- Recent skill: auth_strategy_recommendation-v2 (88% success)
- Latest update: 5 days ago

SKILL UPDATED:
After Auth0 success with P99 latency 45ms (vs 100ms assumed):
- Auth0: 90% success (9/10) [IMPROVED from 89%]
- Firebase Auth: 88% success (7/8)
- Custom JWT: 20% success (2/10) [FLAGGED]

RECOMMENDATION:
Use Auth0 for standard OAuth flows (90% success rate, latest positive outcome)
"

Claude Code: "Your team has strong experience with Auth0. I recommend it."
Developer: "Great, proceed with Auth0."
```

**Process repeats**: decision → code → outcome → calibration → skill improvement

---

## 8. SUCCESS METRICS

### 8.1 Skill Quality

- **Success Rate**: Percentage of decisions following skill succeeded
- **Confidence**: Derived from Beta distribution (higher sample = higher confidence)
- **Quality Score**: 0.0-1.0 (based on success rate + sample size)
- **Sample Size**: Minimum 5 before skill is "confident", 10+ for "strong"

### 8.2 Team Calibration

- **Confidence Gap**: |predicted - actual| < 0.10 = well-calibrated
- **Trend**: Improving/stable/declining over 30-day windows
- **Trend Strength**: Consistent direction over 3+ periods

### 8.3 Outcome Tracking

- **Signal Coverage**: % of decisions with at least 3 signals
- **Observation Completeness**: % of decisions followed 30-day window
- **Metric Reliability**: % of outcomes with quantified metrics

### 8.4 Business Impact

- **Decision Quality**: Decisions made with skill context succeed 85%+ (vs 70% without)
- **Time Saved**: Developers spend <2 min on decision (vs 20 min manually researching)
- **Knowledge Retention**: New hires onboard 25% faster with access to skills
- **Incident Reduction**: Decisions following antipattern warnings have 80% fewer incidents

---

## 9. EDGE CASES & HANDLING

### 9.1 Cold Start Problem

**Scenario:** New domain with no historical decisions

**Solution:**
- Start with confidence interval (0.3, 0.7)
- No skill generation until 5 outcomes
- MCP injects: "No team experience yet. Requires careful analysis."
- After 5 outcomes, generate skill-v1 with low quality_score

### 9.2 Decision Reversal

**Scenario:** Decision made, code started, then reversed before completion

**Solution:**
- Outcome status: "abandoned"
- Mark signals: "abandoned" (valence=neutral)
- Don't include in success/failure calibration
- Still capture as learning ("we tried X and decided against it because Y")

### 9.3 Conflicting Outcomes

**Scenario:** Decision A succeeded for team X but failed for team Y in same domain

**Solution:**
- Calibration per domain (not per team initially)
- In skill, mark as "context-dependent"
- In applicability zones: mark conditions where each option works
- MCP injection: "This domain has conflicting patterns. Team A succeeded with X, Team B with Y."

### 9.4 Skill Decay

**Scenario:** Skill generated 12 months ago, technology landscape changed

**Solution:**
- Mark skill: next_review = skill.last_updated + 90 days
- On review date, trigger regeneration
- If new data contradicts old skill, create new version
- Keep history (skill_v1, skill_v2, ...) for audit

### 9.5 Statistically Insufficient Data

**Scenario:** Domain with 2 outcomes (not enough for confidence)

**Solution:**
- Skill quality_score < 0.5
- MCP injection: "Early data. Recommendations provisional. Need 5+ outcomes for confidence."
- Still generate skill (helps drive discussion) but flag low confidence

---

## 10. TESTING STRATEGY

### 10.1 Unit Tests

```python
# test_skill_generator.py
def test_extract_patterns_success_rate()
def test_antipattern_detection_threshold()
def test_procedure_generation_format()
def test_quality_score_calculation()

# test_calibration.py
def test_beta_update_success()
def test_beta_update_failure()
def test_confidence_gap_calculation()
def test_trend_detection()

# test_mcp_context.py
def test_context_injection_format()
def test_token_budget_respect()
def test_context_prioritization()
```

### 10.2 Integration Tests

```python
# test_full_pipeline.py
def test_decision_to_skill_generation():
    """Full pipeline: decision → outcomes → skill generation"""
    # 1. Create 10 decisions in auth_strategy domain
    # 2. Create outcomes (8 success, 2 failure)
    # 3. Run skill generator
    # 4. Assert skill created with 80% success rate
    # 5. Assert procedure contains recommendations

def test_mcp_injection_to_claude_code():
    """Context injection to Claude Code MCP server"""
    # 1. Query MCP resources with domain=auth_strategy
    # 2. Assert response contains skills + calibration + antipatterns
    # 3. Assert total token size < 2000

def test_calibration_loop_convergence():
    """Calibration improves over time"""
    # 1. Start with gap = 0.2 (overconfident)
    # 2. Add outcomes showing actual < predicted
    # 3. Assert gap shrinks after each update
    # 4. Assert recommendation reduces confidence

def test_antipattern_blocking():
    """Antipattern firewall prevents bad decisions"""
    # 1. Create antipattern: custom_jwt (80% failure)
    # 2. Developer tries custom_jwt
    # 3. Assert firewall returns "warn"
    # 4. Developer tries with override flag
    # 5. Assert logged in audit trail
```

### 10.3 Regression Tests

- Historical skills maintain accuracy
- Calibration doesn't regress
- MCP responses consistent format
- No data loss during migrations

---

## 11. PERFORMANCE CONSIDERATIONS

### 11.1 Query Performance

**Problem:** Large graphs (10k+ decisions) slow down queries

**Solution:**
- Index on domain, status, created_at
- Limit similarity queries to last 90 days
- Cache frequently accessed skills (Redis)

### 11.2 Skill Generation Performance

**Problem:** Generating skill from 1000 decisions is slow

**Solution:**
- Batch process: only regenerate on trigger (5 new outcomes)
- Use incremental updates (add new decision to existing pattern)
- Cache pattern aggregates

### 11.3 MCP Injection Latency

**Problem:** Developer waits for context injection (latency-critical)

**Solution:**
- Cache all context resources (TTL 1 hour)
- Return cached + async refresh in background
- Prioritize top-3 most-relevant resources (budget aware)

---

## 12. SECURITY & AUDIT

### 12.1 Decision Privacy

- Decisions stored on-prem (not cloud)
- Accessible only to team members
- Git history immutable (decisions reference commit SHAs)

### 12.2 Override Audit Trail

When developer overrides firewall (WARN → PROCEED):
```python
override_log = {
    "timestamp": datetime.now(),
    "developer": "alice@company.com",
    "antipattern": "custom_jwt",
    "decision_id": "d-2026-02-12-001",
    "justification": "Legacy API requires custom JWT",
    "outcome_tracked": True  # We'll measure if it fails
}
```

### 12.3 Skill Reproducibility

- Every skill references the decisions it was generated from
- Skill generation queries are versioned
- Can re-generate at any time and compare

---

**End of Specification**
