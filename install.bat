@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Locate repo root from script location
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo   LambdaScript Toolchain Installer
echo ========================================
echo.

:: Check prerequisites
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm is not installed or not in PATH.
    exit /b 1
)

where git >nul 2>nul
if errorlevel 1 (
    echo [WARNING] git was not found. Some features may be limited.
)

where g++ >nul 2>nul
if errorlevel 1 (
    echo [WARNING] g++ not found. C++ FFI demo will not be buildable.
)

echo [OK] Node.js and npm detected.
echo.

:: Install glc dependencies
echo [1/3] Installing dependencies in glc/...
pushd glc
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    exit /b 1
)
popd

echo [2/3] Building glc...
pushd glc
call npm exec -- tsc -p tsconfig.json
if errorlevel 1 (
    echo [ERROR] Build failed.
    popd
    exit /b 1
)
popd

echo [3/3] Running tests...
pushd glc
call npm test
if errorlevel 1 (
    echo [ERROR] Tests failed.
    popd
    exit /b 1
)
popd

echo.
echo ========================================
echo   Installation complete!
echo.
echo Next steps:
echo   cd glc
echo   npm run glc -- --help
echo ========================================
