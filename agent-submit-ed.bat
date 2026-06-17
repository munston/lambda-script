@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\agent_folder_submit.py ed %*
exit /b %ERRORLEVEL%
