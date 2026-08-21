import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default='user')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)
    identifiant = db.Column(db.String(50), unique=True, nullable=True)
    
    ecole = db.relationship('Ecole', backref='users')
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)

class Ecole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), default='BARHAMSCOOL APP')
    identifiant = db.Column(db.String(50), unique=True, nullable=True)
    adresse = db.Column(db.String(300), default='ZAC MBAO CITE CAPEC')
    tel = db.Column(db.String(100), default='338369035-772601310-777385032')
    annee_scolaire = db.Column(db.String(20))  # defini manuellement par l'admin
    zone = db.Column(db.String(100), default='RUFISQUE')
    dev = db.Column(db.String(200), default='Abdou Diatta - Barham Informatique')
    email = db.Column(db.String(150), default='')
    type_ecole = db.Column(db.String(100), default='')
    directeur = db.Column(db.String(150), default='')
    chef_etablissement = db.Column(db.String(150), default='')
    slogan = db.Column(db.String(300), default='')
    autorisation = db.Column(db.String(100), default='')
    code_etablissement = db.Column(db.String(50), default='')
    ia = db.Column(db.String(100), default='')
    ief = db.Column(db.String(100), default='')
    
    # Paramètres de sécurité avancés
    session_timeout = db.Column(db.Integer, default=30)  # en minutes
    max_login_attempts = db.Column(db.Integer, default=5)
    lockout_duration = db.Column(db.Integer, default=15)  # en minutes
    ip_whitelist = db.Column(db.Text, default='')  # IPs autorisées (séparées par virgule)

    # Paramètres SMTP/Email
    smtp_server = db.Column(db.String(150), default='')
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(150), default='')
    smtp_password = db.Column(db.String(150), default='')
    smtp_use_tls = db.Column(db.Boolean, default=True)
    email_expediteur = db.Column(db.String(150), default='')

class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    success = db.Column(db.Boolean, default=False)


class AnneeScolaire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annee = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=False)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='annees_scolaires')

class Eleve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    sexe = db.Column(db.String(1), default='M')
    photo = db.Column(db.String(300))
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    tel = db.Column(db.String(50))
    code_parent = db.Column(db.String(20), unique=True, nullable=True)
    date_naissance = db.Column(db.String(50))
    lieu_naissance = db.Column(db.String(100))
    tuteur = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    precedente_ecole = db.Column(db.String(200))
    date_entree = db.Column(db.String(50))
    observations = db.Column(db.Text)
    situation = db.Column(db.String(50), default='Inscrit')
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    classe = db.relationship('Classe', backref='eleves')
    notes = db.relationship('Note', backref='eleve', lazy='dynamic')
    paiements = db.relationship('Paiement', backref='eleve', lazy='dynamic')
    assiduites = db.relationship('Assiduite', backref='eleve', lazy='dynamic')

class Classe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    niveau = db.Column(db.String(50))
    type_classe = db.Column(db.String(20), default='secondaire')  # 'primaire' ou 'secondaire'
    effectif = db.Column(db.Integer, default=0)
    ordre = db.Column(db.Integer, default=0)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='classes')

class Matiere(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    domaine = db.Column(db.String(100))
    coefficient = db.Column(db.Float, default=1)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='matieres')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'))
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'))
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    trimestre = db.Column(db.Integer, default=1)
    controle = db.Column(db.Float)
    composition = db.Column(db.Float)
    moyenne = db.Column(db.Float)
    rang = db.Column(db.Integer)
    appreciation = db.Column(db.String(50))
    annee_scolaire = db.Column(db.String(20), default='2024-2025')

class Bulletin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'))
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    trimestre = db.Column(db.Integer)
    moyenne_generale = db.Column(db.Float)
    rang = db.Column(db.Integer)
    moyenne_classe = db.Column(db.Float)
    decision = db.Column(db.String(100))
    absences = db.Column(db.Integer, default=0)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')

class Assiduite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    date_evenement = db.Column(db.String(20), nullable=False)
    type_evenement = db.Column(db.String(20), nullable=False, default='Absent')
    motif = db.Column(db.String(255))
    justifie = db.Column(db.Boolean, default=False)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    classe = db.relationship('Classe', backref='assiduites')
    ecole = db.relationship('Ecole', backref='assiduites')

class Personnel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50))
    prenom = db.Column(db.String(100), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    fonction = db.Column(db.String(100))
    tel = db.Column(db.String(50))
    salaire_fixe = db.Column(db.Float, default=0)
    taux_impot = db.Column(db.Float, default=5)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='personnel')

class Salaire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'))
    mois = db.Column(db.String(50))
    salaire_brut = db.Column(db.Float, default=0)
    impot = db.Column(db.Float, default=0)
    primes = db.Column(db.Float, default=0)
    salaire_net = db.Column(db.Float, default=0)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    personnel = db.relationship('Personnel')

class Paiement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'))
    type_paiement = db.Column(db.String(100))
    montant = db.Column(db.Float, default=0)
    montant_attendu = db.Column(db.Float, default=0)
    montant_restant = db.Column(db.Float, default=0)
    caissier = db.Column(db.String(100))
    mode_paiement = db.Column(db.String(30), default='Especes')
    date_paiement = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='paiements')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_doc = db.Column(db.String(100))
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'))
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'), nullable=True)
    contenu = db.Column(db.Text)
    token_verification = db.Column(db.String(200), unique=True, nullable=True)
    qr_code_url = db.Column(db.String(500), nullable=True)
    date_expiration = db.Column(db.DateTime, nullable=True)
    statut = db.Column(db.String(20), default='valide')  # valide, expire, revoke
    date_creation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    ecole = db.relationship('Ecole', backref='documents')

class Licence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cle = db.Column(db.String(50), unique=True, nullable=False)
    date_expiration = db.Column(db.DateTime, nullable=False)
    active = db.Column(db.Boolean, default=True)
    date_activation = db.Column(db.DateTime)
    ecole_nom = db.Column(db.String(200))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # SaaS — Plan d'abonnement
    plan = db.Column(db.String(20), default='starter')  # starter, standard, premium
    eleves_max = db.Column(db.Integer, default=150)       # -1 = illimité
    personnel_max = db.Column(db.Integer, default=10)
    essai = db.Column(db.Boolean, default=False)           # licence d'essai gratuit
    modules = db.Column(db.Text, default='["eleves","classes","notes","bulletins","finances","personnel","documents"]')
    prix_paye = db.Column(db.Float, default=0)
    devise = db.Column(db.String(10), default='XOF')
    mode_paiement = db.Column(db.String(50))

    @property
    def est_valide(self):
        if not self.active:
            return False
        now = datetime.now(timezone.utc)
        if self.date_expiration.tzinfo is None:
            exp_date = self.date_expiration.replace(tzinfo=timezone.utc)
        else:
            exp_date = self.date_expiration
        return now < exp_date

    @property
    def jours_restants(self):
        if not self.date_expiration:
            return 0
        now = datetime.now(timezone.utc)
        df = self.date_expiration
        if df.tzinfo is None:
            df = df.replace(tzinfo=timezone.utc)
        return max(0, (df - now).days)

    @staticmethod
    def licence_active_for_ecole(ecole_id):
        now = datetime.now(timezone.utc)
        licence = Licence.query.filter_by(active=True, ecole_id=ecole_id).first()
        if not licence:
            return None
        if licence.date_expiration.tzinfo is None:
            exp_date = licence.date_expiration.replace(tzinfo=timezone.utc)
        else:
            exp_date = licence.date_expiration
        return licence if exp_date > now else None

class FactureLicence(db.Model):
    """Factures pour achat/renew de licence SaaS"""
    id = db.Column(db.Integer, primary_key=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False)
    licence_id = db.Column(db.Integer, db.ForeignKey('licence.id'), nullable=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    plan = db.Column(db.String(20))
    duree_mois = db.Column(db.Integer, default=12)
    montant = db.Column(db.Float, nullable=False)
    devise = db.Column(db.String(10), default='XOF')
    statut = db.Column(db.String(20), default='en_attente')  # en_attente, payee, annulee
    mode_paiement = db.Column(db.String(50))
    description = db.Column(db.String(300))
    date_paiement = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    ecole = db.relationship('Ecole', backref='factures_licence')
    licence = db.relationship('Licence')

    @staticmethod
    def generer_numero():
        now = datetime.now(timezone.utc)
        prefix = now.strftime('%Y%m')
        count = FactureLicence.query.filter(
            FactureLicence.numero.like(f'FC-{prefix}-%')
        ).count()
        return f'FC-{prefix}-{count + 1:04d}'

class TransactionLicence(db.Model):
    """Transactions de paiement de licence"""
    id = db.Column(db.Integer, primary_key=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False)
    facture_id = db.Column(db.Integer, db.ForeignKey('facture_licence.id'), nullable=True)
    montant = db.Column(db.Float, nullable=False)
    devise = db.Column(db.String(10), default='XOF')
    passerelle = db.Column(db.String(50))  # wave, orange_money, stripe, manual
    statut = db.Column(db.String(20), default='initiee')
    reference = db.Column(db.String(200))
    description = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    ecole = db.relationship('Ecole', backref='transactions_licence')
    facture = db.relationship('FactureLicence')

# Modèles pour la gestion financière
class Scolarite(db.Model):
    """Scolarité par classe (indépendant des catégories)"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    # Montants par période
    inscription = db.Column(db.Float, default=0)
    janvier = db.Column(db.Float, default=0)
    fevrier = db.Column(db.Float, default=0)
    mars = db.Column(db.Float, default=0)
    avril = db.Column(db.Float, default=0)
    mai = db.Column(db.Float, default=0)
    juin = db.Column(db.Float, default=0)
    juillet = db.Column(db.Float, default=0)
    aout = db.Column(db.Float, default=0)
    septembre = db.Column(db.Float, default=0)
    octobre = db.Column(db.Float, default=0)
    novembre = db.Column(db.Float, default=0)
    decembre = db.Column(db.Float, default=0)
    
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ordre = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    classe = db.relationship('Classe')
    ecole = db.relationship('Ecole', backref='scolarites')
    
    @property
    def total_annuel(self):
        """Calcule le total annuel"""
        mois = [self.janvier, self.fevrier, self.mars, self.avril, self.mai, self.juin, 
                self.juillet, self.aout, self.septembre, self.octobre, self.novembre, self.decembre]
        return self.inscription + sum(mois)

class CategorieTarif(db.Model):
    """Catégories de services (cantine, transport, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type_categorie = db.Column(db.String(50), nullable=False)  # 'mensuel' ou 'inscription'
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ecole = db.relationship('Ecole', backref='categories_tarifs')

class TarifService(db.Model):
    """Tarifs des services par classe et catégorie"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie_tarif.id'))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    # Montants par période
    inscription = db.Column(db.Float, default=0)
    janvier = db.Column(db.Float, default=0)
    fevrier = db.Column(db.Float, default=0)
    mars = db.Column(db.Float, default=0)
    avril = db.Column(db.Float, default=0)
    mai = db.Column(db.Float, default=0)
    juin = db.Column(db.Float, default=0)
    juillet = db.Column(db.Float, default=0)
    aout = db.Column(db.Float, default=0)
    septembre = db.Column(db.Float, default=0)
    octobre = db.Column(db.Float, default=0)
    novembre = db.Column(db.Float, default=0)
    decembre = db.Column(db.Float, default=0)
    
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    classe = db.relationship('Classe')
    categorie = db.relationship('CategorieTarif')
    
    @property
    def total_annuel(self):
        """Calcule le total annuel"""
        mois = [self.janvier, self.fevrier, self.mars, self.avril, self.mai, self.juin, 
                self.juillet, self.aout, self.septembre, self.octobre, self.novembre, self.decembre]
        return self.inscription + sum(mois)

class AbonnementService(db.Model):
    """Abonnements d'un élève aux services"""
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'))
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie_tarif.id'))
    actif = db.Column(db.Boolean, default=True)
    mois_debut = db.Column(db.String(20), default='Septembre')
    mois_fin = db.Column(db.String(20), default='Juin')
    montant_personnalise = db.Column(db.Float, nullable=True)
    date_debut = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    eleve = db.relationship('Eleve', backref='abonnements')
    categorie = db.relationship('CategorieTarif')

# ============================================================
# NOUVEAUX MODELES — Emploi du temps, Examens, Conseil, etc.
# ============================================================

class EmploiDuTemps(db.Model):
    """Emploi du temps par classe"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'), nullable=True)
    enseignant = db.Column(db.String(150))
    jour = db.Column(db.String(20), nullable=False)
    heure_debut = db.Column(db.String(10), nullable=False)
    heure_fin = db.Column(db.String(10), nullable=False)
    salle = db.Column(db.String(50))
    couleur = db.Column(db.String(20), default='#3b82f6')
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    classe = db.relationship('Classe', backref='emploi_du_temps')
    matiere = db.relationship('Matiere')
    professeur = db.relationship('Personnel', backref='creneaux_edt')

class DisponibiliteEnseignant(db.Model):
    """Disponibilites des enseignants par jour et creneau"""
    id = db.Column(db.Integer, primary_key=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey('personnel.id'), nullable=False)
    jour = db.Column(db.String(20), nullable=False)
    heure_debut = db.Column(db.String(10), nullable=False)
    heure_fin = db.Column(db.String(10), nullable=False)
    disponible = db.Column(db.Boolean, default=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    personnel = db.relationship('Personnel', backref='disponibilites')
    
    __table_args__ = (
        db.UniqueConstraint('personnel_id', 'jour', 'heure_debut', 'heure_fin', name='uq_dispo_ens'),
    )

class GrilleHoraire(db.Model):
    """Nombre d'heures par matiere et par classe pour la generation auto de l'EDT"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=False)
    heures_par_semaine = db.Column(db.Integer, default=1)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    classe = db.relationship('Classe', backref='grille_horaire')
    matiere = db.relationship('Matiere')
    
    __table_args__ = (
        db.UniqueConstraint('classe_id', 'matiere_id', 'ecole_id', name='uq_grille_classe_matiere'),
    )
    ecole = db.relationship('Ecole', backref='emplois_du_temps')

class Examen(db.Model):
    """Planning des examens / compositions"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=False)
    type_examen = db.Column(db.String(30), default='Composition')
    trimestre = db.Column(db.Integer, default=1)
    date_examen = db.Column(db.String(20), nullable=False)
    heure_debut = db.Column(db.String(10), nullable=False)
    duree_minutes = db.Column(db.Integer, default=120)
    salle = db.Column(db.String(50))
    surveillant = db.Column(db.String(150))
    coefficient = db.Column(db.Float, default=1)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    classe = db.relationship('Classe', backref='examens')
    matiere = db.relationship('Matiere')
    ecole = db.relationship('Ecole', backref='examens')

class ConseilClasse(db.Model):
    """Conseil de classe par classe/trimestre"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    trimestre = db.Column(db.Integer, default=1)
    date_conseil = db.Column(db.String(20))
    president = db.Column(db.String(150))
    observations_generales = db.Column(db.Text)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    classe = db.relationship('Classe', backref='conseils_classe')
    ecole = db.relationship('Ecole', backref='conseils_classe')

class AppreciationConseil(db.Model):
    """Appreciation individuelle par eleve lors du conseil"""
    id = db.Column(db.Integer, primary_key=True)
    conseil_id = db.Column(db.Integer, db.ForeignKey('conseil_classe.id'), nullable=False)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    appreciation = db.Column(db.Text)
    decision = db.Column(db.String(50), default='Passe')
    moyenne_generale = db.Column(db.Float)
    rang = db.Column(db.Integer)
    absences = db.Column(db.Integer, default=0)
    retards = db.Column(db.Integer, default=0)
    
    conseil = db.relationship('ConseilClasse', backref='appreciations')
    eleve = db.relationship('Eleve')

class Message(db.Model):
    """Messagerie interne entre utilisateurs"""
    id = db.Column(db.Integer, primary_key=True)
    expediteur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sujet = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    lu = db.Column(db.Boolean, default=False)
    date_envoi = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    expediteur = db.relationship('User', foreign_keys=[expediteur_id], backref='messages_envoyes')
    destinataire = db.relationship('User', foreign_keys=[destinataire_id], backref='messages_recus')
    ecole = db.relationship('Ecole', backref='messages')

class CahierTexte(db.Model):
    """Cahier de textes - suivi des lecons dispensees"""
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'), nullable=False)
    matiere_id = db.Column(db.Integer, db.ForeignKey('matiere.id'), nullable=False)
    enseignant = db.Column(db.String(150))
    date_seance = db.Column(db.String(20), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    devoirs = db.Column(db.Text)
    observations = db.Column(db.Text)
    annee_scolaire = db.Column(db.String(20), default='2024-2025')
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    classe = db.relationship('Classe', backref='cahier_textes')
    matiere = db.relationship('Matiere')
    ecole = db.relationship('Ecole', backref='cahiers_textes')

class NotificationParent(db.Model):
    """Historique des notifications envoyees aux parents"""
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    type_notif = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    canal = db.Column(db.String(20), default='sms')
    statut = db.Column(db.String(20), default='envoye')
    date_envoi = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    eleve = db.relationship('Eleve', backref='notifications_parents')
    ecole = db.relationship('Ecole', backref='notifications_parents')


class CompteComptable(db.Model):
    """Plan comptable SYSCOHADA"""
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False)
    libelle = db.Column(db.String(300), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('compte_comptable.id'), nullable=True)
    niveau = db.Column(db.Integer, default=1)
    nature = db.Column(db.String(20))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    parent = db.relationship('CompteComptable', remote_side=[id], backref='enfants')
    ecole = db.relationship('Ecole', backref='comptes_comptables')
    
    def __repr__(self):
        return f'<Compte {self.numero} {self.libelle}>'

class EcritureComptable(db.Model):
    """Ecritures comptables (partie double)"""
    id = db.Column(db.Integer, primary_key=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    date_ecriture = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    libelle = db.Column(db.String(300), nullable=False)
    reference = db.Column(db.String(100))
    montant = db.Column(db.Float, nullable=False)
    compte_debit_id = db.Column(db.Integer, db.ForeignKey('compte_comptable.id'), nullable=False)
    compte_credit_id = db.Column(db.Integer, db.ForeignKey('compte_comptable.id'), nullable=False)
    type_ecriture = db.Column(db.String(30), default='manuelle')
    paiement_id = db.Column(db.Integer, db.ForeignKey('paiement.id'), nullable=True)
    annee_scolaire = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    compte_debit = db.relationship('CompteComptable', foreign_keys=[compte_debit_id])
    compte_credit = db.relationship('CompteComptable', foreign_keys=[compte_credit_id])
    ecole = db.relationship('Ecole', backref='ecritures_comptables')
    paiement = db.relationship('Paiement', backref='ecriture_comptable')
    
    def __repr__(self):
        return f'<Ecriture {self.id}: {self.libelle} {self.montant}>'

class AuditLog(db.Model):
    """Journal d'audit : trace automatique des creations, modifications et suppressions"""
    id = db.Column(db.Integer, primary_key=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(20))  # create, update, delete
    modele = db.Column(db.String(80))  # nom de la table / modele
    objet_id = db.Column(db.String(50))
    details = db.Column(db.Text)
    date_action = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    ecole = db.relationship('Ecole', backref='audit_logs')
    user = db.relationship('User', backref='audit_logs')

    def __repr__(self):
        return f'<Audit {self.action} {self.modele}#{self.objet_id} par {self.username}>'

# ============================================================
# NOUVEAUX MODELES — Formation Professionnelle
# ============================================================

class FilierePro(db.Model):
    """Filière de formation professionnelle"""
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duree_mois = db.Column(db.Integer, default=6)
    actif = db.Column(db.Boolean, default=True)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    ecole = db.relationship('Ecole', backref='filieres_pro')
    modules = db.relationship('ModulePro', backref='filiere', lazy='dynamic', order_by='ModulePro.ordre')
    sessions = db.relationship('SessionFormation', backref='filiere', lazy='dynamic', order_by='SessionFormation.date_debut.desc()')

class ModulePro(db.Model):
    """Module dans une filiere pro"""
    id = db.Column(db.Integer, primary_key=True)
    filiere_id = db.Column(db.Integer, db.ForeignKey('filiere_pro.id'), nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    duree_heures = db.Column(db.Integer, default=30)
    coefficient = db.Column(db.Float, default=1)
    ordre = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    ecole = db.relationship('Ecole', backref='modules_pro')

class SessionFormation(db.Model):
    """Session de formation (promotion)"""
    id = db.Column(db.Integer, primary_key=True)
    filiere_id = db.Column(db.Integer, db.ForeignKey('filiere_pro.id'), nullable=False)
    nom = db.Column(db.String(200), nullable=False)
    date_debut = db.Column(db.String(20), nullable=False)
    date_fin = db.Column(db.String(20), nullable=False)
    statut = db.Column(db.String(20), default='ouverte')  # ouverte, en_cours, terminee, annulee
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    ecole = db.relationship('Ecole', backref='sessions_formation')
    inscriptions = db.relationship('InscriptionSession', backref='session', lazy='dynamic')

class InscriptionSession(db.Model):
    """Inscription d'un eleve a une session de formation pro"""
    id = db.Column(db.Integer, primary_key=True)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleve.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session_formation.id'), nullable=False)
    date_inscription = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    statut = db.Column(db.String(20), default='actif')  # actif, abandon, termine, certifie
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    
    eleve = db.relationship('Eleve', backref='inscriptions_pro')
    evaluations = db.relationship('EvaluationModulePro', backref='inscription', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('eleve_id', 'session_id', name='uq_inscription_eleve_session'),
    )

class EvaluationModulePro(db.Model):
    """Evaluation d'un eleve sur un module en formation pro"""
    id = db.Column(db.Integer, primary_key=True)
    inscription_id = db.Column(db.Integer, db.ForeignKey('inscription_session.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('module_pro.id'), nullable=False)
    note = db.Column(db.Float, default=0)
    type_eval = db.Column(db.String(30), default='Controle')  # Controle, Examen, Rattrapage
    date_eval = db.Column(db.String(20))
    observations = db.Column(db.Text)
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    module = db.relationship('ModulePro', backref='evaluations')
    ecole = db.relationship('Ecole', backref='evaluations_pro')
    
    __table_args__ = (
        db.UniqueConstraint('inscription_id', 'module_id', 'type_eval', name='uq_eval_inscription_module_type'),
    )


PLAN_SYSCOHADA = [
    ("10", "CAPITAL", "passif", 1, None),
    ("101", "Capital social", "passif", 2, "10"),
    ("11", "RESERVES", "passif", 1, None),
    ("111", "Reserve legale", "passif", 2, "11"),
    ("118", "Autres reserves", "passif", 2, "11"),
    ("12", "REPORT A NOUVEAU", "passif", 1, None),
    ("13", "RESULTAT NET DE L'EXERCICE", "passif", 1, None),
    ("131", "Resultat net : benefice", "passif", 2, "13"),
    ("139", "Resultat net : perte", "passif", 2, "13"),
    ("14", "SUBVENTIONS D'INVESTISSEMENT", "passif", 1, None),
    ("16", "EMPRUNTS ET DETTES ASSIMILEES", "passif", 1, None),
    ("161", "Emprunts obligataires", "passif", 2, "16"),
    ("162", "Emprunts aupres des etab. de credit", "passif", 2, "16"),
    ("168", "Autres emprunts", "passif", 2, "16"),
    ("18", "COMPTES DE LIAISON", "passif", 1, None),
    ("19", "PROVISIONS POUR RISQUES ET CHARGES", "passif", 1, None),
    ("20", "CHARGES IMMOBILISEES", "actif", 1, None),
    ("201", "Frais d'etablissement", "actif", 2, "20"),
    ("21", "IMMOBILISATIONS CORPORELLES", "actif", 1, None),
    ("211", "Terrains", "actif", 2, "21"),
    ("212", "Batiments", "actif", 2, "21"),
    ("213", "Amenagements et installations", "actif", 2, "21"),
    ("214", "Materiel et mobilier", "actif", 2, "21"),
    ("215", "Materiel de transport", "actif", 2, "21"),
    ("218", "Autres immobilisations corporelles", "actif", 2, "21"),
    ("22", "IMMOBILISATIONS CORPORELLES (SUITE)", "actif", 1, None),
    ("222", "Materiel et outillage", "actif", 2, "22"),
    ("223", "Materiel informatique", "actif", 2, "22"),
    ("23", "IMMOBILISATIONS EN COURS", "actif", 1, None),
    ("24", "IMMOBILISATIONS INCORPORELLES", "actif", 1, None),
    ("241", "Logiciels", "actif", 2, "24"),
    ("25", "IMMOBILISATIONS FINANCIERES", "actif", 1, None),
    ("28", "AMORTISSEMENTS", "actif", 1, None),
    ("281", "Amort. immobilisations corporelles", "actif", 2, "28"),
    ("284", "Amort. immobilisations incorporelles", "actif", 2, "28"),
    ("29", "PROVISIONS POUR DEPRECIATION", "actif", 1, None),
    ("31", "MATIERES PREMIERES ET FOURNITURES", "actif", 1, None),
    ("32", "AUTRES APPROVISIONNEMENTS", "actif", 1, None),
    ("321", "Fournitures scolaires", "actif", 2, "32"),
    ("322", "Fournitures de bureau", "actif", 2, "32"),
    ("36", "MARCHANDISES", "actif", 1, None),
    ("39", "DEPRECIATION DES STOCKS", "actif", 1, None),
    ("40", "FOURNISSEURS ET COMPTES RATTACHES", "passif", 1, None),
    ("401", "Fournisseurs de biens et services", "passif", 2, "40"),
    ("408", "Fournisseurs - factures non parvenues", "passif", 2, "40"),
    ("409", "Fournisseurs - avances et acomptes", "actif", 2, "40"),
    ("41", "CLIENTS ET COMPTES RATTACHES", "actif", 1, None),
    ("411", "Clients", "actif", 2, "41"),
    ("416", "Clients douteux", "actif", 2, "41"),
    ("419", "Clients - avances et acomptes", "passif", 2, "41"),
    ("42", "PERSONNEL", "passif", 1, None),
    ("421", "Personnel - remunerations dues", "passif", 2, "42"),
    ("422", "Personnel - avances et acomptes", "actif", 2, "42"),
    ("43", "ORGANISMES SOCIAUX", "passif", 1, None),
    ("431", "Securite sociale (CSS)", "passif", 2, "43"),
    ("432", "Caisse de retraite (IPRES)", "passif", 2, "43"),
    ("44", "ETAT", "passif", 1, None),
    ("441", "Etat - impots sur les benefices", "passif", 2, "44"),
    ("443", "Etat - TVA", "passif", 2, "44"),
    ("447", "Etat - autres impots et taxes", "passif", 2, "44"),
    ("46", "ASSOCIES ET GROUPE", "passif", 1, None),
    ("47", "DEBITEURS ET CREDITEURS DIVERS", "passif", 1, None),
    ("471", "Comptes d'attente", "passif", 2, "47"),
    ("48", "CREANCES ET DETTES H.A.O.", "passif", 1, None),
    ("49", "PROVISIONS DEPRECIATION COMPTES TIERS", "actif", 1, None),
    ("50", "TITRES DE PLACEMENT", "actif", 1, None),
    ("51", "BANQUES", "actif", 1, None),
    ("511", "Banque principale", "actif", 2, "51"),
    ("518", "Autres banques", "actif", 2, "51"),
    ("52", "CHEQUES POSTAUX / MOBILE MONEY", "actif", 1, None),
    ("53", "CAISSE", "actif", 1, None),
    ("531", "Caisse principale", "actif", 2, "53"),
    ("532", "Caisse secondaire", "actif", 2, "53"),
    ("57", "CAISSE (AUTRES)", "actif", 1, None),
    ("58", "VIREMENTS INTERNES", "actif", 1, None),
    ("59", "PROVISIONS DEPRECIATION TRESORERIE", "actif", 1, None),
    ("60", "ACHATS ET VARIATIONS DE STOCKS", "charge", 1, None),
    ("601", "Achats de marchandises", "charge", 2, "60"),
    ("602", "Achats de matieres et fournitures", "charge", 2, "60"),
    ("604", "Achats de fournitures scolaires", "charge", 2, "60"),
    ("605", "Achats de fournitures de bureau", "charge", 2, "60"),
    ("608", "Autres achats", "charge", 2, "60"),
    ("61", "TRANSPORTS", "charge", 1, None),
    ("611", "Transport du personnel", "charge", 2, "61"),
    ("618", "Autres transports", "charge", 2, "61"),
    ("62", "SERVICES EXTERIEURS", "charge", 1, None),
    ("621", "Location et charges locatives", "charge", 2, "62"),
    ("622", "Entretien et reparations", "charge", 2, "62"),
    ("623", "Assurances", "charge", 2, "62"),
    ("624", "Documentation et fournitures pedagogiques", "charge", 2, "62"),
    ("625", "Eau et electricite", "charge", 2, "62"),
    ("626", "Frais postaux et telecommunications", "charge", 2, "62"),
    ("627", "Services bancaires", "charge", 2, "62"),
    ("628", "Publicite et relations publiques", "charge", 2, "62"),
    ("63", "IMPOTS ET TAXES", "charge", 1, None),
    ("631", "Patente et licences", "charge", 2, "63"),
    ("635", "Autres impots et taxes", "charge", 2, "63"),
    ("64", "CHARGES DE PERSONNEL", "charge", 1, None),
    ("641", "Salaires et appointements", "charge", 2, "64"),
    ("642", "Primes et gratifications", "charge", 2, "64"),
    ("643", "Charges sociales (CSS)", "charge", 2, "64"),
    ("644", "Charges de retraite (IPRES)", "charge", 2, "64"),
    ("648", "Autres charges sociales", "charge", 2, "64"),
    ("65", "AUTRES CHARGES", "charge", 1, None),
    ("651", "Redevances et droits", "charge", 2, "65"),
    ("658", "Charges diverses", "charge", 2, "65"),
    ("66", "CHARGES FINANCIERES", "charge", 1, None),
    ("661", "Interets des emprunts", "charge", 2, "66"),
    ("668", "Autres charges financieres", "charge", 2, "66"),
    ("67", "PERTES DE CHANGE", "charge", 1, None),
    ("68", "DOTATIONS AUX AMORTISSEMENTS", "charge", 1, None),
    ("681", "Dotations aux amort. d'exploitation", "charge", 2, "68"),
    ("69", "DOTATIONS AUX PROVISIONS", "charge", 1, None),
    ("70", "VENTES ET PRESTATIONS DE SERVICES", "produit", 1, None),
    ("701", "Ventes de marchandises", "produit", 2, "70"),
    ("706", "Prestations de services", "produit", 2, "70"),
    ("7061", "Frais de scolarite", "produit", 3, "706"),
    ("7062", "Services annexes (cantine, transport)", "produit", 3, "706"),
    ("7063", "Frais d'inscription", "produit", 3, "706"),
    ("707", "Autres produits d'exploitation", "produit", 2, "70"),
    ("71", "SUBVENTIONS D'EXPLOITATION", "produit", 1, None),
    ("73", "PRODUITS ACCESSOIRES", "produit", 1, None),
    ("75", "AUTRES PRODUITS", "produit", 1, None),
    ("758", "Produits divers", "produit", 2, "75"),
    ("76", "PRODUITS FINANCIERS", "produit", 1, None),
    ("77", "GAINS DE CHANGE", "produit", 1, None),
    ("78", "REPRISES SUR AMORTISSEMENTS", "produit", 1, None),
    ("79", "REPRISES SUR PROVISIONS", "produit", 1, None),
    ("81", "VALEURS COMPTABLES DES CESSIONS", "charge", 1, None),
    ("82", "PRODUITS DES CESSIONS", "produit", 1, None),
    ("83", "CHARGES HORS ACTIVITES ORDINAIRES", "charge", 1, None),
    ("84", "PRODUITS HORS ACTIVITES ORDINAIRES", "produit", 1, None),
    ("85", "DOTATIONS H.A.O.", "charge", 1, None),
    ("86", "REPRISES H.A.O.", "produit", 1, None),
    ("88", "SUBVENTIONS D'EQUILIBRE", "produit", 1, None),
    ("89", "IMPOTS SUR LE RESULTAT", "charge", 1, None),
    ("891", "Impots sur les benefices (IBIC)", "charge", 2, "89"),
    ("90", "ENGAGEMENTS RECUS", "hors_bilan", 1, None),
    ("91", "ENGAGEMENTS DONNES", "hors_bilan", 1, None),
]

def init_comptes_syscohada(ecole_id=1):
    """Initialise le plan comptable SYSCOHADA pour une ecole"""
    from app import app
    with app.app_context():
        existing = CompteComptable.query.filter_by(ecole_id=ecole_id).first()
        if existing:
            return
        comptes_map = {}
        for numero, libelle, nature, niveau, parent_num in PLAN_SYSCOHADA:
            parent_id = comptes_map.get(parent_num) if parent_num else None
            compte = CompteComptable(
                numero=numero, libelle=libelle, nature=nature,
                niveau=niveau, parent_id=parent_id, ecole_id=ecole_id
            )
            db.session.add(compte)
            db.session.flush()
            comptes_map[numero] = compte.id
        db.session.commit()

def init_data():
    import random
    import string
    def gen_key(prefix):
        return f"{prefix}-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        
    baye = User.query.filter_by(username='baye').first()
    if baye is None:
        baye = User(username='baye', role='dev', identifiant=gen_key("USR"))
        db.session.add(baye)
    # Garantir un mot de passe connu pour le compte dev
    # (sinon un compte recree apres suppression d'ecole serait inaccessible)
    dev_password = os.environ.get('DEV_PASSWORD') or 'admin123'
    baye.role = 'dev'
    baye.set_password(dev_password)
    # S'assurer que baye a toujours une ecole
    if baye.ecole_id is None:
        first_ecole = Ecole.query.first()
        if first_ecole:
            baye.ecole_id = first_ecole.id
    from datetime import datetime
    now = datetime.now()
    annee = f'{now.year}-{now.year + 1}' if now.month >= 9 else f'{now.year - 1}-{now.year}'
    if not Ecole.query.first():
        ecole = Ecole(identifiant=gen_key("ECL"), nom='BARHAMSCOOL APP', annee_scolaire=annee)
        db.session.add(ecole)
    if not AnneeScolaire.query.first():
        db.session.add(AnneeScolaire(annee=annee, active=True))
    if not Classe.query.first():
        niveaux = [
            ('PS','Prescolaire'),('GS','Prescolaire'),
            ('CI','Primaire CI/CP'),('CP','Primaire CI/CP'),
            ('CE1A','Primaire Elementaire'),('CE1B','Primaire Elementaire'),('CE2A','Primaire Elementaire'),('CE2B','Primaire Elementaire'),
            ('CM1A','Primaire Elementaire'),('CM1B','Primaire Elementaire'),('CM2A','Primaire Elementaire'),('CM2B','Primaire Elementaire'),
            ('6E_A','Moyen Secondaire'),('6E_B','Moyen Secondaire'),('5E_A','Moyen Secondaire'),('5E_B','Moyen Secondaire'),
            ('4E_A','Moyen Secondaire'),('4E_B','Moyen Secondaire'),('3E_A','Moyen Secondaire'),('3E_B','Moyen Secondaire'),
            ('2NDS','Secondaire'),('2NDL','Secondaire'),
            ('1ERES2','Secondaire'),('1EREL','Secondaire'),('1ERE_S1','Secondaire'),
            ('TLE_S2','Secondaire'),('TLE_L1','Secondaire'),('TLE_L2','Secondaire'),('TLE_S1','Secondaire'),
        ]
        for nom, niv in niveaux:
            db.session.add(Classe(nom=nom, niveau=niv))
    if not Matiere.query.first():
        matieres = [
            ('Ecriture','LANGUES ET COMMUNICATIONS',1),('Copie','LANGUES ET COMMUNICATIONS',1),
            ('Activite de lecture','LANGUES ET COMMUNICATIONS',3),('Dictee','LANGUES ET COMMUNICATIONS',1),
            ('Activite de Mesure','MATHEMATIQUES',1),('Activite Geometrique','MATHEMATIQUES',1),
            ('Activite numerique','MATHEMATIQUES',1),('Resolution de Problemes','MATHEMATIQUES',1),
            ('Histoire','DECOUVERTE DU MONDE',1),('Geographie','DECOUVERTE DU MONDE',1),
            ('IST','DECOUVERTE DU MONDE',1),('Vivre ensemble','EDD',1),
            ('Art dessin','AUTRES',1),('Recitation / chant','AUTRES',1),
            ('Francais','LANGUES',3),('Orthographe','LANGUES',1),('TSQ','LANGUES',1),
            ('Anglais','LANGUES',2),('Espagnol','LANGUES',2),
            ('Philo','LANGUES',2),('Maths','MATHEMATIQUES',3),
            ('SVT','SCIENCES',2),('PC','SCIENCES',2),
            ('Hist-geo','HISTOIRE-GEO',2),('E. civique','HISTOIRE-GEO',1),
            ('EPS','AUTRES',1),('Arabe','AUTRES',1),('Conduite','AUTRES',1),
        ]
        for nom, dom, coef in matieres:
            db.session.add(Matiere(nom=nom, domaine=dom, coefficient=coef))
    db.session.commit()
