@echo off
setlocal
cd /d "%~dp0..\.."

if exist "glc\backend\ffi\test\test_python_ffi.py" (
  python "glc\backend\ffi\test\test_python_ffi.py"
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo no FFI smoke test found; skipping
)

exit /b 0
