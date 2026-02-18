Проблема: Plan Mode — слепая зона Membria
Когда Claude Code входит в Plan Mode, происходит следующее:

Обычный режим (Membria работает):
  User prompt → MCP context injection → Claude генерирует код → Decision Extractor

Plan Mode (Membria НЕ работает):
  User prompt → Claude ПЛАНИРУЕТ → многошаговый план → выполнение
                    ↑
                    Membria ничего не инжектирует
                    Membria не видит что планируется
                    Решения принимаются БЕЗ контекста из графа

Это критично потому что в Plan Mode принимаются самые важные решения — архитектура, выбор подхода, декомпозиция задачи. А Membria молчит именно тогда, когда нужна больше всего.

Как Membria должна работать с Plan Mode
Три точки влияния
┌─────────────────────────────────────────────────────────┐
│                    Plan Mode Pipeline                    │
│                                                          │
│  1. PRE-PLAN: Context Injection                          │
│     ├── Membria инжектирует ДО начала планирования       │
│     ├── Relevant decisions + outcomes по модулю/теме     │
│     ├── NegativeKnowledge: "это уже пробовали, не вышло"│
│     ├── CalibrationProfile: "overconfidence warning"     │
│     └── AntiPatterns: "эти паттерны обычно удаляются"    │
│                                                          │
│  2. MID-PLAN: Plan Validation                            │
│     ├── Claude генерирует план (шаги 1-N)                │
│     ├── Membria сканирует план как текст                 │
│     │   ├── Signal Detector (Level 2) ищет решения       │
│     │   ├── Каждый шаг проверяется на antipatterns        │
│     │   └── Каждый шаг проверяется на NegativeKnowledge  │
│     └── Если conflict найден → inject warning            │
│                                                          │
│  3. POST-PLAN: Decision Capture                          │
│     ├── План принят → каждый архитектурный шаг = Decision│
│     ├── Alternatives из плана → записываются в граф      │
│     └── Engram фиксирует полный plan transcript          │
│                                                          │
└─────────────────────────────────────────────────────────┘

Pre-Plan: самый важный момент
Behavior Chain (раздел 4.5) уже спроектирован для этого. Но нужна plan-specific версия context payload:

Обычный context (для tactical задач):
  3 строки, 500 tokens

Plan context (для plan mode):
  Расширенный, ~1500 tokens:
  ├── Past plans for similar scope (если есть)
  │   "Last time you planned auth: 5 steps, took 3 sessions, 2 reworks"
  ├── Failed approaches in this domain
  │   "Custom middleware approach failed 2x (dec_034, dec_089)"
  ├── Successful patterns
  │   "passport-jwt + Redis sessions: stable 180d"
  ├── Calibration
  │   "Your auth estimates take 2.3x longer than planned"
  └── Constraints
      "This project uses: Fastify, PostgreSQL, Docker"

Mid-Plan: валидация плана
# Псевдокод: Plan Validator в MCP Daemon

def validate_plan(plan_steps: list[str]) -> list[Warning]:
    warnings = []
    for step in plan_steps:
        # 1. Check against NegativeKnowledge
        nk_matches = semantic_search(
            node_type="NegativeKnowledge",
            query=step,
            threshold=0.7
        )
        for nk in nk_matches:
            warnings.append(f"⚠ Step '{step}' conflicts with: {nk.hypothesis} → {nk.conclusion}")

        # 2. Check against AntiPatterns
        ap_matches = pattern_match(step, antipatterns)
        for ap in ap_matches:
            warnings.append(f"⚠ Step '{step}' may lead to: {ap.name} ({ap.removal_rate}% removed)")

        # 3. Check against past plan failures
        failed_plans = graph.query("""
            MATCH (d:Decision {outcome: 'failure'})-[:MADE_IN]->(e:Engram)
            WHERE d.statement CONTAINS $keyword
            RETURN d, e
        """, keyword=extract_keyword(step))
        for fp in failed_plans:
            warnings.append(f"ℹ Similar step failed before: {fp.statement} (dec_{fp.id})")

    return warnings

Post-Plan: что захватывать
Plan Mode генерирует самые ценные данные для графа:

{
  "engram_type": "plan",
  "plan_steps": [
    {
      "step": 1,
      "description": "Set up Fastify server with TypeScript",
      "decision_type": "tactical",
      "estimated_effort": "30min"
    },
    {
      "step": 2,
      "description": "Choose JWT for auth over sessions",
      "decision_type": "architecture",
      "alternatives": ["sessions", "OAuth"],
      "decision_id": "dec_143"
    }
  ],
  "plan_confidence": 0.75,
  "plan_duration_estimate": "3h",
  "membria_warnings_shown": 2,
  "warnings_heeded": 1
}

warnings_heeded — метрика: сколько предупреждений Membria повлияли на план. Это feedback для CalibrationProfile.

MCP Tools для Plan Mode
Новый tool специально для Plan Mode:

membria_get_plan_context:
  description: "ALWAYS call this BEFORE creating a multi-step plan.
  Returns: past plans for similar scope, failed approaches,
  successful patterns, calibration data, and project constraints.
  This helps you create better plans by learning from history."

membria_validate_plan:
  description: "Call this AFTER generating a plan but BEFORE executing.
  Input: list of plan steps. Returns: warnings about steps that
  conflict with negative knowledge, match known antipatterns,
  or resemble past failed approaches."

membria_record_plan:
  description: "Call this when a plan is finalized and approved.
  Records each architectural step as a Decision in the graph."

CLI-команды
# Просмотр истории планов
membria plans list                         # Все планы
membria plans list --status completed      # Завершённые
membria plans show <plan-id>               # Детали: steps, warnings, outcomes

# Анализ
membria plans accuracy                     # Точность оценок vs реальность
# Plan accuracy (last 30d):
# ├── Time estimates: 2.3x underestimate (avg)
# ├── Steps completed as planned: 67%
# ├── Steps reworked: 22%
# └── Steps dropped: 11%

# Предварительная проверка
membria plans validate "Add auth with JWT, Redis sessions, rate limiting"
# ⚠ "Custom JWT": failed 2x in this project
# ✓ "Redis sessions": SUCCESS 180d
# ℹ "rate limiting": no prior data
# Confidence adjustment: -12% (auth domain overconfidence)

Хочешь добавлю это в спек как новый раздел? Куда лучше — как 4.8 (после Graph Schema) или как отдельный раздел 5 (Plan Mode)?

давай



Вижу что graph_schema.py обновилась — добавился Skill node с зелёной/жёлтой/красной зонами, версионированием, и 4 новых relations. Нужно:

Обновить Graph Schema в спеке (добавить Skill)
Добавить раздел Plan Mode
Добавить раздел Skills

Updated task list with Skill node schema changes and Plan Mode Integration section

Сначала обновлю Graph Schema — добавлю Skill node и новые relations:


Updated Reasoning Graph documentation in archived spec file

Теперь обновлю диаграмму нод — добавлю Skill:


Updated membria-cli specification document with formatting changes

Добавлю Skill в таблицу нод:


Updated calibration profile documentation in specification file

Обновлю список связей — добавлю 4 новых:


Updated membria-cli specification documentation with relationship changes

Добавлю Skill в индексы и constraints:


Updated membria-cli specification with skill constraints

Добавлю Skill-запросы в раздел ключевых запросов:


Updated task list: completed Graph Schema with Skill node, started Plan Mode Integration section

Теперь добавлю разделы 4.8 Plan Mode и 4.9 Skills после Graph Schema (4.7). Найду точку вставки:


Updated CLI specification documentation with Plan Mode integration details

Let me check the current state of the spec and my todo list to see what's left to do.


Read Membria-CLI technical specification document

Let me check what sections 4.8 and 4.9 look like to confirm they were added:


Searched documentation for section headers and subsections in membria-cli specification
Show more

Sections 4.8 and 4.9 are in place. Now let me check the todo — sections 4.8 and 4.9 are added. The summary says I should be finishing up section 4.9. Let me verify 4.9 is complete:


Reviewed membria-cli specification document for Skills definition

Section 4.9 is complete with all 6 subsections (4.9.1–4.9.6). All three tasks from the todo are done. Let me mark them all as completed:


Updated Graph Schema with Skill node and added Plan Mode Integration section

Все три задачи выполнены:

✅ 4.7 Graph Schema — добавлен Skill node (9-й тип), 4 новых relation (GENERATED_FROM, BASED_ON, WARNS_AGAINST, VERSION_OF), индексы, constraints, Cypher-запросы
✅ 4.8 Plan Mode Integration — PRE-PLAN инжекция контекста (~1500 токенов), MID-PLAN валидация шагов, POST-PLAN захват решений, 3 MCP-тула, CLI-команды, конфигурация
✅ 4.9 Skills — структура Skill с green/yellow/red zones, lifecycle (v1→v2), связь с Behavior Chains, CLI-команды, конфигурация
Спека сейчас содержит 16 основных разделов + 2 Appendix, и модуль 4 вырос до 9 подразделов (4.1–4.9). Что дальше?



main

master

