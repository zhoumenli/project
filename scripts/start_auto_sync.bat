@echo off
REM ============================================================
REM  Start the auto-sync daemon (background, minimized window)
REM  Usage:  start_auto_sync.bat  [extra args passed to auto_sync.py]
REM  Logs:   logs\auto_sync.log
REM ============================================================
setlocal
cd /d "%~dp0.."

set "PY=C:\python\python.exe"
if not exist "%PY%" set "PY=python"

REM If a daemon is already running, do nothing.
if exist "logs\auto_sync.lock" (
    echo [auto-sync] Already running. Use stop_auto_sync.bat to stop it.
    exit /b 0
)

start "auto-sync" /min "%PY%" "%~dp0auto_sync.py" %*

timeout /t 2 /nobreak >nul
if exist "logs\auto_sync.lock" (
    echo [auto-sync] Started in background. Log: logs\auto_sync.log
) else (
    echo [auto-sync] Failed to start. Check logs\auto_sync.log
)
endlocal
