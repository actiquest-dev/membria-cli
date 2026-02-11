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
| `membria_record_decision` | Записать решение в graph | Когда Task Router классифицировал как decision |
| `membria_check_patterns` | Проверить код на antipatterns | Post-generation validation |
| `membria_link_outcome` | Связать outcome с decision | При PR merge, CI fail и т.д. |
| `membria_get_negative_knowledge` | Запросить negative knowledge по теме | Pre-generation context fetch |
| `membria_get_calibration` | Получить calibration hint для домена | Decision Surface rendering |

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

**Ключевое отличие от Entire.io:** Entire сохраняет "что произошло" (transcript). Membria извлекает из чекпойнтов **decisions, assumptions, negative knowledge** и загружает их в Reasoning Graph. Engrams — это сырьё для Causal Memory.

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

Чекпойнты — **входной канал** для Reasoning Graph. Pipeline извлечения:

```
Engram transcript
    │
    ├── 1. Signal Extraction (lightweight LLM call)
    │   ├── Decision signals: "choose", "decide", alternatives mentioned
    │   ├── Assumption signals: "this should work because..."
    │   ├── Negative knowledge: "I tried X but it didn't work"
    │   └── Confidence signals: "definitely", "probably", "not sure"
    │
    ├── 2. DECISION_CANDIDATE creation
    │   ├── Statement: extracted decision
    │   ├── Alternatives: mentioned options
    │   ├── Confidence: extracted/inferred
    │   ├── Context: immutable engram reference
    │   └── Source: engram_id + commit_sha
    │
    ├── 3. Outcome Linking (async)
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

---

## 10. Установка и Quick Start

### 9.1 Установка

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

### 9.2 Quick Start — Solo (5 минут)

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

### 9.3 Quick Start — Team (30 минут)

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

### 9.4 Quick Start — Enterprise

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

## 10. Нефункциональные требования

### 10.1 Performance

| Метрика | Требование | Обоснование |
|---|---|---|
| Context fetch latency | < 100ms (local), < 500ms (cloud) | Не должен замедлять Claude Code |
| Daemon startup | < 3 секунды | Developer experience |
| Cache sync | Background, не блокирует работу | Offline resilience |
| Memory footprint daemon | < 100MB RSS | Не мешает IDE и другим инструментам |

### 10.2 Security

- Токены хранятся encrypted в `~/.membria/auth/`
- Daemon слушает **только localhost** (127.0.0.1)
- HTTPS для всех cloud connections
- Никаких credentials в логах
- Enterprise: SSO session refresh без re-login

### 10.3 Reliability

- Daemon: auto-restart при crash (через systemd/launchd)
- Graph connection: retry с exponential backoff
- Cache: corruption detection + auto-rebuild
- Migration: всегда backup перед изменением

### 10.4 Compatibility

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

## 11. Метрики успеха

Из `coding-superagent.mdx` — метрики, значимые для разработчика (не $, а время/поломки):

| Метрика | Как измеряем | Target |
|---|---|---|
| Rework reduction | Decisions с outcome FAILURE vs baseline | -60% |
| Antipattern prevention | Patterns detected & user changed decision | >50% conversion |
| Onboarding time | Время до первого PR нового разработчика | -50% |
| Decision recall | "Почему мы это решили?" — ответ есть в graph | >80% |
| Adoption friction | Время от `membria init` до первого recorded decision | < 1 день |

---

## 12. Фазы разработки

### Phase 1: Core (MVP)

**Цель:** Solo developer может использовать Membria с Claude Code.

Что входит:
- `membria init`, `daemon start/stop/status`, `config`
- MCP Server с базовым context injection
- Local SQLite graph
- Task Router (keyword-based classification)
- `membria decisions list/show/record`
- `membria doctor`
- `membria setup claude-code`

Что НЕ входит:
- Team/Enterprise auth
- Cloud graph
- Bias Firewall
- Causal Memory
- Outcome linking

### Phase 2: Team

**Цель:** Команда из 5–10 человек работает с shared graph.

Добавляется:
- `membria login/logout`, `team join/leave/info`
- Cloud graph connection (FalkorDB Cloud)
- Offline mode + sync
- `membria migrate --to-team`
- Antipatterns из CodeDigger
- Post-generation validators (bias detection in output)
- `membria patterns`, `membria stats`

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

## 13. Открытые вопросы

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

## 14. Зависимости и пререквизиты

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
