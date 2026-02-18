# Руководство по настройке и подключению Membria

В этом руководстве описано, как подключить LLM-провайдеров к CLI и интегрировать Membria с вашим рабочим пространством в VSCode или Claude Desktop.

---

## 1. Подключение провайдеров (CLI)

Membria использует провайдеров для работы агентов. Вы можете настроить их двумя способами:

### Способ А: Интерактивный (Рекомендуется)

Запустите мастер настройки:

```bash
membria onboarding
```

Мастер проведет вас через 3 шага:

1.  **Выбор провайдеров**: Anthropic, OpenAI, Ollama и др.
2.  **Настройка ключей**: Вы можете ввести ключи или оставить их в переменных окружения.
3.  **Сборка команды**: Выберите пресет (например, "Full Power" для Claude 3.5 + GPT-4o).

### Способ Б: Переменные окружения

Если вы не хотите хранить ключи в конфиге, просто добавьте их в свой `.zshrc` или `.bashrc`:

```bash
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

---

## 2. Интеграция с VSCode / Cursor

Интеграция происходит через **MCP Server** (Model Context Protocol), который Membria запускает внутри.

### Установка расширения

1. Перейдите в папку расширения: `cd ~/membria-cli/vscode-extension`
2. Соберите пакет: `npm run vsce-package`
3. Установите полученный `.vsix` файл в VSCode:
   `code --install-extension membria-1.0.0.vsix`

### Настройка в VSCode

После установки расширение автоматически попытается запустить MCP сервер.

- Проверьте настройки в VSCode (`Cmd+,`): найдите **Membria**.
- Убедитесь, что `membria.enabled` включен.

### Горячие клавиши

- **`Cmd + Shift + M, D`**: Записать решение (Capture Decision).
- **`Cmd + Shift + M, V`**: Проверить план (Validate Plan).
- **`Cmd + Shift + M, P`**: Открыть панель Membria в боковой колонке.

---

## 3. Подключение к Claude Desktop

Если вы используете Claude Desktop, вы можете подключить Membria как MCP-инструмент.

Отредактируйте конфиг Claude (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "membria": {
      "command": "python3",
      "args": ["/absolute/path/to/membria-cli/src/membria/mcp_server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "..."
      }
    }
  }
}
```

---

## 4. Проверка статуса

Чтобы убедиться, что всё подключено правильно, используйте команду:

```bash
membria doctor
```

Она проверит доступность графа FalkorDB, наличие ключей и статус демона.

---

## 5. Визуализация (Dashboard)

Чтобы увидеть ваш граф решений в браузере:

```bash
membria dashboard
```

Это откроет страницу `http://localhost:8000` с интерактивной картой вашей "памяти решений".
