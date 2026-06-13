@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "scripts\forks\forks.py" (
  echo forks: missing scripts\forks\forks.py
  exit /b 1
)

if /I "%~1"=="capture" (
  shift
  python scripts\forks\submission_object.py capture %*
  exit /b %errorlevel%
)

if /I "%~1"=="submission-status" (
  shift
  python scripts\forks\submission_object.py status %*
  exit /b %errorlevel%
)

if /I "%~1"=="replay" (
  shift
  python scripts\forks\submission_object.py replay %*
  exit /b %errorlevel%
)

if /I "%~1"=="verify-submission" (
  shift
  python scripts\forks\submission_object.py verify %*
  exit /b %errorlevel%
)

if /I "%~1"=="submit-submission" (
  shift
  python scripts\forks\submission_object.py submit %*
  exit /b %errorlevel%
)

if /I "%~1"=="submission-ship-plan" (
  shift
  python scripts\forks\submission_object.py ship-plan %*
  exit /b %errorlevel%
)

if /I "%~1"=="sync-captured-lane" (
  shift
  python scripts\forks\submission_object.py sync-lane %*
  exit /b %errorlevel%
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
