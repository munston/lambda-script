@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\gadget_amalgamate_agent.py eddy %*
exit /b %ERRORLEVEL%
