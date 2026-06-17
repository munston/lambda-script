@echo off
setlocal
cd /d "%~dp0"
python scripts\forks\land_anything.py %*
exit /b %ERRORLEVEL%
