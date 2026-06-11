@echo off
setlocal
call "%~dp0pull.bat"
if errorlevel 1 exit /b %errorlevel%
python "%~dp0scripts\test\verify-interface.py"
exit /b %errorlevel%
