@echo off
cd /d "%~dp0"
if exist "models\ollama\manifests\registry.ollama.ai\library\qwen2.5\0.5b-instruct-q4_K_M" goto localai
".venv\Scripts\python.exe" -m deployment.native start
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m deployment.local start
if errorlevel 1 goto failed
exit /b 0
:localai
".venv\Scripts\python.exe" -m deployment.ai
if errorlevel 1 goto failed
exit /b 0
:failed
echo Startup did not complete. See docs\local-deployment.md and the local logs.
pause
exit /b 1
