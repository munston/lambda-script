@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\targeted_onepush_create.py %*
exit /b %ERRORLEVEL%
