@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
set "PKG=%ROOT%tools\image_metrics"
pushd "%PKG%"
call npm run build --silent
set "BUILD_STATUS=%ERRORLEVEL%"
popd
if not "%BUILD_STATUS%"=="0" exit /b %BUILD_STATUS%
node "%PKG%\dist\src\cli.js" %*
exit /b %errorlevel%
