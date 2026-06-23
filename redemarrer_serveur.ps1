# Script PowerShell pour redémarrer le serveur EduGestion
Write-Host "Arrêt du serveur existant..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "Démarrage du serveur EduGestion..." -ForegroundColor Green

# Activer l'environnement virtuel (si nécessaire, sinon utilise le python global)
# & ".venv\Scripts\Activate.ps1"

# Lancer l'application
python app.py

Write-Host "Serveur arrêté." -ForegroundColor Red
