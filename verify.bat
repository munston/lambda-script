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

echo [1/3] Building project...
pushd glc
call npm run build
if errorlevel 1 (
    echo [ERROR] Build failed.
    popd
    exit /b 1
)
popd

echo [2/3] Running tests...
pushd glc
call npm test
if errorlevel 1 (
    echo [ERROR] Tests failed.
    popd
    exit /b 1
)
popd

echo.
echo [3/3] Running CLI smoke commands...
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

call npm run glc -- parse ../examples/milk_metric.ls --json
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

call npm run glc -- emit ../examples/hello.ls --target py >nul 2>nul
if not errorlevel 1 (
    echo [ERROR] Python emission unexpectedly succeeded for hello.ls.
    popd
    exit /b 1
)

call npm run glc -- emit ../examples/ffi_cpp.ls --target py >nul 2>nul
if not errorlevel 1 (
    echo [ERROR] Python emission unexpectedly succeeded for ffi_cpp.ls.
    popd
    exit /b 1
)

popd

where python >nul 2>nul
if not errorlevel 1 (
    echo.
    echo Checking repository Python tooling syntax...
    for %%F in (scripts\forks\forks.py tools\milk_metrics\milk_metrics\*.py) do (
        python -m py_compile "%%F"
        if errorlevel 1 (
            echo [ERROR] Python tooling syntax check failed: %%F
            exit /b 1
        )
    )
) else (
    echo [WARNING] python not found. Skipping repository Python tooling syntax check.
)

echo.
echo ========================================
echo   All verifications passed!
echo ========================================
