@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Locate repo root from this script's location
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.."

echo Building C++ FFI demo...

where g++ >nul 2>nul
if errorlevel 1 (
    echo [ERROR] g++ not found in PATH.
    echo Please install MinGW-w64 or MSYS2 g++.
    popd
    exit /b 1
)

g++ -std=c++17 -O2 native\cppffi\ffi_demo.cpp -o native\cppffi\ffi_demo.exe

if errorlevel 1 (
    echo [ERROR] Failed to compile ffi_demo.cpp
    popd
    exit /b 1
) else (
    echo [OK] Built native\cppffi\ffi_demo.exe
)

popd
