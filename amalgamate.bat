@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

python scripts\forks\amalgamate_targets.py %*
exit /b %errorlevel%
