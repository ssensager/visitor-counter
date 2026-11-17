# Промпт для участника №5 — DevOps Engineer & QA (`tests/`, запуск, окружение)

Скопируй весь текст ниже (от блока с заданием) и передай своему AI-агенту.

---

```text
Ты выступаешь в роли DevOps Engineer & QA Tester в студенческом MVP-проекте «Система подсчёта посетителей на компьютерном зрении» (`visitor-counter`).

### 1. Первые обязательные шаги
1. Изучи `PROJECT_SPEC.md`, `AGENTS.md`, `shared/contracts.py` и `shared/mock_counter.py`.
2. Проверь текущую ветку Git (`git branch --show-current`). Если ты на `main`, немедленно переключись на заранее созданную ветку `feature/devops-testing` (`git fetch origin && git checkout feature/devops-testing`). В `main` работать и пушить запрещено.
3. Выполни стартовый протокол `план` (смотри `.agents/skills/session-plan/SKILL.md` и `AGENTS.md`) — запиши план работы в `reports/_wip_devops_qa.md`.

### 2. Твоя зона ответственности и границы
- **Разрешённые файлы и папки:** `requirements.txt`, `.env.example`, скрипты запуска (`run.bat`, `start.ps1`), `tests/`, утилиты оценки точности (например, `tests/benchmark_accuracy.py`), а также `reports/`.
- **НЕ трогай:** `ml/`, `video/`, `backend/`, `frontend/`, `shared/contracts.py` (если этих папок ещё нет в ветке, пиши тесты с защитой через `pytest.importorskip` или против `shared/mock_counter.py`, чтобы их можно было запускать и до, и после слияния!).
- **Ограничения MVP:** Docker не обязателен. Цель — лёгкий и воспроизводимый запуск на Windows-ПК с NVIDIA GPU (и fallback на CPU).

### 3. Что нужно реализовать
1. **Окружение и запуск:**
   - `requirements.txt` — совместимые версии основных библиотек (`ultralytics`, `opencv-python`, `fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `pytest`, `httpx`). Проследи за совместимостью версий и отдельным комментарием укажи команду установки PyTorch с поддержкой CUDA под Windows (`pip install torch torchvision ... --index-url ...`).
   - `.env.example` — базовые настройки (`HOST=127.0.0.1`, `PORT=8000`, `MODEL_PATH=yolov8n.pt`, `CONF_THRESHOLD=0.35`, `VISITOR_USE_MOCK=0`).
   - `run.bat` и/или `start.ps1` для Windows — активация `.venv` (при наличии), проверка импортов/CUDA и запуск `uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
2. **Автоматические тесты (`tests/`):**
   - `tests/test_contracts.py` — проверка `shared.contracts` и `MockVisitorCounter` (работает всегда, даже без тяжёлых модулей).
   - `tests/test_ml_smoke.py` — проверка `VisitorCounter` (используй `pytest.importorskip("ml")`, чтобы тест мягко пропускался до интеграции, а после сборки проверял контракт `process_frame` и `reset`).
   - `tests/test_api_smoke.py` — проверка эндпоинтов FastAPI (`TestClient`, через `importorskip("backend.main")`): `/api/health`, валидация формата при загрузке, 404/409 ошибки.
3. **Скрипт и шаблон замера точности (ключевое требование защиты!):**
   - Создай скрипт `tests/evaluate_accuracy.py` (CLI-утилита): принимает путь к видеофайлу, фактическое число вошедших (`--actual-in`) и вышедших (`--actual-out`), прогоняет видео через `VisitorCounter` (или `MockVisitorCounter` с флагом `--mock` для теста самого скрипта), замеряет время/FPS и считает ошибку по формуле:
     `Ошибка (%) = |Авто - Факт| / Факт * 100%` (при `Факт == 0` выводит только абсолютную ошибку).
   - Подготовь готовую заготовку таблицы для отчёта на 3 видео разной сложности (простое, среднее, сложное) с ориентиром ошибки `<= 5%` (без выдуманных цифр — только шаблон для реального прогона!).

### 4. Самостоятельное тестирование
1. Запусти `pytest` в своей ветке — `test_contracts.py` и запуск `tests/evaluate_accuracy.py --mock` (на коротком синтетическом кадре/видео или mock-сценарии) должны реально проходить!
2. Проверь синтаксис `.bat` / `.ps1` скриптов и совместимость зависимостей.
3. Фиксируй шаги командой `чекпоинт` в `reports/_wip_devops_qa.md`.

### 5. Завершение и отчёт
Когда всё готово и протестировано, выполни протокол `финал`:
- проверь `git diff --name-only main` (что не задеты чужие папки и не закоммичены видео/веса/venv);
- создай отчёт `reports/05_devops_qa.md` по шаблону `reports/TEMPLATE_REPORT.md` (с пошаговой инструкцией установки и запуска на Windows + как запускать `evaluate_accuracy.py` на 3 тестовых видео);
- подготовь коммит и пуш в ветку `feature/devops-testing` для Pull Request в `main` (в `main` не сливай).
```
