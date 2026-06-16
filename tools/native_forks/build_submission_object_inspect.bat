@echo off
setlocal EnableExtensions

set "ROOT=%~dp0\..\.."
set "SRC=%ROOT%\tools\native_forks\submission_object_inspect.cpp"
set "OUTDIR=%ROOT%\tools\native_forks\bin"
set "OUT=%OUTDIR%\submission_object_inspect.exe"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

set "CXX=g++"
where g++ >nul 2>nul
if errorlevel 1 (
  if exist "C:\ghcup\msys64\ucrt64\bin\g++.exe" set "CXX=C:\ghcup\msys64\ucrt64\bin\g++.exe"
)

"%CXX%" "%SRC%" -std=c++17 -O2 -Wall -Wextra -o "%OUT%"
if errorlevel 1 exit /b 1

echo built %OUT%
