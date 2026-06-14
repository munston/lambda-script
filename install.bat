@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo   LambdaScript Toolchain Installer
echo ========================================
echo.

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

echo [1/4] Establishing local Node/TypeScript toolchains...
python scripts\forks\ensure_node_toolchains.py --install
if errorlevel 1 (
    echo [ERROR] Node/TypeScript toolchain setup failed.
    exit /b 1
)

echo [2/4] Building glc...
pushd glc
call npm run build
if errorlevel 1 (
    echo [ERROR] glc build failed.
    popd
    exit /b 1
)
popd

echo [3/4] Running glc tests...
pushd glc
call npm test
if errorlevel 1 (
    echo [ERROR] glc tests failed.
    popd
    exit /b 1
)
popd

echo [4/4] Checking optional tool builds...
if exist "tools\gizmo\package.json" (
    pushd tools\gizmo
    call npm run build
    if errorlevel 1 (
        echo [ERROR] gizmo build failed.
        popd
        exit /b 1
    )
    popd
)

echo.
echo ========================================
echo   Installation complete!
echo.
echo Next steps:
echo   cd glc
echo   npm run glc -- --help
echo ========================================
