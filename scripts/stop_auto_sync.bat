@echo off
REM ============================================================
REM  Stop the auto-sync daemon
REM ============================================================
setlocal
cd /d "%~dp0.."

if not exist "logs\auto_sync.lock" (
    echo [auto-sync] Not running.
    exit /b 0
)

set /p PID=<"logs\auto_sync.lock"
if "%PID%"=="" (
    echo [auto-sync] Lock file is empty, removing it.
    del "logs\auto_sync.lock" >nul 2>&1
    exit /b 0
)

taskkill /PID %PID% /F >nul 2>&1
if errorlevel 1 (
    echo [auto-sync] Process %PID% not found, cleaning up lock file.
) else (
    echo [auto-sync] Stopped process %PID%.
)
del "logs\auto_sync.lock" >nul 2>&1
endlocal
