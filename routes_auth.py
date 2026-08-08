from flask import render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import joinedload
from models import db, User, Ecole, LoginAttempt
from app import app
from system_logger import system_logger
from datetime import datetime, timedelta, timezone

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '')

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
    from models import AnneeScolaire, Licence
    from datetime import timedelta
    
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
        
        # Creer l'ecole (annee scolaire laissee vide, l'admin la definira)
        ecole = Ecole(
            nom=nom_ecole.upper(),
            identifiant=f"EC-{nom_ecole[:4].upper()}-{Ecole.query.count() + 1}"
        )
        db.session.add(ecole)
        db.session.flush()
        
        # Creer le compte
        user = User(username=username, role='super_users', ecole_id=ecole.id)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Creer une annee scolaire par defaut
        now = datetime.now(timezone.utc)
        annee = f'{now.year}-{now.year + 1}' if now.month >= 9 else f'{now.year - 1}-{now.year}'
        try:
            if not AnneeScolaire.query.filter_by(ecole_id=ecole.id, annee=annee).first():
                an = AnneeScolaire(ecole_id=ecole.id, annee=annee, active=True)
                db.session.add(an)
                db.session.flush()
        except:
            # Si l'annee existe deja (unicite), utiliser un suffixe unique
            try:
                an = AnneeScolaire(ecole_id=ecole.id, annee=f"{annee}-{ecole.id}", active=True)
                db.session.add(an)
                db.session.flush()
            except:
                pass  # L'annee scolaire n'est pas critique pour la licence d'essai
        
        # Licence d'essai 30 jours automatique
        import random, string
        def gen_cle(prefix):
            return f"{prefix}-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))}"
        
        cle = gen_cle("BS-ESSAI")
        while Licence.query.filter_by(cle=cle).first():
            cle = gen_cle("BS-ESSAI")
        
        licence = Licence(
            cle=cle,
            date_expiration=now + timedelta(days=30),
            active=True,
            date_activation=now,
            ecole_id=ecole.id,
            ecole_nom=ecole.nom,
            plan='starter',
            eleves_max=150,
            personnel_max=10,
            essai=True,
            modules='["eleves","classes","matieres","notes","bulletins","finances","personnel","documents"]',
            prix_paye=0,
            devise='XOF'
        )
        db.session.add(licence)
        db.session.commit()
        
        login_user(user)
        flash(f'Bienvenue {nom_ecole.upper()} ! Vous beneficiez d\'un essai gratuit de 30 jours.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/wizard/skip')
@login_required
def wizard_skip():
    session['wizard_done'] = True
    return redirect(url_for('dashboard'))

@app.route('/wizard')
@login_required
def wizard():
    from models import Classe, Eleve
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    nb_classes = Classe.query.filter_by(ecole_id=ecole_id).count()
    nb_eleves = Eleve.query.filter_by(ecole_id=ecole_id).count()
    
    # Determiner l'etape actuelle
    if nb_classes == 0:
        etape = 1
    elif nb_eleves == 0:
        etape = 2
    else:
        etape = 3
    
    def safe_url(endpoint, **kwargs):
        try:
            return url_for(endpoint, **kwargs)
        except Exception:
            return '#'

    return render_template(
        'wizard.html',
        ecole=ecole,
        etape=etape,
        nb_classes=nb_classes,
        nb_eleves=nb_eleves,
        classe_url=safe_url('classe_ajouter'),
        eleve_url=safe_url('eleve_ajouter'),
        parametres_url=safe_url('parametres_financiers'),
        dashboard_url=safe_url('dashboard'),
        wizard_skip_url=safe_url('wizard_skip'),
    )

@app.route('/')
@login_required
def dashboard():
    from models import Eleve, Classe, Personnel, Paiement, Scolarite, CategorieTarif, TarifService, AbonnementService, Assiduite
    from app import get_current_ecole_id
    from datetime import datetime
    ecole_id = get_current_ecole_id()
    
    # Rediriger vers le wizard si premiere utilisation
    if not session.get('wizard_done'):
        nb_classes = Classe.query.filter_by(ecole_id=ecole_id).count()
        nb_eleves = Eleve.query.filter_by(ecole_id=ecole_id).count()
        if nb_classes == 0 or nb_eleves == 0:
            return redirect(url_for('wizard'))
    
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    eleves_filter = db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).filter(eleves_filter).all()
    eleve_ids = [el.id for el in eleves]
    mois_scolaires = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    
    # Stats de base
    total_eleves = len(eleves)
    total_classes = Classe.query.filter_by(ecole_id=ecole_id).count()
    total_personnel = Personnel.query.filter_by(ecole_id=ecole_id).count()
    
    # Paiements
    total_paiements = db.session.query(db.func.sum(Paiement.montant)).filter_by(annee_scolaire=annee, ecole_id=ecole_id).scalar() or 0
    today_encaisse = db.session.query(db.func.sum(Paiement.montant)).filter(
        db.func.date(Paiement.date_paiement) == datetime.now().date(),
        Paiement.annee_scolaire == annee,
        Paiement.ecole_id == ecole_id
    ).scalar() or 0
    
    # Impayés : calcul réel (scolarité due - payée + services)
    scolarites = Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all()
    scolarite_map = {s.classe_id: s for s in scolarites}
    paiements_map = {}
    paiements_par_mois = {}
    for p in Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        if p.eleve_id not in paiements_map:
            paiements_map[p.eleve_id] = {}
        key = p.type_paiement or ''
        paiements_map[p.eleve_id][key] = paiements_map[p.eleve_id].get(key, 0) + p.montant
        paiements_par_mois[key] = paiements_par_mois.get(key, 0) + p.montant
    categories = CategorieTarif.query.filter_by(ecole_id=ecole_id).all()
    tarifs_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        tarifs_map[(t.classe_id, t.categorie_id)] = t
    abos_map = {}
    if eleve_ids:
        abos = AbonnementService.query.filter(AbonnementService.actif == True, AbonnementService.eleve_id.in_(eleve_ids)).all()
    else:
        abos = []
    for a in abos:
        if a.eleve_id not in abos_map:
            abos_map[a.eleve_id] = set()
        abos_map[a.eleve_id].add(a.categorie_id)
    
    total_impayes = 0
    nb_eleves_impayes = 0
    total_du = 0
    for eleve in eleves:
        if not eleve.classe: continue
        scol = scolarite_map.get(eleve.classe_id)
        payes = paiements_map.get(eleve.id, {})
        abos = abos_map.get(eleve.id, set())
        scolarite_due = scol.total_annuel if scol else 0
        scolarite_paye = sum(payes.get(m, 0) for m in mois_scolaires)
        services_due = 0
        services_paye = 0
        for cat in categories:
            tarif = tarifs_map.get((eleve.classe_id, cat.id))
            if not tarif or cat.id not in abos: continue
            services_due += tarif.total_annuel
            services_paye += payes.get(cat.nom, 0)
        due_total = scolarite_due + services_due
        reste = max(due_total - scolarite_paye - services_paye, 0)
        total_du += due_total
        total_impayes += reste
        if reste > 0: nb_eleves_impayes += 1
    
    # Répartition filles/garçons
    garcons = sum(1 for eleve in eleves if eleve.sexe == 'M')
    filles = sum(1 for eleve in eleves if eleve.sexe == 'F')
    
    # Top classes par effectif
    classes_count_map = {
        classe_id: total for classe_id, total in db.session.query(Eleve.classe_id, db.func.count(Eleve.id))
        .filter(Eleve.ecole_id == ecole_id)
        .filter(eleves_filter)
        .filter(Eleve.classe_id != None)
        .group_by(Eleve.classe_id)
        .all()
    }
    classes_stats = []
    for c in Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all():
        nb = classes_count_map.get(c.id, 0)
        classes_stats.append({'nom': c.nom, 'nb': nb})
    classes_stats.sort(key=lambda x: x['nb'], reverse=True)
    
    # Paiements par mois pour graphique
    paiements_mois = {m: int(paiements_par_mois.get(m, 0)) for m in mois_scolaires}
    
    # Derniers paiements
    recent_paiements = Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).options(
        joinedload(Paiement.eleve).joinedload(Eleve.classe)
    ).order_by(Paiement.date_paiement.desc()).limit(10).all()

    # Assiduité
    date_jour = datetime.now().date().isoformat()
    assiduite_jour = {
        type_evt: total for type_evt, total in db.session.query(Assiduite.type_evenement, db.func.count(Assiduite.id))
        .filter_by(ecole_id=ecole_id, annee_scolaire=annee, date_evenement=date_jour)
        .group_by(Assiduite.type_evenement)
        .all()
    }
    assiduite_annee = {
        type_evt: total for type_evt, total in db.session.query(Assiduite.type_evenement, db.func.count(Assiduite.id))
        .filter_by(ecole_id=ecole_id, annee_scolaire=annee)
        .group_by(Assiduite.type_evenement)
        .all()
    }
    absents_jour = int(assiduite_jour.get('Absent', 0))
    retards_jour = int(assiduite_jour.get('Retard', 0))
    absences_annee = int(assiduite_annee.get('Absent', 0))
    retards_annee = int(assiduite_annee.get('Retard', 0))

    # Taux de recouvrement
    taux_recouvrement = round((total_paiements / total_du * 100) if total_du > 0 else 0, 1)
    
    return render_template('dashboard.html', ecole=e,
        total_eleves=total_eleves, total_classes=total_classes,
        total_personnel=total_personnel, total_paiements=total_paiements,
        total_impayes=total_impayes, nb_eleves_impayes=nb_eleves_impayes,
        today_encaisse=today_encaisse, taux_recouvrement=taux_recouvrement,
        recent_paiements=recent_paiements, garcons=garcons, filles=filles,
        classes_stats=classes_stats, paiements_mois=paiements_mois,
        mois_scolaires=mois_scolaires, absents_jour=absents_jour,
        retards_jour=retards_jour, absences_annee=absences_annee,
        retards_annee=retards_annee)

from models import Classe, Matiere
