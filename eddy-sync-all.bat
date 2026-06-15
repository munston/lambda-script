@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo replay plan
call forks.bat replay-plan --fail-unsafe
if errorlevel 1 exit /b %errorlevel%

echo replay sync dry-run
call forks.bat replay-sync --dry-run --only-replay-needed --verify-command "verify.bat" --fail-failed %*
if errorlevel 1 exit /b %errorlevel%

echo replay sync apply
call forks.bat replay-sync --apply --only-replay-needed --verify-command "verify.bat" --fail-failed %*
exit /b %errorlevel%
