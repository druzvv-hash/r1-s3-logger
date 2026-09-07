@echo off
cd /d "%~dp0.."
py -3 viewer\server.py
if errorlevel 1 pause
