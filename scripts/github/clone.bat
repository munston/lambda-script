@echo off
setlocal
if "%~1"=="" (
  echo usage: clone.bat TARGET_DIRECTORY
  exit /b 2
)
git clone https://github.com/munston/lambda-script.git "%~1"
endlocal
