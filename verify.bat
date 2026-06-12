@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Locate repo root from script location
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo   LambdaScript Toolchain Verifier
echo ========================================
echo.

if not exist "glc\node_modules" (
    echo [ERROR] glc dependencies are not installed.
    echo Run install.bat from the repo root first.
    exit /b 1
)

echo [1/2] Building project...
pushd glc
call npm run build
if errorlevel 1 (
    echo [ERROR] Build failed.
    popd
    exit /b 1
)
popd

echo [2/2] Running tests...
pushd glc
call npm test
if errorlevel 1 (
    echo [ERROR] Tests failed.
    popd
    exit /b 1
)
popd

echo.
echo Running CLI smoke commands...
echo.

pushd glc

call npm run glc -- parse ../examples/hello.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/hello.ls --target ts
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/hello.ls --target hs
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/hello.ls --target py
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- parse ../examples/milk_metric.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/milk_metric.ls --target py
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- parse ../examples/ffi_cpp.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- check ../examples/ffi_cpp.ls
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/ffi_cpp.ls --target ts
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/ffi_cpp.ls --target hs
if errorlevel 1 (
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/ffi_cpp.ls --target py
if errorlevel 1 (
    popd
    exit /b 1
)

popd

where python >nul 2>nul
if not errorlevel 1 (
    echo Running milk metric tool smoke command...
    echo {"features":{"self_possession":1,"consent_signal":1,"surface_auditability":1,"whole_person_presence":1}} | python tools\milk_metric.py
    if errorlevel 1 (
        exit /b 1
    )
) else (
    echo [WARNING] python not found. Skipping milk metric tool smoke command.
)

echo.
echo ========================================
echo   All verifications passed!
echo ========================================
