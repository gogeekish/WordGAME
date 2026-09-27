@echo off
REM Builds TradingAssistant.exe - a standalone Windows program.
REM
REM RUN THIS ON WINDOWS, from inside this "app" folder, with Python
REM already installed. It cannot be run here (this was written on
REM Linux, which cannot produce a Windows .exe) - it has to run on
REM your own Windows PC, which is also where your MT5 terminal lives.
REM
REM What it does:
REM   1. Installs the two packages this app needs (MetaTrader5, PyInstaller)
REM   2. Packages gui_app.py, and the strategy/broker/risk-gate code it
REM      imports from ../python, into one .exe
REM
REM The finished file appears at: dist\TradingAssistant.exe

echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install requirements. Make sure Python and pip are
    echo installed and on your PATH, then try again.
    pause
    exit /b 1
)

echo.
echo Building TradingAssistant.exe ...
pyinstaller --onefile --windowed --name TradingAssistant --paths ..\python gui_app.py

if errorlevel 1 (
    echo.
    echo Build failed - see the messages above.
    pause
    exit /b 1
)

echo.
echo Done! Find it at: dist\TradingAssistant.exe
echo You can copy that one file anywhere - it does not need Python installed to run.
pause
