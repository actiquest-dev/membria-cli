# Security Hardening (MCP + Graph)

Этот документ фиксирует выполненные меры защиты и текущие границы.

## ✅ Реализовано

### 1) MCP JSON schema validation
- Входы/выходы валидируются на уровне MCP сервера и daemon.
- Схемы реализованы через Pydantic.

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/mcp_schemas.py`
- `/Users/miguelaprossine/membria-cli/src/membria/mcp_server.py`
- `/Users/miguelaprossine/membria-cli/src/membria/mcp_daemon.py`

### 2) Prompt-safe sanitization
- Санитизация строк перед context injection.
- Санитизация данных при записи Decision/NegativeKnowledge в граф.
- Санитизация контента в процедурах skill.

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/security.py`
- `/Users/miguelaprossine/membria-cli/src/membria/context_injector.py`
- `/Users/miguelaprossine/membria-cli/src/membria/graph.py`
- `/Users/miguelaprossine/membria-cli/src/membria/skill_generator.py`

### 3) Cypher safety
- Ключевые запросы переведены на parameterized queries.
- В `SkillNodeSchema` применяется безопасное экранирование строк.

Файлы:
- `/Users/miguelaprossine/membria-cli/src/membria/plan_context_builder.py`
- `/Users/miguelaprossine/membria-cli/src/membria/plan_validator.py`
- `/Users/miguelaprossine/membria-cli/src/membria/mcp_server.py`
- `/Users/miguelaprossine/membria-cli/src/membria/skill_generator.py`
- `/Users/miguelaprossine/membria-cli/src/membria/graph_schema.py`

## ⚠️ Остается (next steps)

1. Перевести на parameterized queries оставшиеся Cypher‑запросы в:
   - `/Users/miguelaprossine/membria-cli/src/membria/graph_queries.py`
   - `/Users/miguelaprossine/membria-cli/src/membria/decision_surface.py`

2. Санитизация при записи:
   - Outcome, Antipattern, Document, CalibrationProfile.

3. Ввести whitelist/enum для лейблов и property names (где динамика).

4. Набор тестов на:
   - invalid MCP payloads
   - prompt injection strings
   - cypher escaping edge‑cases
