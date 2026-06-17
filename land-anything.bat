@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo usage: land-anything.bat ^<patch.json^>
  exit /b 2
)
python scripts\forks\land_anything.py "%~1"
exit /b %ERRORLEVEL%
