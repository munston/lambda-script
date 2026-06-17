@echo off
setlocal

cd /d "%~dp0"
cabal run installation_script.hs
