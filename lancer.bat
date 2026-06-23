@echo off
title Barham School - Lanceur
cd /d "%~dp0"

echo [1/2] Arret ancien serveur...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/2] Demarrage du serveur...
start /min "Barham School Server" C:\Python314\python.exe "%~dp0app.py"

echo Le serveur est pret ! Ouvrez http://localhost:5000
echo.
echo Pour arreter, utilisez arreter.bat
timeout /t 4 /nobreak >nul
exit
