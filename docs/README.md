# Membria Документация

Полная документация по установке, использованию и разработке Membria.

---

## 🚀 Начните Отсюда

### Новичок на Mac?
📄 **[MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)** (30-60 минут)
- Проверка требований
- Пошаговая установка
- Запуск MCP Сервера
- Настройка VSCode Extension
- Решение проблем

### Хочу быстро подключить к Claude?
📄 **[CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md)** (10 минут)
- Запуск MCP Сервера
- Настройка `.claude/claude.json`
- Проверка что работает
- 7 основных команд

### Нужен полный индекс всех гайдов?
📄 **[GUIDES_INDEX.md](GUIDES_INDEX.md)** (5 минут)
- Навигация по всем документам
- Поиск по темам
- Гайды по сценариям
- Контрольный список

---

## 📚 Все Документы

### Установка & Запуск
- **[MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)** - Полная инструкция для Mac
- **[CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md)** - Быстрое подключение к Claude

### Интеграции
- **[CLAUDE_INTEGRATION.md](CLAUDE_INTEGRATION.md)** - Claude Code (7 tools)
- **[VSCODE_INTEGRATION.md](VSCODE_INTEGRATION.md)** - VSCode Tasks (11 tasks)

### VSCode Extension (в папке ../vscode-extension/)
- **README.md** - Для пользователей
- **DEVELOPMENT.md** - Для разработчиков
- **INTEGRATION_GUIDE.md** - Полная архитектура
- **COMPLETION_STATUS.md** - Статус реализации
- **SETUP_CHECKLIST.md** - Тестирование

### Обзор
- **[GUIDES_INDEX.md](GUIDES_INDEX.md)** - Индекс всех документов

### Architecture & Design (2026-02-18 Updated)
- **[SQUAD_ROLES_SETUP.md](SQUAD_ROLES_SETUP.md)** - Squad roles CLI management, graph-backed
- **[COUNCIL_SQUAD_INTEGRATION.md](COUNCIL_SQUAD_INTEGRATION.md)** - Council vs Squad architecture
- **[WHITESPACE_AUDIT_FIXES.md](WHITESPACE_AUDIT_FIXES.md)** - Bug audit report (23 bugs identified, 10 fixed)
- **[ARCHITECTURE_INVENTORY.md](ARCHITECTURE_INVENTORY.md)** - Complete inventory of all changes this session

### Security Updates (2026-02-18)
- **Cypher Injection Fixed** - All 18 methods now parameterized (graph.py + graph_schema.py)
- **Prompt Injection Mitigated** - red_team_audit() sanitized
- **Real Calibration** - CalibrationUpdater integrated in daemon

---

## 🔒 Security & Data Integrity (NEW)

Membria инжектирует контекст в LLM через MCP. Чтобы исключить "грязные" JSON payloads,
prompt-injection через данные графа и небезопасные записи в FalkorDB:

- **MCP JSON schema validation** для всех tool inputs/outputs
- **Prompt-safe sanitization** для всех текстовых полей в context injection
- **Cypher escaping** для любых строк, записываемых в граф

Подробнее: `/docs/ARCHIVE/membria-cli-spec.md`.

Дополнительно: `/Users/miguelaprossine/membria-cli/docs/SECURITY_HARDENING.md`.

---

## 📘 MCP Doc-First (Graph-Backed) (NEW)

Membria использует **doc-first workflow** для MCP инструментов: агент должен вызвать
`membria.fetch_docs` перед другими MCP tools, чтобы загрузить базовый контекст
из графа. Это снижает дрейф и дает аудит источников.

Документация: `/Users/miguelaprossine/membria-cli/docs/MCP_DOC_FIRST.md`.

---

## 🔁 Memory Loop (NEW)

Документация по циклу памяти: store → index → retrieve → update → forget.

- `/Users/miguelaprossine/membria-cli/docs/MEMORY_LOOP.md`

---

## 📚 Knowledge Base (MVP)

Ингест документов в граф с embeddings (Cohere).

Команда:
`membria kb ingest <path> --type kb --tag <tag>`

---

## 🧩 Memory Tools (MCP)

Если включить `memory_tools.enabled = true`, MCP автоматически регистрирует:
`membria.memory_store`, `membria.memory_retrieve`, `membria.memory_delete`,
`membria.memory_list`.

---

## 🎯 Выберите Вашу Роль

### 👤 Я новичок
1. Прочитайте: [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)
2. Следуйте пошаговым инструкциям
3. Попробуйте первую команду
4. Готово! 🎉

**Время:** ~1 час

### 💻 Я разработчик
1. Прочитайте: [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)
2. Изучите: ../vscode-extension/DEVELOPMENT.md
3. Запустите в debug режиме: `F5`
4. Делайте изменения в `src/`

**Время:** зависит от задачи

### 🤖 Я хочу использовать Claude
1. Прочитайте: [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md)
2. Запустите: `python src/membria/start_mcp_server.py`
3. Настройте: `.claude/claude.json`
4. Используйте 7 tools в Claude

**Время:** ~30 минут

### ⚙️ Я хочу автоматизировать VSCode
1. Прочитайте: [VSCODE_INTEGRATION.md](VSCODE_INTEGRATION.md)
2. Настройте: `.vscode/tasks.json`
3. Используйте: `Ctrl+Shift+M` + буква

**Время:** ~15 минут

---

## 🔍 Быстрый Поиск

| Вопрос | Ответ |
|--------|-------|
| Как установить на Mac? | [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md) |
| Как подключить к Claude? | [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md) |
| Какие tools доступны в Claude? | [CLAUDE_INTEGRATION.md](CLAUDE_INTEGRATION.md) |
| Какие tasks доступны в VSCode? | [VSCODE_INTEGRATION.md](VSCODE_INTEGRATION.md) |
| Как разрабатывать extension? | ../vscode-extension/DEVELOPMENT.md |
| Как я что-то сломал? | [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md) → Решение Проблем |
| Полный индекс всех гайдов | [GUIDES_INDEX.md](GUIDES_INDEX.md) |

---

## 📋 Структура Папок

```
membria-cli/
├── docs/                          ← ВЫ ЗДЕСЬ
│   ├── README.md                  ← Этот файл
│   ├── MACOS_SETUP_GUIDE.md       ← Установка на Mac
│   ├── CLAUDE_QUICKSTART.md       ← Быстрое подключение Claude
│   ├── CLAUDE_INTEGRATION.md      ← Claude Code tools
│   ├── VSCODE_INTEGRATION.md      ← VSCode Tasks
│   └── GUIDES_INDEX.md            ← Индекс всех документов
│
├── src/membria/
│   ├── start_mcp_server.py        ← Запуск MCP сервера
│   ├── skill_generator.py
│   ├── behavior_chains.py
│   └── commands/
│       ├── plan_commands.py       ← CLI команды для планов
│       └── skill_commands.py      ← CLI команды для skills
│
├── vscode-extension/      ← VSCode Extension
│   ├── README.md                  ← Пользователям
│   ├── DEVELOPMENT.md             ← Разработчикам
│   ├── INTEGRATION_GUIDE.md       ← Архитектура
│   └── src/
│       ├── extension.ts
│       ├── membriaClient.ts
│       └── providers/
│
└── README.md                      ← Главный README проекта
```

---

## ✅ Контрольный Список: Что Прочитать

### Обязательно
- [ ] [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md) - как установить и запустить

### Смотря что делать
- [ ] [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md) - если используете Claude
- [ ] [CLAUDE_INTEGRATION.md](CLAUDE_INTEGRATION.md) - если нужны детали tools
- [ ] [VSCODE_INTEGRATION.md](VSCODE_INTEGRATION.md) - если используете VSCode Tasks
- [ ] ../vscode-extension/DEVELOPMENT.md - если разрабатываете extension

### Для справки
- [ ] [GUIDES_INDEX.md](GUIDES_INDEX.md) - полный индекс
- [ ] ../vscode-extension/README.md - как использовать extension

---

## 🆘 Что Делать Если Что-то Не Работает?

1. **Проблемы при установке?**
   → [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md) → Решение Проблем

2. **MCP Сервер не подключается?**
   → [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md) → Решение Проблем

3. **Extension не работает?**
   → ../vscode-extension/README.md → Troubleshooting

4. **Нужна общая помощь?**
   → [GUIDES_INDEX.md](GUIDES_INDEX.md) → Поиск по теме

---

## 📞 Быстрые Команды

```bash
# Запустить MCP Сервер
cd ~/Developer/membria-cli
source venv/bin/activate
python src/membria/start_mcp_server.py

# Проверить что сервер работает
curl http://localhost:6379/health

# Открыть документацию в VSCode
code docs/

# Запустить CLI команду
membria plans list
membria skills list
membria plans validate "Step 1: ...\nStep 2: ..."
membria squad preset-list
membria squad create-from-preset incident-rca --project-id proj_123
```

---

## 📚 Рекомендуемый Порядок Чтения

**Первый день:**
1. [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md) - Установка (30 мин)
2. [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md) - Подключение Claude (10 мин)
3. ../vscode-extension/README.md - Использование Extension (20 мин)

**Итого:** ~1 час практической работы

**Если нужна архитектура:**
- [GUIDES_INDEX.md](GUIDES_INDEX.md) → Выберите вашу роль
- ../vscode-extension/INTEGRATION_GUIDE.md - Полная архитектура

---

## 🎓 Примеры Использования

### Пример 1: Записать решение в Claude
```
User: "I decided to use PostgreSQL. I'm 85% confident."

Claude: [Использует capture_decision]
→ Decision saved to Membria
```

### Пример 2: Получить контекст в Claude
```
User: "What has the team learned about caching?"

Claude: [Использует get_decision_context]
→ Shows past decisions, success rates, warnings
```

### Пример 3: Проверить план в Claude
```
User: "Is this database migration plan safe?
       1. Backup current database
       2. Run migration script
       3. Test new schema"

Claude: [Использует validate_plan]
→ Checks against known failures, antipatterns
```

### Пример 4: Использовать VSCode Extension
```
1. Нажмите: Ctrl+Shift+M D
2. Введите: "Use Redis for caching"
3. Вводите: "Memcached, In-memory"
4. Уверенность: 0.8
5. ✅ Decision captured
```

---

## 📈 Статистика

- **Всего документов:** 8 гайдов
- **Всего строк:** 10,000+ строк документации
- **Среднее время чтения:** 5-30 минут на гайд
- **Всех примеров:** 50+

---

## 🔄 Версионирование

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0.1 | 2026-02-18 | CRITICAL bugs fixed (5/5), HIGH (5/8), Cypher injection security hardening, Squad integration |
| 1.0.0 | 2026-02-11 | Начальная версия, все компоненты готовы |

---

## 📞 Помощь и Поддержка

**Документация:**
- Основной README: [../README.md](../README.md)
- Все гайды: [GUIDES_INDEX.md](GUIDES_INDEX.md)

**Быстрая помощь:**
- Installation: [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)
- Claude integration: [CLAUDE_QUICKSTART.md](CLAUDE_QUICKSTART.md)
- Troubleshooting: [MACOS_SETUP_GUIDE.md](MACOS_SETUP_GUIDE.md)

---

**Обновлено:** 2026-02-18
**Статус:** ✅ Полная документация (+ архитектурная инвентаризация)
**Версия:** 1.0.1
