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
    classe_id = db.Column(db.Integer, db.ForeignKey('classe.id'))
    ecole_id = db.Column(db.Integer, db.ForeignKey('ecole.id'), nullable=False, default=1)
    tel = db.Column(db.String(50))
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

class Classe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    niveau = db.Column(db.String(50))
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

def init_data():
    import random
    import string
    def gen_key(prefix):
        return f"{prefix}-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))}"
        
    if not User.query.filter_by(username='baye').first():
        baye = User(username='baye', role='dev', identifiant=gen_key("USR"))
        baye.set_password('admin123')
        db.session.add(baye)
    # S'assurer que baye a toujours une ecole
    baye = User.query.filter_by(username='baye').first()
    if baye and baye.ecole_id is None:
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
