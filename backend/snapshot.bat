@echo off
REM Quick snapshot of current sensor readings
cd /d "%~dp0"
python test_real_notification.py
pause
