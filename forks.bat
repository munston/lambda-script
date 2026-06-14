@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "scripts\forks\forks.py" (
  echo forks: missing scripts\forks\forks.py
  exit /b 1
)

if /I "%~1"=="import-json" goto import_json
if /I "%~1"=="land-json" goto land_json
if /I "%~1"=="land-json-file" goto land_json_file
if /I "%~1"=="gadget-init" goto gadget_init
if /I "%~1"=="gadget-status" goto gadget_status
if /I "%~1"=="gadget-sync" goto gadget_sync
if /I "%~1"=="gadget-sync-all" goto gadget_sync_all
if /I "%~1"=="gadget-land-json" goto gadget_land_json
if /I "%~1"=="gadget-land-json-file" goto gadget_land_json_file
if /I "%~1"=="gadget-promote" goto gadget_promote
if /I "%~1"=="capture" goto capture
if /I "%~1"=="submission-status" goto submission_status
if /I "%~1"=="replay" goto replay
if /I "%~1"=="verify-submission" goto verify_submission
if /I "%~1"=="submit-submission" goto submit_submission
if /I "%~1"=="submission-ship-plan" goto submission_ship_plan
if /I "%~1"=="sync-captured-lane" goto sync_captured_lane
if /I "%~1"=="plan" goto plan
if /I "%~1"=="run" goto run
if /I "%~1"=="land" goto land
if /I "%~1"=="sync-all" goto sync_all
if /I "%~1"=="verify-agent" goto verify_agent

python scripts\forks\forks.py %*
exit /b %errorlevel%

:import_json
shift
python scripts\forks\import_json_patch.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:land_json
shift
python scripts\forks\land_json_patch.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:land_json_file
shift
python scripts\forks\land_json_patch.py --require-file %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_init
shift
python scripts\forks\gadget_branches.py init %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_status
shift
python scripts\forks\gadget_branches.py status %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_sync
shift
python scripts\forks\gadget_branches.py sync %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_sync_all
shift
python scripts\forks\gadget_branches.py sync-all %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_land_json
shift
python scripts\forks\gadget_land_json.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_land_json_file
shift
python scripts\forks\gadget_land_json.py --require-file %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:gadget_promote
shift
python scripts\forks\gadget_promote.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:capture
shift
python scripts\forks\submission_object.py capture %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:submission_status
shift
python scripts\forks\submission_object.py status %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:replay
shift
python scripts\forks\submission_object.py replay %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:verify_submission
shift
python scripts\forks\submission_object.py verify %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:submit_submission
shift
python scripts\forks\submission_object.py submit %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:submission_ship_plan
shift
python scripts\forks\submission_object.py ship-plan %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:sync_captured_lane
shift
python scripts\forks\submission_object.py sync-lane %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:plan
shift
python scripts\forks\workflow_plan.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:run
shift
python scripts\forks\workflow_runner.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:land
shift
python scripts\forks\workflow_runner.py land %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:sync_all
shift
python scripts\forks\workflow_runner.py sync-all %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:verify_agent
shift
python scripts\forks\workflow_runner.py verify-agent %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%
