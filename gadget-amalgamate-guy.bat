@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\gadget_amalgamate_agent.py guy %*
exit /b %ERRORLEVEL%
