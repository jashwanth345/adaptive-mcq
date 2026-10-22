@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m deployment.ai
if errorlevel 1 pause
