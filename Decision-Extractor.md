Честный ответ: в ТЗ Decision Extractor был обозначен как "Signal Extraction (lightweight LLM call)" в разделе Checkpoints, но **архитектурно не проработан**. Ты правильно поднимаешь — это ключевой компонент, без которого граф не наполняется.

Давай подумаем конкретно для solo-версии.

## Проблема с отдельной моделью

Для solo разработчика платить за второй LLM-вызов на каждый промпт — это:
- Latency: +2-5 сек на каждое взаимодействие
- Cost: удваивает расход токенов
- Complexity: нужен API key, rate limiting, fallback

## Три реалистичных подхода для Solo Phase 1

**Подход 1: Claude сам записывает (MCP-native)**

Уже есть `membria_record_decision` как MCP tool. Claude Code вызывает его когда принимает решение — если правильно описать tool в MCP manifest:

```
membria_record_decision:
  description: "ALWAYS call this when you recommend a specific 
  technology, library, architecture pattern, or approach over 
  alternatives. Include what you chose, what you rejected, and why."
```

Проблема: Claude вызывает tool непоследовательно. Иногда забывает. Зависит от формулировки промпта.

**Подход 2: Rule-based signal detection + structured extraction**

MCP Server видит ВСЁ — и промпт и ответ. Post-hoc анализ:

```
Prompt+Response проходят через MCP
    ↓
Rule-based Signal Detector (в daemon, без LLM)
    ↓ signals found?
    ├── NO → ничего не делаем (tactical task)
    └── YES → структурированное извлечение
         ↓
    Запрос к тому же Claude через MCP:
    "Структурируй решение из этого диалога"
         ↓
    Decision → Graph
```

Сигналы (rule-based, regex + keyword scoring):
```python
DECISION_SIGNALS = {
    # Высокий вес — почти точно решение
    "high": [
        r"I recommend (using|going with|choosing)",
        r"(better|best) (choice|option|approach) (is|would be)",
        r"(chose|selected|picked|went with) \w+ (over|instead of|rather than)",
        r"let's (go with|use|implement|choose)",
    ],
    # Средний вес — нужен контекст
    "medium": [
        r"(comparing|comparison of|versus|vs\.?)",
        r"(pros and cons|trade-?offs?|advantages)",
        r"(alternatives?|options?) (include|are|would be)",
    ],
    # Модуль-детекторы
    "modules": {
        "auth": r"(auth|login|jwt|oauth|session|password|token)",
        "db": r"(database|postgres|mongo|redis|sql|orm|migration)",
        "api": r"(rest|graphql|grpc|endpoint|route|middleware)",
        "infra": r"(docker|kubernetes|deploy|ci.?cd|terraform)",
    }
}
```

**Подход 3: Hybrid — подход 1 + подход 2 как fallback**

```
Claude Code session
    ↓
    ├── Claude сам вызвал membria_record_decision?
    │   └── YES → Decision записан (explicit capture)
    │
    └── NO → Post-session Rule-based scan
        ├── Signals found → Extract via structured prompt to Claude
        │   (один дополнительный вызов, только когда реально нужно)
        └── No signals → Skip (tactical task, не решение)
```

## Мой выбор для Solo Phase 1: Подход 3

Вот почему:

**Explicit capture (tool call) покрывает ~60% решений** — когда Claude явно сравнивает и рекомендует. Это бесплатно, мгновенно, уже работает через MCP tool.

**Rule-based fallback ловит остальные ~30%** — решения, которые Claude принял "молча" (выбрал Express без обсуждения, использовал конкретный паттерн). Сигнал-детектор работает в daemon, нулевая latency, нулевая стоимость.

**LLM extraction вызывается только для подтверждённых сигналов** — это ~2-5 вызовов в день, не на каждый промпт. И можно батчить: раз в час собрать все pending signals и извлечь одним вызовом.

**~10% решений будет потеряно** — и это нормально для Phase 1. Лучше 90% точных решений чем 100% с мусором.

## Куда тут ложится Monty?

Monty не для Decision Extraction (это не задача для Python-интерпретатора). Но Monty идеально подходит для другого:

```
Membria Daemon (Rust binary)
    ├── MCP Server (context injection + tool handling)
    ├── Signal Detector (rule-based, Rust)
    ├── Monty Runtime ← вот тут
    │   ├── Пользовательские extraction patterns (Python)
    │   ├── Custom scoring logic
    │   ├── Config-driven decision rules
    │   └── Future: plugin system для антипаттернов
    ├── FalkorDB Local (in-memory graph)
    └── Git hooks (checkpoint capture)
```

Monty даёт возможность писать **кастомную логику на Python** внутри Rust-демона:
- Пользователь пишет `~/.membria/extractors/my_patterns.py`
- Monty исполняет это безопасно, за микросекунды
- Нет контейнеров, нет latency, нет зависимостей

Это также открывает путь к **plugin system**: антипаттерны, scoring формулы, custom module detection — всё на Python, исполняется в Monty.

## Архитектура Decision Extractor для ТЗ

```
┌─────────────────────────────────────────────────┐
│                 MCP Server (daemon)              │
│                                                  │
│  Claude Code ←→ MCP Tools                        │
│       ↓                                          │
│  ┌─────────────────────────────────────────┐     │
│  │         Decision Capture Layer          │     │
│  │                                         │     │
│  │  1. Explicit: membria_record_decision   │     │
│  │     (Claude calls tool directly)        │     │
│  │              ↓ stored immediately       │     │
│  │                                         │     │
│  │  2. Implicit: Signal Detector           │     │
│  │     (rule-based scan of prompt+response)│     │
│  │     Runs in: Rust core + Monty plugins  │     │
│  │              ↓ signal found             │     │
│  │                                         │     │
│  │  3. Extraction: Structured LLM call     │     │
│  │     (batched, async, same Claude API)   │     │
│  │     Template:                           │     │
│  │     "Given this exchange, extract:      │     │
│  │      - decision statement               │     │
│  │      - alternatives considered          │     │
│  │      - confidence (0-1)                 │     │
│  │      - reasoning                        │     │
│  │      - module/domain                    │     │
│  │      Return JSON only."                 │     │
│  │              ↓                          │     │
│  │  4. Confirmation (optional):            │     │
│  │     Terminal notification:              │     │
│  │     "📌 Decision detected:              │     │
│  │      Use JWT for auth (conf: 0.85)      │     │
│  │      [✓ Save] [✗ Skip] [✎ Edit]"       │     │
│  └─────────────────────────────────────────┘     │
│              ↓                                    │
│  FalkorDB Graph (in-memory)                      │
└─────────────────────────────────────────────────┘
```

Хочешь — обновлю это в ТЗ как отдельный раздел? И вопрос: что у тебя за CLI сейчас — TypeScript/Node.js или уже Rust? Это важно для решения, реально ли встроить Monty.