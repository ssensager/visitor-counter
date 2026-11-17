---
name: session-plan
description: >-
  Start-of-task planning protocol for visitor-counter team members. Use when starting
  a module task or when the user says "план" or "/plan". Reads PROJECT_SPEC.md, checks
  git branch and scope boundaries, and initializes reports/_wip_<role>.md.
---

# Session Plan Protocol (`план`)

Используй этот протокол в начале работы над задачей или по команде пользователя `план`.

## Шаги

1. **Изучи контекст проекта:**
   - Прочитай `PROJECT_SPEC.md`, `AGENTS.md` и `shared/contracts.py`.
2. **Проверь Git и границы:**
   - Выполни `git branch --show-current` и `git status`.
   - Убедись, что работа идёт НЕ в `main` (кроме лидерской финальной сборки) и соответствует целевой ветке `feature/<роль>`. Если ветка ещё не создана — создай её от актуальной `main`.
   - Зафиксируй список директорий, которые разрешено менять в твоей роли.
3. **Создай/обнови черновик сессии `reports/_wip_<role>.md`:**
   - Определи короткое имя роли (например: `ml`, `video`, `backend`, `frontend`, `devops_qa`, `lead`, `pres_context`, `pres_tech`, `pres_final`).
   - Запиши в `reports/_wip_<role>.md`:
     - цель и ветку;
     - пошаговый план из 3–7 конкретных пунктов;
     - контракты из `PROJECT_SPEC.md` / `shared/contracts.py`, на которые опирается модуль;
     - открытые вопросы или риски (если есть).
4. **Кратко покажи план пользователю** перед началом правок кода/материалов.
