@echo off
title Chemkonnect Global - B2B AI Sales Portal
cd /d "%~dp0"
cls
echo ====================================================================
echo    CHEMKONNECT GLOBAL - B2B AI SALES PORTAL
echo    Opening Web Dashboard at: http://127.0.0.1:5000
echo ====================================================================
echo.

set "PATH=%USERPROFILE%\.local\bin;%PATH%"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

echo Starting Chemkonnect Sales Portal on http://127.0.0.1:5000...
echo Opening browser in 2 seconds...
start "" http://127.0.0.1:5000

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" -m uvicorn src.portal:app --host 127.0.0.1 --port 5000
) else (
    uv run uvicorn src.portal:app --host 127.0.0.1 --port 5000
)

pause