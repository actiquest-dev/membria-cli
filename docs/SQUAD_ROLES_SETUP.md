# Squad Roles Setup Guide

## Architecture: ExpertRegistry + Graph Fallback

**ExpertRegistry** содержит 9 default ролей (architect, implementer, reviewer, security_auditor, sre, ux_designer, database_pro, analyst, copywriter).

Когда squad вызывает роль, которой нет в коде (например, `investigator`, `arbiter`), **ExpertRegistry теперь автоматически проверяет FalkorDB**:

```
ExpertRegistry.get_expert("investigator")
  1. Есть в коде? → использовать default prompt
  2. Нет в коде? → проверить graph.get_role("investigator")
  3. Найдена в графе? → использовать name + prompt_path из графа
  4. Не найдена нигде? → fallback на implementer
```

## Как создать кастомную роль для Squad

### Вариант 1: Через CLI (без кода)

```bash
# 1. Создать файл с system prompt
mkdir -p ~/.membria/prompts
cat > ~/.membria/prompts/investigator.md << 'EOF'
You are an Incident Investigator. Methodically trace root causes using logs, metrics,
and timeline reconstruction. Avoid guessing; follow the evidence.
EOF

# 2. Зарегистрировать роль в графе
membria squad role-set investigator \
  --description "Incident Investigator" \
  --prompt-path ~/.membria/prompts/investigator.md

# 3. Использовать в пресете
membria squad create-from-preset incident-rca --project-id proj_123
```

### Вариант 2: Через Python (для advanced)

```python
from membria.graph import GraphClient

graph = GraphClient()
graph.connect()

# Создать роль с prompt_path
graph.upsert_role(
    role_id="role_investigator",
    name="Incident Investigator",
    description="Traces root causes methodically",
    prompt_path="/path/to/investigator.md"
)

# Связать с DocShots/Skills/NK для контекста
graph.link_role_docshot("investigator", "docshot_xxx")
graph.link_role_skill("investigator", "skill_yyy")
```

## Встроенные Squad-роли (пресеты)

Squad пресеты используют следующие роли. Если их нет в графе, ExpertRegistry создаёт минимальный prompt от имени role name.

### incident-rca (Parallel Arbiter)
- **investigator** — методично ищет root cause
- **skeptic** — challenges assumptions
- **arbiter** — выбирает лучшее объяснение

### security-fix (Red Team)
- **fixer** — предлагает минимальную правку
- **red_team** — атакует и находит дыры

### migration-plan (Parallel Arbiter)
- **migrator** — дизайнит миграцию
- **ops** — проверяет с точки зрения операций
- **arbiter** — финальное решение

### api-contract (Lead Review)
- **backend** — определяет API контракт
- **frontend** — проверяет юзабельность

### perf-regression (Lead Review)
- **perf** — диагностирует регрессию
- **reviewer** — проверяет

### release-gate (Lead Review)
- **release_manager** — гейт на релиз
- **qa** — финальная проверка

## Flow: От пресета к ExpertRegistry к LLM

```
membria squad run sqd_xxx --task "diagnose prod outage"
  ↓
squad.py: strategy="parallel_arbiter", roles=["investigator", "skeptic", "arbiter"]
  ↓
executor.run_task(task, role="investigator")
  ↓
ExpertRegistry.get_expert("investigator")
  → NOT in EXPERTS dict
  → GraphClient.get_role("investigator")
  → if graph has role: use prompt_path, name, description
  → else: minimal fallback
  ↓
AgentExecutor: Load system prompt + graph context + LLM call
  → _get_context(prompt, role="investigator")
  → Fetch DocShots/Skills/NK linked to investigator
  ↓
LLM Response → stored as Decision in FalkorDB (via _record_decision)
```

## Best Practices

1. **Prompt файлы**: Хранить в `~/.membria/prompts/` или в проекте
2. **DocShots**: Линкить к ролям для контекста (incident logs, metrics...)
3. **Skills**: Линкить специфичные знания (incident response procedure...)
4. **Profiling**: После первого запуска `squad run --record-decisions` — смотреть результаты в FalkorDB

## Пример: Custom Squad с новыми ролями

```bash
# 1. Создать prompts
cat > ./prompts/data_engineer.md << 'EOF'
You are a Data Engineer. Design ETL pipelines with focus on:
- Data quality checks
- Schema evolution
- Performance optimization
EOF

cat > ./prompts/data_analyst.md << 'EOF'
You are a Data Analyst. Review data models and pipelines from analytical perspective:
- Can we query this efficiently?
- Are metrics correct?
- Are there hidden assumptions?
EOF

# 2. Зарегистрировать роли
membria squad role-set data_engineer --prompt-path ./prompts/data_engineer.md
membria squad role-set data_analyst --prompt-path ./prompts/data_analyst.md

# 3. Создать squad с этими ролями
membria squad create \
  --name "Data Pipeline Review" \
  --project-id proj_123 \
  --strategy parallel_arbiter \
  --role data_engineer \
  --role data_analyst \
  --role arbiter \
  --profile default \
  --profile default \
  --profile default

# 4. Запустить
membria squad run sqd_xxx --task "Review new fact table schema" --record-decisions
```

## Troubleshooting

### Role не находит свой prompt
```
membria squad role-show investigator
```
Проверить:
- `prompt_path` существует и доступен?
- Файл читаемый?
- Содержимое валидно (не пусто)?

### Role всегда fallback-ает на implementer
- Проверить что роль создана в графе: `membria squad role-show <role_name>`
- Если нет — создать: `membria squad role-set <role_name> --description "..." --prompt-path ...`

### Context из графа не инжектируется
Убедиться что роль lined с DocShots/Skills/NK:
```
membria squad role-link investigator \
  --docshot docshot_incident_logs \
  --skill skill_rca_procedure
```

## Миграция от hardcoded ролей

Если у вас есть свои пресеты с нестандартными ролями — просто создайте их через `role-set`:

```bash
for role in custom_role1 custom_role2; do
  membria squad role-set $role --prompt-path ./prompts/$role.md
done
```

ExpertRegistry автоматически будет их использовать.
