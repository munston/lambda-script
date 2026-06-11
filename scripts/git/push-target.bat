@echo off
setlocal

set "NAME=%~1"
set "DIR=%~2"
set "REMOTE=%~3"
set "BRANCH=%~4"
set "TEST=%~5"
set "MESSAGE=%~6"

if "%NAME%"=="" exit /b 2
if "%DIR%"=="" exit /b 2
if "%REMOTE%"=="" set "REMOTE=origin"
if "%BRANCH%"=="" set "BRANCH=main"
if "%MESSAGE%"=="" exit /b 2

if not exist "%DIR%\.git" (
  echo [%NAME%] not a git repository: "%DIR%"
  exit /b 1
)

echo.
echo [%NAME%] status before push
git -C "%DIR%" status --short --branch
if errorlevel 1 exit /b %errorlevel%

echo.
echo [%NAME%] fetch %REMOTE%
git -C "%DIR%" fetch "%REMOTE%"
if errorlevel 1 exit /b %errorlevel%

if not "%TEST%"=="-" if not "%TEST%"=="" (
  if exist "%DIR%\%TEST%" (
    echo.
    echo [%NAME%] test %TEST%
    call "%DIR%\%TEST%"
    if errorlevel 1 exit /b %errorlevel%
  ) else (
    echo [%NAME%] configured test script not found: "%DIR%\%TEST%"
    exit /b 1
  )
)

echo.
echo [%NAME%] stage all
git -C "%DIR%" add -A
if errorlevel 1 exit /b %errorlevel%

git -C "%DIR%" diff --cached --quiet
if errorlevel 1 (
  echo.
  echo [%NAME%] commit
  git -C "%DIR%" commit -m "%MESSAGE%"
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo.
  echo [%NAME%] no staged changes; push will still publish existing local commits if any
)

echo.
echo [%NAME%] push %REMOTE% HEAD:%BRANCH%
git -C "%DIR%" push "%REMOTE%" HEAD:"%BRANCH%"
exit /b %errorlevel%
