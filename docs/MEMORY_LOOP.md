# Memory Loop (store → index → retrieve → update → forget)

Этот документ фиксирует текущую реализацию memory loop и базовую политику.

## ✅ Реализовано (минимальный контур)

### Store
- `MemoryManager.store_decision`
- `MemoryManager.store_negative_knowledge`

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/memory_manager.py`
- `/Users/miguelaprossine/membria-cli/src/membria/graph.py`
- `/Users/miguelaprossine/membria-cli/src/membria/models.py`

### Index
- FalkorDB индексы в `graph_schema.py`
- Данные пишутся с `memory_type`, `memory_subject`, `ttl_days`, `is_active`

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/graph_schema.py`
- `/Users/miguelaprossine/membria-cli/src/membria/graph.py`

### Retrieve
- `MemoryManager.retrieve_decisions` с ранжированием:
  `score = relevance * confidence * freshness * (0.5 + 0.5 * impact)`
 - Unified Context Manager: единый компактный bundle для инжекции

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/context_manager.py`

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/memory_manager.py`
- `/Users/miguelaprossine/membria-cli/src/membria/memory_policy.py`

### Update
- `MemoryManager.update_decision`
- `MemoryManager.update_negative_knowledge`

### Forget (soft)
- `MemoryManager.forget_decision`
- `MemoryManager.forget_negative_knowledge`
- Механика: `is_active=false`, `deprecated_reason`, `last_verified_at`

## ⚙️ Политика памяти (MemoryPolicy)

Параметры:
- `default_ttl_days`
- `ttl_by_type` (episodic/semantic/procedural)
- `half_life_days`
- `min_confidence`
- `allow_hard_delete`

Файл:
- `/Users/miguelaprossine/membria-cli/src/membria/memory_policy.py`

## ⚠️ Next Steps

1. Интегрировать `MemoryManager` в `PlanContextBuilder` и `DecisionSurface`.
2. Добавить forget policy cron/job (по TTL).
3. Учесть user‑centric память (разделение неймспейсов).
4. Добавить тесты на:
   - scoring/freshness
   - update/forget
   - retrieval ranking

## 📌 DocShot (Provenance)

DocShot фиксирует, какие документы использованы при решении и дает
`doc_shot_id` для трассировки. Decision связывается с DocShot и
Document через отношения `USES_DOCSHOT` и `DOCUMENTS`.

## 🧠 Two-Level Memory (In-Context vs Persistent)

- **In-Context (SessionContext):** короткоживущий контекст сессии,
  хранится в графе и доступен другим агентам. TTL по умолчанию — 3 дня.
- **Persistent:** Decision / NegativeKnowledge / Skill / Outcome / Document.

Связь:
- `Engram -[:HAS_CONTEXT]-> SessionContext`

## ✅ Context Injection (Daemon)

`membria_get_context` теперь возвращает:
- unified `compact_context`
- `doc_shot_id` (если известен session_id)

## 🔁 Session Persistence (CLI)

- `membria session resume [session_id]` — восстановить активный SessionContext.
- `membria session checkpoint --task ...` — сохранить snapshot контекста.

## 🧩 Memory Tools (Auto-Registration)

Если `memory_tools.enabled = true`, MCP автоматически регистрирует:
- `membria.memory_store`
- `membria.memory_retrieve`
- `membria.memory_delete`
- `membria.memory_list`

## 🧰 Backend MCP Tools (Extended)

Доступны базовые backend tools:
- SessionContext: `membria.session_context_*`
- Documents/DocShot: `membria.docs_*`, `membria.docshot_link`
- Outcomes: `membria.outcome_get`, `membria.outcome_list`
- Skills/Antipatterns: `membria.skills_*`, `membria.antipatterns_*`
- Infra: `membria.health`, `membria.migrations_status`, `membria.logs_tail`

## 🔐 Context Isolation (Graph)

Контекстные ноды получают поля:
- `tenant_id`, `team_id`, `project_id`

Все MCP-запросы на чтение фильтруются этими полями в GraphClient.

## 🧩 Plugin-First Context Manager

Порядок сборки контекста задаётся `context_plugins` в config.
Это позволяет менять приоритеты и отключать источники без правки кода.

## 🔁 Миграции

Добавлена миграция `v0.3.0` для проставления default memory‑metadata
в существующих нодах.

Файл:
- `/Users/miguelaprossine/membria-cli/src/membria/migrations/versions/v0_3_0_memory_lifecycle.py`
