@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\agent_folder_submit.py eddy %*
exit /b %ERRORLEVEL%
