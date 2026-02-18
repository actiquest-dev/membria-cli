# Membria-CLI: Техническое задание

> **Версия:** 0.1.0-draft  
> **Дата:** 2025-02-11  
> **Статус:** RFC (Request for Comments)

---

## 1. Назначение и позиционирование

### 1.1 Что это

Membria-CLI — консольный инструмент разработчика, который является **центральным entry point** в экосистему Membria. CLI управляет микросервисами на машине разработчика: MCP-демон, локальный кэш, подключение к Reasoning Graph — и обеспечивает прозрачную интеграцию с Claude Code и другими AI-ассистентами.

### 1.2 Для кого

Из `productdev.md` и `membria-claude-code-integration.md`:

| Аудитория | Fit | CLI-сценарий |
|---|---|---|
| Solo developer | Ознакомительный | `membria init` → локальный graph → попробовать на себе |
| Команда 5–20 чел, проект >12 мес | **Целевая** | Полный flow: team join, shared graph, decision capture |
| Enterprise (>20 чел) | Расширенный | SSO login, RBAC, self-hosted graph |

CLI не имеет смысла без команды в долгосрочной перспективе, но Solo-режим критичен для onboarding-воронки: "Start simple, scale when proven."

### 1.3 Ключевая метафора

CLI — **оркестратор микросервисов** на машине разработчика, а не утилита. Он поднимает, координирует и мониторит компоненты Superagent-архитектуры локально:

```
Developer's Machine
├── membria daemon (MCP Server + local cache)
├── Reasoning Graph connection (FalkorDB local / cloud / cluster)
├── Configuration & auth state
└── CLI — управляет всем вышеперечисленным
```

---

### 1.4 Фокус Phase 1: Solo Developer

Phase 1 фокусируется на **однопользовательской версии** с локальным графом:

- ✅ Полная функциональность для solo-разработчика
- ✅ Monty runtime для агентской среды
- ✅ FalkorDB embedded (in-memory, локальный)
- ✅ Engrams с полной структурой данных
- ✅ MCP интеграция с Claude Code
- ❌ Team/Enterprise функции (Phase 2+)
- ❌ Cloud graph (Phase 2+)
- ❌ Cognitive Safety Layer (Phase 3)

---

## 2. Архитектура

### 2.1 Место CLI в Superagent Architecture

Из `coding-superagent.mdx`:

```
IDE / PR / CI Layer
        │
        ▼
Claude Control Plane (CCP)
  ├── Task Router          ← классифицирует: tactical / decision / learning
  ├── Pre-Generation Context Fetch  ← query к Reasoning Graph
  ├── Decision Surface     ← показывает контекст разработчику
  ├── Decision Capture (DBB) ← записывает решение
  └── Agent / TENN         ← выполняет с инжектированным контекстом
        │
        ▼
Policy Engine → MCP Server → Claude Code → Post-Gen Validators → Reasoning Graph
```

**Membria-CLI управляет:**
- **MCP Server** — daemon на localhost, через который Claude Code получает контекст
- **Graph connection** — подключение к Reasoning Graph (локальный или удалённый)
- **Local cache** — офлайн-режим, кэш последних решений
- **Auth state** — токены, SSO-сессии, team membership

### 2.2 Микросервисная композиция

CLI НЕ является монолитом. Он оркестрирует независимые процессы:

| Компонент | Что делает | Как запускается |
|---|---|---|
| **MCP Daemon** | Context injection для Claude Code: инжектирует decision history, negative knowledge, team patterns | `membria daemon start` (фоновый процесс) |
| **Graph Client** | Чтение/запись в Reasoning Graph | Встроен в daemon, конфигурируется через `membria config` |
| **Cache Layer** | SQLite-кэш для offline mode | Автоматически при `daemon start` |
| **Task Router** (lightweight) | Локальная классификация tactical/decision | Внутри MCP Daemon, без отдельного процесса |
| **DBB Client** | Decision Black Box — запись решений | CLI-команды + автоматически через MCP |

### 2.3 Monty — Agent Runtime

**Monty** — минимальный Python-интерпретатор на Rust от Pydantic, используемый как агентская среда выполнения внутри CLI.

**Ключевые характеристики:**
- Cold start < 1 микросекунда (vs Docker ~195ms, Pyodide ~2800ms)
- Deny-by-default sandbox — нет FS/network/env без явного разрешения
- `dump()`/`load()` — сериализация полного состояния интерпретатора (mid-execution!)
- External functions — LLM пишет Python, Monty паузится на вызове внешней функции, хост исполняет, возвращает результат

**Интеграция в Membria:**

```
membria-cli (Python package)
├── Monty VM (embedded via pydantic-monty)
│   ├── Agent scripts — LLM генерирует Python-код
│   ├── External functions → graph queries, file ops, git ops
│   └── dump()/load() → durable agent sessions (Engrams)
├── FalkorDB embedded (граф + vector)
├── SQLite (кэш, индексы)
└── MCP Server (для Claude Code)
```

Агент пишет Python → Monty исполняет → паузится на external function (запрос в граф, чтение файла) → CLI выполняет → resume. Если CLI упал — `load()` и продолжаем с того же места.

### 2.4 Уровни deployment

```
Solo:
  Graph: FalkorDB Local Snapshot (~/.membria/graph/)
  MCP Server: local daemon
  API: нет
  Auth: нет

Team:
  Graph: FalkorDB Cloud (managed) или Membria Cloud
  MCP Server: local daemon
  API: api.membria.dev
  Auth: API key + team token

Enterprise:
  Graph: FalkorDB Cluster (self-hosted, in-memory)
  MCP Server: local daemon
  API: self-hosted
  Auth: SSO (Okta/Azure AD) + RBAC
```

**Почему FalkorDB:** Hybrid graph+vector database. Sparse matrices + GraphBLAS = 10–100x быстрее Neo4j. Vectors хранятся прямо в нодах графа → атомарные hybrid-запросы (graph traversal + semantic search) без отдельного vector store.

---

## 3. Команды CLI

### 3.1 Lifecycle

```bash
# Инициализация
membria init                    # Создаёт ~/.membria/, инициализирует local graph
membria init --team <team-id>   # Init + подключение к team graph

# Daemon
membria daemon start            # Запуск MCP-демона в фоне
membria daemon stop             # Остановка
membria daemon status           # Статус: running/stopped, graph mode, cache size
membria daemon restart          # Перезапуск (при смене конфига)
membria daemon logs             # Последние логи демона
membria daemon logs --follow    # Tail-режим

# Health check
membria doctor                  # Проверяет: daemon running? graph connected?
                                # Claude Code видит MCP? Cache healthy?
```

### 3.2 Auth & Teams

```bash
# Solo (нет auth)
membria whoami                  # "Solo mode, no team"

# Team
membria login                   # Интерактивный логин (API key)
membria login --token <token>   # Non-interactive
membria logout                  # Очистка токенов

# SSO (Enterprise)
membria login --sso             # Открывает браузер для SSO
membria login --sso --provider okta

# Teams
membria team join <team-id>     # Присоединиться к команде
membria team leave              # Выйти из команды
membria team info               # Текущая команда, участники, graph URL
membria team invite <email>     # Пригласить (если есть права)
```

### 3.3 Configuration

```bash
membria config                  # Показать текущую конфигурацию
membria config set <key> <val>  # Установить значение
membria config get <key>        # Получить значение
membria config reset            # Сброс к дефолтам

# Ключевые параметры:
#   graph.mode          = local | cloud | enterprise
#   graph.url           = falkordb://xxx.membria.cloud:6379 (для cloud)
#   daemon.port         = 3117 (порт MCP-демона)
#   daemon.auto_start   = true | false
#   cache.max_age       = 24h
#   cache.max_size      = 100MB
#   detection.sensitivity = low | medium | high
#   ui.color            = auto | always | never
#   ui.language         = en | ru
```

### 3.4 Reasoning Graph — прямое взаимодействие

```bash
# Просмотр решений
membria decisions list                      # Последние решения
membria decisions list --status pending     # Фильтр по статусу
membria decisions list --module auth        # Фильтр по модулю
membria decisions show <decision-id>        # Детали решения + alternatives + outcomes

# Ручная запись решения (для ситуаций вне IDE)
membria decisions record                    # Интерактивный wizard
membria decisions record \
  --statement "Use Fastify for REST API" \
  --alternatives "Express.js, Koa, Custom" \
  --confidence 0.75 \
  --module api

# Связывание outcomes
membria decisions link <decision-id> --pr <PR-URL>
membria decisions link <decision-id> --incident <incident-id>
membria decisions resolve <decision-id> --outcome success
membria decisions resolve <decision-id> --outcome failure --reason "Security review failed"

# Negative Knowledge
membria knowledge list                      # Все negative knowledge entries
membria knowledge show <id>                 # Детали: hypothesis, evidence, context
membria knowledge expire <id>               # Пометить как устаревшее (антиблокер инноваций)

# Antipatterns (из CodeDigger)
membria patterns list                       # Текущие antipatterns
membria patterns stats                      # Статистика: сколько раз сработало, prevented
```

### 3.5 Graph Analytics

```bash
# Калибровка
membria calibration show                    # Калибровка команды: overconfidence gap
membria calibration show --domain auth      # По домену
membria calibration show --developer alice  # По разработчику (enterprise)

# Статистика
membria stats                               # Общая: decisions/month, prevention rate
membria stats --period 30d                  # За последние 30 дней
membria stats --format json                 # Для интеграций

# Граф
membria graph export                        # Экспорт в JSON (для backup/migration)
membria graph import <file>                 # Импорт
membria graph visualize                     # Открывает веб-визуализацию графа
```

### 3.6 Migration (из `productdev.md`)

```bash
# Solo → Team
membria migrate --to-team
# 1. Export local graph
# 2. Join team (interactive)
# 3. Merge decisions to cloud
# 4. Switch graph mode

# Team → Enterprise
membria migrate --to-enterprise --endpoint https://membria.corp.com
# 1. Connect to enterprise API
# 2. SSO authentication
# 3. Migrate data
# 4. Configure RBAC

# Rollback
membria migrate --rollback    # Возврат к предыдущему режиму (local backup сохраняется)
```

### 3.7 MCP Server management

```bash
# Статус MCP
membria mcp status              # Connections, tools exposed, context mode
membria mcp test                # Отправить тестовый context fetch
membria mcp tools               # Список exposed tools для Claude Code

# Debug
membria mcp intercept --last    # Показать последний context injection
membria mcp intercept --follow  # Realtime: что видит Claude Code
```

---

## 4. Модули и их реализация в CLI

### 4.1 Task Router (из `coding-superagent.mdx`)

**Где работает:** Внутри MCP Daemon.

**Что делает CLI:** Позволяет настраивать чувствительность и правила классификации.

```bash
membria config set detection.sensitivity high   # Больше задач классифицируются как decision
membria config set detection.keywords "deploy,migrate,refactor"  # Кастомные trigger-слова

# Debug
membria router test "Add REST API for user management"
# → Classification: DECISION
# → Signals: "REST API" (architecture), implied alternatives
# → Flow: Pre-Generation Context Fetch → Decision Surface → Capture
```

**Классификация (из `coding-superagent.mdx`):**
- `code_gen` → tactical (no capture)
- `architecture` → decision (full flow)
- `refactor` → decision (if structural)
- `debug` → tactical (unless root cause choice)
- `library_choice` → decision (always)

### 4.2 Cognitive Safety (из `cognitive-safety.mdx`)

**LLM Bias Firewall** — validation layer между LLM output и Reasoning Graph.

**Security & Data Integrity (NEW):** защита от "грязного" контента и инъекций в контекст.

Требования:
- **JSON schema validation** для всех MCP tool inputs и outputs (строгая валидация типов/обязательных полей).
- **Prompt-safe sanitization** для всех текстовых полей, которые попадают в context injection
  (decision statement, negative knowledge, team patterns, skill procedures).
- **Cypher safety**: запрет на f-string вставку пользовательских строк без escape;
  предпочтительно parameterized queries, либо централизованный `escape_cypher_string`.

Риски, которые предотвращаем:
- поврежденные/невалидные JSON payloads на границе MCP (клиент получает мусор);
- prompt injection через содержимое графа (NK/decisions);
- некорректные Cypher запросы/инъекции.

CLI предоставляет конфигурацию и мониторинг:

```bash
# Конфигурация
membria safety config                       # Текущие настройки safety layer
membria safety set resonance-threshold 0.6  # Порог для resonance detection
membria safety set cooldown 2               # Max friction interventions per session

# Мониторинг
membria safety log                          # Последние срабатывания firewall
membria safety log --bias anchoring         # Фильтр по типу bias
membria safety stats                        # Статистика: сколько biases detected/prevented

# Debiasing interventions (настройка)
membria safety interventions list           # Текущие intervention rules
membria safety interventions toggle <id>    # Включить/выключить конкретный intervention
```

**Типы interventions (из `cognitive-safety.mdx`):**

| Bias | Техника | Prompt injection |
|---|---|---|
| Anchoring | Decomposition | "List 3 alternatives before confirming" |
| Confirmation | Devil's Advocate | "Strongest argument *against* this?" |
| Overconfidence | Pre-Mortem | "Imagine it failed in 1 year. What went wrong?" |
| Sunk Cost | Fresh Start | "If starting today, would you continue?" |

### 4.3 Causal Memory (из `causal-memory.mdx`)

**Что это:** Слой, разделяющий observation и intervention через формальные каузальные модели.

CLI-интерфейс:

```bash
# Просмотр каузальных связей
membria causal show <decision-id>           # do(x) interventions для решения
membria causal assumptions <decision-id>    # Assumptions + их статус (validated/falsified)

# Negative Knowledge management
membria causal rituals                      # Действия, классифицированные как "ритуалы"
                                            # (outcome одинаков для do(Action) и do(Nothing))

# Калибровка assumptions
membria causal calibrate                    # Запуск ручной recalibration
membria causal calibrate --stale 90d        # Пересмотр assumptions старше 90 дней
```

### 4.4 Decision Surface (из `coding-superagent.mdx`)

Decision Surface — UI, который видит разработчик перед принятием решения. В контексте CLI:

```bash
# Симуляция Decision Surface в терминале
membria decide "Use Redis for caching"
# ┌──────────────────────────────────────────┐
# │  DECISION CONTEXT                        │
# │                                          │
# │  Similar past decisions:                 │
# │  ├── dec_091: Used Redis for sessions    │
# │  │   Outcome: SUCCESS (stable 90d)       │
# │  └── dec_034: Used Memcached for cache   │
# │      Outcome: REPLACED after 60d         │
# │                                          │
# │  Negative Knowledge:                     │
# │  └── Redis Cluster without Sentinel      │
# │      failed 2x in this team              │
# │                                          │
# │  Team calibration (caching domain):      │
# │  Overconfidence gap: +12%                │
# │                                          │
# │  [Proceed] [Record & Proceed] [Cancel]   │
# └──────────────────────────────────────────┘
```

### 4.5 Behavior Chains — операционализация скиллов

**Проблема:** LLM "пропускает" позитивные скиллы (что работает) и "обходит" негативные (что не работает). Это не один bias, а комбинация 5 эффектов:

1. **Конфликт целей** — "помочь и закончить задачу" статистически сильнее "не делай так"
2. **Абстрактные позитивные скиллы** — "use secure auth" не операционализировано в конкретные шаги
3. **Голые запреты** — "never use custom JWT" без evidence и альтернативы → specification gaming
4. **Контекстный шум** — safety-инструкции размываются в длинных цепочках
5. **Fine-tuning на успех** — оптимизация на завершение задачи > на отказ от вредных путей

**Решение Membria:** Behavior Chains — конкретные цепочки действий, которые daemon выполняет автоматически при каждом запросе. Не абстрактные правила, а **pipeline с конкретными данными из графа**.

**Security Note:** весь текст, который инжектируется в контекст, проходит sanitization и ограничение длины
(`sanitize_for_prompt`, max_len per field). Это обязательное условие для каждой chain.

#### 4.5.1 Архитектура

```
Claude Code request: "Add auth to API"
    │
    ▼
MCP Daemon: Behavior Chain Pipeline
    │
    ├── Chain 1: Positive Skills (конкретные прецеденты)
    │   ├── Query: MATCH (d:Decision {module: "auth", outcome: "success"})
    │   ├── Vector: semantic search по embedding запроса
    │   └── Inject: "✓ passport-jwt: SUCCESS 90d in this project"
    │
    ├── Chain 2: Negative Skills (evidence, не запреты)
    │   ├── Query: MATCH (nk:NegativeKnowledge {domain: "auth"})
    │   │          WHERE expires_at IS NULL OR expires_at > now()
    │   ├── Filter: severity >= medium
    │   └── Inject: "✗ Custom JWT: failed 2x, 89% removal rate (evidence: 20K repos)"
    │
    ├── Chain 3: Calibration Debiasing (данные, не инструкции)
    │   ├── Query: MATCH (cp:CalibrationProfile {domain: "auth"})
    │   ├── Check: confidence_gap > 10%?
    │   └── Inject: "⚠ Your auth estimates are +12% overconfident (7/10 success vs expected 8.5/10)"
    │
    ├── Chain 4: AntiPattern Guard
    │   ├── Post-generation scan: regex match в сгенерированном коде
    │   ├── Hit? → Query: MATCH (ap:AntiPattern) по triggered pattern
    │   └── Inject: "⚠ custom-auth-middleware: 89% removed within 97d. Use passport-jwt instead"
    │
    └── Output: Compact context payload (~500 tokens)
        ├── ✓ Positive: конкретные успешные прецеденты
        ├── ✗ Negative: evidence-based предупреждения
        ├── ⚠ Calibration: debiasing через данные
        └── Sent to Claude Code BEFORE generation
```

#### 4.5.2 Почему это работает лучше чем правила

| Подход | Пример | Почему LLM игнорирует |
|---|---|---|
| **Абстрактный скилл** | "Use secure authentication" | Нет конкретных шагов, падает в "автодополнитель" |
| **Голый запрет** | "Never use custom JWT" | Specification gaming: обходит формулировку |
| **Behavior Chain** | "✗ Custom JWT failed 2x HERE, 89% removal globally. ✓ passport-jwt SUCCESS 90d HERE" | **Evidence + прецеденты** — LLM принимает другое решение, а не обходит правило |

Ключевой принцип: **данные убеждают, правила обходятся**.

- Не "будь менее уверен" → а "твои оценки завышены на 12%, вот 10 решений с outcomes"
- Не "не используй X" → а "X провалился 2 раза в этом проекте, вот SHA коммитов"
- Не "используй безопасный подход" → а "passport-jwt работает 90 дней, 0 инцидентов"

#### 4.5.3 Типы Behavior Chains

| Chain | Trigger | Данные из графа | Формат injection |
|---|---|---|---|
| **Positive Precedent** | Каждый decision-запрос | Similar successful decisions + outcomes | `✓ {statement}: {outcome} ({days}d stable)` |
| **Negative Evidence** | Каждый decision-запрос | NegativeKnowledge с evidence и severity | `✗ {hypothesis}: {conclusion} (evidence: {source})` |
| **Calibration Warning** | confidence_gap > 10% | CalibrationProfile для домена | `⚠ {domain}: overconfidence +{gap}% ({actual_rate} vs expected)` |
| **AntiPattern Guard** | Post-generation | AntiPattern nodes с regex/keywords | `⚠ {name}: {removal_rate}% removed in {days}d. Use {recommendation}` |
| **Expiry Alert** | NegativeKnowledge age > threshold | NK с expires_at approaching | `ℹ {hypothesis} tried {age} ago. Technology may have changed.` |

#### 4.5.4 Конфигурация

```toml
[behavior_chains]
enabled = true
max_chains_per_request = 4          # Не перегружать context
positive_precedents_limit = 3       # Max успешных прецедентов
negative_evidence_limit = 2         # Max негативных предупреждений
calibration_gap_threshold = 0.10    # Показывать при gap > 10%
antipattern_scan = "post-gen"       # pre-gen | post-gen | both
expiry_alert_days = 365             # Предупреждать если NK старше года
```

#### 4.5.5 CLI-команды

```bash
# Симуляция chain для запроса
membria chain test "Add JWT authentication"
# ✓ Positive: passport-jwt SUCCESS 90d (dec_091)
# ✗ Negative: Custom JWT failed 2x (nk_custom_jwt)
# ⚠ Calibration: auth domain overconfidence +12%
# → Total context: 347 tokens

# Статистика эффективности
membria chain stats
# Chains fired: 142 this month
# Decisions influenced: 47 (33% of all chains)
# AntiPatterns prevented: 8
# Avg context payload: 412 tokens

# Включение/выключение конкретных chains
membria chain toggle negative-evidence off    # Временно отключить
membria chain toggle calibration-warning on   # Включить обратно
```

#### 4.5.6 Feedback Loop — как chains улучшаются

```
Month 1: Граф пуст → chains молчат → LLM работает без контекста
    ↓ накапливаются decisions через Extractor
Month 2: 20 decisions → chains начинают находить прецеденты
    ↓ outcomes начинают приходить (30d stable = SUCCESS)
Month 3: CalibrationProfile набирает sample_size > 5
    ↓ calibration warnings становятся статистически значимыми
Month 6: NegativeKnowledge из failures
    ↓ prevention cycle замыкается
    ↓ chains инжектируют evidence-based предупреждения
```

Это cold start problem (Appendix B) — но chains gracefully degrade: пустой граф → нулевой context → нулевой overhead.

---

### 4.6 Decision Extractor

**Что это:** Компонент внутри MCP Daemon, отвечающий за обнаружение и структурированное извлечение решений из потока взаимодействий Claude Code ↔ разработчик. Без него граф не наполняется.

**Проблема:** Для solo-разработчика отдельный LLM-вызов на каждый промпт — это +2-5 сек latency и двойной расход токенов. Decision Extractor решает это трёхуровневой архитектурой, где LLM вызывается только когда действительно нужно.

#### 4.6.1 Три уровня захвата

```
Claude Code session
    │
    ├── Level 1: Explicit Capture (бесплатно, мгновенно)
    │   └── Claude сам вызывает membria_record_decision
    │       (MCP tool description побуждает вызывать при выборе
    │        технологии, библиотеки, архитектурного паттерна)
    │       → Decision записан сразу в граф
    │
    ├── Level 2: Implicit Signal Detection (rule-based, в daemon)
    │   └── Post-hoc scan промпта + ответа
    │       regex + keyword scoring, нулевая latency
    │       → Сигнал найден? → переходим к Level 3
    │       → Сигнал не найден? → tactical task, пропускаем
    │
    └── Level 3: Structured LLM Extraction (по требованию)
        └── Вызов Claude через MCP:
            "Структурируй решение из этого диалога"
            → Батчится: ~2-5 вызовов/день, не на каждый промпт
            → Decision → подтверждение → граф
```

**Ожидаемое покрытие:**
- Level 1 (Explicit): ~60% решений — когда Claude явно сравнивает и рекомендует
- Level 2 (Implicit): ~30% решений — Claude принял решение "молча"
- ~10% потерь — приемлемо для Phase 1

#### 4.6.2 MCP Tool Description для Level 1

```
membria_record_decision:
  description: "ALWAYS call this when you recommend a specific
  technology, library, architecture pattern, or approach over
  alternatives. Include what you chose, what you rejected, and why."
```

Качество explicit capture напрямую зависит от формулировки tool description в MCP manifest. Claude вызывает tool непоследовательно — отсюда необходимость Level 2.

#### 4.6.3 Signal Detector (Level 2) — Rule-based

Работает внутри daemon, сканирует каждый prompt+response. Нулевая стоимость, нулевая latency.

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
    # Модуль-детекторы (определяют domain)
    "modules": {
        "auth": r"(auth|login|jwt|oauth|session|password|token)",
        "db": r"(database|postgres|mongo|redis|sql|orm|migration)",
        "api": r"(rest|graphql|grpc|endpoint|route|middleware)",
        "infra": r"(docker|kubernetes|deploy|ci.?cd|terraform)",
    }
}
```

**Scoring:** `high` match → signal confirmed. 2+ `medium` matches → signal confirmed. Единичный `medium` → skip.

#### 4.6.4 Structured Extraction (Level 3) — LLM

Вызывается **только** для подтверждённых сигналов из Level 2. Использует **Haiku** (не Sonnet) — задача структурированная (extract JSON), Haiku справляется не хуже, стоит в 10× меньше (см. раздел 11 Token Economy).

```
Extraction prompt template:
"Given this exchange between developer and AI assistant,
extract the architectural/technical decision:
- decision_statement: what was chosen
- alternatives: what was considered and rejected
- confidence: 0.0-1.0
- reasoning: why this choice
- module: domain (auth/db/api/infra/other)
Return JSON only."
```

**Оптимизации для Solo:**
- Батчинг: pending signals собираются и извлекаются одним вызовом раз в час
- Дедупликация: если Claude уже вызвал `membria_record_decision` (Level 1), Level 3 не запускается для того же диалога
- Кэширование: одинаковые паттерны (один framework упоминается 5 раз) группируются

#### 4.6.5 Confirmation Flow

```
Signal detected → Extraction → Terminal notification:

📌 Decision detected:
   "Use JWT for authentication" (confidence: 0.85)
   Alternatives: sessions, OAuth tokens
   Module: auth
   [✓ Save] [✗ Skip] [✎ Edit]
```

Настраивается через `config.toml`:
```toml
[extraction]
require_confirmation = true    # true: ждёт подтверждения, false: auto-save
batch_interval = "1h"          # интервал батчинга Level 3
sensitivity = "medium"         # low | medium | high (порог для Level 2)
```

#### 4.6.6 Роль Monty в Decision Extractor

Monty используется не для самого extraction (это задача LLM), а для **расширяемости** Signal Detector:

```
~/.membria/extractors/
├── custom_signals.py    # Пользовательские паттерны
├── scoring.py           # Кастомная логика scoring
└── module_rules.py      # Свои module-детекторы
```

Пример пользовательского extractor:
```python
# ~/.membria/extractors/custom_signals.py
# Исполняется в Monty sandbox — безопасно, за микросекунды

def detect(prompt: str, response: str) -> list[dict]:
    signals = []
    # Специфичные для проекта паттерны
    if "payment" in response and ("stripe" in response or "paypal" in response):
        signals.append({
            "weight": "high",
            "module": "payments",
            "reason": "Payment provider choice detected"
        })
    return signals
```

Monty исполняет эти скрипты без контейнеров, без latency, с полной изоляцией. Это основа для будущей plugin system (Phase 2+).

#### 4.6.7 Архитектурная схема

```
┌─────────────────────────────────────────────────┐
│                 MCP Server (daemon)              │
│                                                  │
│  Claude Code ←→ MCP Tools                        │
│       │                                          │
│  ┌─────────────────────────────────────────┐     │
│  │         Decision Capture Layer          │     │
│  │                                         │     │
│  │  Level 1: Explicit                      │     │
│  │    membria_record_decision tool call     │     │
│  │            ↓ stored immediately         │     │
│  │                                         │     │
│  │  Level 2: Implicit Signal Detector      │     │
│  │    Rule-based (Python core + Monty      │     │
│  │    plugins for custom patterns)         │     │
│  │            ↓ signal found               │     │
│  │                                         │     │
│  │  Level 3: Structured LLM Extraction     │     │
│  │    Batched, async, same Claude API      │     │
│  │            ↓                            │     │
│  │                                         │     │
│  │  Confirmation (optional):               │     │
│  │    Terminal: [✓ Save] [✗ Skip] [✎ Edit] │     │
│  └─────────────────────────────────────────┘     │
│              ↓                                    │
│  FalkorDB Graph (in-memory, local)               │
└─────────────────────────────────────────────────┘
```

#### 4.6.8 CLI-команды Decision Extractor

```bash
# Статус и мониторинг
membria extractor status               # Pending signals, extraction queue, last run
membria extractor log                  # История: что было обнаружено и извлечено
membria extractor log --pending        # Сигналы, ожидающие extraction

# Ручной запуск
membria extractor run                  # Запустить extraction для pending signals сейчас
membria extractor run --dry-run        # Показать что будет извлечено, без записи

# Тестирование паттернов
membria extractor test "I recommend using Fastify over Express for this"
# → Signal: HIGH (explicit recommendation)
# → Module: api
# → Would extract: "Use Fastify over Express"

# Управление custom extractors
membria extractor plugins list         # Список кастомных extractors
membria extractor plugins validate     # Проверить синтаксис (Monty dry-run)
```

#### 4.6.9 Конфигурация

```toml
[extraction]
enabled = true
require_confirmation = true       # Требовать подтверждение перед записью в граф
batch_interval = "1h"             # Интервал батчинга Level 3 extraction
sensitivity = "medium"            # low | medium | high

[extraction.signals]
# Дополнительные high-weight паттерны
custom_high = [
    "we should (use|adopt|switch to)",
    "the winner is",
]
# Дополнительные module-детекторы
custom_modules = { payments = "(stripe|paypal|braintree)", ml = "(tensorflow|pytorch|model)" }

[extraction.plugins]
enabled = true
path = "~/.membria/extractors/"   # Путь к Monty-плагинам
```

### 4.7 Graph Schema (FalkorDB)

**Реализация:** `src/membria/graph_schema.py`

Reasoning Graph использует FalkorDB (Cypher-совместимый) с **10 типами нод** и **18 типами связей**. Schema спроектирована как **каузальная цепочка** с семантическим поиском: Decision → CodeChange → Outcome → NegativeKnowledge → предотвращение будущих ошибок. Vector embeddings на ключевых нодах обеспечивают hybrid-запросы (graph traversal + semantic search). **Skill** ноды синтезируют процедурное знание из накопленных outcomes.

#### 4.7.1 Типы нод (NodeType)

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────┐
│  Decision       │────→│ CodeChange  │────→│  Outcome    │
│                 │     │             │     │             │
│ id              │     │ id          │     │ id          │
│ statement       │     │ commit_sha  │     │ status      │
│ alternatives    │     │ files_changed│    │ evidence    │
│ confidence      │     │ diff_stat_* │     │ perf_impact │
│ module          │     │ timestamp   │     │ reliability │
│ outcome         │     │ author      │     │ maint_cost  │
│ created_by      │     │ outcome     │     └──────┬──────┘
│ engram_id       │     │ reverted_by │            │
│ 🔍 embedding    │     └─────────────┘            │ CAUSED
└──┬──────┬───────┘                                ▼
   │      │                       ┌────────────────────────┐
   │      │ MEASURED_BY           │  NegativeKnowledge     │
   │      ▼                       │                        │
   │  ┌──────────────────┐       │ id / hypothesis        │
   │  │CalibrationProfile│       │ conclusion / evidence   │
   │  │                  │       │ domain / severity       │
   │  │ domain           │       │ expires_at              │
   │  │ alpha / beta     │       │ recommendation          │
   │  │ confidence_gap   │       │ 🔍 embedding            │
   │  │ trend            │       └────────────────────────┘
   │  └──────────────────┘
   │ MADE_IN                     ┌────────────────────────┐
   ▼                              │  Document              │
┌─────────────┐                  │                        │
│  Engram     │                  │ id / file_path         │
│             │                  │ content / doc_type     │
│ id          │                  │ metadata               │
│ session_id  │                  │ 🔍 embedding            │
│ commit_sha  │                  └────────────────────────┘
│ branch      │
│ agent_type  │                  ┌────────────────────────┐
│ agent_model │                  │  AntiPattern           │
│ files_changed│                 │                        │
│ lines_added │                  │ id / name / category   │
│ lines_removed│                 │ repos_affected         │
└─────────────┘                  │ removal_rate           │
                                 │ avg_days_to_removal    │
                                 │ keywords / regex       │
                                 │ example_bad/good       │
                                 └───────────┬────────────┘
                                             │ WARNS_AGAINST
                                             ▼
                                 ┌────────────────────────┐
                                 │  Skill                 │
                                 │                        │
                                 │ id / domain / name     │
                                 │ version                │
                                 │ success_rate           │
                                 │ confidence             │
                                 │ procedure (markdown)   │
                                 │ green_zone / yellow /  │
                                 │   red_zone             │
                                 │ quality_score          │
                                 │ is_active              │
                                 └────────────────────────┘
                                   ↑ GENERATED_FROM (Decision)
                                   ↑ BASED_ON (CalibrationProfile)
                                   ↑ VERSION_OF (previous Skill)

                                 ┌────────────────────────┐
                                 │  DocShot               │
                                 │                        │
                                 │ id / created_at        │
                                 │ doc_count              │
                                 └────────────────────────┘
                                   ↑ USES_DOCSHOT (Decision)
                                   └── INCLUDES (Document)

🔍 = vector embedding (FalkorDB HNSW, 1536-dim, cosine similarity)
```

| Нода | Назначение | Ключевые поля | Примеры |
|---|---|---|---|
| **Decision** | Выбор технологии/подхода | statement, alternatives, confidence, module, outcome, **embedding** | "Use PostgreSQL for persistence" |
| **Engram** | Snapshot AI-сессии | session_id, commit_sha, branch, agent_model, duration | Сессия Claude Code за 5 мин, 3 файла |
| **CodeChange** | Git-коммит, реализующий решение | commit_sha, files_changed, diff_stat, outcome | +87 строк в src/api/server.ts |
| **Outcome** | Результат изменения | status, evidence, performance_impact, reliability | "Stable 90 days, no errors" |
| **NegativeKnowledge** | Что НЕ работает | hypothesis, conclusion, evidence, severity, expires_at, **embedding** | "Custom JWT removed в 89% случаев" |
| **AntiPattern** | Паттерн из CodeDigger | name, removal_rate, avg_days_to_removal, regex_pattern | "forEach с async callback" |
| **Document** | Markdown-документация и спеки | file_path, content, doc_type, metadata, **embedding** | "docs/design/graph.md" (type: design) |
| **DocShot** | Снимок документации для doc-first | id, created_at, doc_count | "docshot_a13f92d0b6c2" |
| **CalibrationProfile** | Метрики калибровки по домену | domain, alpha/beta (Bayesian), confidence_gap, trend | "auth domain: overconfidence +12%" |
| **Skill** | Процедурное знание из outcomes | domain, procedure, green/yellow/red zones, version, quality_score | "database_strategy: Use PostgreSQL (89% success)" |
| **DomainIndex** | Иерархический индекс для навигации по графу (Phase 2) | domain, subdomain, level, summary, decision_count, success_rate, top_patterns | "auth/jwt: 12 decisions, 75% success, антипаттерн: custom JWT" |

Связи DomainIndex:
- `DomainIndex →[CONTAINS]→ DomainIndex` (вложенность уровней)
- `DomainIndex →[INDEXES]→ Decision | NegativeKnowledge | Skill | AntiPattern`

#### 4.7.2 Vector Embeddings (Semantic Search)

Три типа нод хранят vector embeddings прямо в свойствах (FalkorDB native):

| Нода | Зачем embedding | Пример запроса |
|---|---|---|
| **Decision** | Семантический поиск похожих решений (не только по module, а по смыслу) | "Что мы решали по аутентификации?" → находит "Use JWT", "Switch to OAuth" |
| **NegativeKnowledge** | Поиск релевантного негативного опыта по смыслу задачи | "API rate limiting" → находит "Custom throttling failed 3x" |
| **Document** | Связь документации с решениями через семантику | "REST API design" → находит spec, ADR, README |

```cypher
-- Vector similarity search (FalkorDB HNSW)
CALL db.idx.vector.queryNodes('Decision', 'embedding', 5, $query_embedding)
YIELD node, score
RETURN node.statement, node.outcome, score

-- Hybrid: graph traversal + vector search
CALL db.idx.vector.queryNodes('NegativeKnowledge', 'embedding', 3, $query_embedding)
YIELD node, score
WHERE node.expires_at IS NULL OR node.expires_at > timestamp()
MATCH (node)-[:CAUSED]-(o:Outcome)-[:RESULTED_IN]-(c:CodeChange)
RETURN node.hypothesis, o.evidence, c.commit_sha, score
```

#### 4.7.3 Типы связей (RelationType)

```
Decision ──[MADE_IN]──────────→ Engram             (решение сделано в сессии)
Decision ──[IMPLEMENTED_IN]───→ CodeChange         (решение реализовано в коммите)
Decision ──[REWORKED_BY]──────→ CodeChange         (решение переделано)
Decision ──[SIMILAR_TO]───────→ Decision           (похожие решения, similarity_score)
Decision ──[MEASURED_BY]──────→ CalibrationProfile (решение учтено в калибровке домена)
Decision ──[DOCUMENTS]────────→ Document           (решение задокументировано)
Decision ──[USES_DOCSHOT]─────→ DocShot            (какой doc-shot использован)
CodeChange ─[RESULTED_IN]────→ Outcome             (коммит привёл к результату)
CodeChange ─[TRIGGERED]──────→ AntiPattern         (коммит содержит антипаттерн)
Outcome ───[CAUSED]──────────→ NegativeKnowledge   (неудача создала знание)
NegativeKnowledge ─[PREVENTED]→ Decision           (знание предотвратило решение)
Document ──[REFERENCES]──────→ Decision            (документ ссылается на решение)
DocShot ──[INCLUDES]────────→ Document            (содержит документы snapshot'а)
CalibrationProfile ─[TRACKS]─→ Domain              (профиль отслеживает домен, implicit)
Skill ─────[GENERATED_FROM]──→ Decision            (скилл сгенерирован из решений)
Skill ─────[BASED_ON]────────→ CalibrationProfile  (скилл основан на калибровке)
Skill ─────[WARNS_AGAINST]───→ AntiPattern         (скилл предупреждает об антипаттерне)
Skill ─────[VERSION_OF]──────→ Skill               (новая версия скилла → предыдущая)
```

**Каузальный цикл** — ключевая особенность схемы:
```
Decision → CodeChange → Outcome (failure) → NegativeKnowledge → PREVENTED → future Decision
```
Негативный опыт замыкается в цикл предотвращения — граф "учится" на ошибках.

**CalibrationProfile** замыкает цикл калибровки:
```
Decision (confidence 0.9) → Outcome (failure) → CalibrationProfile update
→ confidence_gap увеличивается → future context injection предупреждает об overconfidence
```

**Document** обеспечивает трассируемость:
```
Decision ──[DOCUMENTS]──→ ADR doc ←──[REFERENCES]── другие Decisions
```

#### 4.7.4 CalibrationProfile — Bayesian Calibration

CalibrationProfile использует **Beta-распределение** для отслеживания точности решений по доменам:

```
CalibrationProfile {
    domain: "auth"
    alpha: 8.0        # successes + prior (1)
    beta: 3.0         # failures + prior (1)
    sample_size: 9     # α + β - 2
    mean_success_rate: 0.73  # α / (α + β)
    variance: 0.016
    confidence_gap: 0.12    # expected (0.85) - actual (0.73)
    trend: "improving"
    recommendations: ["Lower confidence estimates for auth decisions by ~12%"]
}
```

При каждом resolved Decision:
- outcome = SUCCESS → `alpha += 1`
- outcome = FAILURE → `beta += 1`
- Пересчёт mean, variance, confidence_gap, trend

#### 4.7.5 Индексы и ограничения

```cypher
-- Стандартные индексы
CREATE INDEX ON :Decision(id)
CREATE INDEX ON :Decision(module)
CREATE INDEX ON :Decision(created_at)
CREATE INDEX ON :Decision(outcome)
CREATE INDEX ON :Engram(id)
CREATE INDEX ON :Engram(session_id)
CREATE INDEX ON :Engram(commit_sha)
CREATE INDEX ON :CodeChange(id)
CREATE INDEX ON :CodeChange(commit_sha)
CREATE INDEX ON :CodeChange(decision_id)
CREATE INDEX ON :Outcome(id)
CREATE INDEX ON :Outcome(status)
CREATE INDEX ON :NegativeKnowledge(id)
CREATE INDEX ON :NegativeKnowledge(domain)
CREATE INDEX ON :AntiPattern(id)
CREATE INDEX ON :AntiPattern(category)
CREATE INDEX ON :Document(id)
CREATE INDEX ON :Document(doc_type)
CREATE INDEX ON :Skill(id)
CREATE INDEX ON :Skill(domain)
CREATE INDEX ON :Skill(version)
CREATE INDEX ON :Skill(quality_score)

-- Vector индексы (FalkorDB HNSW)
CALL db.idx.vector.createNodeIndex('Decision', 'embedding', 1536, 'cosine')
CALL db.idx.vector.createNodeIndex('NegativeKnowledge', 'embedding', 1536, 'cosine')
CALL db.idx.vector.createNodeIndex('Document', 'embedding', 1536, 'cosine')

-- Уникальность
CREATE CONSTRAINT FOR (d:Decision) REQUIRE d.id IS UNIQUE
CREATE CONSTRAINT FOR (e:Engram) REQUIRE e.id IS UNIQUE
CREATE CONSTRAINT FOR (c:CodeChange) REQUIRE c.id IS UNIQUE
CREATE CONSTRAINT FOR (o:Outcome) REQUIRE o.id IS UNIQUE
CREATE CONSTRAINT FOR (nk:NegativeKnowledge) REQUIRE nk.id IS UNIQUE
CREATE CONSTRAINT FOR (ap:AntiPattern) REQUIRE ap.id IS UNIQUE
CREATE CONSTRAINT FOR (doc:Document) REQUIRE doc.id IS UNIQUE
CREATE CONSTRAINT FOR (sk:Skill) REQUIRE sk.id IS UNIQUE
```

#### 4.7.6 Ключевые запросы для Context Injection

```cypher
-- Семантически похожие решения (vector search)
CALL db.idx.vector.queryNodes('Decision', 'embedding', 5, $query_embedding)
YIELD node, score
WHERE node.outcome IS NOT NULL
RETURN node.statement, node.outcome, node.confidence, score

-- Похожие решения по модулю (fallback без embedding)
MATCH (d:Decision {module: $module})
WHERE d.outcome IS NOT NULL
RETURN d.statement, d.outcome, d.confidence
ORDER BY d.created_at DESC LIMIT 5

-- Negative knowledge — semantic + expiry filter
CALL db.idx.vector.queryNodes('NegativeKnowledge', 'embedding', 3, $query_embedding)
YIELD node, score
WHERE node.expires_at IS NULL OR node.expires_at > timestamp()
RETURN node.hypothesis, node.conclusion, node.severity, score

-- Каузальная цепочка: "почему мы это решили?"
MATCH path = (d:Decision {id: $id})-[*1..3]->(n)
RETURN path

-- AntiPatterns для файлов
MATCH (c:CodeChange)-[:TRIGGERED]->(ap:AntiPattern)
WHERE ANY(f IN c.files_changed WHERE f STARTS WITH $path_prefix)
RETURN ap.name, ap.removal_rate, ap.recommendation

-- Calibration для домена (overconfidence warning)
MATCH (cp:CalibrationProfile {domain: $domain})
WHERE cp.confidence_gap > 0.1
RETURN cp.confidence_gap, cp.mean_success_rate, cp.trend, cp.recommendations

-- Документация, связанная с решением
MATCH (doc:Document)-[:REFERENCES]->(d:Decision {id: $id})
RETURN doc.file_path, doc.doc_type

-- Prevention cycle: что предотвратило плохие решения?
MATCH (nk:NegativeKnowledge)-[:PREVENTED]->(d:Decision)
RETURN nk.hypothesis, d.statement, d.outcome

-- Active Skills для домена (процедурное знание)
MATCH (sk:Skill {domain: $domain, is_active: true})
RETURN sk.name, sk.procedure, sk.green_zone, sk.yellow_zone, sk.red_zone,
       sk.quality_score, sk.success_rate, sk.version
ORDER BY sk.quality_score DESC LIMIT 3

-- Skill с полной цепочкой evidence
MATCH (sk:Skill {id: $skill_id})-[:GENERATED_FROM]->(d:Decision)
OPTIONAL MATCH (sk)-[:WARNS_AGAINST]->(ap:AntiPattern)
OPTIONAL MATCH (sk)-[:BASED_ON]->(cp:CalibrationProfile)
RETURN sk, collect(d) as decisions, collect(ap) as antipatterns, cp
```

#### 4.7.7 Schema Versioning

Schema имеет встроенную ноду `SchemaVersion` для миграций:

```cypher
CREATE (sv:SchemaVersion {
    version: 2,
    migrated_at: timestamp(),
    description: "Added Document, CalibrationProfile, vector embeddings"
})
```

При обновлениях CLI:
1. Проверяет текущую `SchemaVersion` в графе
2. Если версия < ожидаемой — запускает миграцию
3. Миграция создаёт `Migration` ноду с логом изменений
4. Backup перед каждой миграцией

### 4.8 Plan Mode Integration

**Проблема:** Когда Claude Code входит в Plan Mode, принимаются **самые важные решения** — архитектура, декомпозиция, выбор подхода. Но без Membria этот процесс идёт вслепую: нет контекста из графа, нет проверки против NegativeKnowledge, нет калибровки.

```
Без Membria:
  User: "Plan auth system" → Claude планирует БЕЗ контекста → ошибки повторяются

С Membria:
  User: "Plan auth system"
    ↓ PRE-PLAN: context injection
    ↓ MID-PLAN: validation каждого шага
    ↓ POST-PLAN: capture decisions + skills update
```

#### 4.8.1 Три точки влияния на Plan Mode

**1. PRE-PLAN: Extended Context Injection**

Plan Mode получает **расширенный** context payload (~1500 tokens vs обычных 500):

```json
{
  "mode": "plan",
  "context": {
    "past_plans": [
      {
        "scope": "auth system",
        "steps": 5,
        "sessions_to_complete": 3,
        "reworks": 2,
        "time_estimate_accuracy": 0.43
      }
    ],
    "failed_approaches": [
      "Custom middleware approach failed 2x (dec_034, dec_089)"
    ],
    "successful_patterns": [
      "passport-jwt + Redis sessions: stable 180d"
    ],
    "calibration": {
      "domain": "auth",
      "time_underestimate_factor": 2.3,
      "overconfidence_gap": 0.12
    },
    "project_constraints": [
      "Stack: Fastify, PostgreSQL, Docker",
      "Existing: 12 API endpoints, JWT in use"
    ],
    "active_skills": [
      {
        "name": "auth_strategy",
        "procedure": "...(green/yellow/red zones)...",
        "quality_score": 0.82
      }
    ]
  }
}
```

**2. MID-PLAN: Step Validation**

Каждый шаг плана проверяется по графу:

```
Plan step: "Implement custom JWT middleware"
    ↓
    ├── NegativeKnowledge check:
    │   ⚠ "Custom JWT" matches nk_custom_jwt (severity: high)
    │   Evidence: "failed 2x, 89% removal rate"
    │
    ├── AntiPattern check:
    │   ⚠ "custom-auth-middleware" (ap_custom_auth)
    │   Removal rate: 89% within 97 days
    │
    ├── Skill check:
    │   ℹ Active skill "auth_strategy" recommends:
    │   GREEN: passport-jwt, express-session
    │   RED: custom JWT, custom session store
    │
    └── Past plan failure check:
        ℹ Similar step failed in plan_auth_v1 (dec_034)
```

**3. POST-PLAN: Decision Capture + Skill Update**

```
План принят →
  ├── Каждый архитектурный шаг → Decision node в граф
  ├── Alternatives из плана → записаны в Decision.alternatives
  ├── Plan confidence → используется для CalibrationProfile
  ├── Engram фиксирует полный plan transcript
  └── Existing Skills → проверяются на consistency с новым планом
```

#### 4.8.2 MCP Tools для Plan Mode

```
membria_get_plan_context:
  description: "ALWAYS call this BEFORE creating a multi-step plan.
  Returns: past plans for similar scope, failed approaches,
  successful patterns, active skills, calibration data,
  and project constraints."

membria_validate_plan:
  description: "Call this AFTER generating a plan but BEFORE executing.
  Input: list of plan steps. Returns: warnings about steps that
  conflict with negative knowledge, match known antipatterns,
  contradict active skills, or resemble past failed approaches."

membria_record_plan:
  description: "Call this when a plan is finalized and approved.
  Records each architectural step as a Decision in the graph.
  Updates relevant Skills with new plan data."
```

#### 4.8.3 CLI-команды Plan Mode

```bash
# Просмотр истории планов
membria plans list                         # Все планы
membria plans list --status completed      # Завершённые
membria plans show <plan-id>               # Детали: steps, warnings, outcomes

# Анализ точности планирования
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
# 🎯 Skill "auth_strategy" recommends: passport-jwt (green zone)
# Confidence adjustment: -12% (auth domain overconfidence)
```

#### 4.8.4 Конфигурация

```toml
[plan_mode]
enabled = true
extended_context = true              # Расширенный payload для plan mode
validate_steps = true                # Валидация каждого шага
capture_plan_decisions = true        # Автоматическая запись steps как decisions
inject_skills = true                 # Инжектировать active skills в plan context
time_accuracy_tracking = true        # Трекинг точности временных оценок
```

---

### 4.9 Skills — процедурное знание из графа

**Что это:** Skills — ноды в графе, которые синтезируют **процедурное знание** из накопленных decisions и их outcomes. Если Decision — это "что мы решили", а NegativeKnowledge — "что не работает", то Skill — это **"как надо действовать"**, подкреплённое статистикой.

**Реализация:** `SkillNodeSchema` в `graph_schema.py`

#### 4.9.1 Структура Skill

```json
{
  "id": "sk-auth_strategy-v2",
  "domain": "auth",
  "name": "auth_strategy_recommendation",
  "version": 2,

  "success_rate": 0.89,
  "confidence": 0.82,
  "sample_size": 9,

  "procedure": "## Auth Strategy\n1. Use passport-jwt for JWT validation...",

  "green_zone": [
    "passport-jwt (89% success, 9 projects)",
    "express-session + Redis (85% success, 7 projects)"
  ],
  "yellow_zone": [
    "Custom OAuth2 flow (62% success, needs careful review)",
    "Firebase Auth (60% success in non-Firebase stack)"
  ],
  "red_zone": [
    "Custom JWT implementation (11% success, 89% removed)",
    "Custom session store (23% success)"
  ],

  "quality_score": 0.78,
  "is_active": true,
  "generated_from_decisions": ["dec_091", "dec_034", "dec_089", "dec_142"],
  "conflicts_with": [],
  "related_skills": ["sk-session_management-v1"]
}
```

#### 4.9.2 Зоны применимости

```
GREEN zone (>75% success rate):
  ✓ Используй уверенно, данные подтверждают
  ✓ Инжектируется в context как рекомендация

YELLOW zone (50-75% success rate):
  ⚠ Review carefully, результаты неоднозначны
  ⚠ Инжектируется с предупреждением

RED zone (<50% success rate):
  ✗ Avoid, данные показывают высокий риск
  ✗ Инжектируется как anti-recommendation
  ✗ Связан с NegativeKnowledge и AntiPattern нодами
```

#### 4.9.3 Lifecycle: как Skill рождается и эволюционирует

```
Month 1-2: Накопление данных
  ├── Decisions записываются в граф
  ├── Outcomes приходят (30d stable = SUCCESS)
  └── Skill не генерируется (sample_size < 3)

Month 3: Skill v1 создаётся
  ├── sample_size >= 3 в домене
  ├── LLM (Haiku) анализирует decisions + outcomes
  ├── Генерирует procedure + green/yellow/red zones
  └── quality_score = success_rate * (1 - 1/√sample_size)

Month 6: Skill v2 обновляется
  ├── Новые outcomes изменили success_rate
  ├── Старый Skill v1 --[VERSION_OF]--> Skill v2
  └── Zones пересчитаны с новыми данными

Continuous: Auto-review
  ├── next_review = last_updated + review_interval
  ├── При срабатывании → пересчёт zones
  └── Если success_rate изменился > 10% → notify developer
```

#### 4.9.4 Связь с Behavior Chains (раздел 4.5)

Skills — **источник данных** для Behavior Chains:

```
Behavior Chain "Positive Precedent":
  └── Query: active Skills для домена
      └── Inject: green zone рекомендации

Behavior Chain "Negative Evidence":
  └── Query: red zone из Skills
      └── Inject: anti-recommendations с evidence

Plan Mode validation:
  └── Каждый step проверяется по zones Skills
      └── Step в red zone → warning
```

#### 4.9.5 CLI-команды Skills

```bash
# Просмотр
membria skills list                        # Все active skills
membria skills list --domain auth          # По домену
membria skills show <skill-id>             # Полный skill с zones и evidence
membria skills show <skill-id> --history   # История версий

# Генерация / обновление
membria skills generate                    # Сгенерировать skills из текущих данных
membria skills generate --domain auth      # Только для конкретного домена
membria skills regenerate <skill-id>       # Принудительное обновление

# Аналитика
membria skills quality                     # Quality scores по всем skills
# Skills quality:
# ├── auth_strategy v2:    0.78 (9 decisions, 89% success)
# ├── db_selection v1:     0.65 (5 decisions, 80% success)
# └── api_framework v1:    0.52 (3 decisions, 67% success) ← needs more data

# Экспорт (для review / sharing)
membria skills export --format markdown    # Экспорт в readable формат
membria skills export --format json        # Машиночитаемый
```

#### 4.9.6 Конфигурация

```toml
[skills]
enabled = true
auto_generate = true                 # Автоматически создавать при sample_size >= threshold
generation_threshold = 3             # Min decisions в домене для генерации
review_interval = "30d"              # Интервал пересчёта
generation_model = "haiku"           # haiku | sonnet (Haiku для structured generation)
inject_in_context = true             # Инжектировать active skills в context payload
notify_on_zone_change = true         # Уведомлять при изменении zones
```

---

### 4.10 Domain Index — иерархическая навигация по графу

**Проблема:** При росте графа (500+ нод) плоский поиск деградирует: vector search по 1000 Decision нод — дорого по токенам, медленно, много нерелевантных результатов. Behavior Chains перебирают весь граф при каждом запросе.

**Решение:** Иерархический индекс поверх графа. Идея заимствована из PageIndex (reasoning-based навигация по дереву вместо brute-force vector search), но адаптирована для графовой структуры.

#### 4.10.1 Архитектура

```
DomainIndex (root)
├── DomainIndex "auth" (summary: "47 решений, 82% success, основной: passport-jwt")
│   ├── DomainIndex "auth/jwt" (summary: "12 решений, 3 провала, custom JWT — антипаттерн")
│   │   ├── Decision dec_034
│   │   ├── Decision dec_089
│   │   ├── NegativeKnowledge nk_custom_jwt
│   │   └── Skill sk-auth_strategy-v2
│   ├── DomainIndex "auth/oauth" (summary: "8 решений, 100% success")
│   └── DomainIndex "auth/sessions" (summary: "5 решений, 60% success")
├── DomainIndex "database" (summary: "31 решение, 74% success, overconfidence +30%")
│   ├── DomainIndex "database/postgresql" (...)
│   └── DomainIndex "database/mongodb" (...)
└── DomainIndex "api" (...)
```

#### 4.10.2 Нода DomainIndex

```json
{
  "id": "idx_auth_jwt",
  "domain": "auth",
  "subdomain": "jwt",
  "level": 2,
  "summary": "12 decisions, 3 failures. Custom JWT is antipattern (11% success). passport-jwt recommended (89% success, 9 projects).",
  "decision_count": 12,
  "success_rate": 0.75,
  "failure_count": 3,
  "top_patterns": ["passport-jwt", "jsonwebtoken"],
  "top_antipatterns": ["custom JWT implementation"],
  "calibration_gap": 0.12,
  "last_updated": "2025-06-15T10:00:00Z"
}
```

Связи:
- `DomainIndex →[CONTAINS]→ DomainIndex` (вложенность)
- `DomainIndex →[INDEXES]→ Decision | NegativeKnowledge | Skill | AntiPattern`

#### 4.10.3 Как работает поиск

```
Запрос: "Add JWT authentication"
    │
    ├── 1. Запрос дерева индексов (1 Cypher-запрос)
    │   MATCH (idx:DomainIndex {level: 1})
    │   RETURN idx.domain, idx.summary, idx.decision_count, idx.success_rate
    │   → ~20 нод верхнего уровня с summary
    │
    ├── 2. LLM (Haiku) выбирает ветки (~200 токенов вход, ~50 выход)
    │   "Для JWT authentication релевантны: auth, auth/jwt"
    │
    ├── 3. Запрос конкретных нод из выбранных веток
    │   MATCH (idx:DomainIndex {id: "idx_auth_jwt"})-[:INDEXES]->(n)
    │   RETURN n
    │   → 12 нод вместо 1000
    │
    └── 4. Injection в Behavior Chains (~500 токенов)
```

**Сравнение с текущим подходом:**

| | Текущий (плоский) | С DomainIndex |
|---|---|---|
| Запрос при 1000 нодах | vector search по всем 1000 | Haiku выбирает ветку → 12 нод |
| Токены на поиск | ~2K (embedding + results) | ~250 (tree + Haiku reasoning) |
| Точность | Зависит от embedding quality | Reasoning по summary + structure |
| Explainability | "cosine similarity 0.82" | "выбран auth/jwt потому что запрос про JWT" |

#### 4.10.4 Обновление индекса

Summary пересчитывается при:
- Новый outcome финализирован → пересчёт success_rate в ветке
- Новый Skill сгенерирован → обновление top_patterns
- Новый AntiPattern создан → обновление top_antipatterns

Режим: **батчевый, раз в день** (или при `membria index rebuild`). Не real-time — summary не критично для немедленного обновления.

#### 4.10.5 Автоматическое включение

```
Граф < 100 нод → DomainIndex отключён (плоский поиск дешевле)
Граф 100-500 нод → DomainIndex level 1 (только домены)
Граф > 500 нод → DomainIndex level 1+2 (домены + поддомены)
```

#### 4.10.6 CLI-команды

```bash
membria index show                    # Показать дерево индексов
membria index show --domain auth      # Ветка auth с summary
membria index rebuild                 # Пересчитать все summary
membria index stats                   # Статистика: нод в индексе, coverage, freshness
```

#### 4.10.7 Конфигурация

```toml
[domain_index]
enabled = "auto"                      # auto | true | false
auto_threshold = 100                  # Включить при > N нод в графе
max_depth = 2                         # Максимальная глубина дерева
summary_model = "haiku"               # haiku | sonnet
rebuild_interval = "1d"               # Интервал пересчёта
navigation_model = "haiku"            # Модель для reasoning по дереву
```

---

## 5. Файловая структура

```
~/.membria/
├── config.toml              # Конфигурация
├── auth/
│   ├── token                # API token (encrypted)
│   └── sso-session          # SSO session cache
├── graph/
│   ├── dump.rdb             # FalkorDB local snapshot (in-memory graph persisted)
│   └── appendonly.aof       # FalkorDB AOF для durability
├── cache/
│   ├── sessions.db          # SQLite: user preferences, session state
│   ├── patterns.json        # CodeDigger patterns snapshot
│   └── team-context.json    # Team context snapshot
├── engrams/
│   ├── pending/             # Чекпойнты, ожидающие коммита
│   └── index.db             # SQLite-индекс чекпойнтов для быстрого поиска
├── extractors/
│   └── custom_signals.py    # Пользовательские Monty-плагины для Signal Detector
├── daemon/
│   ├── membria.pid          # PID файл демона
│   ├── membria.sock         # Unix socket для IPC
│   └── logs/
│       └── daemon.log       # Лог демона (ротация)
└── backups/
    └── pre-migration-<date>.json  # Backup перед миграцией
```

---

## 6. config.toml — Референсная конфигурация

```toml
[general]
mode = "solo"                     # solo | team | enterprise
language = "en"                   # en | ru

[graph]
backend = "falkordb"              # falkordb-local | falkordb-cloud | falkordb-cluster
path = "~/.membria/graph/"        # для falkordb-local
# url = "falkordb://xxx.membria.cloud:6379"  # для cloud
# password_cmd = "pass show membria/falkor"  # команда для получения пароля

[daemon]
port = 3117
auto_start = true                 # запускать daemon при первой CLI-команде
log_level = "info"                # debug | info | warn | error

[cache]
enabled = true
max_age = "24h"
max_size_mb = 100
sync_interval = "5m"              # как часто синхронизировать с cloud graph

[detection]
sensitivity = "medium"            # low | medium | high
custom_keywords = []              # дополнительные trigger-слова

[safety]
resonance_threshold = 0.6
max_friction_per_session = 2
enabled_interventions = [
  "anchoring_decomposition",
  "confirmation_devils_advocate",
  "overconfidence_premortem",
  "sunk_cost_fresh_start"
]

[auth]
# team_id = "team-abc123"
# endpoint = "https://api.membria.dev"

[ui]
color = "auto"                    # auto | always | never
compact = false                   # компактный вывод
```

---

## 7. Протокол MCP Server

### 7.1 Exposed Tools (для Claude Code)

MCP Server экспонирует следующие tools через MCP protocol:

| Tool | Описание | Триггер |
|---|---|---|
| `membria_get_context` | Получить decision context для текущего запроса | Каждый запрос к Claude Code |
| `membria.fetch_docs` | Загрузить документацию из графа (doc-first) | Перед любыми read/write MCP tools |
| `membria_record_decision` | Записать решение в graph | Когда Task Router классифицировал как decision |
| `membria_check_patterns` | Проверить код на antipatterns | Post-generation validation |
| `membria_link_outcome` | Связать outcome с decision | При PR merge, CI fail и т.д. |
| `membria_get_negative_knowledge` | Запросить negative knowledge по теме | Pre-generation context fetch |
| `membria_get_calibration` | Получить calibration hint для домена | Decision Surface rendering |

Дополнительно (extended backend tools):
- SessionContext: `membria.session_context_store/retrieve/delete`
- Documents: `membria.docs_add/docs_get/docs_list`
- DocShot link: `membria.docshot_link`
- Outcomes: `membria.outcome_get/outcome_list`
- Skills: `membria.skills_list/skills_get`
- Antipatterns: `membria.antipatterns_list/antipatterns_get`
- Infra: `membria.health`, `membria.migrations_status`, `membria.logs_tail`

#### 7.1.1 Doc-First (Graph-Backed)

**Требование:** перед любыми read/write MCP tools агент обязан вызвать `membria.fetch_docs`.
Источник — **граф**, не внешние сети. Это фиксирует **doc-set snapshot** и делает
решения трассируемыми.

**Выход `membria.fetch_docs`:**
- `doc_shot_id` — детерминированный snapshot id (hash от doc_id + updated_at).

**Traceability:**
- Decision → DocShot (`USES_DOCSHOT`)
- Decision → Document (`DOCUMENTS`, с `doc_shot_id` + `doc_updated_at`)

**Unified Context Manager:**
- Единый контекстный bundle с компакцией под общий budget.
- Источники: decisions, negative knowledge, calibration, doc-shot provenance.

**Two-Level Memory:**
- In-Context: `SessionContext` с TTL (multi-agent visible).
- Persistent: Decision / NegativeKnowledge / Skill / Outcome / Document.

**Session Persistence:**
- `membria session resume <session_id>` — восстановить контекст из SessionContext + Engram.
- Auto-resume: если `session_id` не указан, брать последнюю активную SessionContext.
- Checkpoint: сохранить текущий SessionContext как snapshot (short-lived state).

**Memory Tools (auto-registration):**
- Включается через `memory_tools.enabled = true`.
- Автоматически добавляет MCP tools: `memory_store`, `memory_retrieve`, `memory_delete`, `memory_list`.

**Context Isolation (Graph):**
- Все контекстные ноды содержат `tenant_id`, `team_id`, `project_id`.
- MCP-слой фильтрует чтение по этим полям (GraphClient).

**Plugin-First Context Manager:**
- Порядок источников задаётся `context_plugins` в config.

### 7.2 Context Injection Flow

```
Claude Code request: "Add REST API"
    │
    ▼
MCP Daemon получает запрос
    │
    ├── 1. Task Router: "architecture" → DECISION flow
    │
    ├── 2. Pre-Generation Context Fetch:
    │   ├── Query graph: past decisions on "REST API" / "API framework"
    │   ├── Query graph: negative knowledge for this module
    │   ├── Query graph: team calibration for "api" domain
    │   └── Формирует context payload (~2K tokens)
    │
    ├── 3. Context Injection:
    │   └── Возвращает context как MCP tool response
    │
    └── 4. Claude Code генерирует код С КОНТЕКСТОМ
            │
            ▼
        Post-Generation Validators:
        ├── Bias detection (overconfident language?)
        ├── Consistency check (matches decision?)
        └── Negative knowledge check (respects known failures?)
```

### 7.3 Формат context payload

```json
{
  "task_type": "decision",
  "context": {
    "similar_decisions": [
      {
        "id": "dec_091",
        "statement": "Use Fastify for REST API",
        "outcome": "SUCCESS",
        "confidence": 0.75,
        "date": "2025-01-15"
      }
    ],
    "negative_knowledge": [
      {
        "hypothesis": "Custom JWT implementation",
        "evidence": "Failed security review 2x",
        "last_attempt": "2025-01-28"
      }
    ],
    "calibration": {
      "domain": "api",
      "overconfidence_gap": 0.12,
      "accuracy_rate": 0.68
    },
    "antipatterns": [
      {
        "pattern": "custom-auth-middleware",
        "prevalence": "89% removed within 97 days",
        "recommendation": "Use passport-jwt"
      }
    ]
  },
  "interventions": []
}
```

### 7.4 Единый MCP Server — архитектура клиентов

**Архитектурное решение:** один MCP Server, несколько клиентов.

```
MCP Server (membria-mcp, stdio)
    │
    ├── Claude Code ← MCP клиент (встроенный, уже работает)
    │   └── Использует тулы: capture_decision, get_context, get_plan_context, validate_plan, record_plan
    │
    └── VSCode Extension ← MCP клиент (TypeScript, нужен)
        └── Использует те же тулы + UI: dashboard, decision list, calibration view
```

**Почему не HTTP:**
- HTTP сервер (`webhook_server.py`) — отдельный API, отдельная логика, отдельные ошибки
- Два API = расхождения между тем что видит Claude и что видит VSCode
- Новый тул добавляется дважды: в MCP и в HTTP
- HTTP требует отдельной авторизации, CORS, error handling

**Что нужно:**
- VSCode Extension содержит MCP клиент на TypeScript
- Клиент подключается к тому же `membria-mcp` серверу через stdio
- Extension получает те же данные что и Claude — один граф, одна логика, одни тулы
- HTTP сервер удаляется

**Протокол:** JSON-RPC 2.0 (стандарт MCP). Оба клиента используют одинаковый формат запросов.

---

## 8. Offline Mode

Из `productdev.md`: CLI должен работать при отсутствии сети.

### 8.1 Принцип: Graceful Degradation

```
Online:
  └── Full access to cloud graph + real-time sync

Offline:
  └── MCP Server работает
  └── FalkorDB local snapshot (in-memory, persisted to disk):
      ├── Полная копия доступных decision subgraphs
      ├── CodeDigger patterns (JSON snapshot)
      └── Team context (snapshot)
  └── Новые decisions записываются в queue
  └── Engrams сохраняются локально и синкаются позже
  └── Warning в CLI: "⚠ Working offline"

Back Online:
  └── Auto-sync queued decisions
  └── Push pending engrams
  └── Update local snapshot
  └── Conflict resolution (CRDT-based merge с предупреждением)
```

### 8.2 CLI-поведение

```bash
$ membria daemon status
⚠ Mode: offline (cloud unreachable since 14:32)
  Graph: local cache (47 decisions, last sync: 14:30)
  Queue: 3 decisions pending sync
  Patterns: snapshot from 2025-02-10

$ membria sync
Syncing... ✔ 3 decisions uploaded
           ✔ Cache updated (52 decisions)
           ✔ No conflicts
```

---

## 9. Agent Session Engrams

### 9.1 Концепция

Engrams — примитив, который автоматически сохраняет полный контекст AI-агентской сессии как версионируемый артефакт рядом с кодом в Git. При коммите кода, сгенерированного агентом, Membria захватывает: промпты, переписку, затронутые файлы, вызовы тулов, токены, timing — всё, что нужно для воспроизводимости и аудита.

**Ключевое отличие от Entire.io:** Entire сохраняет "что произошло" (transcript) — это чистый capture tool без feedback loop. Membria **замыкает цикл**: извлекает из engrams decisions, assumptions, negative knowledge → загружает в Reasoning Graph → инжектирует обратно в AI через MCP. Engrams — сырьё, которое граф превращает в каузальную память.

```
Entire:     capture → store → human reads later
Membria:    capture → extract → graph → inject → AI reads → better decisions
```

### 9.2 Как работает

```
Developer запускает Claude Code
    │
    ├── membria daemon перехватывает сессию через MCP
    │   ├── Записывает: prompts, responses, tool calls
    │   ├── Записывает: файлы до/после изменений
    │   └── Записывает: timestamps, tokens consumed
    │
    ├── Developer делает git commit
    │   │
    │   └── Git hook (post-commit) срабатывает:
    │       ├── Создаёт engram snapshot
    │       ├── Извлекает decision candidates из переписки
    │       ├── Линкует engram к commit SHA
    │       └── Сохраняет на отдельную ветку: membria/engrams/v1
    │
    └── Async: Decision Extraction Pipeline
        ├── Парсит transcript → находит decision signals
        ├── Создаёт DECISION_CANDIDATE nodes в graph
        ├── Связывает с файлами и коммитами
        └── Developer подтверждает/отклоняет (1 click)
```

### 9.3 Что сохраняется в Engram

```json
{
  "engram_id": "a3b2c4d5e6f7",
  "session_id": "2025-02-11-abc123de-f456-7890",
  "commit_sha": "9f8e7d6c5b4a",
  "branch": "feature/auth-api",
  "timestamp": "2025-02-11T14:32:00Z",
  
  "agent": {
    "type": "claude-code",
    "model": "claude-sonnet-4-5-20250514",
    "session_duration_sec": 342,
    "total_tokens": 45200,
    "total_cost_usd": 0.14
  },
  
  "transcript": [
    {
      "role": "user",
      "content": "Add REST API for user management, need to choose a framework",
      "timestamp": "2025-02-11T14:26:00Z"
    },
    {
      "role": "assistant",
      "content": "I'll evaluate Fastify vs Express for this...",
      "timestamp": "2025-02-11T14:26:05Z",
      "tool_calls": ["membria_get_context", "membria_record_decision"]
    }
  ],
  
  "files_changed": [
    {
      "path": "src/api/server.ts",
      "action": "created",
      "lines_added": 87,
      "lines_removed": 0
    }
  ],
  
  "decisions_extracted": ["dec_142"],
  "membria_context_injected": true,
  "antipatterns_triggered": ["custom-auth-middleware"],
  
  "monty_state": {
    "snapshot": "<bytes>",
    "paused_at_function": "query_graph",
    "pending_args": {"topic": "auth"},
    "resumable": true
  },
  
  "reasoning_trail": [
    {
      "hypothesis": "Use JWT",
      "evidence_for": 3,
      "evidence_against": 1
    },
    {
      "hypothesis": "Use sessions",
      "evidence_for": 1,
      "evidence_against": 2
    }
  ],
  "elimination_order": ["sessions", "JWT chosen"],
  
  "context_window_snapshot": {
    "injected_context": {
      "similar_decisions": ["dec_091"],
      "negative_knowledge": ["custom JWT failed 2x"],
      "calibration_hint": "overconfidence +12%"
    },
    "context_influenced_outcome": true
  },
  
  "tool_call_graph": [
    {
      "tool": "read_file",
      "args": "src/auth.ts",
      "led_to": "decision_change"
    },
    {
      "tool": "grep",
      "args": "passport",
      "led_to": "alternative_discovered"
    }
  ],
  "critical_path": ["read_file→grep→decision"],
  
  "confidence_trajectory": [
    {"t": 0, "value": 0.3, "trigger": "initial_prompt"},
    {"t": 45, "value": 0.8, "trigger": "found_similar_decision"},
    {"t": 120, "value": 0.6, "trigger": "negative_knowledge_surfaced"}
  ],
  
  "energy_cost": {
    "tokens_total": 45200,
    "monty_executions": 12,
    "monty_total_time_us": 340,
    "graph_queries": 8,
    "files_read": 15
  },
  
  "summary": {
    "intent": "Add REST API with Fastify framework",
    "outcome": "API skeleton created with 4 endpoints",
    "learnings": "Fastify plugin ecosystem confirmed sufficient",
    "friction_points": ["Initial config took longer than expected"],
    "open_items": ["Add rate limiting", "Configure CORS"]
  }
}

**Специфичные для Membria поля:**

- **monty_state**: Сериализованное состояние Monty VM — позволяет "заморозить" агентскую сессию и продолжить позже
- **reasoning_trail**: Цепочка рассуждений — не просто "что решили", а как пришли к решению
- **context_window_snapshot**: Какой контекст из графа был инжектирован и повлиял ли он на решение
- **tool_call_graph**: Граф вызовов инструментов — какие инструменты привели к инсайтам
- **confidence_trajectory**: Как менялась уверенность во время сессии
- **energy_cost**: Ресурсы сессии (токены, время Monty, запросы к графу)

### 9.4 Storage Model

```
Git Repository
├── main (обычный код)
├── feature/auth-api (обычный код)
└── membria/engrams/v1 (отдельная ветка, не мешает коду)
    ├── sessions/
    │   └── 2025-02-11-abc123de.json
    ├── engrams/
    │   ├── a3b2c4d5e6f7.json  → linked to commit 9f8e7d6c
    │   └── b4c3d5e6f7a8.json  → linked to commit 1a2b3c4d
    └── summaries/
        └── 2025-02-11.md      → daily AI summary
```

**Принципы хранения:**
- Чекпойнты живут на **отдельной ветке** — не загрязняют историю кода
- Ветка `membria/engrams/v1` пушится в remote → доступна всей команде
- `.gitattributes` помечает ветку как non-mergeable
- Размер контролируется: transcript можно truncate, сохраняя только decision-relevant фрагменты

### 9.5 CLI-команды

```bash
# Просмотр чекпойнтов
membria engrams list                    # Последние чекпойнты
membria engrams list --branch main      # Фильтр по ветке
membria engrams list --author alice     # Фильтр по автору
membria engrams show <engram-id>    # Полный transcript + decisions

# Поиск
membria engrams search "fastify"        # Семантический поиск по transcripts
membria engrams search --decision "API framework"  # Поиск по решениям
membria engrams search --file src/api/  # Какие сессии затрагивали эти файлы?

# Связь с коммитами
membria engrams for-commit <sha>        # Какие сессии создали этот коммит?
membria engrams for-file <path>         # История AI-сессий для файла

# Управление
membria engrams enable                  # Включить capture (git hooks)
membria engrams disable                 # Выключить
membria engrams strategy auto-commit    # Автоматически при каждом коммите
membria engrams strategy manual         # Только по `membria engram save`
membria engrams push                    # Push чекпойнтов в remote
membria engrams pull                    # Pull чекпойнтов команды

# Ручное создание
membria engram save                     # Сохранить текущую сессию как чекпойнт
membria engram save --message "Auth API decision"  # С описанием

# Rewind (откат к состоянию на момент чекпойнта)
membria engrams rewind <engram-id>  # Восстановить файлы + контекст сессии
```

### 9.6 Интеграция с Reasoning Graph

Engrams — **входной канал** для Reasoning Graph. Извлечение решений из engrams выполняется **Decision Extractor** (см. раздел 4.6):

```
Engram transcript
    │
    ├── 1. Decision Extractor (раздел 4.6)
    │   ├── Level 1: Explicit capture (membria_record_decision)
    │   ├── Level 2: Rule-based Signal Detection
    │   └── Level 3: Structured LLM Extraction (batched)
    │
    ├── 2. DECISION_CANDIDATE creation
    │   ├── Statement: extracted decision
    │   ├── Alternatives: mentioned options
    │   ├── Confidence: extracted/inferred
    │   ├── Context: immutable engram reference
    │   └── Source: engram_id + commit_sha
    │
    ├── 3. Outcome Linking (async, Phase 2+)
    │   ├── PR merge → decision EXECUTED
    │   ├── CI fail → NEGATIVE signal
    │   ├── Revert commit → FAILURE
    │   └── 30d stable → SUCCESS
    │
    └── 4. Graph Update
        ├── New Decision nodes
        ├── RELIES_ON → Assumption nodes
        ├── SUPERSEDES → previous decisions on same topic
        └── Calibration update
```

### 9.7 Командная работа с чекпойнтами

```bash
# Поиск по чекпойнтам всей команды
membria engrams search "authentication" --team
# → 12 sessions found across 4 developers
# → dec_034 (Bob, Jan 15): Chose passport-jwt → SUCCESS
# → dec_089 (Alice, Feb 2): Custom JWT attempt → REVERTED after 3 days
# → dec_142 (You, today): Evaluating auth frameworks

# Переиспользование успешных сессий
membria engrams show dec_034 --transcript
# Показывает полный transcript успешной сессии Bob'а
# → Можно использовать как reference для текущей задачи

# "Почему этот код такой?"
membria engrams for-file src/auth/middleware.ts
# → Session 2025-01-15 by Bob: "Chose passport-jwt because..."
# → Decision dec_034: confidence 0.8, outcome SUCCESS
# → 0 antipatterns triggered
```

### 9.8 Конфигурация чекпойнтов

```toml
[engrams]
enabled = true
strategy = "auto-commit"          # auto-commit | manual
branch = "membria/engrams/v1"
auto_push = true                  # Push при каждом git push
auto_pull = true                  # Pull при каждом git pull

[engrams.capture]
transcript = true                 # Сохранять полный transcript
tool_calls = true                 # Сохранять вызовы тулов
files_diff = true                 # Сохранять diff файлов
token_usage = true                # Сохранять расход токенов
truncate_transcript = 50000       # Max символов transcript (0 = без лимита)

[engrams.extraction]
auto_extract_decisions = true     # Автоматически извлекать decisions
extraction_model = "local"        # local | cloud (для signal extraction)
require_confirmation = true       # Требовать подтверждение extracted decisions

[engrams.privacy]
redact_secrets = true             # Автоматически маскировать секреты в transcripts
redact_patterns = [               # Кастомные паттерны для маскирования
  "(?i)api[_-]?key",
  "(?i)password",
  "(?i)token"
]
```

### 9.9 Session State Machine

Engram capture управляется формальной state machine (вдохновлено Entire.io):

```
          SessionStart
               │
               ▼
          ┌─────────┐
          │ ACTIVE   │ ← сессия Claude Code запущена
          └────┬─────┘
               │ UserPromptSubmit (каждый промпт)
               │   → захват pre-prompt state
               │   → проверка concurrent sessions
               │
               │ Stop (конец turn'а)
               │   → парсинг transcript
               │   → извлечение modified files
               │   → подсчёт токенов
               │   → создание checkpoint
               ▼
     ┌──────────────────┐
     │ ACTIVE_COMMITTED │ ← есть git commit во время сессии
     └────────┬─────────┘
              │ SessionStop / timeout
              ▼
          ┌─────────┐
          │  IDLE    │ ← сессия паузится
          └────┬─────┘
               │ timeout / explicit end
               ▼
          ┌─────────┐
          │  ENDED  │ ← engram финализирован
          └─────────┘
```

**События:** `TurnStart`, `TurnEnd`, `GitCommit`, `SessionStop`
**Конфликты:** При обнаружении concurrent session (два Claude Code в одном репо) — warning + раздельные engrams.

### 9.10 Subagent Tracking

Claude Code запускает Task subagents — у каждого свой transcript. Membria отслеживает их отдельно:

```json
{
  "engram_id": "eng_abc123",
  "main_transcript": "full.jsonl",
  "subagents": [
    {
      "agent_id": "task_a1b2c3",
      "parent_tool_call": "Task",
      "transcript": "agent-a1b2c3.jsonl",
      "tokens": {"input": 3200, "output": 1800},
      "files_touched": ["src/utils.py"],
      "decisions_extracted": 0
    },
    {
      "agent_id": "task_d4e5f6",
      "parent_tool_call": "Task",
      "transcript": "agent-d4e5f6.jsonl",
      "tokens": {"input": 5100, "output": 2900},
      "files_touched": ["src/api/routes.py", "tests/test_api.py"],
      "decisions_extracted": 1
    }
  ],
  "total_tokens": {
    "main": {"input": 12000, "output": 8000},
    "subagents": {"input": 8300, "output": 4700},
    "total": {"input": 20300, "output": 12700}
  }
}
```

Decision Extractor (раздел 4.6) сканирует каждый subagent transcript отдельно — решения принятые в subagents тоже попадают в граф.

### 9.11 Secret Redaction (двухуровневая)

Перед сохранением transcript в engram — автоматическая маскировка секретов:

**Level 1: Entropy-based detection**
```
Shannon entropy > 4.5 для строк длиной > 20 символов
→ вероятный секрет (API key, token, password hash)
→ заменяется на [REDACTED:entropy]
```

**Level 2: Pattern-based detection**
```python
REDACT_PATTERNS = [
    # Стандартные
    r"(?i)api[_-]?key\s*[:=]\s*['\"]?[\w-]{20,}",
    r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]+",
    r"(?i)token\s*[:=]\s*['\"]?[\w.-]{20,}",
    r"(?i)secret\s*[:=]\s*['\"]?[\w.-]{20,}",
    # AWS
    r"AKIA[0-9A-Z]{16}",
    r"(?i)aws_secret_access_key\s*[:=]\s*[\w/+=]{40}",
    # GitHub
    r"gh[pousr]_[A-Za-z0-9_]{36,}",
    # Generic high-entropy (Base64, hex)
    r"[A-Za-z0-9+/=]{40,}",
    r"[a-f0-9]{32,}",
]
```

Пользовательские паттерны добавляются через `[engrams.privacy].redact_patterns` в config.toml.

### 9.12 Git Commit Linking (Trailers)

Bidirectional linking между git commits и engrams через **git commit trailers**:

```bash
# При коммите Membria добавляет trailer:
$ git log --format="%s%n%b" -1
feat: add REST API with Fastify

Membria-Engram: eng_a3b2c4d5e6f7
```

**Это обеспечивает:**
- `git log --grep="Membria-Engram"` — найти все коммиты с AI-сессиями
- `membria engrams for-commit <sha>` → читает trailer, находит engram мгновенно
- Двусторонняя связь: engram → commit_sha, commit → engram_id (через trailer)

**Реализация:** Git hook `prepare-commit-msg` добавляет trailer если текущая сессия активна:

```python
# hooks/prepare-commit-msg
import sys
from membria.session import get_active_session

session = get_active_session()
if session:
    with open(sys.argv[1], 'a') as f:
        f.write(f"\n\nMembria-Engram: {session.engram_id}\n")
```

---

## 10. Установка и Quick Start

### 10.1 Установка

```bash
# pipx (primary, recommended)
pipx install membria

# pip (alternative)
pip install membria

# Homebrew (macOS)
brew install membria

# Manual
curl -fsSL https://get.membria.dev | sh
```

### 10.2 Quick Start — Solo (5 минут)

```bash
$ membria init
✔ Created ~/.membria/
✔ Initialized local graph (FalkorDB in-memory)
✔ Default config written

$ membria daemon start
✔ MCP daemon running on port 3117
✔ Graph: local (FalkorDB)
✔ Git hooks: installed (engram capture enabled)
✔ Ready for Claude Code integration

# Настройка Claude Code:
$ membria setup claude-code
✔ Added MCP server to Claude Code config:
  ~/.claude/mcp_servers.json → membria @ localhost:3117
  Restart Claude Code to activate.
```

### 10.3 Quick Start — Team (30 минут)

```bash
$ membria init --team
? Team ID: team-abc123
? API Key: mem_sk_...
✔ Authenticated
✔ Connected to team graph (FalkorDB Cloud)
✔ Synced 234 decisions to local snapshot

$ membria daemon start
✔ MCP daemon running on port 3117
✔ Graph: cloud (api.membria.dev)
✔ Team: Backend (5 members)
✔ Ready
```

### 10.4 Quick Start — Enterprise

```bash
$ membria login --sso
[Opens browser for Okta authentication]
✔ Authenticated via Okta (alice@corp.com)

$ membria init --enterprise --endpoint https://membria.corp.com
✔ Connected to enterprise graph
✔ Team: Backend (RBAC: developer)
✔ Synced to local cache

$ membria daemon start
✔ MCP daemon running on port 3117
✔ Graph: enterprise (membria.corp.com)
✔ RBAC: developer (read: backend, public)
✔ Ready
```

---

## 11. Token Economy

### 11.1 Проблема

Solo-разработчик с Claude Code тратит ~$30-60/мес на токены. Membria не должна удваивать этот расход. Цель: **overhead < 5%** от основного потребления.

### 11.2 Источники потребления и оптимизации

```
Компонент               Наивный подход      Оптимизированный      Экономия
─────────────────────── ─────────────────── ───────────────────── ─────────
Context Injection        30K ток/день        8K ток/день           -73%
  (compact payload,      (2K × 15 запр.)     (500 × 15 запр.,
   conditional inject)                        skip если граф пуст)

Extractor Level 3        3.5K ток/день       2K ток/день           -43%
  (Haiku вместо Sonnet)  (Sonnet, 5 вызов.)  (Haiku, 5 вызов.)

Engram summaries         25K ток/день        4K ток/день           -84%
  (batch daily)          (2.5K × 10 коммит.)  (1 batch/день)

─────────────────────── ─────────────────── ───────────────────── ─────────
ИТОГО                    58K ток/день        14K ток/день
                         ~$5.4/мес           ~$1.3/мес             -76%
```

### 11.3 Ключевые принципы

1. **Level 1 (Explicit) бесплатен** — Claude вызывает `membria_record_decision` в рамках обычной сессии, дополнительных токенов нет
2. **Level 2 (Rule-based) бесплатен** — regex + keyword scoring в daemon, нулевая стоимость
3. **Level 3 использует Haiku** — структурированная задача (extract JSON из текста), Haiku справляется не хуже Sonnet, стоит в 10× меньше
4. **Context injection — compact mode** — вместо полных текстов decisions передаём one-liners + IDs (~500 токенов vs ~2K)
5. **Conditional injection** — если граф пуст или Task Router классифицировал задачу как tactical → context не инжектируется
6. **Engram summaries — batch daily** — не на каждый коммит, а один раз в конце дня для всех engrams

### 11.4 Конфигурация

```toml
[token_budget]
daily_limit = 50000                  # Hard cap: daemon прекращает LLM-вызовы при достижении
warning_threshold = 0.8              # Предупреждение при 80% бюджета
extraction_model = "haiku"           # haiku | sonnet (Haiku для structured extraction)
context_payload_max_tokens = 500     # Compact mode для context injection
engram_summary = "batch-daily"       # per-commit | batch-daily | on-demand | disabled
skip_context_when_empty = true       # Не инжектировать контекст если граф пуст
```

### 11.5 Мониторинг

```bash
$ membria stats --tokens
Today: 12.4K tokens used (of 50K budget)
├── Context injection: 6.2K (8 decision queries)
├── Extraction L3:     1.8K (3 decisions, Haiku)
└── Engram summaries:  4.4K (1 daily batch)

Month: 287K tokens (~$2.10)
Budget remaining: 78%

$ membria stats --tokens --period 30d --format json
{
  "total_tokens": 287000,
  "estimated_cost_usd": 2.10,
  "breakdown": {
    "context_injection": 180000,
    "extraction": 52000,
    "summaries": 55000
  },
  "decisions_captured": 47,
  "cost_per_decision": 0.045
}
```

### 11.6 Поведение при исчерпании бюджета

```
Budget > 80%: ⚠ Warning в CLI при каждой команде
Budget = 100%:
  ├── Level 3 extraction → остановлен (signals копятся в pending)
  ├── Engram summaries → отложены
  ├── Context injection → продолжает работать (critical path)
  └── Level 1 + Level 2 → продолжают работать (бесплатны)

Следующий день → бюджет сброшен, pending signals обработаны
```

---

## 12. Нефункциональные требования

### 12.1 Performance

| Метрика | Требование | Обоснование |
|---|---|---|
| Context fetch latency | < 100ms (local), < 500ms (cloud) | Не должен замедлять Claude Code |
| Daemon startup | < 3 секунды | Developer experience |
| Cache sync | Background, не блокирует работу | Offline resilience |
| Memory footprint daemon | < 100MB RSS | Не мешает IDE и другим инструментам |

### 12.2 Security

- Токены хранятся encrypted в `~/.membria/auth/`
- Daemon слушает **только localhost** (127.0.0.1)
- HTTPS для всех cloud connections
- Никаких credentials в логах
- Enterprise: SSO session refresh без re-login

### 12.3 Reliability

- Daemon: auto-restart при crash (через systemd/launchd)
- Graph connection: retry с exponential backoff
- Cache: corruption detection + auto-rebuild
- Migration: всегда backup перед изменением

### 12.4 Compatibility

| Платформа | Поддержка |
|---|---|
| macOS (Apple Silicon + Intel) | Primary |
| Linux (x64, arm64) | Primary |
| Windows (WSL2) | Secondary |
| Windows (native) | Future |

| AI Assistant | Интеграция |
|---|---|
| Claude Code | Primary (MCP native) |
| Cursor | Secondary (MCP adapter) |
| VS Code + Continue | Future |

---

## 13. Метрики успеха

Из `coding-superagent.mdx` — метрики, значимые для разработчика (не $, а время/поломки):

| Метрика | Как измеряем | Target |
|---|---|---|
| Rework reduction | Decisions с outcome FAILURE vs baseline | -60% |
| Antipattern prevention | Patterns detected & user changed decision | >50% conversion |
| Onboarding time | Время до первого PR нового разработчика | -50% |
| Decision recall | "Почему мы это решили?" — ответ есть в graph | >80% |
| Adoption friction | Время от `membria init` до первого recorded decision | < 1 день |

---

## 14. Фазы разработки

### Phase 1: Core (MVP)

**Цель:** Solo developer может использовать Membria с Claude Code.

Что входит:
- `membria init`, `daemon start/stop/status`, `config`
- **Единый MCP Server** (JSON-RPC 2.0, stdio) — один сервер для Claude Code и VSCode Extension
- FalkorDB embedded (in-memory, local)
- Causal Graph (9 типов нод, 16 типов связей)
- Task Router (keyword-based classification)
- **Decision Extractor** (Level 1: explicit + Level 2: rule-based + Level 3: batched LLM)
- **Outcome Tracker** — signal-based lifecycle, автоматическая проверка через git (30d stable = SUCCESS)
- **Calibration Profile** — Байесовский Beta-distribution по доменам
- **Behavior Chains** (positive precedents, negative evidence, calibration warnings, antipattern guard)
- **Skills** — автогенерация из outcomes, green/yellow/red zones, версионирование
- **Plan Mode Integration** — PRE-PLAN context, MID-PLAN validation, POST-PLAN capture
- **Decision Firewall** — RedFlag detection, 3-tier (allow/warn/block)
- **Bias Detector** — anchoring, confirmation bias, overconfidence, sunk cost
- Engrams с полной структурой данных + secret redaction + git trailers
- Monty runtime для custom extractor plugins
- `membria decisions list/show/record`
- `membria chain test/stats/toggle`
- `membria skills list/show/generate/quality`
- `membria plan context/validate`
- `membria extractor status/log/run/test`
- `membria engrams list/show/search/save`
- `membria outcomes list/show`
- `membria calibration show/domains`
- `membria doctor`
- `membria setup claude-code`

Что НЕ входит:
- Team/Enterprise auth
- Cloud graph
- VSCode Extension MCP клиент (Phase 2)

### Phase 2: Team + VSCode Integration

**Цель:** Команда из 5–10 человек работает с shared graph. VSCode Extension подключается через MCP.

Добавляется:
- **VSCode Extension MCP клиент** — TypeScript MCP client, подключается к тому же `membria-mcp` серверу через stdio
- **Удаление HTTP сервера** — `webhook_server.py` заменяется MCP клиентом, единый API для Claude Code и VSCode
- `membria login/logout`, `team join/leave/info`
- Cloud graph connection (FalkorDB Cloud)
- Offline mode + sync
- `membria migrate --to-team`
- Antipatterns из CodeDigger
- Post-generation validators (bias detection in output)
- **Domain Index** — иерархическая навигация по графу (авто-включение при >100 нод), reasoning-based поиск через Haiku
- `membria patterns`, `membria stats`
- `membria index show/rebuild/stats`

### Phase 3: Cognitive Safety

**Цель:** Полная Cognitive Safety Layer.

Добавляется:
- LLM Bias Firewall (из `cognitive-safety.mdx`)
- Resonance Detection
- Debiasing Interventions (anchoring, confirmation, overconfidence, sunk cost)
- `membria safety` подкоманды
- Friction by Design (block quick actions при resonance > 0.6)

### Phase 4: Causal Memory & Enterprise

**Цель:** Полная глубина продукта.

Добавляется:
- Causal Memory Layer (do(x) interventions, stratified retrieval)
- Negative Knowledge с automatic expiry
- Ritual detection
- Enterprise: SSO, RBAC, `membria login --sso`
- `membria migrate --to-enterprise`
- Calibration engine
- `membria graph visualize`

---

## 15. Открытые вопросы

1. **Язык реализации:** ✅ **РЕШЕНО: Python**
   - **Обоснование:** 
     - PydanticAI + Monty = готовая агентская среда из коробки
     - Лучший FalkorDB SDK
     - Богатая экосистема агентов (langchain, pydantic-ai, crew)
     - Зрелый MCP SDK
   - **Distribution:** `pipx install membria` (изолированная среда)
   - **Phase 3+:** Возможен вынос daemon в Rust-binary для production performance

2. **MCP Protocol version:** Какую версию MCP поддерживаем? Только stdio или также SSE/HTTP?

3. **Graph schema versioning:** Как мигрировать schema при обновлениях CLI?

4. **Конфликт-резолюция при offline sync:** Last-write-wins достаточно или нужен merge с ручным разрешением?

5. **Telemetry:** Собираем ли анонимную статистику использования? Если да — opt-in only.

6. **Plugin system:** Нужен ли механизм расширений для кастомных antipatterns / interventions?

7. **Negative Knowledge expiry:** Автоматический (half-life decay из `architecture-governance.mdx`) или только ручной через `membria knowledge expire`?

---

## 16. Зависимости и пререквизиты

| Зависимость | Для чего | Обязательность |
|---|---|---|
| Python >= 3.11 | Runtime CLI | Required |
| pydantic-monty | Monty VM для агентской среды | Bundled |
| pydantic-ai | Agent framework с Code Mode | Bundled |
| typer | CLI framework | Bundled |
| Claude Code | Primary AI assistant integration | Required для value |
| FalkorDB (embedded) | Local graph + vector storage (in-memory) | Bundled |
| SQLite | Session state, preferences, engram index | Bundled |
| Git | Engram hooks, version control integration | Required |
| FalkorDB client | Cloud/Enterprise graph connection | Phase 2+ |

---

## Appendix A: Связь с существующими документами

| Документ проекта | Что взято для ТЗ |
|---|---|
| `productdev.md` | Target audience, deployment tiers, migration paths, honest limitations |
| `coding-superagent.mdx` | Architecture, Task Router, token economics, decision flow |
| `superagent-architecture.mdx` | High-level architecture, vibe coding outcomes |
| `cognitive-safety.mdx` | Bias Firewall, Resonance Detection, Debiasing Interventions |
| `causal-memory.mdx` | do(x) layer, Negative Knowledge, stratified retrieval, ritual detection |
| `membria-claude-code-integration.md` | Full integration architecture, honest limitations, qualification criteria |

## Appendix B: Примечания по Limitations

Из `membria-claude-code-integration.md` — честные ограничения, которые CLI должен учитывать:

1. **Cold start problem:** Membria полезна через 2–3 месяца использования. CLI должен показывать прогресс: "47 decisions recorded, 3 antipatterns prevented this month."

2. **Discipline required:** Разработчик должен подтверждать решения (1 click). CLI не должен создавать friction на тактических задачах.

3. **Negative Knowledge как блокер инноваций:** CLI должен поддерживать `membria knowledge expire` и показывать возраст negative knowledge: "⚠ This was tried 2 years ago. Technology may have changed."

4. **Privacy:** CLI хранит историю решений, включая ошибки. Enterprise должен иметь RBAC, чтобы это не использовалось against employees.

---

## TODO: Knowledge Base Ingestion (Planned)

**Goal:** Long-term semantic memory из документов/URL, а не только из decisions.

**Почему позже (несмотря на FalkorDB vector index):**
- Нужен ingestion pipeline (parsing, chunking, metadata)
- Нужны embeddings (batch/refresh)
- Нужны update/forget политики для документов

**MVP-план:**
- Parse `.md`/`.pdf` в `Document` nodes
- Chunk + store embeddings
- Retrieval: keyword + vector, с tags/subject фильтрами

**CLI:**
`membria kb ingest <path> --type kb --tag <tag>` (Cohere embeddings)

**MD xtract (Document Reader → MD xtract, Planned):**
- **Что делает:** Универсальный extractor для PDF/DOCX/XLSX/PPTX/HTML/images → чистый markdown.
- **Зачем:** Единая точка нормализации для ingestion и контекста, без разнобоя форматов.
- **MCP tool (аналог `read_file`):** `membria.md_xtract { input: path|url, options } -> { markdown, metadata }`
- **Интеграция:** `membria kb ingest` использует `md_xtract` перед chunking/embeddings.

## Squads (Task Teams)

**Идея:** под задачу собирается `Squad` (набор ролей/профилей), который запускается по выбранному сценарию.

**Графовая модель (минимум):**
- `Workspace -[:HAS_PROJECT]-> Project`
- `Project -[:USES_SQUAD]-> Squad`
- `Squad -[:ASSIGNS]-> Assignment`
- `Assignment -[:PLAYS_ROLE]-> Role`
- `Assignment -[:USES_PROFILE]-> Profile`

**Почему в графе:**
- Traceability: решения можно связать с `Assignment` и `Profile`.
- Повторяемость: тот же `Squad` можно воспроизвести для новой задачи.

**Сценарии взаимодействия (MVP):**
- `lead_review` — 1 ведущий + 1–2 ревьюера.
- `parallel_arbiter` — 2–3 независимых решения + арбитр.
- `red_team` — решение + атакующий контроль рисков.

**CLI (MVP):**
- `membria squad preset-list`
- `membria squad create --name ... --project-id ... --strategy ... --role ... --profile ...`
- `membria squad create-from-preset <preset_id> --project-id ...`
- `membria squad list [--project-id ...]`
- `membria squad assignments <squad_id>`
- `membria squad run <squad_id> --task "..."`
- `membria squad role-set <role> --prompt-path <path> --context-policy '<json>'`
- `membria squad role-show <role>`
- `membria squad role-link <role> --docshot <id> --skill <id> --nk <id>`
- `membria squad role-unlink <role> --docshot <id> --skill <id> --nk <id>`

**Hybrid Role Control:**
- Роль = (prompt instructions из файла) + (graph-based context policy).
- `context_policy` управляет, какие секции контекста включать (`plugins`), модуль (`module`), бюджет (`max_tokens`) и цепочки (`include_chains`).
 - Предпочтительно: связи Role → DocShot/Skill/NegativeKnowledge для управления контекстом на уровне графа.
