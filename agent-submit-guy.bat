@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\agent_folder_submit.py guy %*
exit /b %ERRORLEVEL%
