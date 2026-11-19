@echo off
REM ============================================================
REM  One-shot: stage -> commit -> push to GitHub
REM
REM  Usage:
REM    push.bat                          interactive, prompts for message
REM    push.bat "fix: 修复登录页样式"       use given message
REM ============================================================
setlocal
cd /d "%~dp0.."

if not "%~1"=="" goto HAVE_MSG
set /p MSG=Enter commit message: 
if "%MSG%"=="" set MSG=chore: update project
goto CONTINUE

:HAVE_MSG
set MSG=%~1

:CONTINUE
echo ============================================
echo  Changes to be committed:
echo ============================================
git status --short
echo.
echo  Commit message: %MSG%
echo.

echo [1/3] Staging changes...
git add -A

git diff --cached --quiet
if errorlevel 1 goto DO_COMMIT
echo [2/3] Nothing to commit, skipping.
goto DO_PUSH

:DO_COMMIT
echo [2/3] Committing...
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
