@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\onepush_agent.py ed %*
exit /b %ERRORLEVEL%
