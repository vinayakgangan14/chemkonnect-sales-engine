@echo off
title Chemkonnect Global - 100 Crore B2B AI Sales Engine
cd /d "%~dp0"
cls
echo ====================================================================
echo    CHEMKONNECT GLOBAL - 100 CRORE B2B AI SALES ENGINE
echo    Pidilite | Gypsum Boards | Plywood | Expansion Joints | Solvents
echo ====================================================================
echo.
echo Choose an action:
echo  [1] Harvest Nearing-Possession Projects (99acres / MagicBricks / NoBroker)
echo  [2] Harvest Turnkey Interior Giants (Ashish Interbuild, Astitva Interiors)
echo  [3] Fetch 30-Day IndiaMART RFQ Buyer Inquiries
echo  [4] Harvest Verified TradeIndia Enterprise Accounts
echo  [5] Scan Web & Tenders for Gypsum & Framing (Mumbai / Thane)
echo  [6] Scan Web & Tenders for Plywood & Panels (Pune / Maharashtra)
echo  [7] Open Web Portal at http://127.0.0.1:5000
echo  [8] View Pipeline Summary & Export Excel CSV
echo  [9] Open Output Folder (View Excel CSVs)
echo  [0] Exit
echo.
set /p choice="Enter choice [0-9]: "

if "%choice%"=="1" (
    uv run python run_pipeline.py --projects
    pause
    goto :eof
)
if "%choice%"=="2" (
    uv run python run_pipeline.py --giants
    pause
    goto :eof
)
if "%choice%"=="3" (
    uv run python run_pipeline.py --indiamart
    pause
    goto :eof
)
if "%choice%"=="4" (
    uv run python run_pipeline.py --tradeindia
    pause
    goto :eof
)
if "%choice%"=="5" (
    uv run python run_pipeline.py --recent --category "Gypsum board" --location "Mumbai"
    pause
    goto :eof
)
if "%choice%"=="6" (
    uv run python run_pipeline.py --recent --category "Plywood" --location "Pune"
    pause
    goto :eof
)
if "%choice%"=="7" (
    start http://127.0.0.1:5000
    uv run uvicorn src.portal:app --host 127.0.0.1 --port 5000 --reload
    goto :eof
)
if "%choice%"=="8" (
    uv run python run_pipeline.py
    pause
    goto :eof
)
if "%choice%"=="9" (
    explorer output
    goto :eof
)
exit