@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "scripts\forks\forks.py" (
  echo forks: missing scripts\forks\forks.py
  exit /b 1
)

if not exist "scripts\forks\forks_dispatch.py" (
  echo forks: missing scripts\forks\forks_dispatch.py
  exit /b 1
)

python scripts\forks\forks_dispatch.py %*
exit /b %errorlevel%
