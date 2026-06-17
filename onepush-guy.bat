@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\onepush_agent.py guy %*
exit /b %ERRORLEVEL%
