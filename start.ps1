#Requires -Version 5.1
<#
.SYNOPSIS
    Запуск visitor-counter на Windows: проверка окружения, CUDA и старт uvicorn.

.DESCRIPTION
    Скрипт делает то же, что run.bat, но с дополнительными возможностями:
    - читает .env (если файл есть) и подхватывает HOST/PORT/MODEL_PATH и другие переменные;
    - умеет работать в режиме только-проверки (-CheckOnly): удобно для диагностики;
    - позволяет задать адрес и порт параметрами.

.PARAMETER BindHost
    Адрес сервера. По умолчанию берётся из .env, иначе 127.0.0.1.

.PARAMETER Port
    Порт сервера. По умолчанию берётся из .env, иначе 8000.

.PARAMETER CheckOnly
    Выполнить проверки и выйти, не запуская сервер.

.PARAMETER SkipDependencyCheck
    Пропустить проверку импортов fastapi/uvicorn/cv2.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\start.ps1

.EXAMPLE
    .\start.ps1 -CheckOnly

.EXAMPLE
    .\start.ps1 -Port 8080 -BindHost 0.0.0.0
#>
[CmdletBinding()]
param(
    [string]$BindHost,
    [int]$Port = 0,
    [switch]$CheckOnly,
    [switch]$SkipDependencyCheck
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Write-Ok {
    param([string]$Message)
    Write-Host "[ok] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[warn] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[error] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message
}

Write-Info '============================================================'
Write-Info ' visitor-counter: запуск веб-приложения (Windows, PowerShell)'
Write-Info '============================================================'

# --- 1. Переменные окружения из .env ---------------------------------------
$envFile = Join-Path $PSScriptRoot '.env'
if (Test-Path -LiteralPath $envFile) {
    $loaded = 0
    foreach ($rawLine in (Get-Content -LiteralPath $envFile -Encoding UTF8)) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $separator = $line.IndexOf('=')
        if ($separator -lt 1) { continue }
        $key = $line.Substring(0, $separator).Trim()
        $value = $line.Substring($separator + 1).Trim().Trim('"').Trim("'")
        if (-not $key) { continue }
        if (-not (Test-Path -LiteralPath "Env:$key")) {
            Set-Item -LiteralPath "Env:$key" -Value $value
            $loaded++
        }
    }
    Write-Ok "Прочитан .env (добавлено переменных: $loaded)"
}
else {
    Write-Warn 'Файл .env не найден - используются значения по умолчанию (см. .env.example)'
}

# --- 2. Python из .venv или системный --------------------------------------
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
    Write-Ok 'Используется окружение .venv'
}
else {
    $python = 'python'
    Write-Warn 'Папка .venv не найдена - используется системный Python.'
    Write-Info '       Создать окружение: python -m venv .venv'
    Write-Info '       Поставить пакеты:  .venv\Scripts\python -m pip install -r requirements.txt'
}

$versionOutput = & $python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail 'Python не найден в PATH. Установите Python 3.11+ с python.org (галочка "Add python.exe to PATH").'
    exit 1
}
Write-Ok "Интерпретатор: $versionOutput"

$versionOk = & $python -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)"
if ("$versionOk".Trim() -ne '1') {
    Write-Fail 'Нужен Python 3.11 или новее (torch 2.x не поддерживает более старые версии).'
    exit 1
}

# --- 3. Импорты ------------------------------------------------------------
if (-not $SkipDependencyCheck) {
    $missing = & $python -c "import importlib.util as u; print(','.join(m for m in ('fastapi','uvicorn','cv2') if u.find_spec(m) is None))"
    if ($LASTEXITCODE -ne 0) {
        Write-Fail 'Не удалось выполнить проверку импортов.'
        exit 1
    }
    $missingText = "$missing".Trim()
    if ($missingText) {
        Write-Fail "Не установлены: $missingText"
        Write-Info '       Установите: .venv\Scripts\python -m pip install -r requirements.txt'
        exit 1
    }
    Write-Ok 'Импорты в порядке: fastapi, uvicorn, cv2'
}

# --- 4. PyTorch / CUDA -----------------------------------------------------
$hasTorch = & $python -c "import importlib.util as u; print(1 if u.find_spec('torch') else 0)"
if ("$hasTorch".Trim() -ne '1') {
    Write-Warn 'torch не установлен: ML-модуль работать не будет (см. requirements.txt).'
}
else {
    $torchInfo = & $python -c "import torch; name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''; print(torch.__version__ + ';' + name)"
    if ($LASTEXITCODE -eq 0) {
        $parts = "$torchInfo".Trim().Split(';')
        $torchVersion = $parts[0]
        if ($parts.Length -gt 1 -and $parts[1]) {
            Write-Ok "torch $torchVersion | CUDA: $($parts[1])"
        }
        else {
            Write-Warn "torch $torchVersion | CUDA не найдена: инференс пойдёт на CPU (это нормально без NVIDIA GPU)"
        }
    }
    else {
        Write-Warn 'Не удалось опросить torch (CUDA/драйвер). Приложение попробует CPU.'
    }
}

# --- 5. Backend ------------------------------------------------------------
$hasBackend = & $python -c "import importlib.util as u; print(1 if u.find_spec('backend.main') else 0)"
if ("$hasBackend".Trim() -ne '1') {
    Write-Fail 'Модуль backend.main не найден: ветка feature/backend-api ещё не слита?'
    Write-Info '       Ожидается файл: backend\main.py'
    if (-not $CheckOnly) { exit 1 }
}
else {
    Write-Ok 'backend.main найден'
}

# --- 6. Итог / запуск ------------------------------------------------------
if ($CheckOnly) {
    Write-Info ''
    Write-Ok 'Режим -CheckOnly: проверки пройдены, сервер не запускался.'
    exit 0
}

if (-not $BindHost) {
    if ($env:HOST) { $BindHost = $env:HOST } else { $BindHost = '127.0.0.1' }
}
if ($Port -le 0) {
    if ($env:PORT) { $Port = [int]$env:PORT } else { $Port = 8000 }
}

Write-Info ''
Write-Info "[run] uvicorn backend.main:app --host $BindHost --port $Port"
Write-Info "      Дашборд: http://${BindHost}:$Port/"
Write-Info '      Остановка: Ctrl+C'
Write-Info ''

& $python -m uvicorn backend.main:app --host $BindHost --port $Port
exit $LASTEXITCODE
