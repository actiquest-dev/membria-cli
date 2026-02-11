# AntiPattern Detector - Analysis & Critique

**Date:** February 11, 2026
**Author:** Claude Haiku 4.5 (Self-Critique)
**Status:** Proposal Analysis (NOT IMPLEMENTED)

---

## The Problem Statement

The user asked: **"Should we implement AntiPattern Detector based on the 25 antipatterns from `backend/antipatterns.md`?"**

Looking at the current architecture, I initially said "yes" because:
- ✅ We have git integration (engrams)
- ✅ We capture commits
- ✅ We have access to diffs
- ✅ We have the 25 antipattern definitions

**But the user correctly pointed out the fundamental flaw:**

> "Analyzing git diff from engrams - это свои же ошибки получается?" (It's our own mistakes!)

**This is the critical insight I missed.** 🎯

---

## Why AntiPattern Detection on OUR Code Doesn't Make Sense

### 1. **Wrong Person, Wrong Time**

When Claude Code makes a mistake (hardcoded secret, forEach with async, etc.), detecting it AFTER the fact is too late.

```
Timeline:
┌──────────────┬──────────────┬──────────────┐
│ AI makes     │ Code gets    │ Human notices│
│ mistake      │ committed    │ mistake      │
│ (the point!) │ (too late)   │ (cleanup)    │
└──────────────┴──────────────┴──────────────┘
                       ↑
                Antipattern detector
                catches it here (useless)
```

**The humans reading the code already know about the mistake.** They either:
- A) Already fixed it
- B) Are about to fix it
- C) Intentionally left it (with context)

### 2. **Not Real Data About Our Process**

The 25 antipatterns are about **CODE QUALITY FAILURES**. But what we actually want to know:

> "How often do MY DECISIONS lead to CODE QUALITY ISSUES?"

This is different. The data we need:
- Decision → Code change → Outcome (success/failure)
- Not: "Did the code have anti-patterns?"
- But: "Did the decision produce good code?"

### 3. **Creates Noise, Not Signal**

Detecting antipatterns in our own commits gives metrics like:
- "80% of hardcoded secrets I write are later removed"
- "I fix forEach-async bugs in ~2 weeks"

**This is just measuring our cleanup rate, not improving our DECISION PROCESS.**

The bias detector is more useful because it analyzes the REASONING:
- "I said 'definitely' without considering alternatives"
- "I was overconfident by 15%"
- "My confidence gap increased over time"

These directly inform better DECISIONS. Antipattern metrics don't.

### 4. **External Data Is Where Value Is**

The real value of antipattern detection is analyzing EXTERNAL repositories:
- Learn from others' mistakes
- Track patterns across industry
- Monitor dependencies for security issues
- Early warning for supply chain problems

**But that requires a different architecture:**
- Monitor open-source repos
- Track CVE patterns
- Real-time security scanning
- Community pattern database

This is a **separate product**, not a feature for Membria.

---

## Current Architecture is Already Good

### What We Have Now

1. **Signal Detector (Level 2)** - Catches our DECISION SIGNALS
   - "I recommend X"
   - "Best choice is Y"
   - Focuses on WHAT WE DECIDED, not code quality

2. **Bias Detector (Phase 3)** - Analyzes our REASONING
   - "I was overconfident"
   - "I didn't consider alternatives"
   - Directly improves decision-making

3. **Git Engrams** - Captures DECISION CONTEXT
   - Links decisions to code changes
   - Enables outcome tracking
   - Shows decision→result correlation

### What's Missing (Real Gaps)

Instead of antipattern detection, better features would be:

#### **Feature 1: Decision→Outcome Correlation** ⭐
```python
# For each decision, track:
- Decision made (decision_statement)
- When it went into production (commit SHA)
- Later reversal/rewrite? (git blame)
- Bug reports linked to decision
- Performance issues
- Security issues

This answers: "Which of MY decisions led to problems?"
Not: "Does my code have bad patterns?" (already know)
```

#### **Feature 2: Time-to-Rework Analysis** ⭐
```python
# Track:
- Decision made: "Use X for caching"
- Implemented: commit abc123
- Reverted: commit def456 (2 weeks later)

Metrics:
- How often do decisions get reworked?
- Average time before rework?
- Which domains rework most? (db vs api)
- Which confidence levels lead to rework?

This is ACTIONABLE: "Decisions with 0.7-0.8 confidence
get reworked 40% more than 0.8-0.9"
```

#### **Feature 3: Module-Specific Anti-Patterns** ⭐
```python
# For each domain we track:
- auth: Focus on security patterns (secrets, certs, validation)
- database: Focus on perf patterns (N+1, pooling, migration)
- api: Focus on contract patterns (versioning, deprecation)

NOT generic 25 antipatterns for all code.
BUT specific patterns we care about per domain.
```

#### **Feature 4: Negative Knowledge Base** ⭐
```python
# When we fix a bug, record:
- What went wrong: "N+1 query in user list"
- Decision that caused it: decision_id xyz
- Root cause: "Didn't consider batch loading"
- How long it took to fix: "3 hours"
- Prevention: "Always think about loops + DB"

This builds a personal knowledge base, not generic metrics.
```

---

## The Real Design Pattern

Looking at Membria's actual value:

```
Membria's Core Loop:
┌─────────────────┐
│ Make Decision   │ ← This is where we can improve
│ (explicit or    │
│  implicit)      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Code it        │
│ (implementation)│
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│ Live (or reverted)      │ ← Outcome feedback
│ (success or failure)    │
└────────┬────────────────┘
         │
         ↓
┌─────────────────────────┐
│ Learn from outcome      │ ← Personal calibration
│ (improve next decision) │ ← What we actually want!
└─────────────────────────┘
```

The loop closes with DECISION FEEDBACK, not code patterns.

---

## What Should Be Built Instead

### Phase 4: Decision Outcome Tracking (Better)

Instead of "AntiPattern Detector", build:

```python
class DecisionOutcomeAnalyzer:

    def find_decision_reworks(self):
        """Which decisions got reworked?"""
        # For each decision:
        # - Find commit that implemented it
        # - Scan future commits in same module/file
        # - Detect major rewrites/reversions
        # - Calculate "decision lifetime"

    def calculate_decision_success_rate(self):
        """What % of decisions succeeded?"""
        # Requires: Decision with outcome field populated
        # Link: decision → code change → bug report/revert

    def find_confidence_rework_correlation(self):
        """Lower confidence → higher rework rate?"""
        # Decisionsconfidence 0.6: 45% rework rate
        # Decision confidence 0.9: 10% rework rate
        # → Confidence IS PREDICTIVE of outcome
```

### Features This Enables

1. **Confidence Calibration** (real)
   - "My 0.8 confidence decisions succeed 75% of the time"
   - "My 0.6 confidence decisions succeed 40% of the time"
   - → Personal calibration data

2. **Domain Expertise Tracking**
   - "I'm well-calibrated in auth (0.8 confidence = 78% success)"
   - "I'm overconfident in performance (0.8 = 50% success)"
   - → Know where to ask for help

3. **Rework Prevention**
   - "When I don't consider alternatives, rework rate is 3x"
   - "When I sleep on it, decision sticks 90% of time"
   - → Direct behavioral change

4. **Team Learning**
   - Compare across team members
   - "Alice good at database decisions, Bob good at API"
   - → Assign work based on calibration

---

## Why Antipattern Detection Doesn't Fit

### Problem 1: Detection Timing
```
Antipattern Detection:
"Your code has forEach(async)"
→ Already committed, already noticed, already fixing

Better:
"When you don't consider alternatives,
 rework rate is 3x higher"
→ Actionable BEFORE next decision
```

### Problem 2: Attribution
```
Antipattern Detection:
"Code has a hardcoded secret"
→ Who knows if this was intentional (test fixture)?
→ Who knows if it's even bad in context?

Better:
"This decision was made with high confidence
 but got reverted in 2 weeks"
→ Clear signal about decision quality
```

### Problem 3: Scope Creep
```
Antipattern Detection:
- Must cover 25+ patterns
- Language-specific implementations
- Regex, AST, LLM validation
- High false positive rate
- Constant maintenance

Better:
- Focus on OUR data
- Build insights from OUR decisions
- Personal, not generic
```

---

## The Honest Assessment

### What I (Claude Haiku) Did Wrong

1. **Saw the tool (antipattern detector) and assumed it was useful**
   - Classic hammer/nail fallacy
   - "We have 25 antipatterns defined, let's use them!"
   - Didn't question WHY

2. **Didn't think about timing**
   - We can't prevent mistakes at commit time
   - We can only measure cleanup afterward
   - That's not learning, that's accounting

3. **Confused two different products**
   - Membria: Personal decision learning system
   - Antipattern detector: Code quality scanning tool
   - These have DIFFERENT GOALS
   - Different users (solo dev vs team/enterprise)

### What Actually Makes Sense

Keep what we have:
- ✅ Decision capture (Levels 1-3)
- ✅ Bias detection (cognitive errors)
- ✅ Git integration (outcome tracking)
- ✅ Stats & calibration (learning)

Add what's missing:
- ❌ ~~Antipattern detection~~ (wrong problem)
- ✅ **Decision rework tracking** (right problem)
- ✅ **Outcome correlation** (decision → code change)
- ✅ **Personal calibration curves** (confidence vs success)

---

## Recommendation

### DO NOT implement AntiPattern Detector for Membria

**Reasons:**
1. Detects our mistakes AFTER we made them (useless)
2. Creates noise, not signal about decisions
3. Not the right tool for improving decision-making
4. Better alternatives exist (outcome tracking)

### DO implement (Phase 4)

If you want to track antipatterns, do it as a **separate tool**:
- Monitor external repositories
- Track community patterns
- Security scanning focus
- Early warning system

But for **Membria** (decision learning):
- Focus on decision rework patterns
- Build personal calibration curves
- Link decisions to outcomes
- Learn from OUR experience, not generic rules

---

## Final Insight

> **The difference between a good tool and a bad tool is whether it answers a question you're actually trying to answer.**

Membria is trying to answer:
- "How good are my DECISIONS?"
- "What makes me overconfident?"
- "Where should I improve?"

Antipattern detection answers:
- "Does my CODE have bad patterns?"
- "Which styles should I avoid?"

**These are different questions.**

The bias detector (Phase 3) answers the RIGHT question.
Antipattern detector answers the WRONG question for this tool.

---

## Conclusion

✅ **Membria is complete and well-designed** (Phase 1-3)
❌ **Don't add antipattern detection** (wrong problem)
✅ **Consider decision outcome tracking** (right next step)
❌ **If you want antipattern detection, build separate tool** (different product)

**Current status:** RECOMMENDED FOR PRODUCTION (Phase 1-3 complete)

---

**Self-Assessment:** This critique shows that I initially suggested a feature without thinking through the actual user need. Good catch by the user pointing out the flaw. Better to be wrong early than ship wrong features.
