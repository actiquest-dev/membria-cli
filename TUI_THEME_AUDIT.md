# TUI Theme Audit — Nord/Arctic цветовая тема

**Статус:** 🔴 Проблема не решена — фон остаётся зелёным (textual-dark teal)
**Дата:** 2026-02-16

---

## Цель

### Как должно выглядеть (Nord тема)

```
╔═══════════════════════════════════════════════════════════════════════╗
║ Membria CLI                              12:34:56                     ║
╠════════════════════════════════════════════════════╦══════════════════╣
║                                                    ║ 🤖 AGENTS        ║
║  Membria CLI  backend · Architect, Senior Dev      ║ ✅ Architect     ║
║                                                    ║ ✅ Senior Dev    ║
║  ▸ plan db schema                                  ║ ✅ Junior Dev    ║
║    → Architect: Use CQRS with event sourcing...    ║                  ║
║                                                    ║ 📊 CALIBRATION   ║
║                                                    ║ Architect  89%   ║
║                                                    ║ Security   93%   ║
║                                                    ║                  ║
║                                                    ║ 💬 SESSION       ║
║                                                    ║ Decisions: 3     ║
║                                                    ║ Mode: pipeline   ║
║                                                    ║                  ║
║                                                    ║ 🔍 LAST DECISIONS║
║                                                    ║ 1. Plan DB (100%)║
╠════════════════════════════════════════════════════╩══════════════════╣
║ membria ▸ [████████████████████████████████████████████████]         ║
╠═══════════════════════════════════════════════════════════════════════╣
║  pipeline  │  ✓3 ⊙0  │  1,234 tok  │  ✓ graph                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Цветовая палитра Nord:**
- Фон: `#2E3440` (тёмно-серый, как ночное небо)
- Поверхность: `#3B4252` (чуть светлее фона)
- Панель: `#434C5E` (sidebar, input container)
- Primary: `#88C0D0` (голубой — заголовки, borders)
- Secondary: `#81A1C1` (синий)
- Accent: `#5E81AC` (тёмно-синий)
- Успех: `#A3BE8C` (зелёный)
- Предупреждение: `#EBCB8B` (жёлтый)
- Ошибка: `#BF616A` (красный)

**Ключевой контраст:** фон `#2E3440` (тёмно-серый) vs textual-dark фон `#1e2a2a` (тёмно-зелёный). Зелёный оттенок — главная проблема.

---

## Хронология изменений

### Изменённые файлы

| Файл | Что изменено |
|------|-------------|
| `src/membria/interactive/textual_shell.py` | Полный рефактор TUI: Nord тема, StatusBar, SidePanel, InputContainer, CSS |
| `src/membria/interactive/commands.py` | Добавлены `/tok`, `/tokens`, `/init`, `/start` команды |
| `pyproject.toml` | `textual>=0.50.0` → `textual>=0.80.0` |
| `TUI_THEME_AUDIT.md` | Этот файл — документация проблемы |

### Детальная хронология

1. **Изучение Textual docs** — прочитаны официальные доки по темам, Input, CSS переменным
2. **Обновление Textual** — `0.50.0` → `7.5.0` (установлен), `pyproject.toml` требует `>=0.80.0`
3. **Рефактор ColorSystem → Theme** — убрана устаревшая `ColorSystem`, переход на `register_theme`
4. **Исправление InputContainer** — `Static` → `Vertical` для работы key events (↑↓ история)
5. **Исправление Input border** — `border: tall` → `border: none` + `height: 1`
6. **Исправление command bar** — `#input-container height: 3` с `border-top + border-bottom`
7. **Исправление status bar** — убран `Footer` (перекрывал), статус бар получил `border-top`
8. **Убрана стоимость в $** — из SidePanel убраны доллары, токены только в status bar
9. **Добавлена `/tok` команда** — в `commands.py` общий счётчик токенов
10. **Добавлены `/init`, `/start`** — ручной запуск онбординга
11. **Исправлен AgentExecutor** — убран несуществующий `TaskRouter.route()` → `executor.run_orchestration()`
12. **`object.__setattr__` hack** — попытка установить Nord до `super().__init__()`
13. **Написан TUI_THEME_AUDIT.md** — документация всех попыток

### Ссылки на ключевые места кода

```
textual_shell.py:348-351  — __init__ с _reactive_theme hack
textual_shell.py:224-346  — CSS с Nord $variables
textual_shell.py:162-208  — InputContainer (Vertical)
textual_shell.py:22-62    — StatusBar.render()
textual_shell.py:67-157   — SidePanel
commands.py               — /tok, /init, /start команды
```

---

## Что было сделано

### 1. Обновление Textual
- `textual 0.50.0` → `textual 7.5.0`
- `pyproject.toml`: `textual>=0.80.0`

### 2. Переход с ColorSystem на Theme API
Было:
```python
from textual.design import ColorSystem
ARCTIC_DARK = ColorSystem(primary="#88C0D0", background="#2E3440", ...)
self.design = {"dark": ARCTIC_DARK, "light": ARCTIC_LIGHT}
```
Стало:
```python
from textual.theme import Theme
# Используем встроенную Nord тему (BUILTIN_THEMES)
# Nord: background=#2E3440, surface=#3B4252, primary=#88C0D0
```

### 3. Исправления command bar и status bar
- `InputContainer` базовый класс: `Static` → `Vertical` (фикс фокуса и key events)
- `Input border: none` + `height: 1` (по документации: border съедает строки)
- `#input-container height: 3` с `border-top + border-bottom`
- `#status-bar height: 3` с `border-top + border-bottom`

### 4. Исправление TaskRouter
- Убран несуществующий `router.route()` → `executor.run_orchestration()`
- Убран неиспользуемый `import TaskRouter`

### 5. Добавлены команды `/start` и `/init`
- Запускают `OnboardingFlow` вручную в любой момент
- Добавлены в `/help`

---

## Проблема: зелёный фон (нерешена)

### Корневая причина

Textual 7.x инициализирует `Stylesheet` в `App.__init__` на строке 153:
```python
# textual/app.py line 151-153
# Note that the theme must be set *before* self.get_css_variables() is called
# to ensure that the variables are retrieved from the currently active theme.
self.stylesheet = Stylesheet(variables=self.get_css_variables())
```

`get_css_variables()` читает `self.current_theme` → `self.theme` (Reactive).
По умолчанию `theme = Reactive("textual-dark")` → `$background` = тёмно-зелёный.

### Что пробовали и почему не работало

| Подход | Результат | Причина |
|--------|-----------|---------|
| `self.design = {"dark": ColorSystem(...)}` в `__init__` | ❌ | `Stylesheet` создаётся раньше |
| `self.theme = "nord"` в `on_mount` | ❌ | `Stylesheet` уже создан с textual-dark |
| `os.environ["TEXTUAL_THEME"] = "nord"` в `run_textual_shell` | ❌ | `textual.constants` уже импортирован |
| `os.environ` в начале модуля | ❌ | Другие модули импортируют textual раньше |
| `theme = "nord"` как class variable | ❌ | Reactive дескриптор заменяется строкой — ломает reactive механизм |
| `get_css_variables()` override | ❌ | Можно, но пользователь попросил не хардкодить |
| `register_theme` + `self.theme = "arctic"` в `__init__` | ❌ | После `super().__init__()` — слишком поздно |

### Текущее решение (частично работает)
```python
def __init__(self, config_manager):
    # Устанавливаем _reactive_theme до super().__init__()
    # чтобы Stylesheet создался с Nord переменными
    object.__setattr__(self, "_reactive_theme", "nord")
    super().__init__()
```

Это устанавливает значение reactive ДО создания `Stylesheet` — верифицировано в тестах:
```
stylesheet bg: #2E3440  ← Nord цвет
```

**Но**: фон всё равно зелёный в рантайме. Возможно, `App.DEFAULT_CSS` или CSS виджетов перезаписывают `$background` после, или `_watch_theme` не срабатывает при изначальном значении.

---

## Что нужно исследовать дальше

### Вариант A: App.DEFAULT_CSS

Textual `App` имеет свой `DEFAULT_CSS`:
```python
# textual/app.py lines 304-359
DEFAULT_CSS = """
App {
    background: $background;
    color: $foreground;
    ...
}
"""
```
Возможно, `App.DEFAULT_CSS` применяется отдельно от нашего `CSS` и берёт старые переменные.

**Проверить:** Добавить в `MembriaApp.CSS`:
```css
App {
    background: $background;
}
```

### Вариант B: _watch_theme не вызывается

`_watch_theme` вызывается когда reactive **меняется**. Если мы устанавливаем значение через `object.__setattr__` до `super().__init__()`, reactive механизм не знает о изменении и `_watch_theme` не вызывается при монтировании.

**Проверить:** Вызвать `self._watch_theme("nord")` явно в `on_mount`.

### Вариант C: SplashScreen перезаписывает

`SplashScreen.DEFAULT_CSS` содержит:
```css
Screen {
    background: $panel;
    ...
}
```
После закрытия splash, этот CSS может оставлять следы.

### Вариант D: textual-dev инструмент

Использовать `textual run --dev membria/interactive/textual_shell.py` с devtools для инспекции CSS дерева и проверки какой именно CSS правило задаёт зелёный фон.

---

## Документация для изучения

### Textual официальная
- **Themes / Design system:** https://textual.textualize.io/guide/design/
- **Input widget:** https://textual.textualize.io/widgets/input/
- **CSS Variables:** https://textual.textualize.io/guide/CSS/#css-variables
- **App lifecycle:** https://textual.textualize.io/guide/app_lifecycle/
- **DEFAULT_CSS:** https://textual.textualize.io/guide/default_css/
- **Reactives:** https://textual.textualize.io/guide/reactivity/

### Textual исходники (установлены)
- `/Users/miguelaprossine/miniconda3/lib/python3.12/site-packages/textual/app.py`
  - Строка 535: `theme: Reactive[str] = Reactive(constants.DEFAULT_THEME)`
  - Строка 153: `self.stylesheet = Stylesheet(variables=self.get_css_variables())`
  - Строка 1338: `get_css_variables()` — читает `current_theme`
  - Строка 1422: `_watch_theme()` — вызывает `_invalidate_css()` + `refresh_css`
- `/Users/miguelaprossine/miniconda3/lib/python3.12/site-packages/textual/theme.py`
  - Nord встроенная тема: `background="#2E3440"`, `surface="#3B4252"`, `primary="#88C0D0"`
- `/Users/miguelaprossine/miniconda3/lib/python3.12/site-packages/textual/constants.py`
  - `DEFAULT_THEME: Final[str] = get_environ("TEXTUAL_THEME", "textual-dark")`

### textual-dev
- https://github.com/Textualize/textual-dev/tree/main/src/textual_dev

### Локальные проектные доки
- `/Users/miguelaprossine/membria-cli/docs/INTERACTIVE_CLI_SPEC.md` — UI/UX спецификация, примеры промптов
- `/Users/miguelaprossine/membria-cli/docs/PHASE1_SHELL_REQUIREMENTS.md` — требования Phase 1
- `/Users/miguelaprossine/membria-cli/DESIGN_IMPROVEMENTS.md` — дизайн улучшения
- `/Users/miguelaprossine/membria-cli/ONBOARDING_VISUAL_GUIDE.md` — визуальные примеры onboarding
- `/Users/miguelaprossine/membria-cli/PHASE1_UI_COMPLETE.md` — статус UI Phase 1

---

## Текущее состояние файла

**`src/membria/interactive/textual_shell.py`**

```
MembriaApp
├── theme = Nord (через _reactive_theme hack)  ← НЕ работает визуально
├── CSS = Nord $variables                       ← корректно
├── StatusBar — работает (pipeline | ✓0 ⊙0 | 0 tok | ✓ graph)
├── SidePanel — работает (AGENTS, CALIBRATION, SESSION, LAST DECISIONS)
├── InputContainer — работает (membria ▸ [input])
└── on_mount → executor.run_orchestration()    ← исправлено
```

---

## Следующий шаг для разработчика

```bash
# 1. Запустить с textual devtools
pip install textual-dev
textual run --dev -c "membria shell"

# 2. В devtools (Ctrl+\) проверить:
#    - Какое CSS правило задаёт background на Screen/App
#    - Какое значение у $background переменной

# 3. Проверить _watch_theme:
# В on_mount добавить:
async def on_mount(self):
    self._watch_theme("nord")  # Принудительно применить Nord
    ...
```
