@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%"
if "%~1"=="" (
  echo usage: edd-land-json.bat path\to\targeted_patch.json
  exit /b 1
)
python scripts\forks\agent_land_json.py edd "%~1"
exit /b %errorlevel%
