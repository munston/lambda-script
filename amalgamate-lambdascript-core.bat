@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo amalgamate lambdascript/core start
git fetch origin --prune
if errorlevel 1 exit /b %errorlevel%

python scripts\forks\amalgamate_all.py --gadget lambdascript core --agents ed edd eddy guy --apply
if errorlevel 1 exit /b %errorlevel%

python scripts\forks\gadget_branches.py status lambdascript core
exit /b %errorlevel%
