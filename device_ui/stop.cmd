@echo off
cd /d "%~dp0.."
"%USERPROFILE%\.platformio\penv\Scripts\python.exe" device_ui\bridge.py --stop
pause
