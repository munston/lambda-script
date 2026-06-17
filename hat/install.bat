@echo off
setlocal

cd /d "%~dp0"
cabal run src/hat -- installation_script.hat
