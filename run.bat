@echo off
rem ============================================================================
rem  visitor-counter: Windows launcher (cmd.exe).
rem  Messages are ASCII on purpose: a UTF-8 .bat with Cyrillic breaks cmd.exe
rem  line parsing (multibyte desync), so the Russian-friendly variant lives in
rem  start.ps1.
rem
rem  Usage:
rem     run.bat               - check environment and start uvicorn
rem     run.bat --check-only  - run the checks only, do not start the server
rem ============================================================================
setlocal EnableExtensions
cd /d "%~dp0"
title visitor-counter

set "CHECK_ONLY="
if /i "%~1"=="--check-only" set "CHECK_ONLY=1"

echo ============================================================
echo  visitor-counter: starting web application (Windows)
echo ============================================================
echo.

rem --- 1. Virtual environment -------------------------------------------------
if exist ".venv\Scripts\activate.bat" goto venv_ok
echo [warn] .venv not found - using system Python.
echo        Create it:  python -m venv .venv
echo        Install:    .venv\Scripts\python -m pip install -r requirements.txt
goto python_check

:venv_ok
call ".venv\Scripts\activate.bat"
echo [ok] Activated .venv

rem --- 1b. Optional .env ------------------------------------------------------
if not exist ".env" goto env_done
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%b"=="" if not defined %%a set "%%a=%%b"
)
echo [ok] Loaded variables from .env
:env_done

rem --- 2. Python in PATH ------------------------------------------------------
:python_check
where python >nul 2>&1
if errorlevel 1 goto no_python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto old_python
for /f "delims=" %%v in ('python --version 2^>^&1') do echo [ok] Interpreter: %%v

rem --- 3. Required libraries --------------------------------------------------
python -c "import importlib.util as u,sys; missing=[m for m in ('fastapi','uvicorn','cv2') if u.find_spec(m) is None]; print('[ok] fastapi, uvicorn, cv2 import fine' if not missing else '[error] Missing: '+', '.join(missing)); sys.exit(1 if missing else 0)"
if errorlevel 1 goto missing_deps

rem --- 4. PyTorch and CUDA (optional: mock mode works without it) -------------
python -c "import importlib.util as u,sys; sys.exit(0 if u.find_spec('torch') else 1)"
if errorlevel 1 goto no_torch
python -c "import torch; name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''; print('[ok] torch '+torch.__version__+(' | CUDA: '+name if name else ' | CUDA: not available, CPU mode'))"
goto backend_check

:no_torch
echo [warn] torch is not installed: the ML counter will not run (see requirements.txt).

rem --- 5. Backend module ------------------------------------------------------
:backend_check
python -c "import importlib.util as u,sys; sys.exit(0 if u.find_spec('backend.main') else 1)"
if errorlevel 1 goto no_backend

if defined CHECK_ONLY goto check_ok

rem --- 6. Run the server ------------------------------------------------------
if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8000"
echo.
echo [run] uvicorn backend.main:app --host %HOST% --port %PORT%
echo       Dashboard: http://%HOST%:%PORT%/
echo       Stop: Ctrl+C
echo.
python -m uvicorn backend.main:app --host %HOST% --port %PORT%
goto end

rem --- Error exits ------------------------------------------------------------
:no_python
echo [error] Python not found in PATH.
echo         Install Python 3.11+ from https://www.python.org/downloads/windows/
echo         Enable the "Add python.exe to PATH" checkbox during setup.
exit /b 1

:old_python
echo [error] Python 3.11 or newer is required (torch 2.x dropped older versions).
exit /b 1

:missing_deps
echo [hint] Install dependencies: python -m pip install -r requirements.txt
echo        With NVIDIA GPU install torch first:
echo        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
exit /b 1

:no_backend
echo [error] Module backend.main is missing - is feature/backend-api merged yet?
echo         Expected file: backend\main.py
if defined CHECK_ONLY goto check_ok
exit /b 1

:check_ok
echo.
echo [check-only] All checks passed, server was not started.
exit /b 0

:end
endlocal
