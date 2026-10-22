@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m deployment.native start
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m deployment.native create-teacher
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo Teacher creation did not complete. Review the message above.
pause
exit /b 1
