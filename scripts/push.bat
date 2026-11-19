@echo off
REM ============================================================
REM  One-shot: stage -> commit -> push to GitHub
REM  Usage:
REM    push.bat                      (default commit message)
REM    push.bat "fix: 修复登录页样式"   (custom commit message)
REM ============================================================
setlocal
cd /d "%~dp0.."

set MSG=%~1
if "%MSG%"=="" set MSG=chore: update project

echo ============================================
echo  Changes to be committed:
echo ============================================
git status --short
echo.

echo [1/3] Staging changes...
git add -A

git diff --cached --quiet
if errorlevel 1 goto DO_COMMIT
echo [2/3] Nothing to commit, skipping.
goto DO_PUSH

:DO_COMMIT
echo [2/3] Committing: %MSG%
git commit -m "%MSG%"
if errorlevel 1 goto FAILED
echo.

:DO_PUSH
echo [3/3] Pushing to origin main...
git push origin main
if errorlevel 1 goto FAILED
echo.
echo [OK] Pushed successfully.
goto END

:FAILED
echo.
echo [FAILED] See the error message above.
echo         If it is a network error, just run this file again.

:END
echo.
pause
endlocal
