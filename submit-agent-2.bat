@echo off
setlocal
set "B=agents/edd"
call "%~dp0scripts\git\submit-agent-to-main.bat" %B% verify.bat
exit /b %errorlevel%
