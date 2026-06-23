from flask import render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Ecole, LoginAttempt
from app import app
from system_logger import system_logger
from datetime import datetime, timedelta, timezone

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '2024-2025')

@login_manager.user_loader
def load_user(id): return User.query.get(int(id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        ip_address = request.remote_addr
        
        ecole = Ecole.query.first()
        max_attempts = ecole.max_login_attempts if ecole else 5
        lockout_duration = ecole.lockout_duration if ecole else 15
        
        # Vérifier si l'utilisateur est bloqué
        since = datetime.now(timezone.utc) - timedelta(minutes=lockout_duration)
        attempts = LoginAttempt.query.filter(
            LoginAttempt.username == username,
            LoginAttempt.timestamp > since,
            LoginAttempt.success == False
        ).count()
        
        if attempts >= max_attempts:
            system_logger.log_login(username, False, f"Compte temporairement bloqué (Brute-force)")
            flash(f'Trop de tentatives. Réessayez dans {lockout_duration} minutes.', 'danger')
            return render_template('login.html')
            
        u = User.query.filter_by(username=username).first()
        
        if u and u.check_password(password):
            # Succès
            attempt = LoginAttempt(username=username, ip_address=ip_address, success=True)
            u.last_login = datetime.now(timezone.utc)
            db.session.add(attempt)
            db.session.commit()
            
            session.permanent = True
            login_user(u)
            
            # Si l'utilisateur est lié à une école précise, on la force en session
            if u.ecole_id:
                session['ecole_id'] = u.ecole_id
                if u.ecole and u.ecole.annee_scolaire:
                    session['annee_scolaire'] = u.ecole.annee_scolaire
            
            system_logger.log_login(username, True)
            return redirect(url_for('dashboard'))
        else:
            # Échec
            attempt = LoginAttempt(username=username, ip_address=ip_address, success=False)
            db.session.add(attempt)
            db.session.commit()
            
            system_logger.log_login(username, False, "Mot de passe incorrect")
            flash('Identifiant ou mot de passe incorrect', 'danger')
            
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nom_ecole = request.form.get('nom_ecole', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not nom_ecole or not username or not password:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 3:
            flash('Le mot de passe doit contenir au moins 3 caracteres.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Cet identifiant existe deja.', 'danger')
            return render_template('auth/register.html')
        
        # Creer l'ecole
        ecole = Ecole(
            nom=nom_ecole.upper(),
            identifiant=f"EC-{nom_ecole[:4].upper()}-{db.session.query(Ecole).count() + 1}",
            annee_scolaire='2024-2025'
        )
        db.session.add(ecole)
        db.session.flush()
        
        # Creer le compte
        user = User(username=username, role='user', ecole_id=ecole.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash(f'Bienvenue {nom_ecole.upper()} ! Votre compte est cree. Choisissez un abonnement pour commencer.', 'success')
        return redirect(url_for('abonnement'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    from models import Eleve, Classe, Personnel, Paiement
    from app import get_current_ecole_id
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)

    return render_template('dashboard.html', ecole=e,
        total_eleves=Eleve.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).count(), 
        total_classes=Classe.query.filter_by(ecole_id=ecole_id).count(),
        total_personnel=Personnel.query.filter_by(ecole_id=ecole_id).count(),
        total_paiements=db.session.query(db.func.sum(Paiement.montant)).filter_by(annee_scolaire=annee, ecole_id=ecole_id).scalar() or 0,
        total_impayes=db.session.query(db.func.sum(Paiement.montant_restant)).filter_by(annee_scolaire=annee, ecole_id=ecole_id).scalar() or 0,
        recent_paiements=Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).order_by(Paiement.date_paiement.desc()).limit(5).all(),
        garcons=Eleve.query.filter_by(sexe='M', annee_scolaire=annee, ecole_id=ecole_id).count(),
        filles=Eleve.query.filter_by(sexe='F', annee_scolaire=annee, ecole_id=ecole_id).count())

from models import Classe, Matiere
