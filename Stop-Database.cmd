@echo off
cd /d "%~dp0"
echo Stop the website with Ctrl+C before stopping the database.
".venv\Scripts\python.exe" -m deployment.native stop
if errorlevel 1 pause
exit /b %errorlevel%
