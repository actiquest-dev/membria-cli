# Быстрый Старт: Membria + VSCode + Codex

## 🚀 Запуск за 3 шага

### Шаг 1: Запустить FalkorDB

```bash
# Проверить что FalkorDB работает
redis-cli -h 192.168.0.105 ping
# Должно вернуть: PONG
```

### Шаг 2: Запустить VSCode Extension

```bash
# Открыть папку extension в VSCode
cd ~/Developer/membria-cli/vscode-extension
code .
```

**В VSCode:**
1. Нажать `F5` (или Run → Start Debugging)
2. Откроется новое окно VSCode с загруженным extension
3. В новом окне нажать `Cmd+Shift+P` → набрать "Membria"
4. Должны появиться команды:
   - Membria: Capture Decision
   - Membria: Get Context
   - Membria: Validate Plan
   - и т.д.

### Шаг 3: Использовать Membria

**Команды (в окне с extension):**
- `Cmd+Shift+M D` - Capture Decision
- `Cmd+Shift+M C` - Get Context
- `Cmd+Shift+M V` - Validate Plan
- `Cmd+Shift+M O` - Record Outcome

---

## 🔧 Настройка Codex (OpenAI) в VSCode

### Вариант 1: Через Continue.dev (Рекомендуется)

1. **Установить Continue расширение:**
   - Открыть Extensions в VSCode (`Cmd+Shift+X`)
   - Найти "Continue"
   - Установить

2. **Настроить Continue для OpenAI:**
   
   Создать файл `~/.continue/config.json`:
   ```json
   {
     "models": [
       {
         "title": "GPT-4",
         "provider": "openai",
         "model": "gpt-4",
         "apiKey": "YOUR_OPENAI_API_KEY"
       }
     ]
   }
   ```

3. **Добавить Membria tools:**
   
   В том же файле добавьте:
   ```json
   {
     "models": [...],
     "tools": [
       {
         "name": "membria",
         "type": "mcp",
         "command": "python",
         "args": ["/Users/miguelaprossine/membria-cli/start_mcp_server.py"],
         "env": {
           "FALKORDB_HOST": "192.168.0.105"
         }
       }
     ]
   }
   ```

### Вариант 2: Через Cursor IDE

1. **Установить Cursor:** https://cursor.sh

2. **Настроить MCP:**
   
   Создать `.cursor/mcp.json` в проекте:
   ```json
   {
     "mcp_servers": {
       "membria": {
         "command": "python",
         "args": ["/Users/miguelaprossine/membria-cli/start_mcp_server.py"],
         "env": {
           "FALKORDB_HOST": "192.168.0.105"
         }
       }
     }
   }
   ```

### Вариант 3: Через Claude Code

1. **Установить Claude Code расширение**

2. **Создать `.claude/claude.json`:**
   ```json
   {
     "mcp_servers": {
       "membria": {
         "command": "python",
         "args": ["/Users/miguelaprossine/membria-cli/start_mcp_server.py"],
         "env": {
           "FALKORDB_HOST": "192.168.0.105"
         }
       }
     }
   }
   ```

---

## 📋 Полный чек-лист

### FalkorDB
- [ ] `redis-cli -h 192.168.0.105 ping` → PONG

### VSCode Extension
- [ ] Открыть `membria-cli/vscode-extension` в VSCode
- [ ] Нажать F5
- [ ] В новом окне проверить команды (Cmd+Shift+P → "Membria")

### Codex/OpenAI
- [ ] Установить Continue/Cursor/Claude Code
- [ ] Настроить MCP сервер
- [ ] Перезагрузить окно VSCode

---

## 🎯 Примеры использования

### В VSCode Extension
```
1. Cmd+Shift+M D
2. Ввести: "Use PostgreSQL for user database"
3. Ввести альтернативы: "MongoDB, MySQL"
4. Ввести уверенность: 0.85
5. ✅ Decision captured!
```

### В Codex (через Continue)
```
User: "I'm deciding between Redis and Memcached for caching.
       What has the team tried before?"

Codex: [Вызывает membria.get_decision_context]
       "Based on team history:
        - Redis: 92% success rate (15 decisions)
        - Memcached: 78% success rate (8 decisions)
        Recommendation: Redis"
```

---

## ❓ Частые проблемы

### Extension не активируется
```bash
# Пересобрать
cd membria-cli/vscode-extension
npm run compile
# Затем F5 в VSCode
```

### MCP сервер не подключается
```bash
# Проверить FalkorDB
redis-cli -h 192.168.0.105 ping

# Проверить Python
python3 --version

# Запустить сервер вручную для теста
cd membria-cli
FALKORDB_HOST=192.168.0.105 python start_mcp_server.py
```

### Codex не видит tools
- Перезагрузить окно VSCode (Cmd+Shift+P → "Reload Window")
- Проверить путь к `start_mcp_server.py`
- Проверить переменные окружения

---

## 📚 Документация

- `docs/MACOS_SETUP_GUIDE.md` - Полная установка
- `docs/CLAUDE_QUICKSTART.md` - Подключение к Claude
- `docs/OPENAI_INTEGRATION.md` - OpenAI интеграция
- `vscode-extension/README.md` - Extension документация

---

**Готово!** Membria работает в VSCode с Codex.