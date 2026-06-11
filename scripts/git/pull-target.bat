@echo off
setlocal

set "NAME=%~1"
set "DIR=%~2"
set "REMOTE=%~3"
set "BRANCH=%~4"

if "%NAME%"=="" exit /b 2
if "%DIR%"=="" exit /b 2
if "%REMOTE%"=="" set "REMOTE=origin"
if "%BRANCH%"=="" set "BRANCH=main"

if not exist "%DIR%\.git" (
  echo [%NAME%] not a git repository: "%DIR%"
  exit /b 1
)

echo.
echo [%NAME%] status before pull
git -C "%DIR%" status --short --branch
if errorlevel 1 exit /b %errorlevel%

echo.
echo [%NAME%] fetch %REMOTE%
git -C "%DIR%" fetch "%REMOTE%"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [%NAME%] pull --ff-only %REMOTE% %BRANCH%
git -C "%DIR%" pull --ff-only "%REMOTE%" "%BRANCH%"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [%NAME%] status after pull
git -C "%DIR%" status --short --branch
exit /b %errorlevel%
