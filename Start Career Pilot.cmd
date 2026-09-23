@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_local.py
) else (
  py -3 run_local.py
)
if errorlevel 1 (
  echo.
  echo Startup failed. Read the error above. Python 3.12+ and Node.js 22+ must be installed.
  pause
)
