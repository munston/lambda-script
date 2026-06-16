@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "scripts\forks\forks.py" (
  echo forks: missing scripts\forks\forks.py
  exit /b 1
)

set "FORKS_COMMAND=%~1"
if "%FORKS_COMMAND%"=="" goto default_dispatch
shift /1

set "FORKS_ARGS="
:collect_args
if "%~1"=="" goto dispatch
set "FORKS_ARGS=%FORKS_ARGS% "%~1""
shift /1
goto collect_args

:dispatch
if /I "%FORKS_COMMAND%"=="import-json" goto import_json
if /I "%FORKS_COMMAND%"=="land-json" goto land_json
if /I "%FORKS_COMMAND%"=="land-json-file" goto land_json_file
if /I "%FORKS_COMMAND%"=="replay-plan" goto replay_plan
if /I "%FORKS_COMMAND%"=="replay-sync" goto replay_sync
if /I "%FORKS_COMMAND%"=="ensure-node-toolchains" goto ensure_node_toolchains
if /I "%FORKS_COMMAND%"=="gadget-init" goto gadget_init
if /I "%FORKS_COMMAND%"=="gadget-status" goto gadget_status
if /I "%FORKS_COMMAND%"=="gadget-sync" goto gadget_sync
if /I "%FORKS_COMMAND%"=="gadget-sync-all" goto gadget_sync_all
if /I "%FORKS_COMMAND%"=="gadget-land-json" goto gadget_land_json
if /I "%FORKS_COMMAND%"=="gadget-land-json-file" goto gadget_land_json_file
if /I "%FORKS_COMMAND%"=="gadget-promote" goto gadget_promote
if /I "%FORKS_COMMAND%"=="accelerator" goto accelerator
if /I "%FORKS_COMMAND%"=="capture" goto capture
if /I "%FORKS_COMMAND%"=="submission-status" goto submission_status
if /I "%FORKS_COMMAND%"=="replay" goto replay
if /I "%FORKS_COMMAND%"=="verify-submission" goto verify_submission
if /I "%FORKS_COMMAND%"=="submit-submission" goto submit_submission
if /I "%FORKS_COMMAND%"=="submission-ship-plan" goto submission_ship_plan
if /I "%FORKS_COMMAND%"=="sync-captured-lane" goto sync_captured_lane
if /I "%FORKS_COMMAND%"=="amalgamate-all" goto amalgamate_all
if /I "%FORKS_COMMAND%"=="plan" goto plan
if /I "%FORKS_COMMAND%"=="run" goto run
if /I "%FORKS_COMMAND%"=="land" goto land
if /I "%FORKS_COMMAND%"=="sync-all" goto sync_all
if /I "%FORKS_COMMAND%"=="verify-agent" goto verify_agent

python scripts\forks\forks.py "%FORKS_COMMAND%" %FORKS_ARGS%
exit /b %errorlevel%

:default_dispatch
python scripts\forks\forks.py
exit /b %errorlevel%

:import_json
python scripts\forks\import_json_patch.py %FORKS_ARGS%
exit /b %errorlevel%

:land_json
python scripts\forks\land_json_patch.py %FORKS_ARGS%
exit /b %errorlevel%

:land_json_file
python scripts\forks\land_json_patch.py --require-file %FORKS_ARGS%
exit /b %errorlevel%

:replay_plan
python scripts\forks\replay_plan.py %FORKS_ARGS%
exit /b %errorlevel%

:replay_sync
python scripts\forks\replay_sync.py %FORKS_ARGS%
exit /b %errorlevel%

:ensure_node_toolchains
python scripts\forks\ensure_node_toolchains.py %FORKS_ARGS%
exit /b %errorlevel%

:gadget_init
python scripts\forks\gadget_branches.py init %FORKS_ARGS%
exit /b %errorlevel%

:gadget_status
python scripts\forks\gadget_branches.py status %FORKS_ARGS%
exit /b %errorlevel%

:gadget_sync
python scripts\forks\gadget_branches.py sync %FORKS_ARGS%
exit /b %errorlevel%

:gadget_sync_all
python scripts\forks\gadget_branches.py sync-all %FORKS_ARGS%
exit /b %errorlevel%

:gadget_land_json
python scripts\forks\gadget_land_json.py %FORKS_ARGS%
exit /b %errorlevel%

:gadget_land_json_file
python scripts\forks\gadget_land_json.py --require-file %FORKS_ARGS%
exit /b %errorlevel%

:gadget_promote
python scripts\forks\gadget_promote.py %FORKS_ARGS%
exit /b %errorlevel%

:accelerator
python scripts\forks\accelerator.py %FORKS_ARGS%
exit /b %errorlevel%

:capture
python scripts\forks\submission_object.py capture %FORKS_ARGS%
exit /b %errorlevel%

:submission_status
python scripts\forks\submission_object.py status %FORKS_ARGS%
exit /b %errorlevel%

:replay
python scripts\forks\submission_object.py replay %FORKS_ARGS%
exit /b %errorlevel%

:verify_submission
python scripts\forks\submission_object.py verify %FORKS_ARGS%
exit /b %errorlevel%

:submit_submission
python scripts\forks\submission_object.py submit %FORKS_ARGS%
exit /b %errorlevel%

:submission_ship_plan
python scripts\forks\submission_object.py ship-plan %FORKS_ARGS%
exit /b %errorlevel%

:sync_captured_lane
python scripts\forks\submission_object.py sync-lane %FORKS_ARGS%
exit /b %errorlevel%

:amalgamate_all
python scripts\forks\amalgamate_all.py %FORKS_ARGS%
exit /b %errorlevel%

:plan
python scripts\forks\workflow_plan.py %FORKS_ARGS%
exit /b %errorlevel%

:run
python scripts\forks\workflow_runner.py %FORKS_ARGS%
exit /b %errorlevel%

:land
python scripts\forks\workflow_runner.py land %FORKS_ARGS%
exit /b %errorlevel%

:sync_all
python scripts\forks\workflow_runner.py sync-all %FORKS_ARGS%
exit /b %errorlevel%

:verify_agent
python scripts\forks\workflow_runner.py verify-agent %FORKS_ARGS%
exit /b %errorlevel%
