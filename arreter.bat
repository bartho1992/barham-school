@echo off
title Barham School - Arret
cd /d "%~dp0"

echo Arret du gardien et du serveur...
taskkill /f /im python.exe 2>nul
taskkill /f /im wscript.exe 2>nul
timeout /t 2 /nobreak >nul

echo Serveur arrete.
echo.
echo Pour relancer, utilisez lancer.bat
pause
