@echo off
setlocal
set "B=agent/edd"
call "%~dp0scripts\git\submit-agent-to-main.bat" %B% verify.bat
exit /b %errorlevel%
