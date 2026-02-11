# Membria CLI - Action Plan (Priority Order)

**Дата:** 11 февраля 2026
**Статус:** In Progress
**Цель:** Превратить mock-only систему в работающую, обкатанную на себе

---

## PHASE 0: Validation (THIS WEEK) 🔥

### Task 0.1: Real FalkorDB Integration Test
**Время:** 2-3 часа
**Что:** Убедиться что граф работает с реальным FalkorDB

```bash
# 1. Проверить что 192.168.0.105:6379 работает
redis-cli -h 192.168.0.105 ping

# 2. Запустить один тест против реальной БД (не mock)
pytest tests/test_decisions_commands.py::test_decisions_record_success \
  --no-mock-graph  # новый флаг

# 3. Проверить что Decision записался в граф
membria decisions list
```

**Ожидаемый результат:**
- ✅ Decision видна в списке
- ✅ Можно её показать: `membria decisions show <id>`
- ✅ Граф возвращает данные

**Файлы для изменения:**
- `tests/conftest.py` - убрать mock GraphClient для одного теста
- `tests/test_decisions_commands.py` - добавить `@pytest.mark.integration`

---

### Task 0.2: Fix Critical Security Issues
**Время:** 1-2 часа
**Что:** Исправить Cypher injection и hardcoded IP

#### 0.2.1: Cypher Injection in graph.py
```python
# BEFORE (уязвимо):
statement = decision.statement.replace("'", "\\'")
query = f"CREATE (d:Decision {{ id: '{decision.decision_id}', statement: '{statement}' }})"

# AFTER (безопасно):
# Используем параметризованные запросы (если FalkorDB поддерживает)
# ИЛИ правильное экранирование
import json
escaped_statement = json.dumps(decision.statement)[1:-1]  # JSON escape
query = f"CREATE (d:Decision {{ id: '{decision.decision_id}', statement: \"{escaped_statement}\" }})"
```

**Файл:** `src/membria/graph.py` (lines ~60-80)

#### 0.2.2: Hardcoded IP
```python
# BEFORE:
falkordb_host = "192.168.0.105"
falkordb_port = 6379

# AFTER:
falkordb_host = config.get("graph.host", "localhost")
falkordb_port = config.get("graph.port", 6379)
```

**Файл:** `src/membria/config.py` - добавить fallback to localhost

---

### Task 0.3: Update Haiku Model
**Время:** 30 минут
**Что:** Использовать актуальную модель

```python
# BEFORE:
model = "claude-3-5-haiku-20241022"

# AFTER:
model = "claude-haiku-4-5-20251001"  # актуальная версия
```

**Файл:** `src/membria/haiku_extractor.py` (line ~25)

**Проверка:**
```bash
grep -r "claude-3-5-haiku" src/
# Должно вывести 0 результатов
```

---

## PHASE 1: Dogfooding (THIS WEEK) 🐕

### Task 1.1: Run Membria on Own Project
**Время:** 3-4 часа
**Что:** Запустить систему на этом проекте (membria-cli)

```bash
# 1. Инициализировать
membria init

# 2. Убедиться что конфиг правильный
membria config show
# Должно показать:
#   graph.host = localhost (or 192.168.0.105)
#   graph.port = 6379
#   daemon.port = 3117

# 3. Запустить daemon
membria daemon start --port 3117

# 4. Проверить что daemon работает
membria daemon status
# Должно показать: Status: running

# 5. Установить git hooks
membria engrams enable

# 6. Сделать коммит (это должно создать engram)
git add ACTION_PLAN.md
git commit -m "Add action plan"

# 7. Проверить что engram создан
membria engrams list
# Должен появиться новый engram с этим коммитом

# 8. Показать детали
membria engrams show <engram_id>
```

**Критические метрики успеха:**
- ✅ Daemon запускается и не крашится
- ✅ Git hook создаёт engram на коммит
- ✅ Engram видна в списке с правильными данными
- ✅ Можно показать детали engram

**Документировать:**
- Время запуска daemon
- Размер engram в graphе
- Ошибки (если есть)

---

### Task 1.2: Manual Decision Recording
**Время:** 1 час
**Что:** Вручную записать несколько решений через MCP

```bash
# Мимикрировать Claude Code вызов:
# 1. Запустить test MCP client
python -c "
import json
import sys

# Simulate Claude Code calling daemon
message = {
    'type': 'call_tool',
    'tool': 'membria_record_decision',
    'params': {
        'statement': 'Use FalkorDB instead of Neo4j for graph storage',
        'alternatives': ['Neo4j', 'Amazon Neptune'],
        'confidence': 0.85,
        'module': 'database'
    }
}

print(json.dumps(message))
"

# 2. Проверить что decision записался
membria decisions list

# 3. Показать детали
membria decisions show <decision_id>

# 4. Проверить что видна в статистике
membria stats show
```

**Ожидаемый результат:**
- ✅ Decision видна в списке
- ✅ Stats показывает её в статистике
- ✅ Можно вытянуть из graphе напрямую

---

### Task 1.3: Test Safety Analysis on Real Decision
**Время:** 30 минут
**Что:** Анализировать реальное решение на bias'ы

```bash
# Запустить bias detector на решении
membria safety analyze --decision <id_from_above>

# Ожидаемый вывод:
# Statement: "Use FalkorDB instead of Neo4j..."
# Detected Biases: (if any)
# Risk Score: X.XX
# Recommendations: (if any)

# Если risk > 0: отлично, сработало
# Если risk = 0: тоже нормально (хорошее решение)
```

---

## PHASE 2: Real Integration Tests (NEXT WEEK)

### Task 2.1: Remove Mock Tests, Add Real Tests
**Время:** 4-5 часов
**Что:** Переписать тесты чтобы они использовали реальный GraphClient

**Новая структура:**
```
tests/
├── conftest.py                      # Shared fixtures
├── unit/                            # Юнит-тесты (с моками)
│   ├── test_bias_detector.py        # BiasDetector logic
│   ├── test_signal_detector.py      # Signal patterns
│   └── test_models.py               # Data model validation
├── integration/                     # Интеграционные (реальный граф!)
│   ├── test_graph_operations.py     # FalkorDB connection
│   ├── test_decision_flow.py        # Record → List → Show
│   ├── test_engram_flow.py          # Create → Show → List
│   └── test_mcp_daemon.py           # Real daemon + stdio
└── e2e/                             # End-to-end (полный цикл)
    └── test_full_workflow.py        # Init → Daemon → Decision → Stats
```

**Task 2.1.1: Create test_graph_operations.py**
```python
@pytest.mark.integration
def test_falkordb_connection():
    """Тест что граф действительно доступен"""
    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    assert graph.connect() == True
    health = graph.health_check()
    assert health['status'] == 'healthy'
    graph.disconnect()

@pytest.mark.integration
def test_decision_roundtrip():
    """Записать decision → прочитать → проверить данные"""
    config = ConfigManager()
    graph = GraphClient(config.get_falkordb_config())
    graph.connect()

    decision = Decision(
        decision_id="test_" + str(uuid.uuid4())[:8],
        statement="Test decision",
        alternatives=["A", "B"],
        confidence=0.8,
        module="test"
    )

    # Записать
    assert graph.add_decision(decision) == True

    # Прочитать
    results = graph.get_decisions()
    assert any(d.id == decision.decision_id for d in results)

    graph.disconnect()
```

---

### Task 2.2: MCP Daemon Integration Test
**Время:** 3-4 часа
**Что:** Тестировать реальный MCP daemon со stdio

```python
@pytest.mark.integration
def test_mcp_daemon_record_decision():
    """Запустить daemon, отправить decision через stdio, проверить"""
    import subprocess
    import json

    # Запустить daemon как subprocess
    daemon_proc = subprocess.Popen(
        ["python", "-m", "membria.daemon_main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Отправить message
        message = {
            "type": "call_tool",
            "tool": "membria_record_decision",
            "params": {
                "statement": "Test from daemon",
                "alternatives": ["Alt1"],
                "confidence": 0.7,
                "module": "test"
            }
        }
        daemon_proc.stdin.write(json.dumps(message) + "\n")
        daemon_proc.stdin.flush()

        # Прочитать ответ
        response = daemon_proc.stdout.readline()
        result = json.loads(response)

        assert result["type"] == "tool_result"
        assert result["result"]["status"] == "success"

    finally:
        daemon_proc.terminate()
        daemon_proc.wait()
```

---

## PHASE 3: CodeDigger Integration (2-3 НЕДЕЛИ)

### Task 3.1: Design CodeDigger API Endpoint
**Время:** 1-2 часа
**Что:** Определить формат patterns.json

```python
# GET /api/patterns (CodeDigger backend)
Response: [{
    "id": "custom-jwt",
    "name": "Custom JWT Implementation",
    "category": "auth",
    "severity": "high",
    "languages": ["javascript", "typescript"],

    "stats": {
        "repos_affected": 20470,
        "total_occurrences": 156784,
        "removal_rate": 0.89,
        "avg_days_to_removal": 97,
        "median_days_to_removal": 42
    },

    "detection": {
        "keywords": ["jwt.sign", "jwt.verify", "jsonwebtoken"],
        "regex": [r"jwt\.sign\s*\(", r"jsonwebtoken"],
        "exclude_keywords": ["passport", "passport-jwt"]
    },

    "recommendation": "Use passport-jwt instead",
    "examples": {
        "bad": "const token = jwt.sign(payload, secret);",
        "good": "passport.use(new JWTStrategy(...));"
    },

    "evidence": "89% of custom JWT implementations are removed within 97 days"
}, ...]
```

**Файл для создания:**
- `backend/src/routes/api/patterns.py` - implement endpoint

---

### Task 3.2: CLI Integration with CodeDigger
**Время:** 3-4 часа
**Что:** CLI тянет patterns от CodeDigger и использует их

#### 3.2.1: Fetch and Cache Patterns
```python
# src/membria/pattern_cache.py (NEW FILE)

class PatternCache:
    def __init__(self):
        self.cache_file = Path.home() / ".membria" / "patterns.json"
        self.cache_ttl = 86400  # 1 day

    def fetch_from_server(self):
        """GET /api/patterns from CodeDigger"""
        import httpx
        url = os.getenv("CODEDIGGER_API", "http://localhost:4000/api/patterns")
        response = httpx.get(url, timeout=10)
        return response.json()

    def get_patterns(self):
        """Get patterns from cache or fetch fresh"""
        if self.cache_file.exists():
            mtime = self.cache_file.stat().st_mtime
            if time.time() - mtime < self.cache_ttl:
                return json.loads(self.cache_file.read_text())

        # Cache miss or expired
        patterns = self.fetch_from_server()
        self.cache_file.write_text(json.dumps(patterns, indent=2))
        return patterns
```

#### 3.2.2: New Command
```bash
membria patterns list              # Show all 25 patterns with stats
membria patterns list --severity high  # Filter
membria patterns sync              # Force update from server
membria patterns show custom-jwt   # Show one pattern with evidence
```

#### 3.2.3: Pre-commit Hook Integration
```python
# .git/hooks/post-commit (UPDATED)

def check_patterns(diff_text):
    """Check diff against patterns"""
    cache = PatternCache()
    patterns = cache.get_patterns()

    for pattern in patterns:
        for keyword in pattern["detection"]["keywords"]:
            if keyword in diff_text:
                print(f"⚠️  Warning: {pattern['name']}")
                print(f"   Evidence: {pattern['stats']['removal_rate']*100:.0f}% removal rate")
                print(f"   Recommendation: {pattern['recommendation']}")
                return False  # Block or warn?

    return True
```

---

### Task 3.3: MCP Context Injection
**Время:** 2 hours
**Что:** Daemon инжектит паттерны в контекст Claude Code

```python
# src/membria/mcp_daemon.py (UPDATED)

class MCPDaemonServer:
    def _handle_tool_call(self, tool_name, params):
        if tool_name == "membria_get_context":
            # Вернуть не только decision context, но и patterns
            patterns = PatternCache().get_patterns()

            # Фильтровать релевантные паттерны для текущего языка
            relevant_patterns = [
                p for p in patterns
                if "javascript" in p["languages"] or "python" in p["languages"]
            ]

            return {
                "type": "tool_result",
                "pending_signals": ...,
                "similar_decisions": ...,
                "relevant_patterns": relevant_patterns[:5],  # Top 5
                "pattern_evidence": "Recent data from 156K+ occurrences"
            }
```

---

## PHASE 4: Documentation & Cleanup (1 НЕДЕЛЯ)

### Task 4.1: Update Spec
**Время:** 2 часа
**Что:** Сократить spec с 62KB до MVP (3-5 страниц)

**Структура:**
1. Why Membria (1 page)
2. Architecture (1 page)
3. Usage (1 page)
4. Roadmap (Phase 1 done, Phase 2/3/4 planned)

**Удалить:** SSO, RBAC, Monty plugins, Team features (Phase 4+)

---

### Task 4.2: Fix Documentation
**Время:** 1-2 часа
**Что:** Обновить README.md и добавить GETTING_STARTED.md

```markdown
# GETTING_STARTED.md

## Prerequisites
- Python 3.11+
- FalkorDB running (192.168.0.105:6379 or local docker)
- Git repository with write access

## Quick Start

1. Install
   pip install -e ".[dev]"

2. Initialize
   membria init

3. Start daemon
   membria daemon start

4. Verify
   membria daemon status

5. Install git hooks
   membria engrams enable

6. Make a decision
   membria decisions record \
     --statement "Use PostgreSQL for persistence" \
     --confidence 0.85 \
     --alternatives MongoDB --alternatives SQLite

7. View decision
   membria decisions list
   membria decisions show <id>

8. Check calibration
   membria stats show
   membria calibration show
```

---

## Timeline Summary

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| **Phase 0** | 1 week | Real FalkorDB working, Security fixed |
| **Phase 1** | 1 week | System tested on own project (dogfooding) |
| **Phase 2** | 1 week | Real integration tests (no mocks) |
| **Phase 3** | 2-3 weeks | CodeDigger integration, patterns working |
| **Phase 4** | 1 week | Docs, cleanup, release |

**Total: 5-7 weeks to production-ready**

---

## Success Criteria

### By end of Phase 0:
- ✅ FalkorDB tests pass (real, not mock)
- ✅ No security vulnerabilities
- ✅ Latest model versions

### By end of Phase 1:
- ✅ System used on real project
- ✅ Engrams created and stored
- ✅ Decisions recorded and retrieved
- ✅ Daemon doesn't crash under real use

### By end of Phase 2:
- ✅ 20+ integration tests (real DB, no mocks)
- ✅ MCP daemon tested with real stdio
- ✅ 90%+ code coverage (meaningful coverage)

### By end of Phase 3:
- ✅ CLI pulls patterns from CodeDigger API
- ✅ Pre-commit hook works with pattern evidence
- ✅ Pattern stats displayed in warnings

### By end of Phase 4:
- ✅ Clear, concise documentation
- ✅ Getting started guide
- ✅ Ready for production use

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| FalkorDB doesn't work with real data | Test in Phase 0, document issues |
| MCP daemon crashes on real use | Extensive logging, graceful shutdown |
| CodeDigger API not available | Graceful fallback (no patterns) |
| Performance issues with large graphs | Implement pagination, caching early |

---

## Notes

- **Start with Phase 0 THIS WEEK** - it's critical
- **Don't skip dogfooding (Phase 1)** - it will reveal real issues
- **Prioritize integration tests** over unit tests
- **Document as you go** - don't leave it for the end
- **Use real data, not mocks** - mocks hide problems

---

Готов начинать? Начнём с Phase 0?
