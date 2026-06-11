@echo off
setlocal
call "%~dp0scripts\git\push-all.bat" %*
exit /b %errorlevel%
