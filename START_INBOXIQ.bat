@echo off
cd /d "%~dp0"
echo ==============================================
echo           InboxIQ - Gmail Edition
echo ==============================================
echo.
py -m pip install -r requirements.txt
echo.
echo Starting InboxIQ...
echo Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C to stop.
echo.
py app.py
pause
