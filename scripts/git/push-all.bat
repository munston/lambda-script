@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "CONFIG=%ROOT%\git.config"
set "MESSAGE=%~1"
set "SELECT=%~2"

if "%MESSAGE%"=="" (
  set "MESSAGE=Update lambda-script"
)

if not exist "%CONFIG%" (
  echo missing git.config at "%CONFIG%"
  exit /b 1
)

set "FAILED=0"

for /f "usebackq tokens=1-5 delims=|" %%A in ("%CONFIG%") do (
  set "NAME=%%~A"
  set "PATH_PART=%%~B"
  set "REMOTE=%%~C"
  set "BRANCH=%%~D"
  set "TEST=%%~E"
  if not "!NAME!"=="" if not "!NAME:~0,1!"=="#" (
    if "%SELECT%"=="" (
      call "%~dp0push-target.bat" "!NAME!" "%ROOT%\!PATH_PART!" "!REMOTE!" "!BRANCH!" "!TEST!" "%MESSAGE%"
      if errorlevel 1 set "FAILED=1"
    ) else if /i "%SELECT%"=="!NAME!" (
      call "%~dp0push-target.bat" "!NAME!" "%ROOT%\!PATH_PART!" "!REMOTE!" "!BRANCH!" "!TEST!" "%MESSAGE%"
      if errorlevel 1 set "FAILED=1"
    )
  )
)

if "%FAILED%"=="1" exit /b 1
exit /b 0
