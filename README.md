# Visitor Counter (`visitor-counter`)

Студенческий MVP-проект: **«Система подсчёта посетителей на компьютерном зрении»**.  
Приложение получает видеозапись (`MP4` / `AVI`), обнаруживает людей с помощью `YOLOv8n`, отслеживает их перемещение через `ByteTrack`, считает входящих и выходящих при пересечении виртуальной линии и транслирует результат в минималистичный веб-дашборд.

---

## Главное правило работы в репозитории

> **Разработка идёт строго в отдельных ветках!**  
> Все ветки уже созданы заранее от `main`.  
> **В `main` напрямую ничего не коммитим и не пушим** — готовую работу каждый сдаёт через **Pull Request** из своей ветки в `main`.

---

## Роли, ветки и промпты для команды

### Программисты (5 веток)
| Роль | Ветка (уже создана) | Твоя папка | Промпт для ИИ | Итоговый отчёт |
| :--- | :--- | :--- | :--- | :--- |
| **ML Engineer (Лидер)** | `feature/ml-counter` | `ml/` | [`prompts/01_ml_counter.md`](./prompts/01_ml_counter.md) | `reports/01_ml.md` |
| **Video Processing** | `feature/video-processing` | `video/` | [`prompts/02_video_processing.md`](./prompts/02_video_processing.md) | `reports/02_video.md` |
| **Backend Developer** | `feature/backend-api` | `backend/` | [`prompts/03_backend_api.md`](./prompts/03_backend_api.md) | `reports/03_backend.md` |
| **Frontend Developer** | `feature/frontend-dashboard` | `frontend/` | [`prompts/04_frontend_dashboard.md`](./prompts/04_frontend_dashboard.md) | `reports/04_frontend.md` |
| **DevOps & QA** | `feature/devops-testing` | `tests/`, скрипты, `requirements.txt` | [`prompts/05_devops_qa.md`](./prompts/05_devops_qa.md) | `reports/05_devops_qa.md` |

### Сборка проекта (Лидер, после PR от программистов)
| Этап | Ветка (уже создана) | Промпт для ИИ | Итоговый отчёт |
| :--- | :--- | :--- | :--- |
| **Интеграция и замеры на 3+ видео** | `feature/integration` | [`prompts/00_lead_integration.md`](./prompts/00_lead_integration.md) | `reports/00_FINAL_SUMMARY.md` |

### Девушки (только итоговая презентация и речь, без отдельной документации)
| Роль | Ветка (уже создана) | Когда начинать | Промпт для ИИ | Результат |
| :--- | :--- | :--- | :--- | :--- |
| **№1: Проблема, аналоги, ЦА** | `feature/presentation-context` | **Сразу** | [`prompts/06_girls_analytics_context.md`](./prompts/06_girls_analytics_context.md) | `reports/pres_part1_context.md` |
| **№2: Техническая выжимка** | `feature/presentation-tech` | После `00_FINAL_SUMMARY.md` | [`prompts/07_girls_tech_digest.md`](./prompts/07_girls_tech_digest.md) | `reports/pres_part2_tech.md` |
| **№3: Сборщик презентации** | `feature/presentation-final` | После №1 и №2 | [`prompts/08_girls_presentation_builder.md`](./prompts/08_girls_presentation_builder.md) | `presentation/` |

---

## Пошаговая инструкция старта для участника

### Шаг 1. Склонируй репозиторий и переключись на свою ветку
```bash
git clone https://github.com/ssensager/visitor-counter.git
cd visitor-counter
git fetch origin
git checkout <твоя-ветка>
```
*(Если настроен SSH, можно клонировать через `git@github.com:ssensager/visitor-counter.git`.)*

Проверь, что ты действительно не в `main`:
```bash
git branch --show-current
```

### Шаг 2. Запусти своего ИИ-агента с готовым промптом
1. Открой свой файл в [`prompts/`](./prompts/README.md) и скопируй текст промпта целиком в чат с AI-агентом.
2. По ходу работы пользуйся тремя командами в чате (они подключены как скиллы в `.agents/skills/` и прописаны в [`AGENTS.md`](./AGENTS.md)):
   - **`план`** — перед началом работы: ИИ проверит ветку, контракты в `PROJECT_SPEC.md` и запишет план в `reports/_wip_<role>.md`.
   - **`чекпоинт`** — после каждого важного шага или перед паузой: ИИ сохранит прогресс, запуски и ошибки, чтобы контекст не потерялся.
   - **`финал`** — когда модуль готов и протестирован: ИИ перепроверит границы папок, тесты и соберёт чистовой отчёт `reports/<nn>_<role>.md`.

### Шаг 3. Сдай свою ветку через Pull Request
1. Убедись, что не трогал чужие папки и не залил видео (`.mp4`/`.avi`) или веса (`.pt`).
2. Запушь свою ветку:
   ```bash
   git add .
   git commit -m "feat(<твоя-роль>): краткое описание сделанного"
   git push -u origin <твоя-ветка>
   ```
3. Открой репозиторий на GitHub, нажми **Compare & pull request**, проверь что слияние идёт из `<твоя-ветка>` в `main`, и создай Pull Request.

> **Памятка для девушек:** если неудобно работать через Git-ветки, можно просто взять материалы из `main` (и позже из `reports/`), прогнать промпт в любом ИИ-чате и скинуть готовые файлы руководителю. Отдельная бумажная документация не нужна — готовим только презентацию и текст к защите.

---

## Стек и структура проекта

- **Стек:** Python 3.11+, `YOLOv8n` (`ultralytics`), `ByteTrack`, `OpenCV`, `FastAPI`, `Uvicorn`, `WebSocket`, `MJPEG`, `HTML5/CSS3/JS`.
- **Документы-ориентиры:** [`PROJECT_SPEC.md`](./PROJECT_SPEC.md) (архитектура и контракты), [`AGENTS.md`](./AGENTS.md) (правила для ИИ), [`shared/contracts.py`](./shared/contracts.py) и [`shared/mock_counter.py`](./shared/mock_counter.py).

```text
visitor-counter/
├── .agents/skills/        # Скиллы ИИ-агентов (план, чекпоинт, финал)
├── AGENTS.md              # Единые правила для всех ИИ-агентов
├── PROJECT_SPEC.md        # Главная спецификация, архитектура и контракты
├── prompts/               # Готовые промпты для каждого участника команды
├── shared/                # Единые контракты типов и mock-заглушка для тестов
├── ml/                    # [ML] YOLOv8n + ByteTrack + виртуальная линия
├── video/                 # [Video] OpenCV-источник и цикл обработки кадров
├── backend/               # [Backend] FastAPI, загрузка видео, MJPEG, WebSocket
├── frontend/              # [Frontend] Веб-дашборд Visitor Analytics
├── tests/                 # [DevOps / QA] Автотесты и замер точности на видео
├── models/                # Локальные веса моделей (.pt игнорируются в Git)
├── storage/               # Загруженные и тестовые видео (медиа игнорируются в Git)
├── reports/               # Итоговые Markdown-отчёты модулей и скриншоты
└── presentation/          # Материалы итоговой презентации
```

## Целевой запуск (после сборки модулей)

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Веб-интерфейс будет доступен по адресу `http://127.0.0.1:8000/`.
