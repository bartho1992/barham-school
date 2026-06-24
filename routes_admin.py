from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Ecole, AnneeScolaire, LoginAttempt
from app import app, get_current_ecole_id
import random
import string

def generate_random_key(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(random.choice(chars) for _ in range(length))}"

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'super_users': flash('Accès réservé','danger'); return redirect(url_for('dashboard'))
    from models import User, Licence, AnneeScolaire, FactureLicence
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    ecoles = Ecole.query.all()
    users = User.query.all()
    licences = Licence.query.order_by(Licence.created_at.desc()).all()
    annees = AnneeScolaire.query.filter_by(ecole_id=ecole_id).order_by(AnneeScolaire.annee.desc()).all()
    count_paiements_attente = FactureLicence.query.filter_by(statut='en_attente').count()
    
    # Si aucune école n'existe, fournir un placeholder pour éviter les crashs
    if ecole is None:
        ecole = Ecole(nom='Aucun etablissement', identifiant='---')
    
    return render_template('admin.html', 
                         ecole=ecole, 
                         ecoles=ecoles, 
                         users=users, 
                         licences=licences, 
                         annees=annees,
                         all_ecoles=ecoles,
                         count_paiements_attente=count_paiements_attente,
                         aucune_ecole=len(ecoles) == 0)

@app.route('/admin/ecole', methods=['GET','POST'])
@app.route('/admin/ecole/<int:id>', methods=['GET','POST'])
@login_required
def admin_ecole(id=None):
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    
    if id:
        e = Ecole.query.get_or_404(id)
    else:
        # Si pas d'ID, on prend l'école courante ou la première
        from app import get_current_ecole_id
        e = Ecole.query.get(get_current_ecole_id()) or Ecole.query.first()
    
    annees = AnneeScolaire.query.filter_by(ecole_id=e.id).order_by(AnneeScolaire.annee.desc()).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_ecole':
            nom = request.form.get('nom', '').strip()
            if nom:
                nouvelle_ecole = Ecole(nom=nom, identifiant=generate_random_key("ECL"))
                db.session.add(nouvelle_ecole)
                db.session.commit()
                flash(f'Établissement {nom} ajouté','success')
                return redirect(url_for('admin_ecole', id=nouvelle_ecole.id))
                
        elif action == 'add_annee':
            nouvelle_annee = request.form.get('nouvelle_annee', '').strip()
            if nouvelle_annee and not AnneeScolaire.query.filter_by(annee=nouvelle_annee, ecole_id=e.id).first():
                db.session.add(AnneeScolaire(annee=nouvelle_annee, ecole_id=e.id))
                db.session.commit()
                flash('Année scolaire ajoutée','success')
            elif nouvelle_annee:
                flash('Cette année scolaire existe déjà pour cet établissement','warning')
                
        elif action == 'delete_annee':
            annee_id = request.form.get('annee_id')
            annee = AnneeScolaire.query.get(annee_id)
            if annee and annee.ecole_id == e.id:
                db.session.delete(annee)
                db.session.commit()
                flash('Année scolaire supprimée','success')
                
        elif action == 'set_active':
            annee_id = request.form.get('annee_id')
            AnneeScolaire.query.filter_by(ecole_id=e.id).update({AnneeScolaire.active: False})
            annee = AnneeScolaire.query.get(annee_id)
            if annee and annee.ecole_id == e.id:
                annee.active = True
                e.annee_scolaire = annee.annee
                if session.get('ecole_id') == e.id:
                    session['annee_scolaire'] = annee.annee
                db.session.commit()
                flash(f'Année scolaire {annee.annee} activée','success')
                
        elif action == 'update_ecole':
            for f in ['nom','adresse','tel','annee_scolaire','zone']:
                setattr(e, f, request.form.get(f))
            db.session.commit()
            flash('Mise à jour établissement OK','success')
            
        return redirect(url_for('admin_ecole', id=e.id))
        
    ecoles = Ecole.query.all()
    return render_template('admin_ecole.html', ecole=e, ecoles=ecoles, annees=annees)

@app.route('/changer-ecole/<int:id>')
@login_required
def changer_ecole(id):
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    e = Ecole.query.get_or_404(id)
    session['ecole_id'] = e.id
    session['annee_scolaire'] = e.annee_scolaire
    flash(f'Établissement changé pour : {e.nom}', 'info')
    return redirect(request.referrer or url_for('dashboard'))

champs_dev = ['nom','adresse','tel','annee_scolaire','zone','dev','email','type_ecole','directeur','chef_etablissement','slogan','autorisation','code_etablissement','ia','ief']

@app.route('/admin/dev', methods=['GET','POST'])
@app.route('/admin/dev/<int:id>', methods=['GET','POST'])
@login_required
def admin_dev(id=None):
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    
    if id:
        e = Ecole.query.get_or_404(id)
    else:
        from app import get_current_ecole_id
        e = Ecole.query.get(get_current_ecole_id()) or Ecole.query.first()
        
    if request.method == 'POST':
        for f in champs_dev:
            setattr(e, f, request.form.get(f))
        db.session.commit()
        flash(f'Configuration développeur pour {e.nom} enregistrée','success')
        return redirect(url_for('admin_dev', id=e.id))
    
    return render_template('admin_ecole_dev.html', ecole=e)

@app.route('/admin/import', methods=['GET','POST'])
@login_required
def admin_import():
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    if request.method == 'POST':
        import csv, os
        from models import Eleve, Classe
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'BASE_ELEVES.csv')
        if not os.path.exists(file_path): flash(f'Fichier non trouvé: {file_path}', 'danger'); return redirect(url_for('admin'))
        
        ecole_id = get_current_ecole_id()
        e = Ecole.query.get(ecole_id)
        annee = session.get('annee_scolaire', e.annee_scolaire if e else '')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                found_header = False
                count = 0
                for row in reader:
                    if not found_header:
                        if row and row[0] == 'CODE ELEVE': found_header = True
                        continue
                    if not row or not row[0]: continue
                    
                    code, _, prenom, nom, sexe, cls_name = row[0:6]
                    tel, d_naiss, l_naiss, tuteur, addr, p_ecole, d_entree, obs = row[6:14]
                    
                    cls = Classe.query.filter_by(nom=cls_name).first()
                    if not cls:
                        cls = Classe(nom=cls_name)
                        db.session.add(cls); db.session.commit()
                    
                    if not Eleve.query.filter_by(code=code, annee_scolaire=annee).first():
                        el = Eleve(code=code, prenom=prenom, nom=nom, sexe=sexe, classe_id=cls.id,
                                   tel=tel, date_naissance=d_naiss, lieu_naissance=l_naiss,
                                   tuteur=tuteur, adresse=addr, precedente_ecole=p_ecole,
                                   date_entree=d_entree, observations=obs, annee_scolaire=annee)
                        db.session.add(el)
                        count += 1
                db.session.commit()
                flash(f'{count} élèves importés avec succès', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'import: {str(e)}', 'danger')
        return redirect(url_for('admin'))
    ecole_id = get_current_ecole_id()
    return render_template('admin_import.html', ecole=Ecole.query.get(ecole_id))
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    from models import User
    ecole_id = get_current_ecole_id()
    return render_template('admin/users.html', users=User.query.all(), ecole=Ecole.query.get(ecole_id))

@app.route('/admin/users/ajouter', methods=['GET','POST'])
@login_required
def admin_user_ajouter():
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    from models import User, Ecole
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        ecole_id = request.form.get('ecole_id')
        
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà', 'danger')
        else:
            u = User(username=username, role=role, identifiant=generate_random_key("USR"))
            if ecole_id: u.ecole_id = int(ecole_id)
            u.set_password(password)
            db.session.add(u); db.session.commit()
            flash('Utilisateur créé', 'success')
            return redirect(url_for('admin_users'))
    ecole_id = get_current_ecole_id()
    return render_template('admin/user_form.html', ecole=Ecole.query.get(ecole_id), all_ecoles=Ecole.query.all())

@app.route('/admin/users/modifier/<int:id>', methods=['GET','POST'])
@login_required
def admin_user_modifier(id):
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    from models import User, Ecole
    u = User.query.get_or_404(id)
    if request.method == 'POST':
        u.username = request.form.get('username')
        u.role = request.form.get('role')
        ecole_id = request.form.get('ecole_id')
        u.ecole_id = int(ecole_id) if ecole_id else None
        
        password = request.form.get('password')
        if password: u.set_password(password)
        db.session.commit()
        flash('Utilisateur modifié', 'success')
        return redirect(url_for('admin_users'))
    ecole_id = get_current_ecole_id()
    return render_template('admin/user_form.html', user=u, ecole=Ecole.query.get(ecole_id), all_ecoles=Ecole.query.all())

@app.route('/admin/users/supprimer/<int:id>', methods=['POST'])
@login_required
def admin_user_supprimer(id):
    if current_user.role != 'super_users': return redirect(url_for('dashboard'))
    from models import User
    u = User.query.get_or_404(id)
    if u.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte', 'danger')
    else:
        db.session.delete(u); db.session.commit()
        flash('Utilisateur supprimé', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/ecole/supprimer/<int:id>', methods=['POST'])
@login_required
def admin_ecole_supprimer(id):
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur.', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import (User, Eleve, Classe, Matiere, Note, Bulletin, 
                       Personnel, Salaire, Paiement, Document, Licence,
                       FactureLicence, TransactionLicence, AnneeScolaire, Scolarite)
    
    ecole = Ecole.query.get_or_404(id)
    est_derniere = Ecole.query.count() <= 1
    nom_ecole = ecole.nom
    
    try:
        # Supprimer toutes les données liées dans l'ordre (enfants d'abord)
        # SAUF les super_users (développeurs) qui sont préservés
        for model in [Eleve, Classe, Matiere, Note, Bulletin,
                      Personnel, Salaire, Paiement, Document,
                      FactureLicence, TransactionLicence, AnneeScolaire, Scolarite]:
            if hasattr(model, 'ecole_id'):
                model.query.filter_by(ecole_id=id).delete()
        
        # Utilisateurs : supprimer seulement les non-super_users
        User.query.filter(User.ecole_id == id, User.role != 'super_users').delete()
        # Mettre à NULL l'ecole_id des super_users liés à cette école
        User.query.filter(User.ecole_id == id, User.role == 'super_users').update({'ecole_id': None})
        
        # Licences (peut avoir ecole_id nullable)
        Licence.query.filter_by(ecole_id=id).delete()
        
        # Supprimer l'école
        db.session.delete(ecole)
        db.session.commit()
        
        if est_derniere:
            flash(f'Établissement « {nom_ecole} » supprimé. ⚠️ Aucun établissement restant — créez-en un pour continuer.', 'warning')
            return redirect(url_for('admin'))
        
        flash(f'Établissement « {nom_ecole} » supprimé avec toutes ses données.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/changer-annee', methods=['GET', 'POST'])
@login_required
def changer_annee():
    annee = request.args.get('annee', request.form.get('annee', '')).strip()
    if annee:
        session['annee_scolaire'] = annee
        session.modified = True
        flash(f'Annee scolaire changee en {annee}', 'success')
    return redirect(url_for('dashboard'))


# =============================================================================
# ROUTES DEVELOPPEUR - GESTION DES SAUVEGARDES (SUPER USER UNIQUEMENT)
# =============================================================================

from backup_manager import backup_manager
from flask import send_file, jsonify
import os

@app.route('/admin/backup')
@login_required
def admin_backup():
    """Page de gestion des sauvegardes (réservée au développeur)"""
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    backups = backup_manager.list_backups()
    db_info = backup_manager.get_db_info()
    
    return render_template('admin/backup.html', 
                         backups=backups, 
                         db_info=db_info,
                         ecole=Ecole.query.get(get_current_ecole_id()))

@app.route('/admin/backup/create', methods=['POST'])
@login_required
def backup_create():
    """Créer une nouvelle sauvegarde"""
    if current_user.role != 'super_users':
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403
    
    try:
        commentaire = request.form.get('commentaire', '').strip()
        result = backup_manager.create_backup(commentaire)
        
        if result['success']:
            flash(f"Sauvegarde créée: {result['filename']}", 'success')
        else:
            flash(f"Erreur: {result.get('error', 'Erreur inconnue')}", 'danger')
            
        return redirect(url_for('admin_backup'))
        
    except Exception as e:
        flash(f"Erreur lors de la création de la sauvegarde: {str(e)}", 'danger')
        return redirect(url_for('admin_backup'))

@app.route('/admin/backup/download/<filename>')
@login_required
def backup_download(filename):
    """Télécharger un fichier de sauvegarde"""
    if current_user.role != 'super_users':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        backup_path = os.path.join(backup_manager.backup_dir, filename)
        
        if not os.path.exists(backup_path):
            flash('Fichier de sauvegarde non trouvé', 'danger')
            return redirect(url_for('admin_backup'))
            
        return send_file(backup_path, 
                        as_attachment=True, 
                        download_name=filename,
                        mimetype='application/x-sqlite3')
                        
    except Exception as e:
        flash(f"Erreur lors du téléchargement: {str(e)}", 'danger')
        return redirect(url_for('admin_backup'))

@app.route('/admin/backup/restore/<filename>', methods=['POST'])
@login_required
def backup_restore(filename):
    """Restaurer une sauvegarde"""
    if current_user.role != 'super_users':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        result = backup_manager.restore_backup(filename)
        
        if result['success']:
            message = f"Restauration réussie: {filename}"
            if result.get('safety_backup'):
                message += f" (Sauvegarde de sécurité créée: {result['safety_backup']})"
            flash(message, 'success')
        else:
            flash(f"Erreur lors de la restauration: {result.get('error', 'Erreur inconnue')}", 'danger')
            
        return redirect(url_for('admin_backup'))
        
    except Exception as e:
        flash(f"Erreur lors de la restauration: {str(e)}", 'danger')
        return redirect(url_for('admin_backup'))

@app.route('/admin/backup/delete/<filename>', methods=['POST'])
@login_required
def backup_delete(filename):
    """Supprimer une sauvegarde"""
    if current_user.role != 'super_users':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        result = backup_manager.delete_backup(filename)
        
        if result['success']:
            flash(f"Sauvegarde supprimée: {filename}", 'success')
        else:
            flash(f"Erreur: {result.get('error', 'Erreur inconnue')}", 'danger')
            
        return redirect(url_for('admin_backup'))
        
    except Exception as e:
        flash(f"Erreur lors de la suppression: {str(e)}", 'danger')
        return redirect(url_for('admin_backup'))


# =============================================================================
# ROUTES DEVELOPPEUR - LOGS SYSTEME ET MONITORING
# =============================================================================

from system_logger import system_logger
import sqlite3

@app.route('/admin/logs')
@login_required
def admin_logs():
    """Page de visualisation des logs système"""
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    # Paramètres de filtrage
    days = request.args.get('days', 7, type=int)
    category = request.args.get('category', '')
    level = request.args.get('level', '')
    
    # Construire la requête SQL
    query = "SELECT * FROM activity_logs WHERE timestamp > datetime('now', '-{} days')".format(days)
    params = []
    
    if category:
        query += " AND category = ?"
        params.append(category)
    if level:
        query += " AND level = ?"
        params.append(level)
        
    query += " ORDER BY timestamp DESC LIMIT 500"
    
    # Exécuter la requête
    logs = []
    categories = []
    levels = []
    
    try:
        conn = sqlite3.connect(str(system_logger.LOGS_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Récupérer les logs
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        
        # Récupérer les catégories distinctes
        cursor.execute("SELECT DISTINCT category FROM activity_logs ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        
        # Récupérer les niveaux distincts
        cursor.execute("SELECT DISTINCT level FROM activity_logs ORDER BY level")
        levels = [row[0] for row in cursor.fetchall()]
        
        conn.close()
    except Exception as e:
        flash(f"Erreur lors de la récupération des logs: {str(e)}", 'warning')
    
    # Récupérer les statistiques
    stats = system_logger.get_stats(days=days)
    
    return render_template('admin/logs.html',
                         logs=logs,
                         stats=stats,
                         categories=categories,
                         levels=levels,
                         selected_days=days,
                         selected_category=category,
                         selected_level=level,
                         ecole=Ecole.query.get(get_current_ecole_id()))

@app.route('/admin/logs/stats')
@login_required
def admin_logs_stats():
    """API pour récupérer les statistiques de logs"""
    if current_user.role != 'super_users':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    days = request.args.get('days', 7, type=int)
    stats = system_logger.get_stats(days=days)
    
    return jsonify(stats)

@app.route('/admin/logs/clear', methods=['POST'])
@login_required
def admin_logs_clear():
    """Vider les logs anciens"""
    if current_user.role != 'super_users':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        days = request.form.get('days', 30, type=int)
        
        conn = sqlite3.connect(str(system_logger.LOGS_DB))
        cursor = conn.cursor()
        
        # Supprimer les logs plus anciens que X jours
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        tables = ['activity_logs', 'login_logs', 'error_logs']
        total_deleted = 0
        
        for table in tables:
            cursor.execute(
                f"DELETE FROM {table} WHERE timestamp < ?",
                (cutoff_str,)
            )
            total_deleted += cursor.rowcount
            
        conn.commit()
        conn.close()
        
        # Logger l'action
        system_logger.log_activity(
            level='WARNING',
            category='admin',
            action='Purge des logs',
            description=f'{total_deleted} entrées supprimées (plus vieilles que {days} jours)',
            user=current_user
        )
        
        flash(f'{total_deleted} entrées de logs supprimées (plus vieilles que {days} jours)', 'success')
        
    except Exception as e:
        flash(f'Erreur lors de la purge des logs: {str(e)}', 'danger')
        
    return redirect(url_for('admin_logs'))


# =============================================================================
# ROUTES DEVELOPPEUR - SÉCURITÉ AVANCÉE
# =============================================================================

@app.route('/admin/security', methods=['GET', 'POST'])
@login_required
def admin_security():
    """Page de configuration de la sécurité (réservée au développeur)"""
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    
    if request.method == 'POST':
        try:
            ecole.session_timeout = int(request.form.get('session_timeout', 30))
            ecole.max_login_attempts = int(request.form.get('max_login_attempts', 5))
            ecole.lockout_duration = int(request.form.get('lockout_duration', 15))
            ecole.ip_whitelist = request.form.get('ip_whitelist', '').strip()
            
            db.session.commit()
            
            # Logger l'action
            system_logger.log_activity(
                level='WARNING',
                category='security',
                action='Mise à jour paramètres sécurité',
                description='Modification des paramètres de timeout et brute-force',
                user=current_user
            )
            
            flash('Paramètres de sécurité mis à jour', 'success')
            return redirect(url_for('admin_security'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
            
    # Récupérer les dernières tentatives de connexion échouées
    failed_attempts = LoginAttempt.query.filter_by(success=False).order_by(LoginAttempt.timestamp.desc()).limit(10).all()
    
    return render_template('admin/security.html', 
                          ecole=ecole, 
                          failed_attempts=failed_attempts)


# =============================================================================
# ROUTES DEVELOPPEUR - CONFIGURATION EMAIL (SMTP)
# =============================================================================

from mailer import mailer

@app.route('/admin/email', methods=['GET', 'POST'])
@login_required
def admin_email():
    """Page de configuration SMTP (réservée au développeur)"""
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save':
            try:
                ecole.smtp_server = request.form.get('smtp_server', '').strip()
                ecole.smtp_port = int(request.form.get('smtp_port', 587))
                ecole.smtp_user = request.form.get('smtp_user', '').strip()
                ecole.smtp_password = request.form.get('smtp_password', '').strip()
                ecole.smtp_use_tls = 'smtp_use_tls' in request.form
                ecole.email_expediteur = request.form.get('email_expediteur', '').strip()
                
                db.session.commit()
                flash('Configuration Email enregistrée', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de l\'enregistrement: {str(e)}', 'danger')
                
        elif action == 'test':
            dest = request.form.get('test_email', '').strip()
            if dest:
                success, msg = mailer.send_email(
                    dest, 
                    "Test EduGestion IA", 
                    "Ceci est un email de test pour valider votre configuration SMTP."
                )
                if success:
                    flash(msg, 'success')
                else:
                    flash(f"Erreur d'envoi: {msg}", 'danger')
            else:
                flash("Veuillez saisir une adresse email de test", 'warning')
                
        return redirect(url_for('admin_email'))
        
    return render_template('admin/email.html', ecole=ecole)


# =============================================================================
# ROUTES DEVELOPPEUR - MAINTENANCE ET MIGRATIONS
# =============================================================================

@app.route('/admin/maintenance', methods=['GET', 'POST'])
@login_required
def admin_maintenance():
    """Outils de maintenance avancée (réservée au développeur)"""
    if current_user.role != 'super_users':
        flash('Accès réservé au développeur', 'danger')
        return redirect(url_for('dashboard'))
    
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'school.db')
    tables = []
    sql_result = None
    sql_error = None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Liste des tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'execute_sql':
                query = request.form.get('sql_query', '').strip()
                if query:
                    try:
                        cursor.execute(query)
                        if query.lower().startswith('select'):
                            columns = [description[0] for description in cursor.description]
                            rows = cursor.fetchall()
                            sql_result = {'columns': columns, 'rows': rows}
                        else:
                            conn.commit()
                            flash(f"Requête exécutée avec succès ({cursor.rowcount} lignes affectées)", 'success')
                            
                        # Logger l'action SQL
                        system_logger.log_activity(
                            level='CRITICAL',
                            category='maintenance',
                            action='Exécution SQL brute',
                            description=f'Requête: {query[:100]}...',
                            user=current_user
                        )
                    except Exception as e:
                        sql_error = str(e)
            
            elif action == 'integrity_check':
                cursor.execute("PRAGMA integrity_check")
                res = cursor.fetchone()[0]
                if res == 'ok':
                    flash("Intégrité de la base de données : OK", 'success')
                else:
                    flash(f"Problème d'intégrité détecté : {res}", 'danger')
                    
        conn.close()
    except Exception as e:
        flash(f"Erreur base de données: {str(e)}", 'danger')
        
    return render_template('admin/maintenance.html', 
                         tables=tables, 
                         sql_result=sql_result, 
                         sql_error=sql_error,
                         ecole=Ecole.query.get(get_current_ecole_id()))

@app.route('/admin/maintenance/export/<table_name>')
@login_required
def admin_export_json(table_name):
    """Exporte une table au format JSON"""
    if current_user.role != 'super_users':
        return jsonify({'error': 'Accès non autorisé'}), 403
        
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'school.db')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


