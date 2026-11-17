# Промпты для участников команды `visitor-counter`

Каждый участник открывает свой файл промпта, копирует текст целиком и передаёт его своему AI-агенту вместе с доступом к этому репозиторию.

---

## Распределение файлов

### Программисты (разработка модулей параллельно)
| Файл промпта | Роль | Ветка Git | Папка | Итоговый отчёт |
| :--- | :--- | :--- | :--- | :--- |
| [`01_ml_counter.md`](./01_ml_counter.md) | **ML Engineer (Лидер)** | `feature/ml-counter` | `ml/` | `reports/01_ml.md` |
| [`02_video_processing.md`](./02_video_processing.md) | **Video Processing** | `feature/video-processing` | `video/` | `reports/02_video.md` |
| [`03_backend_api.md`](./03_backend_api.md) | **Backend Developer** | `feature/backend-api` | `backend/` | `reports/03_backend.md` |
| [`04_frontend_dashboard.md`](./04_frontend_dashboard.md) | **Frontend Developer** | `feature/frontend-dashboard` | `frontend/` | `reports/04_frontend.md` |
| [`05_devops_qa.md`](./05_devops_qa.md) | **DevOps & QA** | `feature/devops-testing` | `tests/`, корень | `reports/05_devops_qa.md` |

### Финальная сборка (Лидер, после PR от программистов)
| Файл промпта | Роль | Ветка Git | Итоговый отчёт |
| :--- | :--- | :--- | :--- |
| [`00_lead_integration.md`](./00_lead_integration.md) | **Сборка и финальные тесты** | `feature/integration` (или `main`) | `reports/00_FINAL_SUMMARY.md` |

### Девушки (подготовка итоговой презентации — только презентация, без отдельной документации)
| Файл промпта | Роль | Когда стартует | Ветка Git | Результат |
| :--- | :--- | :--- | :--- | :--- |
| [`06_girls_analytics_context.md`](./06_girls_analytics_context.md) | **Девушка №1:** Проблема, аналоги, ЦА, советы по камерам | **Сразу** (параллельно с кодом) | `feature/presentation-context` | `reports/pres_part1_context.md` |
| [`07_girls_tech_digest.md`](./07_girls_tech_digest.md) | **Девушка №2:** Техническая выжимка для слайдов из отчётов парней | После `reports/00_FINAL_SUMMARY.md` | `feature/presentation-tech` | `reports/pres_part2_tech.md` |
| [`08_girls_presentation_builder.md`](./08_girls_presentation_builder.md) | **Девушка №3:** Сборщик презентации + речь защиты | После №1 и №2 | `feature/presentation-final` | `presentation/` |

---

## Как пользоваться командами `план`, `чекпоинт`, `финал`

Во время общения со своей нейронкой вводи в чат эти короткие команды:
1. **`план`** — в самом начале работы: ИИ проверит ветку, контракты и запишет план в `reports/_wip_<role>.md`.
2. **`чекпоинт`** — после каждой готовой части или перед закрытием чата: ИИ сохранит прогресс, ошибки и следующий шаг, чтобы ничего не потерялось.
3. **`финал`** — когда всё готово и протестировано: ИИ перепроверит файлы и тесты, создаст чистовой отчёт `reports/<nn>_<role>.md` и подскажет команды для пуша и Pull Request.
