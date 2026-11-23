# Отчёт модуля: Backend Developer

- **Ответственный / роль:** Backend Developer
- **Ветка Git:** `feature/backend-api`
- **Дата финализации:** `2026-11-23`
- **Статус:** `Готово к интеграции`

## 1. Что реализовано

FastAPI-приложение с потокобезопасным реестром задач в памяти. Загруженные
MP4/AVI сохраняются под UUID в `storage/uploads/`. Одновременно допускается
один обработчик; конкурирующие старты получают 409. Обработка и кодирование
JPEG идут в отдельном потоке, HTTP-обработчики загрузки/остановки — в threadpool.
Последний кадр и статистика каждой задачи доступны нескольким клиентам.

| Метод | Endpoint | Результат |
|---|---|---|
| GET | `/` | frontend/index.html со статикой или информационная страница |
| GET | `/api/health` | 200, `{"status":"ok"}` |
| POST | `/api/video/upload` | multipart `file`; job_id, filename, uploaded |
| POST | `/api/video/start/{job_id}` | processing; необязательный JSON line |
| POST | `/api/video/stop/{job_id}` | stopped после завершения потока |
| GET | `/api/video/stream/{job_id}` | MJPEG, `multipart/x-mixed-replace; boundary=frame` |
| GET | `/api/stats/{job_id}` | StatsResponse |
| WS | `/ws/stats/{job_id}` | Обновления StatsResponse, финальный статус и закрытие |

StatsResponse содержит job_id, entered, exited, current, fps, progress,
status, error. Поддержаны все пять статусов спецификации. Повторный запуск
сбрасывает статистику, кадр и линию; счётчик переиспользуется через reset().
Без переданной линии выбирается середина текущего видео. Обработка ошибок:
415 для расширения, 400 для пустого файла, 404 для неизвестной задачи,
409 для конфликтов состояния, 422 для ошибок модели запроса, 500 для ошибок
сохранения/создания потока. Дополнительно 413 при превышении 512 MiB и 503
при завершении сервера. Повреждённое видео переводит задачу в error.

Примеры запросов (выполнять после запуска сервера; путь и job_id заменить):

```powershell
curl.exe http://127.0.0.1:8000/api/health
curl.exe -F "file=@C:/videos/demo.mp4" http://127.0.0.1:8000/api/video/upload
$jobId = "job_id из ответа"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/video/start/$jobId" -ContentType "application/json" -Body '{"line":[[0,120],[320,120]]}'
Invoke-RestMethod "http://127.0.0.1:8000/api/stats/$jobId"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/video/stop/$jobId"
```

Это примеры для пользователя; проверенные запросы выполнялись программно
через TestClient и HTTPX, включая настоящий локальный Uvicorn.

## 2. Созданные и изменённые файлы

- `backend/main.py` — фабрика приложения, lifespan/shutdown, обработка JobError, статика.
- `backend/schemas/responses.py` — модели ответов и валидация линии.
- `backend/services/job_manager.py` — загрузки, блокировка, состояния, снимки, stop/shutdown.
- `backend/services/video_service.py` — фоновая обработка, фабрика ML/video и mock-reader.
- `backend/api/routes.py` — health.
- `backend/api/video.py` — upload/start/stop/MJPEG.
- `backend/api/stats.py` — HTTP/WS статистика и обработка отключений.
- `backend/__init__.py`, `backend/api/__init__.py`, `backend/schemas/__init__.py`,
  `backend/services/__init__.py` — пакеты Python.
- `backend/requirements.txt`, `backend/requirements-dev.txt` — зависимости backend и тестов.
- `backend/test_backend.py` — контрактные и интеграционные тесты.
- `backend/test_live.py` — реальный HTTP/WebSocket/MJPEG через Uvicorn.
- `backend/README.md` — запуск, API, интеграция и ограничения.
- `reports/03_backend.md` — этот отчёт; рабочий `_wip_backend.md` заменён итоговым.

Чужие модули, PROJECT_SPEC.md, shared/contracts.py и корневые зависимости
не изменены. Окружение `backend/.venv/` игнорируется Git. Тестовые видео
создавались во временных каталогах, в набор сдаваемых файлов не входят.

## 3. Как запустить и проверить (реальные команды)

Установка окружения, реально выполненная при разработке:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
```

Финальные команды после последнего изменения исполняемого кода:

```powershell
backend/.venv/Scripts/python -m pytest backend/test_backend.py backend/test_live.py -q --basetemp=backend/.venv/pytest-final -o faulthandler_timeout=20
backend/.venv/Scripts/python -m pip check
git branch --show-current
git diff --name-only origin/main
git diff --name-only main
git ls-files --others --exclude-standard
```

**Результат проверки:** **27 passed, 1 warning in 4.65s**; pip check —
`No broken requirements found.` Ветка — feature/backend-api. На момент проверки
новые файлы не были добавлены в индекс: diff не показывал их, поэтому границы
дополнительно проверены через `git ls-files --others --exclude-standard`.
В списке только backend/ и собственный отчёт.

Проверены health, пустой/готовый frontend, невалидные расширения, пустые и
слишком большие файлы, сохранение содержимого, безопасное имя файла,
404/409/422, состояния и данные статистики, сброс счётчиков/линии,
повторная остановка, MP4 и AVI, завершение WS, декодирование JPEG из MJPEG,
отключение клиентов без остановки обработки, повреждённые видео,
два одновременных старта (ровно один успешный), shutdown в обычном и
исключительном сценариях. Подключение реальных экспортов проверено тестовыми
классами; mock и ошибки внутренних импортов проверены отдельно.

Для интерактивного запуска из корня проекта:

```powershell
$env:VISITOR_USE_MOCK = "1"
backend/.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Эта CLI-команда приведена как инструкция; в live-тесте Uvicorn запускался
программно на свободном локальном порту и был остановлен после проверки.

## 4. Зависимости и настройки окружения

Проверено на Windows, Python 3.12.10. Установленные основные версии:
FastAPI 0.165.0, Pydantic 2.14.4, Starlette 1.10.0, Uvicorn 0.54.0,
python-multipart 0.0.34, OpenCV 5.1.0.95, NumPy 2.5.5,
websockets 17.4, HTTPX 0.28.1, pytest 9.2.0.

`uvicorn[standard]` устанавливает поддержку WebSocket. DevOps следует
согласовать `backend/requirements.txt` с общими зависимостями; корневой
requirements.txt в этой работе не создавался и не менялся.

`VISITOR_USE_MOCK=1` — принудительный mock. Без него фабрика ищет реальные
экспорты; при отсутствии ml/video или их экспортов включает mock с WARNING.
Пути по умолчанию вычисляются от корня репозитория, не от текущего cwd.

## 5. Проблемы, ограничения и допущения

- Первая установка в песочнице не смогла разрешить DNS; установка с сетевым
  доступом прошла. Два первых pytest-запуска зависли на Windows asyncio
  socketpair; диагностировано faulthandler, процессы завершены. Затем запуск
  вне песочницы упёрся в права системного pytest tmp (24 ошибки setup, 1 pass).
  Указание собственного basetemp в backend/.venv решило проблему. Успешные
  последовательные результаты: 25, 26, затем финальные 27 тестов.
- Единственное предупреждение: Starlette помечает HTTPX-интеграцию TestClient
  устаревающей и предлагает httpx2. Тесты проходят; реальный транспорт
  дополнительно проверен независимо от TestClient.
- Реальных ML/video-модулей в этой ветке нет. Точность подсчёта на людях,
  GPU и производительность YOLO не проверялись; mock-числа не являются
  результатами распознавания.
- Ровно один процесс/worker. Задачи теряются при рестарте, файлы остаются;
  автоматическая очистка файлов/старых задач отсутствует. Нет БД и авторизации.
- Лимит 512 MiB проверяется после разбора multipart, не на уровне входящего
  HTTP-трафика. Это локальный учебный MVP, не публичный upload-сервис.
- Остановка кооперативная. Если сторонний код не выходит за пять секунд,
  stop возвращает 409, слот остаётся занятым до фактического завершения.
  Зависший сторонний декодер/inference может потребовать рестарт процесса.
- MJPEG/WS передают актуальные снимки с интервалом проверки 50 мс;
  промежуточные кадры могут пропускаться. После restart подключать потоки снова.
- Ошибка декодирования в середине файла иногда неотличима от EOF средствами
  OpenCV; полностью нечитаемое видео гарантированно переводится в error.

## 6. Что нужно от других модулей / для интеграции

- ML: экспортировать `ml.VisitorCounter`, соблюдать reset/set_line/process_frame.
- Video: экспортировать `video.VideoProcessor(counter)` с
  `process(source, stop_event=...)`, возвращать кадр и словарь статистики;
  гарантировать освобождение ресурсов при окончании и закрытии генератора.
- Backend создаёт счётчик один раз на сервис, вызывает reset для каждой
  задачи и set_line с линией запроса либо серединой текущего видео.
  Вызовы модели и процессора идут в одном фоновом потоке на активную задачу.
  Сбой реального модуля не скрывается переключением на mock.
- Frontend: использовать относительные URL из спецификации, показывать
  detail/error, открывать потоки после start, учитывать финальные статусы и
  reconnect после повторного start. Готовые index.html/css/js/assets
  будут раздаваться из frontend/ после перезапуска backend.
- Интегратору: убрать VISITOR_USE_MOCK=1, проверить реальное видео с обоими
  модулями и сверить зависимости. ML-точность оценивать отдельно на 3+ видео.

Подготовленные команды сдачи (коммит и push в этой сессии не выполнялись):

```powershell
git add backend reports/03_backend.md
git commit -m "feat(backend): implement video jobs and streaming API"
git push -u origin feature/backend-api
```

После push открыть Pull Request **feature/backend-api → main** для ревью.
Прямой merge/push в main не выполнять.
