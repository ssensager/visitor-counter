# PROJECT_SPEC.md — Единая спецификация проекта `visitor-counter`

Этот файл — **единый источник правды** по архитектуре, интерфейсам взаимодействия и границам ответственности. Любой модуль обязан строго соблюдать описанные здесь контракты.

---

## 1. Цель и рамки студенческого MVP

**Задача:** разработать работающий прототип веб-приложения, который принимает видеозапись (`MP4`/`AVI`), находит на ней людей, отслеживает их траектории, раздельно считает вошедших (`entered`) и вышедших (`exited`) через виртуальную линию и показывает обработанное видео и статистику в браузере в реальном времени.

### Что сознательно НЕ делаем в MVP
- Обучение собственной нейросети с нуля и сбор обучающего датасета (используем предобученные веса `YOLOv8n` и класс `person`, `class_id = 0` в COCO).
- Распознавание лиц, идентификация личности и разделение «сотрудник / посетитель».
- База данных, авторизация/роли пользователей, микросервисы, облако, обязательный Docker.
- Одновременная обработка нескольких видео (в MVP активна **только одна** задача обработки за раз).
- Прямая работа с реальной IP-камерой (демонстрация на видеофайлах, но `VideoSource` в `video/` проектируется так, чтобы в будущем туда можно было передать RTSP URL).

---

## 2. Архитектура и поток данных

```text
[Браузер: frontend/]
   │  REST (upload / start / stop / stats)
   │  MJPEG (/api/video/stream/{job_id})
   │  WebSocket (/ws/stats/{job_id})
   ▼
[Backend: backend/ — FastAPI]  (раздаёт статику frontend/ на "/")
   │  управляет 1 активной задачей (JobManager / VideoService)
   ▼
[Video Pipeline: video/ — VideoSource + VideoProcessor]
   │  читает кадры из MP4/AVI через OpenCV (без загрузки всего видео в RAM)
   │  передаёт каждый кадр в ML-счётчик, замеряет реальный FPS
   ▼
[ML-ядро: ml/ — VisitorCounter]
   │  YOLOv8n (детекция person) -> ByteTrack (ID) -> Виртуальная линия (подсчёт)
   ▼
(processed_frame: np.ndarray, stats: dict) -> обратно в Video -> Backend -> Браузер
```

---

## 3. Жёсткие контракты модулей

Все общие типы и протоколы продублированы в коде в [`shared/contracts.py`](./shared/contracts.py), а для независимой разработки есть заглушка [`shared/mock_counter.py`](./shared/mock_counter.py).

### 3.1. Контракт ML-модуля (`ml/`)

Основной класс — `VisitorCounter` (рекомендуемый экспорт из `ml/counter.py` или `ml/processor.py` и реэкспорт в `ml/__init__.py`):

```python
class VisitorCounter:
    def __init__(
        self,
        model_path: str | None = None,
        line: tuple[tuple[int, int], tuple[int, int]] | None = None,
        conf_threshold: float = 0.35,
    ) -> None: ...

    def set_line(self, p1: tuple[int, int], p2: tuple[int, int]) -> None: ...

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, dict]: ...

    def reset(self) -> None: ...
```

**Требования к поведению:**
- Если `model_path is None`, используется предобученная `yolov8n.pt` (загружается **один раз** при инициализации, не на каждом кадре).
- Если `line is None`, при первом кадре автоматически задаётся линия по умолчанию по центру кадра: `((0, height // 2), (width, height // 2))`.
- `process_frame(frame)` рисует на копии кадра bounding box'ы, ID треков, виртуальную линию (и при желании подписи направления) и возвращает `(processed_frame, stats)`.
- Формат словаря `stats`:
  ```json
  {
    "entered": 15,
    "exited": 8,
    "current": 7,
    "people": [
      {"id": 1, "bbox": [120, 80, 210, 350]}
    ]
  }
  ```
  - `bbox` — строго `[x1, y1, x2, y2]` в целых пикселях (`int`).
  - `current` = `entered - exited`.
  - Один и тот же ID при колебаниях около линии не должен засчитываться повторно.
- `reset()` сбрасывает счётчики и состояние треков для нового видео без пересоздания модели.

### 3.2. Контракт Video Processing (`video/`)

Основные классы в `video/` (рекомендуется реэкспорт в `video/__init__.py`):

- `VideoSource(source: str)` — обёртка над `cv2.VideoCapture(source)` (поддерживает путь к файлу, с заделом на RTSP URL):
  - свойства/методы: `fps: float`, `width: int`, `height: int`, `total_frames: int | None`, `read() -> tuple[bool, np.ndarray | None]`, `release() -> None`, поддержка `with VideoSource(...) as src:`.
- `VideoProcessor(counter: VisitorCounterProtocol)`:
  - `process(self, source: str, stop_event: threading.Event | None = None) -> Iterator[tuple[np.ndarray, dict]]`
  - На каждом кадре вызывает `counter.process_frame(frame)`, вычисляет фактический `fps` обработки (скользящее среднее или мгновенный), добавляет в `stats`:
    - `"fps"`: `float` (округлённый, например до 1 знака);
    - `"frame_index"`: `int`;
    - `"progress"`: `float | None` (от `0.0` до `1.0`, если известно число кадров).
  - При установке `stop_event` или окончании видео корректно освобождает `VideoSource`.

### 3.3. Контракты HTTP / MJPEG / WebSocket API (`backend/`)

Backend работает на одном хосте и порту с Frontend (`http://127.0.0.1:8000`) и раздаёт `frontend/` на `/` (исключает проблемы с CORS).

| Метод | Endpoint | Назначение | Запрос / Ответ |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Веб-дашборд | Отдаёт `frontend/index.html` (и статику `/css`, `/js`, `/assets` или `/static`) |
| `GET` | `/api/health` | Проверка сервера | `200`: `{"status": "ok"}` |
| `POST` | `/api/video/upload` | Загрузка видео | `multipart/form-data`, поле `file` (`.mp4`, `.avi`). `200`: `{"job_id": "abc123", "filename": "demo.mp4", "status": "uploaded"}` |
| `POST` | `/api/video/start/{job_id}` | Запуск обработки | Опционально JSON `{"line": [[x1, y1], [x2, y2]]}`. `200`: `{"job_id": "abc123", "status": "processing"}`. Если уже идёт другая задача: `409 Conflict` |
| `POST` | `/api/video/stop/{job_id}` | Остановка обработки | `200`: `{"job_id": "abc123", "status": "stopped"}` |
| `GET` | `/api/video/stream/{job_id}` | MJPEG-поток | `multipart/x-mixed-replace; boundary=frame` с JPEG-кадрами |
| `GET` | `/api/stats/{job_id}` | Текущая статистика | `200`: JSON `StatsResponse` (см. ниже) |
| `WS` | `/ws/stats/{job_id}` | Статистика в реальном времени | Сервер пушит JSON `StatsResponse` при обновлении кадров и смене статуса |

**Формат `StatsResponse` (для `GET /api/stats/{job_id}` и `WS /ws/stats/{job_id}`):**
```json
{
  "job_id": "abc123",
  "entered": 15,
  "exited": 8,
  "current": 7,
  "fps": 28.5,
  "progress": 0.42,
  "status": "processing",
  "error": null
}
```
Допустимые значения `status`: `"uploaded"`, `"processing"`, `"completed"`, `"stopped"`, `"error"`.  
Формат HTTP-ошибок: стандартный FastAPI `{"detail": "описание ошибки"}` (`400` / `404` / `409` / `415` / `500`).

### 3.4. Требования к Frontend (`frontend/`)

- Чистый `HTML5 + CSS3 + vanilla JS` (без React/Vue/сборщиков).
- Все запросы к API идут по **относительным URL** (`/api/...`, `/ws/...`).
- Элементы интерфейса:
  - Заголовок `Visitor Analytics`, индикатор доступности сервера (`/api/health`) и статус текущей задачи;
  - 3 основные карточки: **Вошло** (`entered`), **Вышло** (`exited`), **Сейчас внутри / Баланс** (`current`), плюс **FPS** и прогресс;
  - Область видеопотока (`<img>` на `/api/video/stream/{job_id}` во время обработки) с понятной заглушкой до старта;
  - Блок управления: выбор `.mp4`/`.avi`, загрузка, «Запустить», «Остановить», вывод понятных ошибок.

---

## 4. Распределение ролей, веток и папок

| № | Роль | Ветка Git | Зона редактирования | Итоговый отчёт |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **ML Engineer (Тимлид)** | `feature/ml-counter` | `ml/` | `reports/01_ml.md` |
| 2 | **Video Processing Engineer** | `feature/video-processing` | `video/` | `reports/02_video.md` |
| 3 | **Backend Developer** | `feature/backend-api` | `backend/` | `reports/03_backend.md` |
| 4 | **Frontend Developer** | `feature/frontend-dashboard` | `frontend/` | `reports/04_frontend.md` |
| 5 | **DevOps & QA** | `feature/devops-testing` | `tests/`, `requirements.txt`, `.env.example`, `run.bat`/`start.ps1` | `reports/05_devops_qa.md` |
| 0 | **Тимлид (Сборка проекта)** | `feature/integration` | Стыковка модулей, общий фикс багов, финальный прогон | `reports/00_FINAL_SUMMARY.md` |
| 6 | **Девушка №1 (Аналитика и паспорт проекта)** | `feature/presentation-context` | `reports/pres_part1_context.md` | `reports/pres_part1_context.md` |
| 7 | **Девушка №2 (Аналитика результатов и описание системы)** | `feature/presentation-tech` | `reports/pres_part2_tech.md` | `reports/pres_part2_tech.md` |
| 8 | **Девушка №3 (Дизайн итоговой презентации)** | `feature/presentation-final` | `presentation/` | `presentation/` |

---

## 5. Проверка качества и точности

Для отчёта на защите требуется проверка минимум на **3 тестовых видеозаписях различной сложности**:
1. Простая (люди проходят по одному).
2. Средняя (несколько людей в кадре одновременно).
3. Сложная (перекрытия, встречные потоки, смена направления).

Формула расчёта ошибки подсчёта (отдельно для входов и выходов):
$$\text{Ошибка (\%)} = \frac{|\text{Авто} - \text{Факт}|}{\text{Факт}} \times 100\%$$
*(Если фактическое число равно `0`, указывается только абсолютная ошибка $|\text{Авто} - \text{Факт}|$.)*  
Целевой ориентир проекта — ошибка не более **5%**; при реальном тестировании фиксируются только честные замеренные числа без подгонки.
