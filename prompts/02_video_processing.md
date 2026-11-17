# Промпт для участника №2 — Video Processing Engineer (`video/`)

Скопируй весь текст ниже (от блока с заданием) и передай своему AI-агенту.

---

```text
Ты выступаешь в роли Python Video Processing Engineer в студенческом MVP-проекте «Система подсчёта посетителей на компьютерном зрении» (`visitor-counter`).

### 1. Первые обязательные шаги
1. Изучи `PROJECT_SPEC.md`, `AGENTS.md`, `shared/contracts.py` и `shared/mock_counter.py`.
2. Проверь текущую ветку Git. Если ты на `main`, создай и переключись на ветку `feature/video-processing`.
3. Выполни стартовый протокол `план` (смотри `.agents/skills/session-plan/SKILL.md` и `AGENTS.md`) — запиши план работы в `reports/_wip_video.md`.

### 2. Твоя зона ответственности и границы
- **Разрешённая папка:** `video/` (а также временный/итоговый отчёт в `reports/`).
- **НЕ трогай:** `ml/`, `backend/`, `frontend/`, `tests/`, `shared/contracts.py`.
- **Ограничения MVP:** НЕ реализуй YOLO, ByteTrack, подсчёт пересечений, FastAPI или WebSocket. Твой модуль — мост между источником видео (OpenCV) и любым счётчиком, реализующим `VisitorCounterProtocol` (для тестов используй `shared.mock_counter.MockVisitorCounter`).

### 3. Что нужно реализовать в `video/`
Рекомендуемая структура:
- `video/__init__.py` (реэкспорт `VideoSource`, `VideoProcessor`, `encode_jpeg`)
- `video/video_source.py` — класс `VideoSource(source: str)`:
  - открывает видеофайл (`.mp4`, `.avi`) или URL (задел под RTSP) через `cv2.VideoCapture`;
  - бросает понятное исключение, если источник не открылся;
  - даёт свойства `fps`, `width`, `height`, `total_frames` (`None` для потоков, где число кадров неизвестно);
  - поддерживает `read() -> tuple[bool, np.ndarray | None]`, `release() -> None` и менеджер контекста `__enter__` / `__exit__`.
- `video/frame_stream.py` — генератор/процессор `VideoProcessor`:
  - полностью соответствует `VideoProcessorProtocol` из `shared/contracts.py`;
  - `__init__(self, counter: VisitorCounterProtocol)` (в начале обработки вызывает `counter.reset()`);
  - `process(self, source: str, stop_event: threading.Event | None = None) -> Iterator[tuple[np.ndarray, dict]]`:
    - читает кадры **последовательно через генератор (`yield`)**, не загружая всё видео в память;
    - корректно прерывается, если установлен `stop_event`;
    - вызывает `counter.process_frame(frame)` и замеряет фактическую скорость обработки (`fps`, например скользящее среднее по последним N кадрам);
    - добавляет в словарь `stats` поля `"fps"`, `"frame_index"`, `"progress"` (от `0.0` до `1.0` или `None`);
    - в блоке `finally` гарантированно освобождает `VideoSource`.
  - Вспомогательная функция `encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes` для подготовки кадра к MJPEG-потоку в Backend.

### 4. Самостоятельное тестирование
До завершения работы обязательно проверь:
1. Создай короткий тестовый скрипт или локальный smoke-test, который генерирует временное синтетическое видео через `cv2.VideoWriter` (или читает тестовый файл, не коммитя `.mp4` в Git!), прогоняет его через `VideoProcessor(MockVisitorCounter())`, проверяет:
   - корректное открытие и чтение кадров;
   - формат `(frame, stats)` и наличие `fps`, `frame_index`, `progress`, `entered`, `exited`, `current`;
   - остановку по `stop_event.set()`;
   - кодирование `encode_jpeg(frame)` (начинается с JPEG-заголовка `\xff\xd8`);
   - освобождение ресурсов после завершения.
2. По ходу работы фиксируй прогресс командой `чекпоинт` в `reports/_wip_video.md`.

### 5. Завершение и отчёт
Когда всё готово и протестировано, выполни протокол `финал`:
- проверь `git diff --name-only main` (что не задеты чужие папки и не закоммичены видеофайлы);
- создай чистовой отчёт `reports/02_video.md` по шаблону `reports/TEMPLATE_REPORT.md` (с примером интеграции `VideoProcessor` для Backend-разработчика);
- подготовь коммит и пуш в ветку `feature/video-processing` для Pull Request в `main` (в `main` не сливай).
```
