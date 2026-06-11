@echo off
setlocal
cd /d "%~dp0..\..\glc"
npm install
npm run build
endlocal
