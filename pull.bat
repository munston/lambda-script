@echo off
setlocal
call "%~dp0scripts\git\pull-all.bat" %*
exit /b %errorlevel%
