@echo off
setlocal
cd /d "%~dp0..\.."
git status --short --branch
endlocal
