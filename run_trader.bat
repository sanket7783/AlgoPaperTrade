@echo off
title Forex Gold to Groww MCX Gold Algo Trader
cd /d "%~dp0"
echo ======================================================================
echo  ⚜  Forex Gold (OANDA) -> Groww MCX Gold Algo Paper Trader Launcher
echo ======================================================================
echo Starting Web Dashboard on http://localhost:8000 ...
python main.py --port 8000
pause
