# Промпт для участника №3 — Backend Developer (`backend/`)

Скопируй весь текст ниже (от блока с заданием) и передай своему AI-агенту.

---

```text
Ты выступаешь в роли Senior Python Backend Developer в студенческом MVP-проекте «Система подсчёта посетителей на компьютерном зрении» (`visitor-counter`).

### 1. Первые обязательные шаги
1. Изучи `PROJECT_SPEC.md`, `AGENTS.md`, `shared/contracts.py` и `shared/mock_counter.py`.
2. Проверь текущую ветку Git (`git branch --show-current`). Если ты на `main`, немедленно переключись на заранее созданную ветку `feature/backend-api` (`git fetch origin && git checkout feature/backend-api`). В `main` работать и пушить запрещено.
3. Выполни стартовый протокол `план` (смотри `.agents/skills/session-plan/SKILL.md` и `AGENTS.md`) — запиши план работы в `reports/_wip_backend.md`.

### 2. Твоя зона ответственности и границы
- **Разрешённая папка:** `backend/` (а также временный/итоговый отчёт в `reports/`).
- **НЕ трогай:** `ml/`, `video/`, `frontend/`, `tests/`, `shared/contracts.py`.
- **Ограничения MVP:** НЕ пиши свой код YOLO, ByteTrack или подсчёта. НЕ добавляй базу данных и авторизацию. Храни состояние задач в памяти приложения (в MVP разрешена **только одна** активная задача обработки за раз).

### 3. Что нужно реализовать в `backend/`
Рекомендуемая структура:
- `backend/main.py` — точка входа FastAPI (`app = FastAPI(...)`), подключение роутов, статики из `frontend/` (чтобы `GET /` отдавал `frontend/index.html`, если файл существует — и работал без падения, если `frontend/` пока пустой).
- `backend/schemas/responses.py` — Pydantic-модели под контракты из `PROJECT_SPEC.md` (`HealthResponse`, `UploadResponse`, `StartRequest`, `JobActionResponse`, `StatsResponse`).
- `backend/services/job_manager.py` — потокобезопасное управление задачами в памяти:
  - генерация `job_id`, сохранение загруженных файлов в `storage/uploads/`;
  - проверка расширений (`.mp4`, `.avi` из `shared.contracts.ALLOWED_VIDEO_EXTENSIONS`);
  - контроль единственной активной задачи (попытка запустить вторую при активной -> ошибка `409 Conflict`);
  - хранение последнего обработанного JPEG-кадра и актуальной статистики `StatsResponse` для каждой задачи.
- `backend/services/video_service.py` — фоновый запуск обработки видео в отдельном потоке (чтобы не блокировать event loop FastAPI):
  - **Важно для независимой работы:** если `ml` или `video` ещё не влиты в твою ветку, сделай аккуратную фабрику/переключатель (например, через переменную окружения `VISITOR_USE_MOCK=1` или безопасный fallback на `shared.mock_counter.MockVisitorCounter` и простое чтение через `cv2.VideoCapture` в mock-режиме), а при наличии `ml.VisitorCounter` и `video.VideoProcessor` используй их! Опиши эту точку стыковки в отчёте.
- `backend/api/routes.py`, `backend/api/video.py`, `backend/api/stats.py` — эндпоинты строго по `PROJECT_SPEC.md`:
  - `GET /api/health`
  - `POST /api/video/upload`
  - `POST /api/video/start/{job_id}` (принимает опциональное тело `{"line": [[x1, y1], [x2, y2]]}`)
  - `POST /api/video/stop/{job_id}`
  - `GET /api/video/stream/{job_id}` (`multipart/x-mixed-replace; boundary=frame`)
  - `GET /api/stats/{job_id}`
  - `WS /ws/stats/{job_id}` (отправляет `StatsResponse` JSON в реальном времени и закрывается/сообщает статус при завершении).

### 4. Обработка ошибок
Предусмотри понятные HTTP-коды и `{"detail": "..."}`:
- неподдерживаемый формат файла (`415` или `400`);
- несуществующий `job_id` (`404`);
- попытка запуска второй активной задачи (`409`);
- остановка незапущенной/несуществующей задачи;
- корректный разрыв WebSocket/MJPEG при закрытии вкладки браузера.

### 5. Самостоятельное тестирование
До завершения работы проверь (через `FastAPI TestClient` / локальный тест или запуск `uvicorn`):
1. `GET /api/health` -> `200`.
2. Загрузку невалидного файла (`.txt`) -> ошибка; валидного (`.mp4`) -> `job_id` и сохранение в `storage/uploads/`.
3. Запуск в mock-режиме, получение `/api/stats/{job_id}`, `/ws/stats/{job_id}`, остановку и повторный старт.
4. Фиксируй промежуточный прогресс командой `чекпоинт` в `reports/_wip_backend.md`.

### 6. Завершение и отчёт
Когда всё готово и проверено, выполни протокол `финал`:
- проверь `git diff --name-only main` (что не задеты чужие папки и не закоммичены видео из `storage/uploads/`);
- создай отчёт `reports/03_backend.md` по шаблону `reports/TEMPLATE_REPORT.md` (с перечнем эндпоинтов, примерами запросов и точкой интеграции с `ml` и `video`);
- подготовь коммит и пуш в ветку `feature/backend-api` для Pull Request в `main` (в `main` не сливай).
```
