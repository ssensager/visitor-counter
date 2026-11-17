---
name: finalize-report
description: >-
  End-of-task verification and final report generation for visitor-counter. Use when
  finishing a module/role or when the user says "финал" or "/finalize". Verifies scope
  and tests, generates reports/<nn>_<role>.md from reports/TEMPLATE_REPORT.md, and
  prepares branch for Pull Request.
---

# Finalize & Report Protocol (`финал`)

Используй этот протокол перед завершением задачи и отправкой ветки на Pull Request, или по команде пользователя `финал`.

## Шаги

1. **Проверь границы изменений:**
   - Выполни `git status` и `git diff --name-only main` (если ветка отведена от `main`).
   - Убедись, что изменены **только** файлы твоей зоны ответственности и отчёт в `reports/`, и не попали тяжёлые медиафайлы/веса (`.mp4`, `.avi`, `.pt`, `venv/`).
2. **Выполни финальную проверку модуля:**
   - Запусти реальные тесты или smoke-проверку модуля после финальных правок.
   - Если это программный модуль (`ml`, `video`, `backend`, `frontend`), убедись, что контракты из `shared/contracts.py` и `PROJECT_SPEC.md` соблюдены.
3. **Сформируй чистовой итоговый отчёт:**
   - Возьми структуру из [`reports/TEMPLATE_REPORT.md`](../../../reports/TEMPLATE_REPORT.md).
   - Создай итоговый файл в согласованном пути:
     - `reports/01_ml.md`, `reports/02_video.md`, `reports/03_backend.md`, `reports/04_frontend.md`, `reports/05_devops_qa.md`, или
     - `reports/00_FINAL_SUMMARY.md` (для лидерской сборки), или
     - `reports/pres_part1_context.md` / `reports/pres_part2_tech.md` (для материалов презентации).
   - Перенеси в отчёт всё важное из `reports/_wip_<role>.md`: что сделано, файлы, команды запуска, реальные результаты тестов, известные проблемы/ограничения и заметки для интеграции и презентации.
   - Удали временный файл `reports/_wip_<role>.md` (если он больше не нужен).
4. **Подготовь ветку к сдаче:**
   - Выведи пользователю понятную сводку и готовые команды `git add`, `git commit`, `git push -u origin <ветка>` (или выполни commit/push, только если пользователь прямо попросил).
   - Напомни: не сливать напрямую в `main` — открыть Pull Request для проверки руководителем.
