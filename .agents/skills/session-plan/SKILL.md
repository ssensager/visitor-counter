---
name: session-plan
description: >-
  Start-of-task planning protocol for visitor-counter team members. Use when starting
  a module task or when the user says "план" or "/plan". Verifies personal feature
  branch checkout (never main), reads PROJECT_SPEC.md, checks scope boundaries, and
  initializes reports/_wip_<role>.md.
---

# Session Plan Protocol (`план`)

Используй этот протокол в начале работы над задачей или по команде пользователя `план`.

## Шаги

1. **Изучи контекст проекта:**
   - Прочитай `PROJECT_SPEC.md`, `AGENTS.md` и `shared/contracts.py`.
2. **Проверь и переключи ветку Git (КРИТИЧНО):**
   - Выполни `git branch --show-current` и `git status`.
   - Работа **строго запрещена в ветке `main`**. Все ветки ролей заранее созданы от `main`:
     - `feature/ml-counter` (`ml/`)
     - `feature/video-processing` (`video/`)
     - `feature/backend-api` (`backend/`)
     - `feature/frontend-dashboard` (`frontend/`)
     - `feature/devops-testing` (`tests/`, скрипты, `requirements.txt`)
     - `feature/integration` (сборка лидером)
     - `feature/presentation-context`, `feature/presentation-tech`, `feature/presentation-final` (презентация)
   - Если текущая ветка `main` — сразу переключись на ветку своей роли:
     ```bash
     git fetch origin
     git checkout <твоя-ветка>
     ```
     (Если такой ветки нет ни локально, ни на `origin`, создай её от `main`: `git checkout -b <твоя-ветка> main`.)
   - Зафиксируй список директорий, которые разрешено менять в твоей роли.
3. **Создай/обнови черновик сессии `reports/_wip_<role>.md`:**
   - Определи короткое имя роли (`ml`, `video`, `backend`, `frontend`, `devops_qa`, `lead`, `pres_context`, `pres_tech`, `pres_final`).
   - Запиши в `reports/_wip_<role>.md`:
     - целевую ветку `feature/...` и зону ответственности;
     - пошаговый план из 3–7 конкретных пунктов;
     - контракты из `PROJECT_SPEC.md` / `shared/contracts.py`, на которые опирается модуль;
     - открытые вопросы или риски (если есть).
4. **Кратко покажи план пользователю** перед началом правок кода/материалов.
