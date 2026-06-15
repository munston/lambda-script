@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
cd /d "%ROOT%tools\image_metrics"
call npm run image-metrics -- %*
exit /b %errorlevel%
