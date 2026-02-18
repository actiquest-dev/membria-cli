# Membria Interactive Shell: Phase 1 Requirements

**Дата:** 2026-02-15  
**Версия:** 1.0  
**Статус:** В разработке 🔄

> **🐛 BUGFIX (2026-02-15):** Resolved white screen hang on startup
> - Fixed splash screen animation timeout
> - Added Ctrl+C signal handlers
> - Added `--no-splash` flag for fallback mode
> - Simplified default splash screen (removed large ASCII logo)

---

## 📋 EXECUTIVE SUMMARY

Membria CLI Phase 1 — это **интерактивный shell для оркестрации многомодельной команды разработки** с памятью о прошлых решениях и их результатах.

**Ключевое отличие от конкурентов:**
- ✅ Decision Memory (подобно Git, но для решений)
- ✅ Bayesian Calibration (знаем, когда AI ошибается)
- ✅ Council Orchestration (5 ролей, не 1 модель)
- ✅ NegativeKnowledge (блокируем известные ошибки)

---

## **1. MEMBRIA ARCHITECTURE (6 слоёв)**

```
┌─────────────────────────────────────────────────────┐
│ LAYER 6: Interactive Shell (Phase 1) ← ЗДЕСЬ НЫ    │
│ • Textual TUI: Header/Messages/Input/Footer        │
│ • /commands routing                                 │
│ • Real-time progress                                │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│ LAYER 5: Council (ролевая модель) — Phase 2        │
│ • Architect (Claude), Senior, Junior, Reviewer      │
│ • 3 режима: Pipeline/FanOut/Specialist              │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│ LAYER 4: Multi-LLM Orchestration — Phase 2          │
│ • Task Router, Splitter, Executor, Merger           │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│ LAYER 3: Decision Memory + Intelligence ✅ EXISTS  │
│ • Decision Storage, NegativeKnowledge, Constraints  │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│ LAYER 2: Calibration System ✅ EXISTS              │
│ • Bayesian Beta distributions, per-domain           │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│ LAYER 1: FalkorDB Graph + MCP ✅ EXISTS             │
│ • 8 node types, 12 relationships, Vector embeddings │
└─────────────────────────────────────────────────────┘
```

---

## **2. PHASE 1: INTERACTIVE SHELL (ЭТА НЕДЕЛЯ)**

### **SCOPE: MVP для программиста**

**Включает:**
- ✅ Textual TUI с 4 зонами (Header/Messages/Input/Footer)
- ✅ Task input + classification
- ✅ Graph query (похожие решения)
- ✅ /commands routing (/help, /status, /plan, /diff, /apply)
- ✅ Real-time progress display
- ✅ Diff viewer
- ✅ Command history

**Исключает (Phase 2+):**
- ❌ Multi-model orchestration
- ❌ Parallel execution
- ❌ Advanced dashboard
- ❌ Skills generation

---

## **2.5 SPLASH SCREEN**

### **Логотип Membria (ASCII Art)**

```
▄     ▄                  ▄     ▄
                                  
                                 ▀
 ▀    ▄             ▄    ▀
      ▀    ▄         ▄    ▀   
       ▀    ▄      ▄    ▀  
        ▀        ▀      
         ▀▀▀         
▄     ▄                  ▄     ▄
                        ▄   ▄
                        ▀   ▀
 ▀    ▀                  ▀     ▀
```

**ANSI-код для красивого рендера:**

```bash
printf "\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m        \e[38;5;15;49m▄\e[48;5;15m     \e[38;5;15;49m▄\e[49m                  \e[38;5;15;49m▄\e[48;5;15m     \e[38;5;15;49m▄\e[49m        \e[m
\e[49m        \e[48;5;15m        \e[49m                 \e[48;5;15m        \e[49m       \e[m
\e[49m        \e[48;5;15m        \e[49m                 \e[48;5;15m       \e[49;38;5;15m▀\e[49m       \e[m
\e[49m         \e[49;38;5;15m▀\e[48;5;15m       \e[38;5;15;49m▄\e[49m             \e[38;5;15;49m▄\e[48;5;15m       \e[49;38;5;15m▀\e[49m        \e[m
\e[49m          \e[48;5;15m    \e[49;38;5;15m▀\e[48;5;15m    \e[38;5;15;49m▄\e[49m         \e[38;5;15;49m▄\e[48;5;15m    \e[49;38;5;15m▀\e[48;5;15m    \e[49m         \e[m
\e[49m          \e[48;5;15m    \e[49m  \e[48;5;15m    \e[38;5;15;49m▄\e[49m      \e[38;5;15;49m▄\e[48;5;15m    \e[49;38;5;15m▀\e[49m  \e[48;5;15m    \e[49m         \e[m
\e[49m          \e[48;5;15m    \e[49m   \e[49;38;5;15m▀\e[48;5;15m    \e[38;5;15;49m▄\e[49m  \e[38;5;15;49m▄\e[48;5;15m    \e[49;38;5;15m▀\e[49m    \e[48;5;15m    \e[49m         \e[m
\e[49m          \e[48;5;15m    \e[49m     \e[49;38;5;15m▀\e[48;5;15m        \e[49;38;5;15m▀\e[49m      \e[48;5;15m    \e[49m         \e[m
\e[49m          \e[48;5;15m    \e[49m       \e[49;38;5;15m▀\e[48;5;15m     \e[49m        \e[48;5;15m    \e[49m         \e[m
\e[49m          \e[48;5;15m    \e[49m         \e[49;38;5;15m▀▀▀\e[49m         \e[48;5;15m    \e[49m         \e[m
\e[49m        \e[38;5;15;49m▄\e[48;5;15m     \e[38;5;15;49m▄\e[49m                  \e[38;5;15;49m▄\e[48;5;15m     \e[38;5;15;49m▄\e[49m        \e[m
\e[49m        \e[48;5;15m        \e[49m                \e[38;5;15;49m▄\e[48;5;15m       \e[38;5;15;49m▄\e[49m       \e[m
\e[49m        \e[48;5;15m        \e[49m                \e[49;38;5;15m▀\e[48;5;15m       \e[49;38;5;15m▀\e[49m       \e[m
\e[49m         \e[49;38;5;15m▀\e[48;5;15m    \e[49;38;5;15m▀\e[49m                  \e[49;38;5;15m▀\e[48;5;15m     \e[49;38;5;15m▀\e[49m        \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
\e[49m                                                \e[m
"
```

### **Display Timing**

- Show for: **2-3 seconds** on first shell launch
- No animation (too slow for dev mode)
- Can skip with any key press (immediate start)
- Show connection status: `🟢 Connected` or `🟡 Connecting...`

### **Color Scheme**

```
Logo text:         #5AA5FF (bright blue)
Subtitle:          #E8E8E8 (light gray)
Agent status:      #21C93A (bright green when ready)
Database/Calibration: #999999 (dimmed gray)
Loading text:      #FFB84D (bright orange)
```

### **Exit Splash**

When user types `/exit`:

```
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║                  Goodbye!                         ║
    ║                                                   ║
    ║  Session Summary:                               ║
    ║    Tasks completed: 2                            ║
    ║    Decisions recorded: 2                         ║
    ║    Tokens used: 45,892 / 100,000                ║
    ║    Calibration updates: 1                        ║
    ║                                                   ║
    ║  Graph is learning... 🧠                         ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
```

---

## **3. UI LAYOUT (Textual)**

```
┌─────────────────────────────────────────────────────┐
│ Header (1 line, fixed)                              │
│ 🟢 Agents: ready | Graph: 47 decisions | Context 48%│
├─────────────────────────────────────────────────────┤
│                                                     │
│  MainArea (scrollable, ResizeHandle)                │
│  - Rendering Rich output (Markdown, tables, etc)    │
│  - Task → Classification → Results                 │
│  - Progress bars for long operations               │
│                                                     │
│  membria ~/myapp ▸ Add rate limiting API           │
│                                                     │
│  [CLASSIFY] TACTICAL → implementer (0.89)           │
│                                                     │
│  Graph check:                                       │
│    ✅ express-rate-limit (dec_023, SUCCESS)         │
│    ❌ custom-rate-limiter (dec_009, FAILURE)        │
│                                                     │
│  🏗️ Plan (5 steps):                                 │
│    1. npm install       →  2. Create middleware     │
│    3. Config endpoint   →  4. Add tests             │
│    5. Apply changes                                 │
│                                                     │
│  [y] Apply  [d] Diff  [r] Review  [?] Ask          │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Input (1 line, fixed height)                        │
│ › [input field with history]                        │
├─────────────────────────────────────────────────────┤
│ Footer (1 line, fixed)                              │
│ ⊙ Tasks: 1 active | ✓ Done: 2 | Tokens: 45K | 48% │
└─────────────────────────────────────────────────────┘
```

### **Зоны:**

1. **Header (1 line, non-scrollable)**
   - System status indicator (🟢/🟡/🔴)
   - Connected agents count
   - Graph database status (✅/❌)
   - Context usage percentage
   - Example: `🟢 Agents: 3 ready | Graph: ✅ | Context: 48%`

2. **Main Area (scrollable)**
   - User input echo (with `›` marker)
   - Classification result with confidence
   - Graph query results (похожие решения)
   - NegativeKnowledge warnings
   - Plan/results display
   - Progress bars for long tasks
   - Diff output

3. **Input Area (1 line, fixed height)**
   - Prompt: `membria ~/myapp [active_context] ▸`
   - Supports multiline (Shift+Enter)
   - Command autocomplete (@agent, /help, #decision)
   - History navigation (↑↓)

4. **Footer (1 line, non-scrollable)**
   - Task metrics: `⊙ active | ✓ done | × failed`
   - Token counter: `Tokens: 45K/100K`
   - Context percentage: `Context: 48%`
   - System status: `Agents: ready`

---

## **4. INPUT TYPES**

### **Type 1: Natural Language Task**
```
› Add rate limiting for POST /api/events

↓ PROCESS:
  1. Classify task (TaskRouter)
  2. Query graph (похожие решения)
  3. Show NegativeKnowledge warning if exists
  4. Show plan (from executor)
  5. Wait for confirmation [y/d/r/?]
```

### **Type 2: Slash Commands**
```
/help              → Show available commands
/status            → Agent status + graph status
/agents            → List agents and calibration
/plan <task>       → Show plan without execution
/diff              → Show pending changes
/apply [file]      → Apply changes
/decisions         → Show last 5 decisions
/calibration       → Show calibration per domain
/exit              → Exit shell
```

### **Type 3: Direct Agent Communication (+Phase 2)**
```
@architect <question>    → Ask specific agent (Phase 2)
#dec_042                 → Reference decision (Phase 2)
!npm test                → Run shell command inline (Phase 2)
```

---

## **5. CLASSIFICATION & ROUTING**

### **TaskRouter: Классификация задач**

```
Input: "Add rate limiting for API"
       ↓
Output: {
  task_type: "TACTICAL",           # TACTICAL/DECISION/LEARNING
  confidence: 0.89,
  target_role: "implementer",       # architect/senior/junior/reviewer
  estimated_steps: 5,
  domain: "infrastructure"
}
```

### **Типы задач:**

| Тип | Примеры | Маршрут |
|-----|---------|---------|
| **TACTICAL** | Реализовать фичу, баг-фикс, рефактор | Junior/Senior → Reviewer |
| **DECISION** | Выбрать БД, фреймворк, архитектуру | Architect → discuss alternatives |
| **LEARNING** | Анализ, документация, исследование | Architect → synthesis |

---

## **6. GRAPH QUERY (Decision Memory)**

### **При получении классификации, запрашиваем FalkorDB:**

```python
# Pseudocode
similar = graph.find_similar_decisions(
    task_type="rate_limiting",
    domain="infrastructure",
    limit=3
)

for decision in similar:
    if decision.status == "SUCCESS":
        print(f"✅ {decision.statement} (6 mo ago)")
    elif decision.status == "FAILURE":
        print(f"❌ {decision.statement} [AVOID!]")

# NegativeKnowledge
warnings = graph.get_antipatterns_for_domain("infrastructure")
for warning in warnings:
    print(f"⚠️  {warning.pattern} → {warning.success_rate}% failure")
```

### **Display:**

```
Graph check:
  ✅ express-rate-limit (dec_023, 6 mo) → SUCCESS
  ✅ Redis store approach (dec_034, 2 mo) → SUCCESS
  ❌ custom-middleware (dec_009, 1 y) → FAILURE
     Reason: "Complex rate-limiting logic, maintenance burden"
     Failure rate in similar: 78%

⚠️ NegativeKnowledge:
   "Custom rate limiters removed from 78% of codebases"
   "Initial implementation of custom rate limiting has 89% failure"

Recommendation: Use proven library (express-rate-limit)
```

---

## **7. EXECUTION FLOW (MVP = Single-Model)**

### **Scenario: Simple Task**

```
User: "Add rate limiting for API"

Step 1: CLASSIFY
  Input → TaskRouter
  Output: TACTICAL, implement, confidence 0.89
  Display: "[CLASSIFY] TACTICAL → implementer (0.89)"

Step 2: QUERY GRAPH
  Find similar decisions + antipatterns
  Display: ✅ ❌ ⚠️  results

Step 3: PLAN (via executor/LLM)
  Show planned steps to user
  Display: 
    🏗️ Plan (5 steps):
      1. npm install
      2. Create middleware
      ...

Step 4: CONFIRM
  Await user: [y] Apply [d] Diff [r] Review [?] Ask
  
Step 5: EXECUTE (Phase 2)
  [In Phase 1, show stub: "Phase 2: Parallel execution"]

Step 6: SHOW RESULTS
  [In Phase 1, show stub: "Phase 2: Results merge"]

Step 7: RECORD DECISION
  capture_decision() → FalkorDB
  Display: ✅ Decision dec_049 recorded
```

---

## **8. COMMANDS DETAIL**

### **/help**
```
Available Commands:
  /help                → This message
  /status              → System and agent status
  /agents              → List connected LLMs
  /plan <task>         → Generate plan only
  /diff [file]         → Show pending changes
  /apply [file]        → Apply changes
  /decisions [n]       → Show last N decisions
  /calibration [domain]→ Show calibration stats
  /cost                → Current session cost
  /session             → Session statistics
  /exit                → Exit shell
```

### **/status**
```
┌─ SYSTEM STATUS ──────────────────────┐
│ 🟢 FalkorDB: Connected (192.168.0.105)│
│ 📊 Decisions: 47 captured            │
│ ✅ Outcomes: 31 tracked              │
│                                      │
│ 🤖 AGENTS:                           │
│   Architect:  ready (test ok)        │
│   Impl:       ready (test ok)        │
│   Reviewer:   ready (test ok)        │
│                                      │
│ 📈 CALIBRATION:                      │
│   API:          +3% (underconfident) │
│   Database:     -8% (overconfident)  │
│   Security:    -15% (very overconf.) │
└──────────────────────────────────────┘
```

### **/diff**
```
=== PENDING CHANGES ===

src/middleware/rateLimiter.ts
  @@ -0,0 +1,42 @@
  +import express from 'express';
  +import RedisStore from 'rate-limit-redis';
  ...

src/index.ts
  @@ -15,3 +15,6 @@
   import { router } from './routes';
  +import { rateLimiter } from './middleware/rateLimiter';
  +
  +app.use(rateLimiter);

Apply? [y/n]
```

### **/apply**
```
Applying changes to ~/myapp...
  ✅ src/middleware/rateLimiter.ts (42 lines)
  ✅ src/index.ts (updated)
  
✅ Changes applied
✅ Decision dec_049 recorded
📊 Outcome will be checked in 30 days
```

---

## **9. TECHNICAL IMPLEMENTATION**

### **Stack (unchanged from before):**
- **Framework:** Textual
- **Rich UI:** Rich library
- **Async:** asyncio
- **Database:** FalkorDB (already connected)
- **LLM:** MCP Server (already running) + LLM client

### **Key Classes to Create/Modify:**

```python
# textual_shell.py (already started, refine)
class MembriaApp(App):
    """Main Textual application"""
    BINDINGS = [("ctrl+d", "quit", "Quit")]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield MessagesArea(id="messages")  # ← Main scrollable
        yield InputArea(id="input")        # ← User input
        yield Footer()
    
    async def process_input(self, text: str):
        """Route input to handlers"""
        if text.startswith("/"):
            await self.handle_command(text)
        else:
            await self.handle_task(text)

# shell_engine.py (NEW)
class ShellEngine:
    """Orchestration logic"""
    
    async def classify_task(self, text: str) -> TaskClassification:
        """Use TaskRouter to classify"""
    
    async def query_graph(self, task_type: str, domain: str) -> GraphResults:
        """Query FalkorDB for similar decisions"""
    
    async def get_plan(self, task: str, classification: TaskClassification):
        """Call executor to generate plan"""
    
    async def execute_task(self, task: str):
        """(Phase 2) Execute with multi-model orchestration"""
```

### **Data Models:**

```python
@dataclass
class TaskClassification:
    task_type: str           # TACTICAL/DECISION/LEARNING
    confidence: float        # 0.0-1.0
    target_role: str        # architect/senior/junior
    domain: str             # database/api/security
    estimated_steps: int

@dataclass
class GraphResults:
    similar_decisions: List[Decision]
    negative_knowledge: List[Warning]
    recommended_action: str
```

---

## **10. IMPLEMENTATION CHECKLIST**

### **A. UI Components (Textual)**
- [ ] Header widget (1 line, fixed)
- [ ] MessagesArea widget (scrollable, Rich-compatible)
- [ ] InputArea widget (1 line, fixed, with history)
- [ ] Footer widget (1 line, fixed, metrics)
- [ ] Overall layout + styling

### **B. Input Processing**
- [ ] Input parser (detect /, @, !, #)
- [ ] Command dispatcher (/help, /status, etc)
- [ ] Async input handling with prompt

### **C. Task Classification & Graph**
- [ ] TaskRouter wrapper (call existing router)
- [ ] FalkorDB query builder (similar decisions)
- [ ] NegativeKnowledge display formatter
- [ ] Results display formatter

### **D. Command Handlers**
- [ ] /help
- [ ] /status
- [ ] /agents
- [ ] /plan
- [ ] /diff
- [ ] /apply
- [ ] /decisions
- [ ] /calibration
- [ ] /exit

### **E. Integration**
- [ ] Connect to existing executor
- [ ] Connect to existing router
- [ ] Connect to FalkorDB
- [ ] Connect to MCP Server

### **F. Testing & Polish**
- [ ] Test all UI elements render
- [ ] Test input handling (empty, long, special chars)
- [ ] Test command routing
- [ ] Test graph queries
- [ ] Error handling & display

---

## **11. SUCCESS CRITERIA**

✅ **Shell starts without errors**
```
$ membria
🟢 Agents: ready | Graph: ✅ | Context: 48%
membria ~/myapp ▸ 
```

✅ **Classification works**
```
› Add rate limiting
[CLASSIFY] TACTICAL → implementer (0.89)
```

✅ **Graph query shows results**
```
Graph check:
  ✅ express-rate-limit (dec_023, SUCCESS)
  ❌ custom-middleware (dec_009, FAILURE)
```

✅ **Commands execute without error**
```
› /status
› /help
› /plan Add caching
```

✅ **Diff viewer displays correctly**
```
› /diff
[shows actual diff in correct format]
```

✅ **User can exit gracefully**
```
› /exit
Goodbye!
$ [back to shell]
```

---

## **12. PHASE 2 PREVIEW (NOT THIS WEEK)**

These are explicitly OUT of scope for Phase 1:
- ❌ Multi-model orchestration (Council roles)
- ❌ Parallel execution
- ❌ @agent direct communication
- ❌ Advanced dashboard
- ❌ Real-time progress from LLM
- ❌ Skills generation
- ❌ membria connect command

---

## **13. DEPENDENCIES & INTEGRATION**

### **Already Exists (USE THEM):**
- ✅ FalkorDB schema + client
- ✅ TaskRouter (for classification)
- ✅ MCP Server (for LLM access)
- ✅ Decision capture/record tools
- ✅ Calibration system
- ✅ CommandHandler (/commands routing)

### **Create in Phase 1:**
- 🔄 Textual App (shell.py → textual_shell.py enhanced)
- 🔄 ShellEngine (task classification → graph query → display)
- 🔄 UI Widgets (Header, MessagesArea, InputArea, Footer)
- 🔄 Command Handlers (all /commands)
- 🔄 Graph Query Formatter (display results beautifully)

---

## **14. TIMELINE**

| Task | Days | Dependency |
|------|------|-----------|
| UI Layout (Textual) | 1 | None |
| Input Handling | 1 | UI |
| TaskRouter Integration | 0.5 | UI |
| Graph Query + Display | 1 | Router |
| Command Handlers | 1.5 | Graph |
| Testing & Polish | 0.5 | All |
| **TOTAL** | **5 days** | — |

---

## **DOCUMENT VERSION HISTORY**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | AI | Initial requirements based on docs analysis |

---

**Document Approved For Development:** ✅

Next: Create detailed Jira tickets from this spec.
