"""
Barham School SaaS — Abonnement, Paiement, Facturation
Construit sur le système de licence existant (clé d'activation)
"""

import json, uuid
from datetime import datetime, timezone, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from models import db, Ecole, Licence, FactureLicence, TransactionLicence, User, AnneeScolaire
from app import app, get_current_ecole_id

# ============================================================
# PLANS + PASSERELLES
# ============================================================
PLANS = {
    'starter': {
        'nom': 'Starter', 'eleves_max': 150, 'personnel_max': 10,
        'prix_1mois': 5000, 'prix_3mois': 13500, 'prix_6mois': 21000, 'prix_12mois': 42000,
        'description': 'Petits établissements (maternelle, primaire)',
        'features': ['Jusqu\'à 150 élèves','10 personnels','Élèves & Classes','Notes & Bulletins','Finances & Paiements','Documents administratifs']
    },
    'standard': {
        'nom': 'Standard', 'eleves_max': 500, 'personnel_max': 50,
        'prix_1mois': 9000, 'prix_3mois': 24300, 'prix_6mois': 39000, 'prix_12mois': 78000,
        'description': 'Établissements moyens (collège, lycée)',
        'features': ['Jusqu\'à 500 élèves','50 personnels','Tout Starter +','Multi-classes avancé','Personnalisation bulletins','Export Excel/PDF','Support prioritaire']
    },
    'premium': {
        'nom': 'Premium', 'eleves_max': -1, 'personnel_max': -1,
        'prix_1mois': 16000, 'prix_3mois': 45000, 'prix_6mois': 75000, 'prix_12mois': 150000,
        'description': 'Grands établissements et groupes scolaires',
        'features': ['Élèves illimités','Personnel illimité','Tout Standard +','Multi-établissements','Gestion avancée','API intégration','Support 24/7']
    },
}

# WhatsApp du développeur pour notifications de paiement
DEV_WHATSAPP = '+221770589800'

PASSERELLES = {
    'manual':    {'nom': 'Espèces / Manuel',  'icone': 'bi-cash',        'actif': True},
    'wave':      {'nom': 'Wave Mobile Money', 'icone': 'bi-phone',       'actif': True},
    'orange_money': {'nom': 'Orange Money',   'icone': 'bi-phone-flip',  'actif': True},
    'stripe':    {'nom': 'Carte bancaire',    'icone': 'bi-credit-card', 'actif': True},
}

MODULES_DEFAUT = ['eleves','classes','notes','bulletins','finances','personnel','documents']

def get_licence_active(ecole_id):
    return Licence.licence_active_for_ecole(ecole_id)

# ============================================================
# PAGE PUBLIQUE — TARIFS
# ============================================================
@app.route('/pricing')
def pricing():
    ecole = Ecole.query.first()
    return render_template('saas/pricing.html', plans=PLANS, passerelles=PASSERELLES, ecole=ecole)

# ============================================================
# DASHBOARD ABONNEMENT (connecté)
# ============================================================
@app.route('/abonnement')
@login_required
def abonnement():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    licence = get_licence_active(ecole_id)
    from models import Eleve, Personnel

    # Développeur super_users = accès illimité gratuit
    est_dev = current_user.is_authenticated and current_user.role == 'dev'

    eleves_count = Eleve.query.filter_by(ecole_id=ecole_id).count()
    personnel_count = Personnel.query.filter_by(ecole_id=ecole_id).count()

    factures = FactureLicence.query.filter_by(ecole_id=ecole_id).order_by(
        FactureLicence.created_at.desc()).limit(10).all()
    transactions = TransactionLicence.query.filter_by(ecole_id=ecole_id).order_by(
        TransactionLicence.created_at.desc()).limit(10).all()

    # Stats
    total_paye = db.session.query(db.func.sum(FactureLicence.montant)).filter_by(
        ecole_id=ecole_id, statut='payee').scalar() or 0

    # Pourcentage barres de progression
    if est_dev:
        pct_eleves = 50
        pct_personnel = 50
    elif licence:
        pct_eleves = min(int(eleves_count / licence.eleves_max * 100), 100) if licence.eleves_max > 0 else 50
        pct_personnel = min(int(personnel_count / licence.personnel_max * 100), 100) if licence.personnel_max > 0 else 50
    else:
        pct_eleves = 50
        pct_personnel = 50

    return render_template('saas/abonnement.html',
        ecole=ecole, licence=licence, plans=PLANS,
        eleves_count=eleves_count, personnel_count=personnel_count,
        factures=factures, transactions=transactions,
        total_paye=total_paye, passerelles=PASSERELLES,
        pct_eleves=pct_eleves, pct_personnel=pct_personnel,
        est_dev=est_dev)


# ============================================================
# CHECKOUT
# ============================================================
@app.route('/abonnement/checkout', methods=['GET', 'POST'])
@login_required
def abonnement_checkout():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)

    plan_key = request.args.get('plan', 'starter')
    duree = int(request.args.get('duree', 12))  # 1, 3, 6 ou 12 mois

    if plan_key not in PLANS:
        flash('Plan invalide.', 'danger')
        return redirect(url_for('abonnement'))

    plan = PLANS[plan_key]
    if duree <= 1:
        montant = plan['prix_1mois']
        duree = 1
    elif duree <= 3:
        montant = plan['prix_3mois']
        duree = 3
    elif duree <= 6:
        montant = plan['prix_6mois']
        duree = 6
    else:
        montant = plan['prix_12mois']
        duree = 12

    return render_template('saas/checkout.html',
        ecole=ecole, plan_key=plan_key, duree=duree,
        plan=plan, montant=montant, passerelles=PASSERELLES)


# ============================================================
# PAIEMENT
# ============================================================
@app.route('/abonnement/payer', methods=['POST'])
@login_required
def abonnement_payer():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)

    plan_key = request.form.get('plan_key', 'starter')
    duree = int(request.form.get('duree', 12))
    passerelle = request.form.get('passerelle', 'manual')
    montant = float(request.form.get('montant', 0))

    if plan_key not in PLANS or passerelle not in PASSERELLES:
        flash('Paramètres invalides.', 'danger')
        return redirect(url_for('abonnement'))

    plan = PLANS[plan_key]
    description = f"Licence {plan['nom']} — {duree} mois"

    # Générer facture
    numero = FactureLicence.generer_numero()
    facture = FactureLicence(
        ecole_id=ecole_id, numero=numero, plan=plan_key,
        duree_mois=duree, montant=montant, devise='XOF',
        statut='en_attente', mode_paiement=passerelle,
        description=description
    )
    db.session.add(facture)
    db.session.flush()

    # Créer transaction
    tr = TransactionLicence(
        ecole_id=ecole_id, facture_id=facture.id,
        montant=montant, devise='XOF', passerelle=passerelle,
        statut='initiee', description=description,
        reference=f"{passerelle.upper()}-{uuid.uuid4().hex[:10]}"
    )
    db.session.add(tr)

    # --- En attente de validation par le dev (sans WhatsApp) ---
    facture.statut = 'en_attente'
    db.session.commit()
    
    flash(f'Votre demande de licence {plan["nom"]} ({duree} mois) a ete enregistree. Vous recevrez l\'acces apres validation.', 'info')
    return redirect(url_for('abonnement'))


# ============================================================
# CALLBACK / CONFIRMATION PAIEMENT
# ============================================================
@app.route('/abonnement/callback/<int:facture_id>')
@login_required
def abonnement_callback(facture_id):
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    facture = FactureLicence.query.filter_by(id=facture_id, ecole_id=ecole_id).first_or_404()

    if facture.statut != 'payee':
        facture.statut = 'en_attente'
        facture.date_paiement = datetime.now(timezone.utc)
        db.session.commit()
        
        flash('Votre paiement a ete declare. Votre licence sera activee apres validation.', 'info')

    return redirect(url_for('abonnement'))


# ============================================================
# ACTIVATION DE LICENCE (interne)
# ============================================================
def activer_licence(ecole_id, plan_key, duree_mois, montant, mode_paiement, facture_id=None):
    plan = PLANS[plan_key]
    date_exp = datetime.now(timezone.utc) + timedelta(days=duree_mois * 30)

    # Désactiver les anciennes licences
    Licence.query.filter_by(ecole_id=ecole_id, active=True).update({'active': False})

    # Créer une nouvelle licence SaaS
    cle_raw = f"SAAS-{ecole_id}-{plan_key}-{uuid.uuid4().hex[:8]}".upper()
    cle_format = f"{cle_raw[:4]}-{cle_raw[4:8]}-{cle_raw[8:12]}-{cle_raw[12:16]}"
    import hashlib
    hash_val = hashlib.sha256(f"{cle_raw}-secret".encode()).hexdigest().upper()
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    key_chars = ''
    for i in range(16):
        idx = int(hash_val[i*2:i*2+2], 16) % len(chars)
        key_chars += chars[idx]
    cle = f"{key_chars[0:4]}-{key_chars[4:8]}-{key_chars[8:12]}-{key_chars[12:16]}"

    licence = Licence(
        cle=cle, date_expiration=date_exp, active=True,
        date_activation=datetime.now(timezone.utc),
        ecole_id=ecole_id, ecole_nom=Ecole.query.get(ecole_id).nom,
        plan=plan_key, eleves_max=plan['eleves_max'],
        personnel_max=plan['personnel_max'],
        modules=json.dumps(MODULES_DEFAUT),
        prix_paye=montant, devise='XOF', mode_paiement=mode_paiement
    )
    db.session.add(licence)
    db.session.flush()

    # Lier la facture à la licence
    if facture_id:
        facture = FactureLicence.query.get(facture_id)
        if facture:
            facture.licence_id = licence.id

    db.session.commit()
    return licence


# ============================================================
# ESSAI GRATUIT 30 JOURS
# ============================================================
@app.route('/abonnement/essai', methods=['POST'])
@login_required
def abonnement_essai():
    ecole_id = get_current_ecole_id()
    existant = Licence.query.filter_by(ecole_id=ecole_id, active=True, essai=False).first()
    if existant and existant.est_valide:
        flash('Vous avez déjà une licence active.', 'warning')
        return redirect(url_for('abonnement'))

    # Désactiver anciens essais
    Licence.query.filter_by(ecole_id=ecole_id, essai=True).update({'active': False})

    plan = PLANS['starter']
    cle = f"ESSAI-{uuid.uuid4().hex[:12].upper()}"
    cle_f = f"{cle[:4]}-{cle[4:8]}-{cle[8:12]}-{cle[12:16]}"

    licence = Licence(
        cle=cle_f, date_expiration=datetime.now(timezone.utc) + timedelta(days=15),
        active=True, date_activation=datetime.now(timezone.utc),
        ecole_id=ecole_id, plan='starter', eleves_max=50,
        personnel_max=5, essai=True,
        modules=json.dumps(MODULES_DEFAUT),
        mode_paiement='essai_gratuit'
    )
    db.session.add(licence)
    db.session.commit()
    flash('Essai gratuit de 15 jours activé (50 élèves max) !', 'success')
    return redirect(url_for('abonnement'))


# ============================================================
# FACTURE PDF / VISUALISATION
# ============================================================
@app.route('/abonnement/facture/<int:facture_id>')
@login_required
def abonnement_facture(facture_id):
    ecole_id = get_current_ecole_id()
    facture = FactureLicence.query.filter_by(id=facture_id, ecole_id=ecole_id).first_or_404()
    ecole = Ecole.query.get(ecole_id)
    return render_template('saas/facture.html', facture=facture, ecole=ecole, plans=PLANS)


# ============================================================
# WEBHOOK (endpoint externe pour callbacks réels)
# ============================================================
@app.route('/api/webhook/<passerelle>', methods=['POST'])
def webhook_recevoir(passerelle):
    data = request.get_json(silent=True) or {}
    try:
        ref = data.get('reference') or data.get('transaction_id', '')
        facture = FactureLicence.query.filter_by(numero=ref).first() or \
                  TransactionLicence.query.filter_by(reference=ref).first()
        if facture:
            # Trouver la facture liée
            f = facture if isinstance(facture, FactureLicence) else facture.facture
            if f and f.statut != 'payee':
                f.statut = 'payee'
                f.date_paiement = datetime.now(timezone.utc)
                tr = TransactionLicence.query.filter_by(facture_id=f.id).first()
                if tr:
                    tr.statut = 'reussie'
                db.session.commit()
                # Activation automatique pour webhook reel
                activer_licence(f.ecole_id, f.plan, f.duree_mois, f.montant, f.mode_paiement, f.id)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# ADMIN — VALIDATION DES PAIEMENTS
# ============================================================
@app.route('/admin/paiements')
@login_required
def admin_paiements():
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    paiements = FactureLicence.query.filter_by(statut='en_attente').order_by(
        FactureLicence.created_at.desc()).all()
    paiements_valides = FactureLicence.query.filter_by(statut='payee').order_by(
        FactureLicence.date_paiement.desc()).limit(20).all()
    paiements_annules = FactureLicence.query.filter_by(statut='annulee').order_by(
        FactureLicence.created_at.desc()).limit(20).all()
    transactions = TransactionLicence.query.order_by(
        TransactionLicence.created_at.desc()).limit(50).all()
    licences = Licence.query.order_by(
        Licence.date_activation.desc()).limit(100).all()
    
    return render_template('saas/admin_paiements.html',
        paiements=paiements, paiements_valides=paiements_valides,
        paiements_annules=paiements_annules, transactions=transactions,
        plans=PLANS, count_attente=len(paiements), licences=licences)


@app.route('/admin/paiements/valider/<int:facture_id>', methods=['POST'])
@login_required
def admin_valider_paiement(facture_id):
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    facture = FactureLicence.query.get_or_404(facture_id)
    ecole = Ecole.query.get(facture.ecole_id)
    
    if facture.statut == 'en_attente':
        facture.statut = 'payee'
        facture.date_paiement = datetime.now(timezone.utc)
        tr = TransactionLicence.query.filter_by(facture_id=facture.id).first()
        if tr:
            tr.statut = 'reussie'
        db.session.commit()
        activer_licence(facture.ecole_id, facture.plan, facture.duree_mois,
                       facture.montant, facture.mode_paiement, facture.id)
        
        # Envoyer email de confirmation au client si possible
        user = User.query.filter_by(ecole_id=facture.ecole_id).first()
        if user and hasattr(user, 'email') and user.email:
            try:
                from mailer import mailer
                mailer.send_email(user.email,
                    f'Licence {PLANS[facture.plan]["nom"]} activée',
                    f'<h3>Votre licence est active !</h3><p>Plan : {PLANS[facture.plan]["nom"]}</p><p>Clé : <strong>Voir dans votre espace</strong></p>',
                    is_html=True)
            except:
                pass
        
        flash(f'Paiement de {ecole.nom if ecole else "ecole inconnue"} validé — Licence activée !', 'success')
    else:
        flash('Ce paiement n\'est plus en attente.', 'warning')
    
    return redirect(url_for('admin_paiements'))


@app.route('/admin/paiements/refuser/<int:facture_id>', methods=['POST'])
@login_required
def admin_refuser_paiement(facture_id):
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    facture = FactureLicence.query.get_or_404(facture_id)
    facture.statut = 'annulee'
    tr = TransactionLicence.query.filter_by(facture_id=facture.id).first()
    if tr:
        tr.statut = 'annulee'
    db.session.commit()
    flash('Paiement refusé.', 'warning')
    return redirect(url_for('admin_paiements'))


@app.route('/admin/paiements/supprimer/<int:facture_id>', methods=['POST'])
@login_required
def admin_supprimer_paiement(facture_id):
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    facture = FactureLicence.query.get_or_404(facture_id)
    # Supprimer la transaction liée
    TransactionLicence.query.filter_by(facture_id=facture.id).delete()
    # Supprimer la facture
    db.session.delete(facture)
    db.session.commit()
    flash('Paiement supprimé.', 'info')
    return redirect(url_for('admin_paiements'))


@app.route('/admin/paiements/supprimer-bulk', methods=['POST'])
@login_required
def admin_paiements_supprimer_bulk():
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé.', 'danger')
        return redirect(url_for('dashboard'))
    
    facture_ids = request.form.getlist('facture_ids[]')
    if not facture_ids:
        flash('Aucune facture sélectionnée.', 'warning')
        return redirect(url_for('admin_paiements'))
    
    fids = [int(fid) for fid in facture_ids]
    TransactionLicence.query.filter(TransactionLicence.facture_id.in_(fids)).delete(synchronize_session=False)
    count = FactureLicence.query.filter(FactureLicence.id.in_(fids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f'{count} facture(s) supprimée(s)', 'info')
    return redirect(url_for('admin_paiements'))


@app.route('/admin/transactions/supprimer/<int:tr_id>', methods=['POST'])
@login_required
def admin_supprimer_transaction(tr_id):
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    tr = TransactionLicence.query.get_or_404(tr_id)
    db.session.delete(tr)
    db.session.commit()
    flash('Transaction supprimée.', 'info')
    return redirect(url_for('admin_paiements'))


# ============================================================
# TUTORIEL / GUIDE D'UTILISATION
# ============================================================
@app.route('/tutoriel')
def tutoriel():
    # Accessible sans connexion (public)
    from flask_login import current_user
    ecole = current_user.ecole if current_user.is_authenticated else None
    return render_template('saas/tutoriel.html', ecole=ecole)


# ============================================================
# ETABLISSEMENT (tous les utilisateurs avec licence)
# ============================================================
@app.route('/etablissement', methods=['GET','POST'])
@login_required
def etablissement():
    if current_user.role not in ('dev', 'super_users'):
        flash("Accès réservé à l'administrateur de l'établissement.", 'danger')
        return redirect(url_for('dashboard'))
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get_or_404(ecole_id)
    annees = AnneeScolaire.query.filter_by(ecole_id=e.id).order_by(AnneeScolaire.annee.desc()).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_ecole':
            for champ in ['nom','adresse','tel','annee_scolaire','zone','ia','type_ecole','slogan','code_etablissement']:
                val = request.form.get(champ)
                if val is not None:
                    setattr(e, champ, val.strip() if isinstance(val, str) else val)
            # Mettre a jour la session
            session['annee_scolaire'] = e.annee_scolaire if e.annee_scolaire else ''
            db.session.commit()
            flash('Etablissement mis a jour.', 'success')
            
        elif action == 'add_annee':
            nouvelle = request.form.get('nouvelle_annee', '').strip()
            if nouvelle:
                existing = AnneeScolaire.query.filter_by(annee=nouvelle, ecole_id=e.id).first()
                if not existing:
                    db.session.add(AnneeScolaire(annee=nouvelle, ecole_id=e.id))
                    db.session.commit()
                    flash(f'Annee {nouvelle} ajoutee.', 'success')
                else:
                    flash('Cette annee existe deja.', 'warning')
                    
        elif action == 'delete_annee':
            aid = request.form.get('annee_id')
            a = AnneeScolaire.query.get(aid)
            if a and a.ecole_id == e.id:
                db.session.delete(a)
                db.session.commit()
                flash('Annee supprimee.', 'info')
                
        elif action == 'set_active':
            aid = request.form.get('annee_id')
            AnneeScolaire.query.filter_by(ecole_id=e.id).update({AnneeScolaire.active: False})
            a = AnneeScolaire.query.get(aid)
            if a and a.ecole_id == e.id:
                a.active = True
                e.annee_scolaire = a.annee
                session['annee_scolaire'] = a.annee
                db.session.commit()
                flash(f'Annee {a.annee} activee.', 'success')
        
        return redirect(url_for('etablissement'))
    
    return render_template('saas/etablissement.html', ecole=e, annees=annees)


# ============================================================
# UTILISATEURS (tous les utilisateurs avec licence)
# ============================================================
@app.route('/utilisateurs', methods=['GET','POST'])
@login_required
def utilisateurs():
    if current_user.role not in ('dev', 'super_users'):
        flash("Accès réservé à l'administrateur.", 'danger')
        return redirect(url_for('dashboard'))
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get_or_404(ecole_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_user':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            role = request.form.get('role', 'user')
            
            # Interdiction de créer un compte 'dev' (super-admin global)
            if role == 'dev':
                flash("Le rôle 'dev' ne peut pas être créé depuis cette page.", 'danger')
            elif not username or len(password) < 8:
                flash('Identifiant requis et mot de passe >= 8 caracteres.', 'danger')
            elif User.query.filter_by(username=username).first():
                flash(f"L'identifiant '{username}' existe deja.", 'danger')
            else:
                user = User(username=username, role=role, ecole_id=ecole_id)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash(f'Utilisateur {username} cree avec le role {role}.', 'success')
                
        elif action == 'delete_user':
            uid = request.form.get('user_id')
            u = User.query.get(uid)
            if u and u.ecole_id == ecole_id and u.id != current_user.id and u.role != 'dev':
                db.session.delete(u)
                db.session.commit()
                flash(f'Utilisateur {u.username} supprime.', 'info')
            else:
                flash('Action non autorisee.', 'danger')
        
        return redirect(url_for('utilisateurs'))
    
    users = User.query.filter_by(ecole_id=ecole_id).all()
    return render_template('saas/utilisateurs.html', ecole=e, users=users)
