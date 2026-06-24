import os
from flask import Flask, session, request, redirect, url_for, send_from_directory, render_template
from models import db, init_data, Ecole, AnneeScolaire

from datetime import timedelta, datetime
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'barham-informatique-2024')
# En production, le repertoire /app/data est necessaire pour SQLite (Render)
if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
    data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, 'school.db')
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'school.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'connect_args': {
        'timeout': 30,
        'isolation_level': None
    }
}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
db.init_app(app)

def get_current_ecole_id():
    if 'ecole_id' in session:
        return session['ecole_id']
    ecole = Ecole.query.first()
    if ecole:
        session['ecole_id'] = ecole.id
        return ecole.id
    return 1

def get_current_annee():
    annee_session = session.get('annee_scolaire')
    if annee_session and str(annee_session).strip().lower() != 'none':
        return annee_session
    
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    if ecole and ecole.annee_scolaire and str(ecole.annee_scolaire).strip().lower() != 'none':
        return ecole.annee_scolaire
    
    try:
        annee_active = AnneeScolaire.query.filter_by(ecole_id=ecole_id, active=True).first()
        if annee_active and annee_active.annee:
            return annee_active.annee
        
        annee_recent = AnneeScolaire.query.order_by(AnneeScolaire.annee.desc()).filter_by(ecole_id=ecole_id).first()
        if annee_recent and annee_recent.annee:
            return annee_recent.annee
    except:
        pass
        
    # Annee scolaire dynamique si rien en base
    now = datetime.now()
    if now.month >= 9:
        return f'{now.year}-{now.year + 1}'
    else:
        return f'{now.year - 1}-{now.year}'

@app.route('/favicon.ico')
@app.route('/favicon.svg')
def favicon():
    return send_from_directory(app.static_folder, request.path[1:] if request.path[1:] else 'favicon.ico')

@app.route('/documents')
def documents():
    return render_template('documents/index.html')

@app.context_processor
def inject_globals():
    try:
        ecole_id = get_current_ecole_id()
        ecole = Ecole.query.get(ecole_id)
        if not ecole:
            ecole = Ecole.query.first()
            if ecole: session['ecole_id'] = ecole.id
            
        all_ecoles = Ecole.query.all()
        annees = AnneeScolaire.query.filter_by(ecole_id=ecole_id).order_by(AnneeScolaire.annee.desc()).all()
        current_annee = get_current_annee()
    except Exception:
        ecole = None
        all_ecoles = []
        annees = []
        current_annee = get_current_annee()
    return dict(ecole=ecole, all_ecoles=all_ecoles, all_annees=annees, current_annee=current_annee)

from routes_auth import *
from routes_eleves import *
from routes_classes import *
from routes_notes import *
from routes_finances import *
from routes_personnel import *
from routes_admin import *
from routes_licence import *
from routes_saas import *

with app.app_context():
    db.create_all()
    # Migration SaaS — Ajouter colonnes plan/eleves_max/etc. à la table licence
    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)
    if 'licence' in inspector.get_table_names():
        cols_existantes = [c['name'] for c in inspector.get_columns('licence')]
        nouvelles_colonnes = [
            ('plan', "VARCHAR(20) DEFAULT 'starter'"),
            ('eleves_max', 'INTEGER DEFAULT 150'),
            ('personnel_max', 'INTEGER DEFAULT 10'),
            ('essai', 'BOOLEAN DEFAULT 0'),
            ('modules', 'TEXT DEFAULT \'["eleves","classes","notes","bulletins","finances","personnel","documents"]\''),
            ('prix_paye', 'FLOAT DEFAULT 0'),
            ('devise', "VARCHAR(10) DEFAULT 'XOF'"),
            ('mode_paiement', 'VARCHAR(50)'),
        ]
        for nom, typ in nouvelles_colonnes:
            if nom not in cols_existantes:
                try:
                    db.session.execute(text(f"ALTER TABLE licence ADD COLUMN {nom} {typ}"))
                    print(f"[SaaS] Colonne licence.{nom} ajoutee")
                except Exception as e:
                    print(f"[SaaS] Erreur {nom}: {e}")
        db.session.commit()
    init_data()

# Injecte has_licence dans tous les templates (pour la sidebar)
# + info essai (jours restants, est un essai)
@app.context_processor
def inject_licence_status():
    from flask_login import current_user
    from models import Licence
    try:
        if current_user.is_authenticated and current_user.role != 'super_users':
            ecole_id = get_current_ecole_id()
            licence = Licence.licence_active_for_ecole(ecole_id)
            if licence:
                return {
                    'has_licence': True,
                    'est_essai': licence.essai,
                    'jours_restants': licence.jours_restants
                }
            return {'has_licence': False, 'est_essai': False, 'jours_restants': 0}
    except:
        pass
    return {'has_licence': True, 'est_essai': False, 'jours_restants': 0}  # super_users = toujours true

@app.before_request
def verifier_licence_et_session():
    from flask import request, redirect, url_for, session
    from flask_login import current_user
    from models import Licence, Ecole
    from datetime import timedelta, datetime
    
    try:
        ecole_id = get_current_ecole_id()
        ecole = Ecole.query.get(ecole_id)
        if ecole and ecole.session_timeout:
            app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=ecole.session_timeout)
    except:
        pass

    routes_libres = ['licence_page', 'licence_activer', 'login', 'logout', 'register', 'static',
                      'pricing', 'webhook_recevoir',
                      'abonnement', 'abonnement_checkout', 'abonnement_payer',
                      'abonnement_callback', 'abonnement_essai', 'abonnement_facture',
                      'admin_paiements', 'admin_valider_paiement', 'admin_refuser_paiement',
                      'admin_supprimer_paiement', 'admin_supprimer_transaction']
    if request.endpoint in routes_libres:
        return None
    
    try:
        if current_user.is_authenticated and current_user.role == 'super_users':
            return None
    except:
        pass
    
    try:
        if current_user.is_authenticated:
            ecole_id = get_current_ecole_id()
            licence = Licence.licence_active_for_ecole(ecole_id)
            if not licence:
                # Verifier si une licence expiree (essai termine)
                old = Licence.query.filter_by(active=True, ecole_id=ecole_id).first()
                if old and old.essai and old.jours_restants == 0:
                    flash('Votre essai gratuit est termine. Souscrivez a un abonnement pour continuer.', 'warning')
                return redirect(url_for('abonnement'))
            # Notifier si essai arrive a expiration
            if licence.essai and licence.jours_restants <= 7 and licence.jours_restants > 0:
                # Stocker en session pour ne pas flasher a chaque requete
                last_warning = session.get('last_trial_warning')
                from datetime import date
                today = date.today().isoformat()
                if last_warning != today:
                    flash(f'Votre essai gratuit expire dans {licence.jours_restants} jour(s). Souscrivez des maintenant !', 'warning')
                    session['last_trial_warning'] = today
    except:
        pass

if __name__ == '__main__':
    app.run(debug=False, port=5001)
