@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\onepush_agent.py eddy %*
exit /b %ERRORLEVEL%
