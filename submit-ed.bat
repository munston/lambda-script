@echo off
setlocal
call "%~dp0scripts\git\submit-agent-to-main.bat" agent/ed verify.bat
exit /b %errorlevel%
