@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Locate repo root from script location
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo   LambdaScript Toolchain Verifier
echo ========================================
echo.

set "SHARED_GLC_NODE_MODULES="
if not exist "glc\node_modules" (
    set "CANDIDATE_SHARED_GLC_NODE_MODULES=%ROOT%..\..\..\glc\node_modules"
    for %%I in ("!CANDIDATE_SHARED_GLC_NODE_MODULES!") do set "CANDIDATE_SHARED_GLC_NODE_MODULES=%%~fI"
    if exist "!CANDIDATE_SHARED_GLC_NODE_MODULES!" (
        set "SHARED_GLC_NODE_MODULES=!CANDIDATE_SHARED_GLC_NODE_MODULES!"
        echo [INFO] Reusing glc dependencies from main checkout.
        echo [INFO] !SHARED_GLC_NODE_MODULES!
    )
)

if not exist "glc\node_modules" if not defined SHARED_GLC_NODE_MODULES (
    echo [ERROR] glc dependencies are not installed.
    echo Run install.bat from the repo root first.
    exit /b 1
)

echo [1/3] Building project...
pushd glc
if defined SHARED_GLC_NODE_MODULES (
    call "!SHARED_GLC_NODE_MODULES!\.bin\tsc.cmd" -p tsconfig.json
) else (
    call npm run build
)
if errorlevel 1 (
    echo [ERROR] Build failed.
    popd
    exit /b 1
)
popd

echo [2/3] Running tests...
pushd glc
if defined SHARED_GLC_NODE_MODULES (
    call "!SHARED_GLC_NODE_MODULES!\.bin\tsc.cmd" -p tsconfig.json
    if errorlevel 1 (
        echo [ERROR] Test build failed.
        popd
        exit /b 1
    )
    call node dist/test/smoke.js
) else (
    call npm test
)
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

if defined SHARED_GLC_NODE_MODULES (
    set "GLC_CMD=node dist/src/cli/main.js"
) else (
    set "GLC_CMD=npm run glc --"
)

call !GLC_CMD! parse ../examples/hello.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/hello.ls --target ts
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/hello.ls --target hs
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! parse ../examples/milk_metric.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! parse ../examples/ffi_cpp.ls --json
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! check ../examples/ffi_cpp.ls
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/ffi_cpp.ls --target ts
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/ffi_cpp.ls --target hs
if errorlevel 1 (
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/hello.ls --target py >nul 2>nul
if not errorlevel 1 (
    echo [ERROR] Python emission unexpectedly succeeded for hello.ls.
    popd
    exit /b 1
)

call !GLC_CMD! emit ../examples/ffi_cpp.ls --target py >nul 2>nul
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
