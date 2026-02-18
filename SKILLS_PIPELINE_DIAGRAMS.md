# Membria Skills Pipeline: Visual Diagrams

---

## 1. FULL CLOSED-LOOP PIPELINE

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║              MEMBRIA SKILLS ARCHITECTURE: DECISION → SKILL → BEHAVIOR              ║
║                                                                                    ║
║                            (Compounding Intelligence Loop)                         ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝

                                    ┌─────────────────┐
                                    │  DAY 0          │
                                    │  Decision Made  │
                                    └────────┬────────┘
                                             │
                ┌────────────────────────────┼────────────────────────────┐
                │                            │                            │
                ▼                            ▼                            ▼
        ┌──────────────┐            ┌──────────────┐            ┌──────────────┐
        │ Tactical     │            │ Decision     │            │ Learning     │
        │ Tasks        │            │ (Main Flow)  │            │ Observations │
        │ (Immediate   │            │              │            │ (Feedback)   │
        │  code gen)   │            │ • Context    │            │              │
        └──────────────┘            │ • Inject     │            └──────────────┘
                                    │ • Capture    │
                                    │ • Store      │
                                    └────────┬─────┘
                                             │
                                             │ ┌──────────────────┐
                                             ├─┤ MCP Injects:     │
                                             │ │ • Skills         │
                                             │ │ • Calibration    │
                                             │ │ • Antipatterns   │
                                             │ └──────────────────┘
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    │                                                 │
                    ▼                                                 ▼
         ┌──────────────────────┐                        ┌──────────────────────┐
         │ Decision Node        │                        │ Claude Code          │
         │ Created in FalkorDB  │                        │ Receives Context     │
         │                      │                        │ Makes Informed       │
         │ • statement          │                        │ Decision             │
         │ • alternatives       │                        │ (90% accuracy vs 70%)│
         │ • assumptions        │                        │                      │
         │ • predicted_outcome  │                        │ "Use Auth0"          │
         │ • confidence: 0.85   │                        └──────────────────────┘
         │ • context_hash       │                                   │
         │                      │                                   │
         │ Status: pending      │                                   ▼
         └──────────┬───────────┘                        ┌──────────────────────┐
                    │                                    │ Developer's Code     │
                    │                                    │ (Auth0 + GitHub PR)  │
                    │                                    └──────────┬───────────┘
                    │                                               │
                    │                    ┌──────────────────────────┴───────────┐
                    │                    │   30-DAY OBSERVATION WINDOW            │
                    │                    └──────────────────────────┬────────────┘
                    │                                               │
                    │                    ┌──────────────────────────┴──────────────────┐
                    │                    │                                            │
                    │         ┌──────────┴──────────┐                    ┌───────────┴──────────┐
                    │         │                     │                    │                      │
                    │         ▼                     ▼                    ▼                      ▼
                    │    ┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
                    │    │ Day 0-3  │         │ Day 4-14 │         │ Day 15-28│         │ Day 29-30│
                    │    │          │         │          │         │          │         │          │
                    │    │ PR #123  │         │ PR merged│         │ All tests│         │ Metrics  │
                    │    │ created  │         │ Deploy   │         │ pass     │         │ finalized│
                    │    │          │         │          │         │ P99: 45ms│         │          │
                    │    │ Signal:  │         │ Signals: │         │          │         │ Final:   │
                    │    │ PR_CREAT │         │ MERGED   │         │ Signal:  │         │ SUCCESS  │
                    │    │ _ED      │         │ CI_PASS  │         │ PERF_OK  │         │ Score: 1.0
                    │    │          │         │ DEPLOY   │         │          │         │          │
                    │    └────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘
                    │         │                    │                    │                    │
                    │         └────────┬───────────┴────────────────────┴────────────────────┘
                    │                  │
                    │                  ▼
                    │        ┌──────────────────────┐
                    │        │ Outcome Node         │
                    │        │ Completed            │
                    │        │                      │
                    │        │ • status: merged     │
                    │        │ • final_status: succ │
                    │        │ • final_score: 0.95  │
                    │        │ • metrics:           │
                    │        │   - uptime: 99.98%   │
                    │        │   - latency: 45ms    │
                    │        │   - bugs: 0          │
                    │        │   - incidents: 0     │
                    │        │                      │
                    │        │ Status: completed    │
                    └───────→└──────────┬───────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
          ┌─────────────────────┐            ┌─────────────────────┐
          │ Calibration Update  │            │ Skill Generation    │
          │ (Beta Distribution) │            │ (Pattern Extraction)│
          │                     │            │                     │
          │ alpha += 1          │            │ Query: All          │
          │ success_rate: 0.80  │            │ auth_strategy       │
          │ → 0.81              │            │ decisions (8 succ,  │
          │                     │            │ 2 fail)             │
          │ gap = 0.85 - 0.95   │            │                     │
          │     = -0.10         │            │ Rate: 8/10 = 80%    │
          │ (underconfident)    │            │                     │
          │                     │            │ Generate Skill-v2:  │
          │ trend: improving    │            │ • procedure:        │
          │                     │            │   IF oauth:         │
          │ Recommend: confidence│           │     USE Auth0 (80%) │
          │ can stay 0.80-0.85  │            │   AVOID JWT (20%)   │
          │                     │            │                     │
          │ Status: Updated     │            │ • quality: 0.80     │
          │ Next review: 90d    │            │ • sample_size: 10   │
          │                     │            │                     │
          │ Node: stored in DB  │            │ Status: Published   │
          └──────────┬──────────┘            └──────────┬──────────┘
                     │                                  │
                     │                                  ▼
                     │                        ┌─────────────────────┐
                     │                        │ Skill Node (v2)     │
                     │                        │ In FalkorDB         │
                     │                        │                     │
                     │                        │ skill_id: sk-       │
                     │                        │   auth_strategy-v2  │
                     │                        │ success_rate: 0.80  │
                     │                        │ confidence: 0.80    │
                     │                        │ sample_size: 10     │
                     │                        │                     │
                     │                        │ procedure:          │
                     │                        │ "IF oauth..."       │
                     │                        │                     │
                     │                        │ Status: active      │
                     │                        │ Version: 2          │
                     └────────────┬───────────→ Prev version: v1    │
                                  │            (superseded)        │
                                  │                                │
                                  │            Related:            │
                                  │            • generated_from:   │
                                  │              [d-001...d-010]   │
                                  │            • antipatterns:     │
                                  │              [custom_jwt]      │
                                  │                                │
                                  └─────────────────────┬──────────┘
                                                        │
                    ┌───────────────────────────────────┴─────────────────────────────┐
                    │                                                                 │
                    │  (Days 31+: Next Developer Benefits)                            │
                    │                                                                 │
                    ▼                                                                 ▼
          ┌──────────────────────┐                            ┌──────────────────────┐
          │ Developer 2          │                            │ MCP Context          │
          │ "Need OAuth"         │                            │ Injected:            │
          │                      │                            │                      │
          │ Claude Code detects: │                            │ "Your team's         │
          │ DECISION             │                            │ Auth0: 80% success   │
          │                      │                            │ (10 decisions,       │
          │ Context injected:    │◄───────────────────────────┤ latest skill v2)     │
          │ • Skill: sk-auth..v2 │                            │                      │
          │   (80% success rate) │                            │ Confidence: 0.85     │
          │ • Calibration:       │                            │ (adjust to 0.80-0.85)│
          │   success: 80%,      │                            │                      │
          │   confidence: 0.85   │                            │ AVOID: Custom JWT    │
          │ • Similar decisions: │                            │ (20% success)        │
          │   Dev 1 used Auth0   │                            │                      │
          │   → SUCCESS          │                            │ Antipattern Warnings:│
          │                      │                            │ Custom JWT: WARN     │
          │ Makes decision:      │                            │ (8 failures)         │
          │ "Use Auth0"          │                            │ Root: token refresh  │
          │ (90% accuracy)       │                            └──────────────────────┘
          │                      │
          │ (New cycle begins)   │
          └──────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                    ║
║   KEY INSIGHT: Each outcome makes the system smarter                              ║
║   - 1st outcome:   Skill generated (1 data point, low confidence)                 ║
║   - 5th outcome:   Patterns clear, recommendations strong                         ║
║   - 10th outcome:  Confidence intervals narrow, calibration tight                 ║
║   - 30th outcome:  Skill trusted by team, compounding advantage grows             ║
║                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. DECISION CONTEXT INJECTION FLOW

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│        DEVELOPER MAKES DECISION → MCP INJECTS CONTEXT → CLAUDE RESPONDS        │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────────────┐
                          │ Developer's Prompt      │
                          │ "We need OAuth 2.0"     │
                          └────────────┬────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │ Task Router             │
                          │ (Decision Classifier)   │
                          │                         │
                          │ "DECISION task detected"│
                          │ domain = "auth_strategy"│
                          └────────────┬────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
        ┌──────────────────────┐          ┌──────────────────────┐
        │ MCP Context Fetcher  │          │ Reasoning Graph      │
        │                      │          │ Queries              │
        │ Triggered:           │          │                      │
        │ • Domain = auth_...  │          │ ├─ Find skills       │
        │ • Available tokens   │          │ │   for domain       │
        │ • Priority list      │          │ ├─ Get calibration  │
        │                      │          │ │   profile          │
        │ Token budget:        │◄─────────┤ ├─ Query similar    │
        │ • Remaining: 1500    │          │ │   decisions       │
        │ • Priority order:    │          │ ├─ Get antipatterns │
        │   1. Skills (600)    │          │ │   (high-failure)  │
        │   2. Calibration(200)│          │ └─ Compile evidence│
        │   3. Antipatterns(300)          └────────────────────┘
        │   4. Similar(400)    │
        │                      │
        └────────────┬─────────┘
                     │
                     │ (Parallel fetches)
                     │
      ┌──────────────┼──────────────┬───────────────────┬────────────────┐
      │              │              │                   │                │
      ▼              ▼              ▼                   ▼                ▼
   ┌──────┐      ┌──────┐      ┌─────────┐        ┌──────────┐    ┌─────────────┐
   │Skill │      │Calib  │      │Antipart │        │Similar   │    │Antipattern  │
   │Query │      │Query  │      │Query    │        │Decisions │    │Root Causes  │
   │      │      │       │      │         │        │Query     │    │Query        │
   │sk:   │      │CP:    │      │AP:      │        │          │    │             │
   │auth_ │      │domain │      │domain:  │        │MATCH (d  │    │MATCH (ap)   │
   │strg  │      │:auth_ │      │auth_str │        │:Decision)│    │WHERE        │
   │-v2   │      │strg   │      │         │        │-[:RESULT │    │failure_rate │
   │      │      │       │      │         │        │ED_IN]->( │    │> 0.5        │
   │Fetch │      │Success │      │Failure  │        │o:Outcome │    │RETURN root_ │
   │...   │      │rate:  │      │_rate:0.8│        │) RETURN │    │causes       │
   │      │      │0.80   │      │         │        │...      │    │             │
   │      │      │Gap:   │      │Firewall │        │         │    │custom_jwt:  │
   │      │      │-2%    │      │:WARN    │        │         │    │• Token      │
   │      │      │Trend: │      │         │        │         │    │  refresh(4) │
   │      │      │improv │      │         │        │         │    │• Scope mgmt │
   │      │      │ing    │      │         │        │         │    │  (3)        │
   └──────┘      └──────┘      └─────────┘        └──────────┘    │• Perf (1)   │
      │              │              │                   │            └─────────────┘
      │              │              │                   │                  │
      └──────────────┼──────────────┴───────────────────┴──────────────────┘
                     │
                     ▼
          ┌──────────────────────────────────┐
          │ Context Injection Assembly        │
          │ (Respecting token budget)         │
          │                                  │
          │ MEMBRIA_CONTEXT = {               │
          │   "skills": [                     │
          │     {                             │
          │       "name": "auth_strategy...  │
          │       "success_rate": 0.80,      │
          │       "procedure": "..."         │
          │     }                            │
          │   ],                             │
          │   "calibration": {                │
          │     "success_rate": 0.80,        │
          │     "confidence_gap": -0.02,     │
          │     "trend": "improving"         │
          │   },                             │
          │   "antipatterns": [               │
          │     {                             │
          │       "name": "Custom JWT",      │
          │       "failure_rate": 0.80,      │
          │       "root_causes": [...]       │
          │     }                            │
          │   ],                             │
          │   "similar_decisions": [          │
          │     {                             │
          │       "statement": "Auth0",      │
          │       "outcome": "SUCCESS"       │
          │     }                            │
          │   ]                              │
          │ }                                │
          │                                  │
          │ Size: 1,400 tokens (within 1,500)│
          └────────────┬─────────────────────┘
                       │
                       ▼
          ┌──────────────────────────────────┐
          │ MCP Resource Response             │
          │ (Streamed to Claude Code)         │
          │                                  │
          │ Your team's 10 auth decisions:   │
          │ • Success rate: 80%              │
          │ • Confidence: 85% (rec: 80-85%)  │
          │ • Trend: improving               │
          │                                  │
          │ Available skill:                 │
          │ auth_strategy_recommendation-v2  │
          │                                  │
          │ STRONGLY RECOMMEND:              │
          │ - Auth0 (80% success, 10 dec)   │
          │                                  │
          │ CONSIDER:                        │
          │ - Firebase Auth (88%, 8 dec)    │
          │                                  │
          │ AVOID:                           │
          │ - Custom JWT (20% success, 10)  │
          │   Root causes: token refresh (4),│
          │   scope management (3), perf (1) │
          │                                  │
          │ Similar decisions from your team:│
          │ - Dev1: "Use Auth0" → SUCCESS   │
          │ - Dev3: "Firebase Auth" → SUC.  │
          │                                  │
          │ Confidence guidance:             │
          │ Your team is well-calibrated for │
          │ this domain. 85% confidence is   │
          │ reasonable.                      │
          └────────────┬─────────────────────┘
                       │
                       ▼
          ┌──────────────────────────────────┐
          │ Claude Code LLM                  │
          │                                  │
          │ (Sees injected context)          │
          │                                  │
          │ "Your team's experience with     │
          │ authentication shows 80% success │
          │ using Auth0. Your team is        │
          │ well-calibrated. The generated   │
          │ skill strongly recommends Auth0. │
          │ Recent similar decision succeeded │
          │ with Auth0."                     │
          │                                  │
          │ Response:                        │
          │ "I recommend using Auth0.        │
          │ Your team has strong experience  │
          │ and recent success with it."     │
          │                                  │
          └────────────┬─────────────────────┘
                       │
                       ▼
          ┌──────────────────────────────────┐
          │ Developer's IDE                  │
          │                                  │
          │ Claude's Suggestion:             │
          │ "Use Auth0"                      │
          │                                  │
          │ Developer: "Yes, proceed"        │
          │                                  │
          │ New Decision created + captured  │
          │ in Membria                       │
          └──────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════╗
║  KEY: Without Membria                  With Membria                           ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║  Developer searches manually (20 min) → Claude gets context instantly (1 min)  ║
║  Decisions made 70% informed          → Decisions made 90% informed            ║
║  Knowledge lost when dev leaves        → Knowledge accumulates in skills       ║
║  Team repeats failures                 → Team learns from antipatterns        ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

---

## 3. SKILL GENERATION & IMPROVEMENT OVER TIME

```
                        SKILL GENERATION & MATURATION CYCLE

┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│         How a Domain Skill Improves as More Outcomes Arrive                   │
│         (Example: auth_strategy)                                              │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

WEEK 1 (1-4 decisions, cold start)
├─ Decision 1: "Use Auth0" → PENDING (waiting for outcome)
├─ Decision 2: "Use Firebase Auth" → PENDING
├─ Decision 3: "Use Custom JWT" → PENDING
└─ Decision 4: "Use Auth0" → PENDING

Status: No skill yet (< 5 outcomes)
Action: MCP injects "Early data. No team pattern yet. Recommend careful review."

───────────────────────────────────────────────────────────────────────────────

WEEK 2 (5 outcomes completed)
├─ Decision 1: "Use Auth0" → SUCCESS (uptime 99.98%, 0 incidents)
├─ Decision 2: "Firebase Auth" → SUCCESS (uptime 99.95%, 0 incidents)
├─ Decision 3: "Custom JWT" → FAILED (token refresh bugs)
├─ Decision 4: "Use Auth0" → SUCCESS (uptime 99.99%, 0 incidents)
└─ Decision 5: "Custom JWT" → FAILED (scope management bugs)

Analysis:
├─ Auth0: 2 success / 2 total = 100%
├─ Firebase Auth: 1 success / 1 total = 100%
└─ Custom JWT: 0 success / 2 total = 0%

SKILL-V1 GENERATED
├─ Name: auth_strategy_recommendation-v1
├─ Success rate: 67% (4/6 total)
├─ Quality score: 0.55 (low, small sample)
├─ Confidence: 0.67 (provisional)
├─ Procedure:
│   "STRONGLY RECOMMEND:
│    - Auth0 (100%, 2/2) ← Highest success
│    - Firebase Auth (100%, 1/1)
│    AVOID:
│    - Custom JWT (0%, 0/2) ← All failed"
│
└─ Antipatterns:
   └─ custom_jwt: 100% failure rate
      ├─ Root cause 1: Token refresh edge cases (2 instances)
      └─ Root cause 2: Scope management complexity (2 instances)

Status: MCP injects "Skill available but early. 5 decisions. Need 10+ for confidence."

───────────────────────────────────────────────────────────────────────────────

WEEK 4 (10 outcomes completed)
├─ Auth0:    8 success / 9 total  = 89%  (trending up)
├─ Firebase: 1 success / 1 total  = 100% (too few samples)
└─ Custom JWT: 0 success / 2 total = 0%  (consistent failure)

Calibration Update:
├─ Team's predicted confidence: 0.78
├─ Team's actual success: 0.80
├─ Confidence gap: -2% (well-calibrated! slightly cautious)
├─ Trend: IMPROVING (last 3 decisions succeeded)
└─ Recommendation: "Team is well-calibrated. Confidence 0.78 is appropriate."

SKILL-V2 GENERATED (Updated from v1)
├─ Name: auth_strategy_recommendation-v2
├─ Success rate: 80% (8/10 total)
├─ Quality score: 0.76 (better, larger sample, high success rate)
├─ Confidence: 0.80
├─ Procedure:
│   "STRONGLY RECOMMEND:
│    - Auth0 (89%, 8/9) ← Primary recommendation
│    CONSIDER:
│    - Firebase Auth (100%, 1/1) ← Promising but limited experience
│    AVOID:
│    - Custom JWT (0%, 2/2) ← Avoid unless issues addressed"
│
├─ Antipatterns:
│   └─ custom_jwt: 100% failure (2/2)
│       ├─ Issue 1: Token refresh (40% of failures)
│       └─ Issue 2: Scope management (40% of failures)
│
└─ Firewall Action: WARN (not BLOCK yet, but escalate to lead)

Status: MCP injects "Skill available and gaining confidence. 10 decisions. Strong for Auth0."

───────────────────────────────────────────────────────────────────────────────

WEEK 8 (20 outcomes completed)
├─ Auth0:          17 success / 19 total = 89%  (consolidated)
├─ Firebase Auth:  7 success / 8 total  = 88%  (consistent)
├─ Custom JWT:     0 success / 10 total = 0%   (persistently fails)
├─ Keycloak:       3 success / 3 total  = 100% (new, limited)
└─ AWS Cognito:    1 success / 1 total  = 100% (new, 1 decision)

Calibration Update:
├─ Team's success rate: 0.82
├─ Confidence gap: -1% (near-perfect calibration)
├─ Trend: STABLE (consistent 85%+ success)
└─ Recommendation: "Team is excellent at auth decisions. Confidence 0.78-0.85 ideal."

SKILL-V3 GENERATED
├─ Name: auth_strategy_recommendation-v3
├─ Success rate: 82% (16/20 total)
├─ Quality score: 0.85 (high! strong success, large sample)
├─ Confidence: 0.85 (high confidence in recommendations)
├─ Procedure:
│   "## Auth Strategy Recommendation (Based on 20 decisions, 82% success)
│
│    ### STRONGLY RECOMMEND (90%+ team success):
│    - Auth0: 89% success (17/19)
│      ├─ Pros: Proven at scale, handles edge cases
│      ├─ Cons: Free tier limited
│      └─ When to use: Standard OAuth 2.0 flows
│
│    - Firebase Auth: 88% success (7/8)
│      ├─ Pros: Simple setup, integrated with GCP
│      ├─ Cons: Limited custom scope support
│      └─ When to use: GCP-first projects with simple scopes
│
│    ### CONSIDER (if special requirements):
│    - Keycloak: 100% success (3/3)
│      ├─ Limited data but perfect record
│      ├─ Use when: Self-hosted needed, full control
│      └─ Risk: Unfamiliar to most team members
│
│    ### AVOID (high failure risk):
│    - Custom JWT: 0% success (0/10)
│      ├─ Failed 100% of the time
│      ├─ Root causes:
│      │  • Token refresh edge cases (40%)
│      │  • Scope management complexity (40%)
│      │  • Clock skew issues (10%)
│      └─ Mitigation: Use established library if unavoidable"
│
├─ Antipatterns (Updated):
│   └─ custom_jwt_oauth: 100% failure (10/10)
│       ├─ Firewall level: BLOCK (not just warn)
│       ├─ Root cause pattern identified
│       │   ├─ Type A (40%): Token refresh on scope change
│       │   ├─ Type B (40%): Scope claims misalignment
│       │   └─ Type C (20%): Other
│       └─ Exception process: "Lead approval required. Document assumptions."
│
└─ Applicability Matrix:
    ┌─────────────────────────────────────────────────┐
    │ GREEN (use confidently):                         │
    │ - Simple OAuth flow + any team size             │
    │ - GCP-first architecture                        │
    │ - Token lifetime < 1 hour                       │
    │ - Standard scopes (email, profile)              │
    │                                                 │
    │ YELLOW (review carefully):                      │
    │ - Complex scope requirements                    │
    │ - Long-lived tokens (> 24 hours)                │
    │ - Custom claim requirements                     │
    │                                                 │
    │ RED (block, needs exception):                   │
    │ - Custom JWT implementation                     │
    │ - Implementing token refresh logic              │
    │ - Custom scope claims (use library)             │
    └─────────────────────────────────────────────────┘

Status: MCP injects "Strong skill available. 20 decisions. Auth0/Firebase recommended
         with high confidence. Custom JWT BLOCKED."

───────────────────────────────────────────────────────────────────────────────

WEEK 12 (30 outcomes completed, full maturity)
├─ Auth0:          24 success / 27 total = 89%  (mature, large sample)
├─ Firebase Auth:  9 success / 10 total = 90%  (very strong)
├─ Custom JWT:     0 success / 15 total = 0%   (clear antipattern)
├─ Keycloak:       5 success / 5 total  = 100% (small but consistent)
└─ Others:         1 success / 2 total  = 50%

Team Calibration:
├─ Success rate: 0.83
├─ Confidence gap: -1% (excellent calibration)
├─ Trend: STABLE (sustained 80%+ success)
├─ Confidence interval (95%): [0.77, 0.89]
└─ Recommendation: "Team is expert in auth decisions. Confidence 0.80-0.85 appropriate."

SKILL-V4 GENERATED
├─ Name: auth_strategy_recommendation-v4
├─ Success rate: 83% (47/57 total)
├─ Quality score: 0.91 (excellent! large sample, high success)
├─ Confidence: 0.91 (very high confidence)
│
├─ Procedure (Refined):
│   "## Enterprise-Grade Auth Strategy Recommendations
│
│    ### Tier 1 (Recommended for 90%+ projects):
│    1. Auth0 (89% team success, 27 decisions)
│       ├─ Scenarios: SaaS, B2B, any company size
│       ├─ Success guaranteed if: [list of conditions]
│       └─ Expected metrics: 45ms latency, 99.98% uptime
│
│    2. Firebase Auth (90% team success, 10 decisions)
│       ├─ Scenarios: GCP-first, startup MVPs
│       ├─ Success guaranteed if: GCP account, simple scopes
│       └─ Expected metrics: 50ms latency, 99.99% uptime
│
│    ### Tier 2 (Specialized use cases):
│    - Keycloak (100%, 5 decisions): Self-hosted only
│    - AWS Cognito (100%, 2 decisions): AWS ecosystem
│
│    ### Anti-Tier (BLOCKED):
│    - Custom JWT (0% success, 15 failures)
│      └─ Exception: Requires CTO approval + risk assessment"
│
├─ Version History:
│   ├─ V1 (Week 2): Provisional (5 outcomes)
│   ├─ V2 (Week 4): Growing confidence (10 outcomes)
│   ├─ V3 (Week 8): Strong (20 outcomes)
│   └─ V4 (Week 12): Expert-level (30 outcomes)
│
└─ Metrics Over Time:
    Quality Score Trajectory:
    ┌─────────────────────────────────────────────────────┐
    │ 1.0 ┤
    │     │                                          v4
    │ 0.9 ┤                                        ●●
    │     │                              v3      ●
    │ 0.8 ┤                            ●●
    │     │                          ●
    │ 0.7 ┤                      v2●
    │     │                    ●
    │ 0.6 ┤                  ●
    │     │          v1    ●
    │ 0.5 ┤        ●●
    │     │      ●
    │ 0.4 ┤   ●
    │     ├──────┼──────┼──────┼──────┼──────┼──────┼──
    │     0     5     10     15     20     25     30 outcomes
    │
    │ Key insight: Quality = success_rate × (1 - 1/√sample_size)
    │ - Early (5):  0.55 (uncertain, small sample)
    │ - Medium (10): 0.76 (gaining confidence)
    │ - Mature (20): 0.85 (strong, reliable)
    │ - Expert (30): 0.91 (excellent, durable)
    └─────────────────────────────────────────────────────┘

Status: MCP injects "Expert-level skill available. 30 decisions. Auth0 = best choice.
         Firebase = strong alternative. Custom JWT = BLOCKED (100% failure)."


╔════════════════════════════════════════════════════════════════════════════════╗
║                       COMPOUNDING EFFECT VISUALIZATION                         ║
║                                                                                ║
║  Team Accuracy Over Time (with vs without Membria)                            ║
║                                                                                ║
║  100% ┤                                   WITH MEMBRIA (has skills)           ║
║       │                                   /                                   ║
║   90% ┤                                 /                                     ║
║       │                               /                                       ║
║   80% ┤                             / ← Improves as more outcomes arrive      ║
║       │                           /                                           ║
║   70% ┤    WITHOUT MEMBRIA       /                                            ║
║       │    (manual research)    /                                             ║
║   60% ┤      ~70% forever      /                                              ║
║       │         ▲▲▲▲▲▲▲▲▲▲▲▲                                                  ║
║       │         no improvement                                                ║
║   50% ┤         (knowledge lost)                                              ║
║       │                                                                       ║
║       ├──────────┼────────────┼────────────┼────────────┼────────────┤        ║
║       0         1mo           3mo          6mo           9mo         12mo     ║
║                                                                                ║
║  Compounding Advantage: Every month, Membria-using teams get smarter         ║
║  while non-Membria teams stay flat. By year 2, the gap is 20%+ accuracy!     ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

---

## 4. COMPARISON: MEMBRIA VS OTHER SYSTEMS

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│          HOW MEMBRIA DIFFERS FROM GSD, AIDER, CURSOR, AND COPILOT             │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ GSD (Get Shit Done)                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Structure:      CLAUDE.md → Phase-based planning                          │
│  Knowledge:      Static Markdown specs                                      │
│  Learning:       Manual (human updates PLAN.md after verification)        │
│  Feedback Loop:  Slow (human-driven)                                       │
│  Skill Gen:      None (specs are hand-written)                             │
│  Outcome Track:  Implicit (VERIFICATION.md)                               │
│                                                                              │
│  GSD Advantage:  Phase-based structure prevents context rot                │
│  GSD Problem:    Requires manual knowledge capture & update               │
│                                                                              │
│  MEMBRIA adds:   ✅ Automatic skill generation from outcomes               │
│                  ✅ Quantified team calibration                            │
│                  ✅ Automated outcome tracking                             │
│                  ✅ Closed feedback loop (decision → skill)               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Aider (Terminal AI Pair Programming)                                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Structure:      Repo map + conversation memory                            │
│  Knowledge:      Implicit in code signatures                               │
│  Learning:       Per-session only (stateless)                              │
│  Feedback Loop:  Immediate (code compiles/fails?)                          │
│  Skill Gen:      None                                                      │
│  Outcome Track:  Implicit (diffs shown in conversation)                   │
│                                                                              │
│  Aider Advantage: Simple, immediate feedback on code quality               │
│  Aider Problem:   Can't distinguish 30-day quality from day-1 quality     │
│                   Knowledge lost between sessions                           │
│                                                                              │
│  MEMBRIA adds:   ✅ Long-term outcome tracking (30 days, not 30 mins)     │
│                  ✅ Team-wide knowledge accumulation                       │
│                  ✅ Persistent skills across sessions                      │
│                  ✅ Learns from incidents, not just compilation            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Cursor IDE (VS Code + LLM)                                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Structure:      CLAUDE.md + project rules                                 │
│  Knowledge:      Static instructions                                       │
│  Learning:       None (CLAUDE.md is hand-maintained)                       │
│  Feedback Loop:  None (no outcome tracking)                                │
│  Skill Gen:      None                                                      │
│  Outcome Track:  None (accepts/rejects suggestions?)                       │
│                                                                              │
│  Cursor Advantage: Native IDE integration (always available)                │
│  Cursor Problem:  Context is static (doesn't evolve with team experience) │
│                  No learning from outcomes (user accepts but we never know │
│                  if it worked)                                             │
│                                                                              │
│  MEMBRIA adds:   ✅ Dynamic context (evolves from team outcomes)            │
│                  ✅ Outcome tracking (did the suggestion work?)            │
│                  ✅ Automatic calibration (adjusts confidence)             │
│                  ✅ Skills improve over time                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ GitHub Copilot (IDE + GitHub)                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Structure:      Custom instructions + @workspace context                  │
│  Knowledge:      Implicit in repo metadata                                 │
│  Learning:       None (PR metrics exist but unused)                        │
│  Feedback Loop:  Broken (GitHub has PR history, but Copilot can't use it) │
│  Skill Gen:      None                                                      │
│  Outcome Track:  Available in GitHub (PR metrics) but not consumed        │
│                                                                              │
│  Copilot Advantage: Access to GitHub PR/issue data (goldmine!)            │
│  Copilot Problem:   Doesn't use it. Can't learn from PR outcomes.         │
│                    Tragic disconnect: 3 years of data, but static prompts │
│                                                                              │
│  MEMBRIA adds:   ✅ Connects decisions to PR outcomes                       │
│                  ✅ Learns from PR success/failure patterns                │
│                  ✅ Auto-improves from GitHub webhook data                 │
│                  ✅ Generates skills from PR history                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Summary: What Makes Membria Different                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TOOL      │ Context │ Outcome │ Learning │ Skills │ Calibration          │
│            │ Inj.    │ Track   │ Loop     │ Gen    │ (Confidence)         │
│  ──────────┼─────────┼─────────┼──────────┼────────┼──────────────────────│
│  GSD       │   ✅    │    ❌   │    ❌    │   ❌   │       ❌              │
│  Aider     │   ✅    │    ❌   │    ❌    │   ❌   │       ❌              │
│  Cursor    │   ✅    │    ❌   │    ❌    │   ❌   │       ❌              │
│  Copilot   │   ✅    │    ❌   │    ❌    │   ❌   │       ❌              │
│  LangGraph │   ❌    │    ✅   │    ❌    │   ❌   │       ❌              │
│  ──────────┼─────────┼─────────┼──────────┼────────┼──────────────────────│
│  MEMBRIA   │   ✅    │    ✅   │    ✅    │   ✅   │       ✅              │
│            │ (MCP)   │(30-day) │(automated│(from   │ (Beta dist)          │
│            │         │ signals)│outcomes) │outcomes│                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Key Insight:
═════════════════════════════════════════════════════════════════════════════
Everyone does context injection (input).
No one does the FULL LOOP (decision → outcome → calibration → skill → behavior).

Membria's innovation: Close the feedback loop for the first time.
═════════════════════════════════════════════════════════════════════════════
```

---

## 5. SKILL QUALITY HEATMAP: When Is a Skill Trustworthy?

```
            SKILL QUALITY MATRIX: Sample Size vs Success Rate

            ┌─────────────────────────────────────────────────────┐
            │  GREEN (Trust this skill)    YELLOW (Be careful)    │
            │  BLUE (Promising)            RED (Don't use yet)    │
            └─────────────────────────────────────────────────────┘

Success     100% ┌────────────────────────────────────────────────┐
Rate        95%  │  🟦🟦🟦🟦🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩  ← Few decisions  │
            90%  │  🟦🟦🟦🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩                │
            85%  │  🟦🟦🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩                │
            80%  │  🟦🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩  STRONG          │
            75%  │  🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩                │
            70%  │  🟨🟨🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩                │
            65%  │  🟨🟨🟨🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩                │
            60%  │  🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩🟩🟩🟩🟩  Comfortable    │
            55%  │  🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩🟩🟩🟩                │
            50%  │  🟥🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩🟩🟩  Acceptable     │
            45%  │  🟥🟥🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩🟩                │
            40%  │  🟥🟥🟥🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩🟩                │
            35%  │  🟥🟥🟥🟥🟨🟨🟨🟨🟨🟨🟩🟩🟩🟩  Risky         │
            30%  │  🟥🟥🟥🟥🟥🟨🟨🟨🟨🟨🟨🟩🟩🟩                │
            25%  │  🟥🟥🟥🟥🟥🟥🟨🟨🟨🟨🟨🟨🟩🟩                │
            20%  │  🟥🟥🟥🟥🟥🟥🟥🟨🟨🟨🟨🟨🟨🟩  Not ready yet │
            15%  │  🟥🟥🟥🟥🟥🟥🟥🟥🟨🟨🟨🟨🟨🟩                │
            10%  │  🟥🟥🟥🟥🟥🟥🟥🟥🟥🟨🟨🟨🟨🟥                │
             5%  └────────────────────────────────────────────────┘
                  1   3   5   7   10  15  20  30  50  70  100 200+
                              Sample Size (# of decisions)

  Legend:
  🟩 GREEN  = Skill is reliable (quality_score > 0.80, high confidence)
             Use for important decisions, no approval needed

  🟦 BLUE   = Skill is promising (success rate > 80%, but few samples)
             Early signal of strong pattern
             Use with caution, document assumptions

  🟨 YELLOW = Skill is provisional (quality_score 0.50-0.80)
             Pattern emerging but needs more data
             Use for guidance, but get second opinion

  🟥 RED    = Skill not ready (quality_score < 0.50, or too few samples)
             Either low success rate or insufficient data
             Don't use for critical decisions

  Key Examples:
  ═══════════════════════════════════════════════════════════════════════════════

  Position                 Interpretation
  ─────────────────────────────────────────────────────────────────────────────
  Top-right (100%, 200):   "Auth0 for OAuth" — Definitely use this
                           (100 successes, 0 failures, trusted)

  Upper-middle (85%, 20):  "Firebase Auth" — Strong skill
                           (17 successes, 3 failures, good confidence)

  Middle-left (70%, 5):    "Keycloak" — Emerging pattern
                           (3.5 successes, 1.5 failures, too early to trust)
                           Quality score: ~0.60 (use with caution)

  Bottom-right (20%, 100): "Custom JWT" — Antipattern
                           (20 successes, 80 failures, strong negative)
                           DO NOT USE without exception approval

  Bottom-left (20%, 5):    "Unknown approach" — No data yet
                           (1 success, 4 failures, insufficient)
                           Needs 10+ more trials before recommendation
  ═══════════════════════════════════════════════════════════════════════════════

  How Membria Uses This Heatmap:
  ─────────────────────────────────────────────────────────────────────────────

  📍 GREEN zone:
     - MCP injects with high confidence
     - "Your team has 100% success with this"
     - Developer can proceed without discussion

  📍 BLUE zone:
     - MCP injects with medium confidence
     - "Promising pattern (few decisions)"
     - Recommend discussion if risky domain

  📍 YELLOW zone:
     - MCP injects with low confidence
     - "Early data, provisional"
     - Recommend getting second opinion

  📍 RED zone:
     - If success rate < 50%: Flag as antipattern
     - If success rate > 50% but low sample: "Not ready, need 10+ decisions"
     - Firewall blocks use unless explicitly overridden
```

---

**End of Diagrams**
