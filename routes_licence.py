import string, random, hashlib
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ecole, Licence
from app import app, get_current_ecole_id
from datetime import datetime, timezone

SECRET = 'barham-licence-2024'

def generer_cle(date_expiration_str, ecole_nom=''):
    """Génère une clé de licence au format XXXX-XXXX-XXXX-XXXX avec timestamp unique"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    seed = f"{date_expiration_str}-{ecole_nom}-{SECRET}-{timestamp}"
    hash_val = hashlib.sha256(seed.encode()).hexdigest().upper()
    chars = string.ascii_uppercase + string.digits
    key_chars = ''
    for i in range(16):
        idx = int(hash_val[i*2:i*2+2], 16) % len(chars)
        key_chars += chars[idx]
    cle = f"{key_chars[0:4]}-{key_chars[4:8]}-{key_chars[8:12]}-{key_chars[12:16]}"
    return cle

@app.route('/licence')
def licence_page():
    from app import get_current_ecole_id
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id) or Ecole.query.first()
    licence = Licence.licence_active_for_ecole(ecole_id)
    if licence:
        return redirect(url_for('dashboard'))
    return render_template('licence/activation.html', ecole=ecole)

@app.route('/licence/activer', methods=['POST'])
def licence_activer():
    cle = request.form.get('cle', '').strip().upper()
    ecole_id = request.form.get('ecole_id', type=int)
    
    if not cle:
        flash('Veuillez saisir la clé de licence', 'danger')
        return redirect(url_for('licence_page'))

    # Vérifier que la clé existe dans la base (a été générée par le développeur)
    licence = Licence.query.filter_by(cle=cle).first()
    if not licence:
        flash('Clé de licence invalide ou inexistante', 'danger')
        return redirect(url_for('licence_page'))
    
    if licence.active:
        flash('Cette licence est déjà activée', 'warning')
        return redirect(url_for('licence_page'))

    if not licence.est_valide:
        flash('Cette licence a expiré', 'danger')
        return redirect(url_for('licence_page'))

    # Lier la licence à l'établissement
    if ecole_id:
        licence.ecole_id = ecole_id
    licence.active = True
    licence.date_activation = datetime.now(timezone.utc)
    db.session.commit()
    
    flash('Licence activée avec succès pour votre établissement !', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/licences')
@login_required
def admin_licences():
    if current_user.role != 'super_users':
        return redirect(url_for('dashboard'))
    licences = Licence.query.order_by(Licence.created_at.desc()).all()
    all_ecoles = Ecole.query.all()
    return render_template('admin/licences.html', licences=licences, ecole=Ecole.query.get(get_current_ecole_id()), all_ecoles=all_ecoles)

@app.route('/admin/licences/generer', methods=['GET', 'POST'])
@login_required
def admin_licence_generer():
    if current_user.role != 'super_users':
        return redirect(url_for('dashboard'))

    cle_generee = None
    all_ecoles = Ecole.query.all()
    
    if request.method == 'POST':
        date_exp = request.form.get('date_expiration', '').strip()
        ecole_nom = request.form.get('ecole_nom', '').strip()
        ecole_id = request.form.get('ecole_id', type=int)
        
        if date_exp:
            cle_generee = generer_cle(date_exp, ecole_nom)
            try:
                date_expiration = datetime.strptime(date_exp, '%Y-%m-%d')
                date_expiration = date_expiration.replace(tzinfo=timezone.utc)
                licence = Licence(cle=cle_generee, date_expiration=date_expiration,
                                  active=False, ecole_nom=ecole_nom, ecole_id=ecole_id)
                db.session.add(licence)
                db.session.commit()
                flash(f'Clé générée pour {ecole_nom or "tous"}', 'success')
            except ValueError:
                flash('Format de date invalide', 'danger')

    return render_template('admin/licence_generer.html', cle_generee=cle_generee, ecole=Ecole.query.get(get_current_ecole_id()), all_ecoles=all_ecoles)


@app.route('/admin/licences/supprimer/<int:id>', methods=['POST'])
@login_required
def admin_licence_supprimer(id):
    if current_user.role != 'super_users':
        return redirect(url_for('dashboard'))
    
    licence = Licence.query.get_or_404(id)
    cle = licence.cle
    db.session.delete(licence)
    db.session.commit()
    flash(f'Licence {cle} supprimée', 'success')
    return redirect(url_for('admin_licences'))

@app.route('/admin/licences/supprimer-bulk', methods=['POST'])
@login_required
def admin_licence_supprimer_bulk():
    if current_user.role not in ('dev', 'super_users'):
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    licence_ids = request.form.getlist('licence_ids[]')
    if not licence_ids:
        flash('Aucune licence sélectionnée', 'warning')
        return redirect(url_for('admin_licences'))
    
    ids = [int(id) for id in licence_ids if id.isdigit()]
    count = 0
    for lid in ids:
        licence = Licence.query.get(lid)
        if licence:
            db.session.delete(licence)
            count += 1
    
    db.session.commit()
    flash(f'{count} licence(s) supprimée(s)', 'success')
    return redirect(url_for('admin_licences'))
