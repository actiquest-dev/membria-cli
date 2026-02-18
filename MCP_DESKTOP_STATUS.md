# Membria MCP Desktop — Work Log & Current Status (2026-02-17)

## Цель
Собрать локальное десктоп‑приложение для управления MCP‑подключениями и авторизацией провайдеров (OpenAI, Claude, Kilo) без UX‑скачков в браузер, с возможностью запускать CLI‑команды и проверять статус.

## Что сделано

### 1) Десктоп‑приложение (Electron)
Создано приложение в:
- `/Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop`

Файлы:
- `main.js`: запуск Electron, создание окна, IPC, запуск PTY (node-pty)
- `renderer.js`: UI‑логика, xterm, статусы, автопроверка токенов, webview‑модал
- `index.html`: две вкладки (MCP Connect / Providers & Auth), встроенный webview, терминалы
- `package.json`: зависимости (electron, node-pty, xterm, xterm-addon-fit)

Статус UI:
- Вкладка **MCP Connect**: карточки OpenAI/Claude/Kilo, кнопка Connect, терминал xterm
- Вкладка **Providers & Auth**: встроенный webview с `http://localhost:8080/my/tokens?auth=1`
- Добавлен модал для OAuth внутри приложения (webview) — без выноса в браузер

### 2) MCP‑Front (Go) — локальный режим без IDP
Изменено:
- `third_party/mcp-front/internal/server/middleware.go`
  - добавлен `MCP_FRONT_DISABLE_IDP=1` → пропуск SSO, локальный пользователь
  - добавлен `MCP_FRONT_LOCAL_USER` (по умолчанию `local@membria`, но можно задать email)

Env:
- `/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.env`
  - `MCP_FRONT_DISABLE_IDP=1`
  - `MCP_FRONT_LOCAL_USER=membria.team@gmail.com`

Важно: после правок требуется пересборка:
```
cd /Users/miguelaprossine/membria-cli/third_party/mcp-front
go build -o /Users/miguelaprossine/membria-cli/bin/mcp-front ./cmd/mcp-front
```

### 3) Хранение токенов
- токены хранятся в `/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.tokens.json`
- зашифрованы `MCP_FRONT_ENCRYPTION_KEY`
- при смене `MCP_FRONT_LOCAL_USER` токены «пропадают» (т.к. сохранены под другим email)

### 4) Ключевые команды и CLI
- Codex: `/opt/homebrew/bin/codex`
- Claude: `/Users/miguelaprossine/.local/bin/claude`
- Kilo: `/Users/miguelaprossine/.nvm/versions/node/v22.19.0/bin/kilo`

Запуск десктоп‑приложения:
```
cd /Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop
npm install
npm start
```

Запуск mcp-front (тихо):
```
/Users/miguelaprossine/membria-cli/scripts/mcp-front.sh stop
/Users/miguelaprossine/membria-cli/scripts/mcp-front.sh start
```

Логи:
- `/tmp/mcp-front.log`

---

## Текущее состояние (важно)

### A) OAuth работает в браузере
`codex mcp login membria` **в обычном терминале** открывает:
- `http://localhost:8080/oauth/services?...`

В браузере видна страница **Optional Service Connections** с Connected для OpenAI/Claude.

### B) Внутри Electron OAuth не запускается корректно
Была попытка:
- запускать `codex mcp login membria` через node-pty
- ловить URL через `$BROWSER`
- открывать URL в webview‑модале

**Фактическое поведение:**
- Прямой запуск `codex` в PTY падает: `posix_spawnp failed`
- Пытались fallback через `/bin/zsh -il` и `/bin/zsh -lc` — команды не дают вывода
- Терминал в app показывает только строку команды и пусто дальше

### C) Встроенный webview работает
Вкладка `Providers & Auth` открывает `http://localhost:8080/my/tokens?auth=1` и показывает UI.

---

## Нерешённая проблема (главная)

**Невозможно стабильно запустить `codex mcp login membria` из Electron через node-pty.**

Симптомы:
- `posix_spawnp failed` при запуске `codex` в PTY
- даже fallback через shell не даёт ожидаемого результата
- в терминале приложения команда «зависает» без вывода
- в обычном терминале всё работает, открывается `/oauth/services` в браузере

Что нужно решить:
1) Надёжно запускать `codex mcp login` внутри Electron (PTY) **или**
2) Реализовать альтернативный поток OAuth **без `codex mcp login`**, напрямую через mcp-front (например, генерировать state + открыть `/oauth/services` из приложения)

Если решить п.2, нужно понять:
- как безопасно формировать `state` для `/oauth/services`
- как сохранять и завершать OAuth без CLI

---

## Артефакты/файлы, которые трогались

- Electron app:
  - `/Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop/main.js`
  - `/Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop/renderer.js`
  - `/Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop/index.html`
  - `/Users/miguelaprossine/membria-cli/apps/membria-mcp-desktop/package.json`

- mcp-front:
  - `/Users/miguelaprossine/membria-cli/third_party/mcp-front/internal/server/middleware.go`
  - `/Users/miguelaprossine/membria-cli/third_party/mcp-front/internal/server/templates/tokens.html` (UI tweaks и скрытие MCP Connect по `?auth=1`)

- env/config:
  - `/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.env`
  - `/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.json`
  - `/Users/miguelaprossine/membria-cli/.config/membria-mcp/mcp-front.tokens.json`

---

## Что можно передать следующему ИИ

1) Текущая схема работает в браузере и в обычном терминале, но **не в Electron + PTY**
2) `codex mcp login` в PTY даёт `posix_spawnp failed`
3) Нужен либо:
   - корректный способ запустить `codex` из Electron PTY
   - или новый OAuth‑flow **без codex CLI**, напрямую из mcp-front

