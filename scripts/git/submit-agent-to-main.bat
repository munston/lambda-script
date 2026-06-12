@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "AGENT_BRANCH=%~1"
set "VERIFY_SCRIPT=%~2"
set "REMOTE=origin"
set "MAIN_BRANCH=main"
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

if "%AGENT_BRANCH%"=="" (
  echo usage: scripts\git\submit-agent-to-main.bat agent/name [verify-script]
  exit /b 2
)

if "%VERIFY_SCRIPT%"=="" set "VERIFY_SCRIPT=verify.bat"

echo.
echo [submit] root: "%ROOT%"
echo [submit] agent branch: %AGENT_BRANCH%
echo [submit] target: %REMOTE%/%MAIN_BRANCH%

git -C "%ROOT%" rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [submit] not a git repository: "%ROOT%"
  exit /b 1
)

for /f "delims=" %%B in ('git -C "%ROOT%" branch --show-current') do set "CURRENT_BRANCH=%%B"
if not "%CURRENT_BRANCH%"=="%AGENT_BRANCH%" (
  echo [submit] refusing: current branch is "%CURRENT_BRANCH%", expected "%AGENT_BRANCH%".
  echo [submit] checkout the agent branch first.
  exit /b 1
)

echo.
echo [submit] fetch latest %REMOTE%/%MAIN_BRANCH%
git -C "%ROOT%" fetch "%REMOTE%" "%MAIN_BRANCH%"
if errorlevel 1 exit /b %errorlevel%

for /f "delims=" %%H in ('git -C "%ROOT%" rev-parse "%REMOTE%/%MAIN_BRANCH%"') do set "MAIN_HASH=%%H"
for /f "delims=" %%H in ('git -C "%ROOT%" rev-parse HEAD') do set "HEAD_HASH=%%H"
for /f "delims=" %%T in ('git -C "%ROOT%" rev-parse HEAD^{tree}') do set "TREE_HASH=%%T"

echo [submit] observed %REMOTE%/%MAIN_BRANCH% commit: %MAIN_HASH%
echo [submit] local HEAD commit:              %HEAD_HASH%
echo [submit] local tree hash:                %TREE_HASH%

echo.
echo [submit] checking working tree is clean
git -C "%ROOT%" diff --quiet
if errorlevel 1 (
  echo [submit] refusing: unstaged changes exist. Commit or discard them first.
  git -C "%ROOT%" status --short
  exit /b 1
)
git -C "%ROOT%" diff --cached --quiet
if errorlevel 1 (
  echo [submit] refusing: staged changes exist. Commit or unstage them first.
  git -C "%ROOT%" status --short
  exit /b 1
)

echo.
echo [submit] checking %REMOTE%/%MAIN_BRANCH% is an ancestor of HEAD
git -C "%ROOT%" merge-base --is-ancestor "%REMOTE%/%MAIN_BRANCH%" HEAD
if errorlevel 1 (
  echo [submit] refusing: %AGENT_BRANCH% is not based on latest %REMOTE%/%MAIN_BRANCH%.
  echo [submit] update the agent branch first, for example:
  echo         git fetch %REMOTE%
  echo         git checkout %AGENT_BRANCH%
  echo         git rebase %REMOTE%/%MAIN_BRANCH%
  exit /b 1
)

if not "%VERIFY_SCRIPT%"=="-" (
  if not exist "%ROOT%\%VERIFY_SCRIPT%" (
    echo [submit] refusing: verify script not found: "%ROOT%\%VERIFY_SCRIPT%"
    exit /b 1
  )
  echo.
  echo [submit] verify: %VERIFY_SCRIPT%
  call "%ROOT%\%VERIFY_SCRIPT%"
  if errorlevel 1 (
    echo [submit] refusing: verification failed.
    exit /b %errorlevel%
  )
)

echo.
echo [submit] pushing HEAD to %REMOTE%/%MAIN_BRANCH% as a fast-forward-only update
echo [submit] no force flag is used; if main moved, Git will reject this push.
git -C "%ROOT%" push "%REMOTE%" HEAD:"%MAIN_BRANCH%"
if errorlevel 1 (
  echo [submit] push rejected or failed. Fetch/rebase/test, then retry.
  exit /b %errorlevel%
)

echo.
echo [submit] success. %AGENT_BRANCH% has been submitted to %REMOTE%/%MAIN_BRANCH%.
exit /b 0
