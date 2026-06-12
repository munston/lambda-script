@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Locate repo root from this script's location
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.."

if not exist "native\cppffi\ffi_demo.exe" (
    echo [ERROR] ffi_demo.exe not found. Run build-demo.bat first.
    popd
    exit /b 1
)

echo Running C++ FFI demo...
native\cppffi\ffi_demo.exe "{\"symbol\":\"ls_add_i32\",\"args\":[40,2]}"

echo.
echo Expected output contains: {"ok":true,"value":42}

popd
