@echo off
title Barham School - Installation Demarrage Auto
cd /d "%~dp0"

echo ========================================
echo   Barham School - Demarrage Automatique
echo   (Installation permanente)
echo ========================================
echo.

echo [1/2] Nettoyage ancienne installation...
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BarhamSchool.*" 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\barham_school.*" 2>nul

echo [2/2] Installation du lancement automatique...

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "wscript.exe ""%~dp0gardien_permanent.vbs""", 0, False
) > "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BarhamSchool.vbs"

echo.
echo ========================================
echo   INSTALLATION REUSSIE !
echo ========================================
echo.
echo FICHIER CREE :
echo   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BarhamSchool.vbs
echo.
echo A chaque demarrage de Windows, le serveur
echo se lancera automatiquement et en silence.
echo.
echo Pour annuler, supprimez ce fichier.
echo.
pause
exit
