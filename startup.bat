@echo off
title Barham School Server
cd /d "%~dp0"
start /min "" "%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
start /min "" wscript.exe "%~dp0gardien.vbs"
timeout /t 8 /nobreak >nul
start "" http://localhost:5000
exit
