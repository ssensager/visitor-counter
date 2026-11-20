# Отчёт модуля: DevOps Engineer & QA Tester

- **Ответственный / роль:** DevOps Engineer & QA Tester
- **Ветка Git:** `feature/devops-testing`
- **Дата финализации:** 2026-11-20
- **Статус:** `Готово к интеграции`
- **Зона ответственности:** `requirements.txt`, `.env.example`, `run.bat`, `start.ps1`, `tests/`, `reports/`

> `ml/`, `video/`, `backend/`, `frontend/` и `shared/contracts.py` не изменялись. В ветке эти папки пока содержат только `.gitkeep`, поэтому ML/API-тесты спроектированы так, чтобы мягко пропускаться сейчас и реально проверять код после слияния.

---

## 1. Что реализовано

### 1.1 Окружение и запуск (Windows, GPU/CPU)

- **`requirements.txt`** — зафиксированные версии основного стека и отдельный блок с командой установки PyTorch под CUDA для Windows. Порядок важен: сначала torch с CUDA-индекса, потом `requirements.txt`, иначе `ultralytics` подтянет CPU-сборку и GPU не задействуется.
- **`.env.example`** — `HOST`, `PORT`, `MODEL_PATH`, `CONF_THRESHOLD`, `VISITOR_USE_MOCK` + закомментированные `DEVICE`, `STORAGE_DIR`, `MAX_UPLOAD_MB`, `LOG_LEVEL` как задел на следующие итерации.
- **`run.bat`** — запуск двойным щелчком: активирует `.venv` (если есть), читает `.env`, проверяет Python 3.11+, импорты `fastapi`/`uvicorn`/`cv2`, наличие `torch` и CUDA (иначе предупреждает про CPU-fallback), наличие `backend.main`, затем поднимает `uvicorn backend.main:app`. Ключ `--check-only` — только проверки, без запуска сервера.
- **`start.ps1`** — то же плюс параметры `-BindHost`, `-Port`, `-CheckOnly`, `-SkipDependencyCheck`; читает `.env` (не перетирая уже заданные переменные), печатает версию torch и имя GPU.

### 1.2 Автотесты (`tests/`)

| Файл | Что проверяет | Сейчас | После слияния |
| :--- | :--- | :--- | :--- |
| `test_contracts.py` | `shared/contracts.py` (`ALLOWED_VIDEO_EXTENSIONS`, `JOB_STATUSES`, `PersonDetection`, `FrameStats`, протоколы) и `MockVisitorCounter` (расписание 30/55 кадров, `current`, bbox, `reset`, `set_line`, неизменность входного кадра, оверлей) | выполняется | выполняется |
| `test_ml_smoke.py` | контракт `VisitorCounter`: `process_frame`/`reset`/`set_line`, формат `stats`, `bbox` как 4 `int`, нулевой кадр без людей, рисование на копии | 8 skip | реальные проверки YOLO+ByteTrack |
| `test_api_smoke.py` | `/api/health`, отказ на `.txt` (400/415), отсутствие поля `file`, успешная загрузка `.avi`, 404 на неизвестный `job_id` (stats/start/stop), цикл start→stats→stop, 409 на вторую одновременную задачу | 1 skip (модуль) | реальные проверки FastAPI |
| `test_evaluate_accuracy.py` | формула ошибки (включая `Факт = 0`), порог 5%, разбор `--line`, CLI на синтетическом видео в `--mock`, коды возврата 0/2/3/4, `--json`, `--max-frames`, таблица и манифест | выполняется | выполняется |

Все тесты умеют работать в «голом» окружении: `numpy` и `cv2` подключаются через фикстуры с `importorskip`, `ml`/`backend.main` — через `pytest.importorskip`.

### 1.3 Оценка точности (требование защиты)

- **`tests/evaluate_accuracy.py`** — CLI: видео + `--actual-in` / `--actual-out`, прогон через `VisitorCounter` или `MockVisitorCounter` (`--mock`), замер времени и FPS, расчёт ошибки по формуле из `PROJECT_SPEC.md` §5:

  $$\text{Ошибка (\%)} = \frac{|\text{Авто} - \text{Факт}|}{\text{Факт}} \times 100\%$$

  При `Факт == 0` процент не считается — выводится только абсолютная ошибка. Есть `--json` (в т.ч. `--json -` в stdout), `--tolerance` (по умолчанию 5%), `--fail-over` (код 3 при выходе за порог — удобно для CI), `--line`, `--max-frames`, `--model`, `--conf`, `--label`.
- **`tests/benchmark_accuracy.py`** — прогон пачки видео по JSON-манифесту и готовая markdown-таблица для отчёта; `--table-template` печатает пустую заготовку на 3 видео; `--out` и `--json-out` сохраняют результаты.
- **`tests/make_test_video.py`** — синтетический ролик (без людей) только для самопроверки CLI, не для замеров точности.
- **`tests/accuracy_manifest.example.json`** — заготовка манифеста на 3 видео с `actual_in/actual_out: null`; скрипт честно скажет, что числа не заполнены, а не подставит выдуманные.

---

## 2. Созданные и изменённые файлы

| Файл | Назначение |
| :--- | :--- |
| `requirements.txt` | Пины зависимостей MVP + инструкция по PyTorch/CUDA для Windows. |
| `.env.example` | Шаблон переменных окружения (копируется в `.env`, который в `.gitignore`). |
| `run.bat` | Простой запуск на Windows через cmd: venv, проверки, `uvicorn`. |
| `start.ps1` | Запуск через PowerShell: `.env`, `-CheckOnly`, параметры хоста/порта, отчёт по CUDA. |
| `tests/conftest.py` | Пути (`shared/`, `ml/`), маркеры, фикстуры кадров и синтетических видео с мягким skip. |
| `tests/test_contracts.py` | Тесты контрактов и `MockVisitorCounter` (работают всегда). |
| `tests/test_ml_smoke.py` | Smoke-тесты реального `VisitorCounter` (skip до слияния `ml/`). |
| `tests/test_api_smoke.py` | Smoke-тесты FastAPI (skip до слияния `backend/`). |
| `tests/evaluate_accuracy.py` | CLI-утилита замера точности на одном видео. |
| `tests/benchmark_accuracy.py` | Пакетный замер + markdown-таблица для отчёта. |
| `tests/test_evaluate_accuracy.py` | Тесты формулы, CLI, таблицы и манифеста. |
| `tests/make_test_video.py` | Генератор синтетического ролика для проверки CLI. |
| `tests/accuracy_manifest.example.json` | Заготовка манифеста на 3 видео (числа не заполнены). |
| `reports/05_devops_qa.md` | Этот отчёт. |

Рабочий журнал `reports/_wip_devops_qa.md` остаётся локальным (в этой среде его нельзя удалить из-за политики файловой песочницы) и **в коммит не включается** — всё важное из него перенесено в этот отчёт. При желании его можно удалить вручную: `del reports\_wip_devops_qa.md`.

---

## 3. Как запустить и проверить (реальные команды)

### 3.1 Установка на Windows с нуля (пошагово)

```bat
:: 1) Python 3.11+ (проверено на 3.13.1), при установке включить "Add python.exe to PATH"
python --version

:: 2) Клонировать репозиторий и перейти в свою ветку
git clone https://github.com/ssensager/visitor-counter.git
cd visitor-counter
git checkout main
git pull

:: 3) Виртуальное окружение
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip

:: 4) ТОЛЬКО для NVIDIA GPU: PyTorch с CUDA ДО остальных зависимостей.
::    CUDA 13.0 (драйвер NVIDIA 580+):
.venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
::    Если драйвер старее (CUDA 12.6):
::    .venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

:: 5) Остальные зависимости (для CPU-режима пункт 4 можно пропустить)
.venv\Scripts\python -m pip install -r requirements.txt

:: 6) Настройки (необязательно, работают значения по умолчанию)
copy .env.example .env

:: 7) Проверка окружения без запуска сервера
run.bat --check-only
::    или
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -CheckOnly

:: 8) Проверка CUDA (должно быть True на NVIDIA GPU)
.venv\Scripts\python -c "import torch; print(torch.__version__, torch.cuda.is_available())"

:: 9) Запуск приложения
run.bat
::    или
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1

:: 10) Браузер: http://127.0.0.1:8000/
```

При первом запуске `ultralytics` скачает `yolov8n.pt` (~6 МБ) в текущую папку, если файла нет; при отсутствии интернета положите веса рядом и укажите `MODEL_PATH` в `.env`.

### 3.2 Запуск тестов

```bat
:: из корня репозитория, в активированном .venv
.venv\Scripts\python -m pytest
:: или только быстрый набор без ML/API
.venv\Scripts\python -m pytest tests\test_contracts.py tests\test_evaluate_accuracy.py -v
```

### 3.3 Замер точности на 3 тестовых видео (пошагово)

1. **Подготовить видео** (3 ролика разной сложности) и положить их в `storage/test_videos/`:
   - `01_simple.mp4` — люди проходят по одному;
   - `02_medium.mp4` — несколько человек в кадре одновременно;
   - `03_hard.mp4` — перекрытия, встречные потоки, смена направления.

   > Папка `storage/test_videos/*.mp4|avi|mkv|mov` уже в `.gitignore`: видео в репозиторий не попадают.

2. **Вручную посмотреть каждое видео и записать фактические числа** вошедших и вышедших. Это единственный источник «Факта»; числа нельзя подгонять под ответ системы.

3. **Самопроверка скрипта без YOLO** (быстро, до появления весов):

   ```bat
   .venv\Scripts\python tests\make_test_video.py --out .tmp\clip.avi --frames 12
   .venv\Scripts\python tests\evaluate_accuracy.py .tmp\clip.avi --actual-in 0 --actual-out 0 --mock
   ```

4. **Реальный замер по каждому видео** (подставьте свои фактические числа):

   ```bat
   .venv\Scripts\python tests\evaluate_accuracy.py storage\test_videos\01_simple.mp4 ^
       --actual-in 10 --actual-out 9 --json reports\accuracy_simple.json

   .venv\Scripts\python tests\evaluate_accuracy.py storage\test_videos\02_medium.mp4 ^
       --actual-in 24 --actual-out 21 --json reports\accuracy_medium.json

   .venv\Scripts\python tests\evaluate_accuracy.py storage\test_videos\03_hard.mp4 ^
       --actual-in 37 --actual-out 33 --json reports\accuracy_hard.json
   ```

   Здесь `--actual-in/--actual-out` — **ваши** фактические числа (в примере показан только синтаксис команды). Коды возврата: `0` — посчитано, `2` — ошибка файла/аргументов, `3` — ошибка выше `--tolerance` (только с `--fail-over`), `4` — нет зависимостей/счётчика.

5. **Одной командой на все 3 видео + таблица для отчёта:**

   ```bat
   copy tests\accuracy_manifest.example.json reports\accuracy_manifest.json
   :: заполнить в reports\accuracy_manifest.json пути и фактические числа
   .venv\Scripts\python tests\benchmark_accuracy.py --manifest reports\accuracy_manifest.json ^
       --out reports\accuracy_table.md --json-out reports\accuracy_raw.json
   ```

6. **Проверить результат:** каждое видео должно уложиться в ориентир **≤ 5%** (по входам и по выходам отдельно). Если нет — цифры остаются как есть, это честный результат MVP.

### 3.4 Заготовка таблицы точности для отчёта (без выдуманных цифр)

Готовая пустая таблица (её же печатает `python tests/benchmark_accuracy.py --table-template`):

| № | Сложность | Видео | Факт (вошло/вышло) | Авто (вошло/вышло) | Ошибка вход, % | Ошибка выход, % | FPS | Ориентир <= 5% |
| :-: | :--- | :--- | :---: | :---: | ---: | ---: | ---: | :-: |
| 1 | простое | `<путь к видео>` | — | — | — | — | — | — |
| 2 | среднее | `<путь к видео>` | — | — | — | — | — | — |
| 3 | сложное | `<путь к видео>` | — | — | — | — | — | — |

Заполняется только после реального прогона: `Авто` берётся из `reports/accuracy_raw.json` (поле `auto`), `Факт` — из ручного просмотра, `Ошибка` — из поля `error_pct` (или абсолютная ошибка при `Факт = 0`).

### 3.5 Результаты проверок (что реально выполнялось)

| Проверка | Команда | Фактический результат |
| :--- | :--- | :--- |
| Полный прогон тестов | `.venv\Scripts\python -m pytest` | **55 passed, 9 skipped** (1.6 с) |
| Тесты на точных версиях из `requirements.txt` | установка пинов в отдельный каталог + `pytest` | **55 passed, 9 skipped**; cv2 4.14.0, fastapi 0.165.0, pydantic 2.14.4, uvicorn 0.54.0, httpx 0.28.1, pytest 9.2.0, numpy 2.5.5 |
| CLI `--mock`, точные числа | `evaluate_accuracy.py .tmp\synthetic40.avi --actual-in 1 --actual-out 0 --mock` | код **0**, PASS, 40 кадров, FPS обработки замерен |
| CLI `--mock` + порог | `... --actual-in 10 --actual-out 5 --mock --fail-over` | код **3**, FAIL (90.00% и 100.00%) |
| CLI без ML-модуля | `... --actual-in 1 --actual-out 0` (без `--mock`) | код **4**, сообщение «пакет ml/ не слит, используйте --mock» |
| CLI + JSON | `... --json .tmp\cli_result.json` | файл создан: `frames`, `fps`, `entered/exited` c `abs_error`, `error_pct`, `passed` |
| Benchmark | `benchmark_accuracy.py --manifest .tmp\manifest.json --mock --out .tmp\table.md` | таблица записана (2 строки, PASS + FAIL), код **1** при провале |
| Заготовка таблицы | `benchmark_accuracy.py --table-template` | 3 строки: простое/среднее/сложное, ориентир `<= 5%` |
| `run.bat` | `run.bat --check-only` | код **0**: venv, Python 3.13.1, fastapi/uvicorn/cv2 OK, `torch` отсутствует (warn), `backend.main` отсутствует (error + check-only) |
| `start.ps1` | `powershell -ExecutionPolicy Bypass -File .\start.ps1 -CheckOnly` | код **0**, тот же набор проверок, русский вывод корректен |
| Синтаксис `start.ps1` | `[System.Management.Automation.Language.Parser]::ParseFile(...)` | **0 ошибок** |
| Синтаксис `tests/*.py` | `ast.parse` всех файлов | **7/7 OK** |
| FastAPI TestClient (совместимость версий) | dummy app: `GET /api/health`, `POST /api/video/upload` | **200** `{"status":"ok"}`, **200** `{"job_id": "..."}` |
| Чтение `.env` | `.env` из `.env.example`, затем `--check-only` / `-CheckOnly` | оба лаунчера сообщили о 5 загруженных переменных |

---

## 4. Зависимости и настройки окружения

| Пакет | Версия | Зачем именно так |
| :--- | :--- | :--- |
| Python | 3.11+ (проверено 3.13.1) | torch 2.15 требует ≥ 3.11; numpy 2.5.5 — ≥ 3.12 (для 3.11 pip подберёт numpy 2.x пониже). |
| `ultralytics` | `8.4.216` | Актуальная стабильная; требует `opencv-python>=4.7`, `torch>=1.8`, `numpy>=1.23`. |
| `opencv-python` | `4.14.0.94` | Сознательно ветка 4.x, а не 5.x: ultralytics 8.4 проверен на OpenCV 4.x; версия не входит в исключения пакета. |
| `numpy` | `>=2.0,<3` | Требование opencv 4.14 (`numpy>=2` для Python ≥ 3.9); точный пин зависит от версии Python, поэтому диапазон. |
| `fastapi` | `0.165.0` | Совместима со starlette 1.10 и pydantic 2.14. |
| `uvicorn[standard]` | `0.54.0` | `[standard]` добавляет websockets/watchfiles — нужны для `/ws/stats/{job_id}` и автоперезапуска. |
| `python-multipart` | `0.0.34` | Обязателен для `multipart/form-data` при загрузке видео. |
| `pydantic` | `2.14.4` | Версия, с которой собран/проверен fastapi 0.165. |
| `pytest` | `9.2.0` | Актуальная стабильная. |
| `httpx` | `0.28.1` | Требуется `TestClient` из Starlette/FastAPI. |

**PyTorch/CUDA (Windows), порядок важен:**

```bat
:: NVIDIA GPU, CUDA 13.0 (драйвер 580+) — рекомендуется
.venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
:: NVIDIA GPU, CUDA 12.6 (драйвер 560+)
.venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
:: затем
.venv\Scripts\python -m pip install -r requirements.txt
```

Проверено по индексам PyTorch: в `cu130` доступны `torch 2.14.1+cu130` и `torchvision 0.29.1+cu130`; в `cu126` — `torch 2.14.1+cu126`. Без отдельной установки `pip install -r requirements.txt` поставит CPU-сборку, и приложение автоматически пойдёт по CPU-ветке (fallback предусмотрен в `run.bat`/`start.ps1` и в самом ML-модуле).

**Переменные окружения (`.env`):** `HOST` (127.0.0.1), `PORT` (8000), `MODEL_PATH` (`yolov8n.pt`), `CONF_THRESHOLD` (0.35), `VISITOR_USE_MOCK` (0 — реальный счётчик, 1 — mock). Файл `.env` в `.gitignore`, шаблон — `.env.example`.

---

## 5. Проблемы, ограничения и допущения

1. **Чужие модули ещё не слиты.** `ml/`, `video/`, `backend/`, `frontend/` содержат только `.gitkeep`, поэтому сейчас `pytest` даёт 55 passed и 9 skipped (8 ML + 1 модуль API). Это ожидаемое поведение: после слияния тех веток те же тесты начнут реально проверять `VisitorCounter` и эндпоинты, ничего менять не потребуется.
2. **`torch`/`ultralytics` локально не устанавливались** (CUDA-колёса ≈ 2.5 ГБ). Совместимость проверена на двух уровнях: (а) метаданные PyPI (`ultralytics 8.4.216` → `opencv-python>=4.7`, `torch>=1.8`, `numpy>=1.23`); (б) фактическая установка «лёгкой» части точных пинов и прогон на них всех тестов. Реальный инференс YOLO на этой машине не выполнялся — это задача интегратора с GPU-машиной.
3. **Реальной точности пока нет.** В отчёте только пустая заготовка таблицы: числа появятся после ручного просмотра 3 видео. Ни одна цифра не выдумана.
4. **`run.bat` намеренно на английском (ASCII).** Русские сообщения в UTF-8 внутри `.bat` ломают разбор строк в `cmd` (проверено: команды терялись, python получал битые аргументы). Русскоязычный и более удобный вариант — `start.ps1` (UTF-8 с BOM).
5. **`start.ps1` требует обхода Execution Policy** в стандартной конфигурации Windows: `powershell -ExecutionPolicy Bypass -File .\start.ps1`. Это документировано выше.
6. **Локальная песочница разработки** (не проектная проблема): каталоги, создаваемые с POSIX-режимом `0700` (`ensurepip`, `tempfile.mkdtemp`, `pytest --basetemp`), становились недоступны, поэтому venv создавался через `--without-pip`, а пакеты ставились с `--target`. Для пользователя на обычной машине шаги из §3.1 работают штатно; в репозиторий эти обходы не попали.
7. **`TestClient` и `httpx`.** Starlette 1.10 предупреждает, что `TestClient` с `httpx` объявлен устаревшим (рекомендует `httpx2`). Связка `fastapi 0.165 + httpx 0.28.1` проверена и работает; `httpx` оставлен как требует задание. При обновлении стека стоит перейти на `httpx2`.
8. **409 Conflict** реализуется бэкендом (в MVP активна одна задача). Тест ожидает именно 409 по `PROJECT_SPEC.md`; если бэкенд выберет другой код, тест это покажет — контракт править нужно в спецификации, а не в тесте.

---

## 6. Что нужно от других модулей / для интеграции

**Backend (`feature/backend-api`):**
- `backend/main.py` с объектом `app` (FastAPI) — без этого `run.bat`/`start.ps1` завершатся с понятной ошибкой, а API-тесты останутся пропущенными.
- Контракты, на которые опираются тесты: `GET /api/health → {"status": "ok"}`; `POST /api/video/upload` с полем `file` (`form-data`), ответ `{"job_id", "filename", "status": "uploaded"}`; отказ на неподдерживаемое расширение — 400/415 с `detail`; неизвестный `job_id` — 404; вторая одновременная задача — 409; `GET /api/stats/{job_id}` — поля `job_id/entered/exited/current/status/error`.
- Загруженные файлы держать в `storage/uploads/` (уже в `.gitignore`).

**ML (`feature/ml-counter`):**
- Реэкспорт `VisitorCounter` из `ml/__init__.py` (или `ml/counter.py` / `ml/processor.py` — тесты ищут в этих местах).
- `process_frame` возвращает `(processed_frame, stats)` и **рисует на копии кадра** (тест проверяет, что входной кадр не изменился); `reset()` обнуляет счётчики; `bbox` — 4 `int`.

**Интегратору (`feature/integration`):**
1. После слияния прогнать `pytest` — сейчас **55 passed + 9 skipped** (8 ML-тестов и файл API-тестов целиком; собирается 63 теста). После появления `ml/` и `backend/` пропуски исчезнут, а к 63 собранным добавятся ещё 12 API-тестов; расхождения по контрактам нужно устранить.
2. Заполнить `reports/accuracy_manifest.json` фактическими числами по 3 видео и выполнить `python tests/benchmark_accuracy.py --manifest ... --out reports/accuracy_table.md`; таблицу из §3.4 вставить в `reports/00_FINAL_SUMMARY.md`.
3. На защите показывать только реальные замеры и явно называть условия (видео, разрешение, GPU/CPU, `CONF_THRESHOLD`), потому что ориентир ≤ 5% достижим не на любом «сложном» видео.

**Напоминание по Git:** работа сдаётся Pull Request'ом из `feature/devops-testing` в `main`. В `main` не коммитить и не пушить; слияние выполняет руководитель проекта.
