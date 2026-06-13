@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "scripts\forks\forks.py" (
  echo forks: missing scripts\forks\forks.py
  exit /b 1
)

if /I "%~1"=="plan" (
  shift
  python scripts\forks\workflow_plan.py %*
  exit /b %errorlevel%
)

if /I "%~1"=="run" (
  python scripts\forks\workflow_runner.py %*
  exit /b %errorlevel%
)

if /I "%~1"=="land" (
  shift
  python scripts\forks\workflow_runner.py land %*
  exit /b %errorlevel%
)

if /I "%~1"=="sync-all" (
  python scripts\forks\workflow_runner.py sync-all
  exit /b %errorlevel%
)

if /I "%~1"=="verify-agent" (
  shift
  python scripts\forks\workflow_runner.py verify-agent %*
  exit /b %errorlevel%
)

python scripts\forks\forks.py %*
exit /b %errorlevel%
