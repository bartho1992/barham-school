@echo off
title Barham School Server
cd /d "%~dp0"
echo ========================================
echo   Barham School - Serveur EduGestion IA
echo   Developpe par Barham Informatique
echo ========================================
echo.
echo Demarrage du serveur en cours...
echo Acces: http://localhost:5000
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.
python app.py
pause
