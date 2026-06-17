@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\agent_amalgamate_agent.py edd %*
exit /b %ERRORLEVEL%
