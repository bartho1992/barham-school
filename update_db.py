"""
Script de mise à jour de la base de données pour ajouter les tables financières
"""
import os
from app import app, db
from models import CategorieTarif, Scolarite, TarifService, AbonnementService

with app.app_context():
    # Créer les nouvelles tables
    db.create_all()
    print("Base de données mise à jour avec succès !")
    print("Tables créées : categorie_tarif, scolarite, tarif_service, abonnement_service")
