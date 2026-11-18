@echo off
title Chemkonnect Global - B2B AI Sales Portal
cd /d "%~dp0"
cls
echo ====================================================================
echo    CHEMKONNECT GLOBAL - B2B AI SALES PORTAL
echo    Opening Web Dashboard at: http://127.0.0.1:5000
echo ====================================================================
echo.
echo Starting FastAPI web server...
start http://127.0.0.1:5000
uv run uvicorn src.portal:app --host 127.0.0.1 --port 5000 --reload
pause