---
name: finalize-report
description: >-
  End-of-task verification and final report generation for visitor-counter. Use when
  finishing a module/role or when the user says "финал" or "/finalize". Verifies feature
  branch (never main), scope, and tests, generates reports/<nn>_<role>.md from
  reports/TEMPLATE_REPORT.md, and prepares git push + Pull Request to main.
---

# Finalize & Report Protocol (`финал`)

Используй этот протокол перед завершением задачи и отправкой ветки на Pull Request, или по команде пользователя `финал`.

## Шаги

1. **Проверь ветку и границы изменений:**
   - Выполни `git branch --show-current`. Убедись, что ты находишься в своей ветке `feature/...`, **а НЕ в `main`**.
   - Выполни `git status` и `git diff --name-only origin/main` (или `main`).
   - Убедись, что изменены **только** файлы твоей зоны ответственности и отчёт в `reports/`, и не попали тяжёлые медиафайлы/веса (`.mp4`, `.avi`, `.pt`, `venv/`, `.env`).
2. **Выполни финальную проверку модуля:**
   - Запусти реальные тесты или smoke-проверку модуля после финальных правок.
   - Если это программный модуль (`ml`, `video`, `backend`, `frontend`), убедись, что контракты из `shared/contracts.py` и `PROJECT_SPEC.md` соблюдены.
3. **Сформируй чистовой итоговый отчёт:**
   - Возьми структуру из [`reports/TEMPLATE_REPORT.md`](../../../reports/TEMPLATE_REPORT.md).
   - Создай итоговый файл в согласованном пути:
     - `reports/01_ml.md`, `reports/02_video.md`, `reports/03_backend.md`, `reports/04_frontend.md`, `reports/05_devops_qa.md`, или
     - `reports/00_FINAL_SUMMARY.md` (для ветки `feature/integration`), или
     - `reports/pres_part1_context.md` / `reports/pres_part2_tech.md` (для материалов презентации).
   - Перенеси в отчёт всё важное из `reports/_wip_<role>.md`: что сделано, файлы, команды запуска, реальные результаты тестов, известные проблемы/ограничения и заметки для интеграции и презентации.
   - Удали временный файл `reports/_wip_<role>.md`, если он больше не нужен.
4. **Подготовь ветку к сдаче через Pull Request (НЕ в `main` напрямую!):**
   - Выведи пользователю понятную сводку и готовые команды:
     ```bash
     git add .
     git commit -m "feat(<role>): <краткое описание>"
     git push -u origin <твоя-ветка>
     ```
     (Выполняй `git commit` / `git push` сам только если пользователь прямо об этом попросил.)
   - Явно напомни: **НЕ делать `git checkout main && git merge ...` и НЕ пушить в `main`**. После пуша нужно открыть на GitHub **Pull Request** из `feature/<твоя-ветка>` в `main` для проверки руководителем проекта.
