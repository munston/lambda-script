@echo off
setlocal
cd /d "%~dp0..\.."
python glc\backend\ffi\test\test_python_ffi.py
endlocal
