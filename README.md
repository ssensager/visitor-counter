# Visitor Counter (`visitor-counter`)

Студенческий MVP-проект: **«Система подсчёта посетителей на компьютерном зрении»**.  
Приложение получает видеозапись (`MP4` / `AVI`), обнаруживает людей с помощью `YOLOv8n`, отслеживает их перемещение через `ByteTrack`, считает входящих и выходящих при пересечении виртуальной линии и транслирует результат в минималистичный веб-дашборд.

---

## Главное правило работы в репозитории

> **Разработка идёт строго в отдельных ветках!**  
> Все ветки уже созданы заранее от `main`.  
> **В `main` напрямую ничего не коммитим и не пушим** — готовую работу каждый сдаёт через **Pull Request** из своей ветки в `main`.

---

## Роли, ветки и промпты

### Программисты (5 веток)
| Роль | Ветка (уже создана) | Твоя папка | Промпт для ИИ | Итоговый отчёт |
| :--- | :--- | :--- | :--- | :--- |
| **ML Engineer (Тимлид)** | `feature/ml-counter` | `ml/` | [`prompts/01_ml_counter.md`](./prompts/01_ml_counter.md) | `reports/01_ml.md` |
| **Video Processing** | `feature/video-processing` | `video/` | [`prompts/02_video_processing.md`](./prompts/02_video_processing.md) | `reports/02_video.md` |
| **Backend Developer** | `feature/backend-api` | `backend/` | [`prompts/03_backend_api.md`](./prompts/03_backend_api.md) | `reports/03_backend.md` |
| **Frontend Developer** | `feature/frontend-dashboard` | `frontend/` | [`prompts/04_frontend_dashboard.md`](./prompts/04_frontend_dashboard.md) | `reports/04_frontend.md` |
| **DevOps & QA** | `feature/devops-testing` | `tests/`, скрипты, `requirements.txt` | [`prompts/05_devops_qa.md`](./prompts/05_devops_qa.md) | `reports/05_devops_qa.md` |

### Финальная сборка прототипа (Тимлид, после PR от программистов)
| Этап | Ветка (уже создана) | Промпт для ИИ | Итоговый отчёт |
| :--- | :--- | :--- | :--- |
| **Сборка и замеры точности на 3+ видео** | `feature/integration` | [`prompts/00_lead_integration.md`](./prompts/00_lead_integration.md) | `reports/00_FINAL_SUMMARY.md` |

### Паспорт проекта и презентация (девушки)
| Роль | Ветка (уже создана) | Когда начинать | Промпт для ИИ | Результат |
| :--- | :--- | :--- | :--- | :--- |
| **Девушка №1: Аналитика и паспорт проекта (актуальность, проблема, цели, аналоги)** | `feature/presentation-context` | **Сразу** | [`prompts/06_girls_analytics_context.md`](./prompts/06_girls_analytics_context.md) | `reports/pres_part1_context.md` |
| **Девушка №2: Аналитика результатов и описание системы** | `feature/presentation-tech` | После `00_FINAL_SUMMARY.md` | [`prompts/07_girls_tech_digest.md`](./prompts/07_girls_tech_digest.md) | `reports/pres_part2_tech.md` |
| **Девушка №3: Дизайн и сборка итоговой презентации** | `feature/presentation-final` | После №1 и №2 | [`prompts/08_girls_presentation_builder.md`](./prompts/08_girls_presentation_builder.md) | `presentation/` |

---

## Инструкция для парней: как запустить ИИ-агента, задать рамки и работать со скиллами `/`

### 1. Склонируй репозиторий и открой именно папку `visitor-counter`
```bash
git clone https://github.com/ssensager/visitor-counter.git
cd visitor-counter
git fetch origin
git checkout <твоя-ветка>
```
*(Если настроен SSH: `git clone git@github.com:ssensager/visitor-counter.git`.)*

> **ВАЖНО для работы скиллов через `/`:**  
> В своём редакторе / IDE (Antigravity, Cursor, VS Code и др.) открой через **File -> Open Folder** именно корневую папку **`visitor-counter`** (где лежат `.agents/` и `AGENTS.md`), а не родительскую папку. Только тогда агент автоматически подхватит проектные правила `AGENTS.md` и слэш-команды из `.agents/skills/`.

### 2. Как задать ИИ жёсткие рамки, чтобы он делал ТОЛЬКО твою часть
Не нужно объяснять задачу своими словами с нуля:
1. Выбери свою роль и открой соответствующий файл в папке [`prompts/`](./prompts/README.md).
2. Скопируй весь блок текста из него и отправь **первым сообщением** в чат своему ИИ-агенту.
3. В этот промпт и в [`AGENTS.md`](./AGENTS.md) уже вшиты жёсткие рамки:
   - агент обязан сначала прочитать [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) и [`shared/contracts.py`](./shared/contracts.py);
   - ему **разрешено менять только твою папку** (`ml/`, `video/`, `backend/`, `frontend/` или `tests/`) и твой отчёт в `reports/`;
   - ему **запрещено** трогать чужие папки, менять общие контракты и коммитить в `main`.

### 3. Как пользоваться скиллами через `/` по ходу разработки
В репозитории в `.agents/skills/` лежат 3 скилла. В чате с агентом набирай `/` и выбирай нужный скилл (или просто пиши короткое русское слово — работает и так, и так):

| Слэш-команда (`/`) | Короткое слово в чат | Когда нажимать и что делает ИИ |
| :--- | :--- | :--- |
| **`/session-plan`** | **`план`** | **На старте задачи.** Агент проверяет, что ты в своей ветке `feature/...` (не в `main`), сверяет контракты из `PROJECT_SPEC.md` и сохраняет пошаговый план в `reports/_wip_<role>.md`. |
| **`/session-checkpoint`** | **`чекпоинт`** | **После каждого крупного шага или перед закрытием чата.** Агент проверяет, что не задеты чужие файлы, и записывает в `reports/_wip_<role>.md`, что уже сделано, какие тесты запускались и что делать дальше. |
| **`/finalize-report`** | **`финал`** | **Когда код готов и протестирован.** Агент сверяет `git diff` с `main`, прогоняет финальные тесты, формирует чистовой отчёт `reports/0X_<role>.md` (по которому девочки потом соберут паспорт и презу) и даёт команды для пуша. |

### 4. Как сдать готовую работу
1. После команды `/finalize-report` (`финал`) проверь, что ты в своей ветке (`git branch --show-current`).
2. Закоммить и запушь свою ветку:
   ```bash
   git add .
   git commit -m "feat(<твоя-роль>): краткое описание"
   git push -u origin <твоя-ветка>
   ```
3. Зайди на страницу репозитория на GitHub, нажми кнопку **Compare & pull request** (из твоей ветки `feature/...` в `main`) и создай Pull Request.

---

## Стек и структура проекта

- **Стек:** Python 3.11+, `YOLOv8n` (`ultralytics`), `ByteTrack`, `OpenCV`, `FastAPI`, `Uvicorn`, `WebSocket`, `MJPEG`, `HTML5/CSS3/JS`.
- **Документы-ориентиры:** [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) (архитектура и контракты), [`AGENTS.md`](./AGENTS.md) (правила для ИИ), [`shared/contracts.py`](./shared/contracts.py) и [`shared/mock_counter.py`](./shared/mock_counter.py).

```text
visitor-counter/
├── .agents/skills/        # Скиллы ИИ-агентов (/session-plan, /session-checkpoint, /finalize-report)
├── AGENTS.md              # Автоматические правила и границы папок для ИИ-агентов
├── PROJECT_SPEC.md        # Главная спецификация, архитектура и контракты
├── prompts/               # Готовые промпты для каждой роли
├── shared/                # Единые контракты типов и mock-заглушка для тестов
├── ml/                    # [ML Engineer] YOLOv8n + ByteTrack + виртуальная линия
├── video/                 # [Video Processing] OpenCV-источник и цикл обработки кадров
├── backend/               # [Backend Developer] FastAPI, загрузка видео, MJPEG, WebSocket
├── frontend/              # [Frontend Developer] Веб-дашборд Visitor Analytics
├── tests/                 # [DevOps & QA] Автотесты, запуск и замер точности
├── models/                # Локальные веса моделей (.pt игнорируются в Git)
├── storage/               # Загруженные и тестовые видео (медиа игнорируются в Git)
├── reports/               # Итоговые Markdown-отчёты модулей и скриншоты
└── presentation/          # Материалы паспорта проекта и итоговой презентации
```

## Целевой запуск (после сборки модулей)

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Веб-интерфейс будет доступен по адресу `http://127.0.0.1:8000/`.
