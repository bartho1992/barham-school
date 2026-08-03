"""
Barham School — Notifications SMS/WhatsApp aux parents
Blueprint notifications_bp, prefix /notifications
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ecole, Eleve, Classe, NotificationParent
from helpers import get_current_ecole_id
from datetime import datetime, timezone

notifications_bp = Blueprint('notifications_bp', __name__, url_prefix='/notifications')

TYPE_LABELS = {
    'absence': 'Absence',
    'retard': 'Retard',
    'paiement': 'Paiement',
    'evenement': 'Événement',
}

MESSAGES_PREDEFINIS = {
    'absence': "Nous vous informons que votre enfant est absent(e) aujourd'hui. Veuillez nous contacter pour justifier cette absence.",
    'retard': "Votre enfant est arrivé(e) en retard aujourd'hui. Merci de veiller à la ponctualité.",
    'paiement': "Nous vous rappelons que des frais de scolarité restent en suspens. Merci de régulariser la situation dans les meilleurs délais.",
    'evenement': "Nous vous informons qu'un événement important aura lieu prochainement. Merci de consulter le carnet de correspondance.",
}


@notifications_bp.route('/')
@login_required
def notifications():
    """Page principale : historique des notifications envoyées"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)

    # Filtres
    filtre_type = request.args.get('type', '')
    filtre_date = request.args.get('date', '')
    filtre_recherche = request.args.get('recherche', '')

    query = NotificationParent.query.filter_by(ecole_id=ecole_id)

    if filtre_type:
        query = query.filter_by(type_notif=filtre_type)
    if filtre_date:
        query = query.filter(
            NotificationParent.date_envoi >= f"{filtre_date} 00:00:00",
            NotificationParent.date_envoi <= f"{filtre_date} 23:59:59"
        )
    if filtre_recherche:
        query = query.join(Eleve).filter(
            db.or_(
                Eleve.nom.ilike(f"%{filtre_recherche}%"),
                Eleve.prenom.ilike(f"%{filtre_recherche}%"),
                NotificationParent.message.ilike(f"%{filtre_recherche}%")
            )
        )

    notifs = query.order_by(NotificationParent.date_envoi.desc()).limit(200).all()

    # Pour le modal : classes
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()

    return render_template('notifications/index.html',
                           ecole=ecole,
                           notifs=notifs,
                           classes=classes,
                           type_labels=TYPE_LABELS,
                           messages_predefinis=MESSAGES_PREDEFINIS,
                           filtre_type=filtre_type,
                           filtre_date=filtre_date,
                           filtre_recherche=filtre_recherche)


@notifications_bp.route('/envoyer')
@login_required
def envoyer_page():
    """Page standalone — redirige vers la page principale (le modal s'y trouve)"""
    return redirect(url_for('notifications_bp.notifications', nouveau='1'))


@notifications_bp.route('/envoyer', methods=['POST'])
@login_required
def envoyer():
    """Enregistre la/les notification(s) dans NotificationParent"""
    ecole_id = get_current_ecole_id()

    type_notif = request.form.get('type_notif', '').strip()
    canal = request.form.get('canal', 'sms').strip()
    message = request.form.get('message', '').strip()
    eleve_id = request.form.get('eleve_id', type=int)
    groupe_type = request.form.get('groupe_type', '').strip()
    groupe_classe_id = request.form.get('groupe_classe_id', type=int)

    if not type_notif or type_notif not in TYPE_LABELS:
        flash('Veuillez sélectionner un type de notification valide.', 'warning')
        return redirect(url_for('notifications_bp.notifications'))

    if not message:
        flash('Veuillez saisir un message.', 'warning')
        return redirect(url_for('notifications_bp.notifications'))

    if canal not in ('sms', 'whatsapp'):
        canal = 'sms'

    # Déterminer la liste des élèves destinataires
    destinataires = []

    if eleve_id:
        eleve = Eleve.query.filter_by(id=eleve_id, ecole_id=ecole_id).first()
        if eleve:
            destinataires.append(eleve)
        else:
            flash('Élève introuvable.', 'danger')
            return redirect(url_for('notifications_bp.notifications'))
    elif groupe_type:
        if groupe_type == 'classe' and groupe_classe_id:
            classe = Classe.query.filter_by(id=groupe_classe_id, ecole_id=ecole_id).first()
            if not classe:
                flash('Classe introuvable.', 'danger')
                return redirect(url_for('notifications_bp.notifications'))
            eleves = Eleve.query.filter_by(classe_id=groupe_classe_id, ecole_id=ecole_id).all()
            destinataires.extend(eleves)
        elif groupe_type == 'impayes':
            from models import Paiement
            ids_rows = db.session.query(Paiement.eleve_id).filter(
                Paiement.montant_restant > 0,
                Paiement.ecole_id == ecole_id
            ).distinct().all()
            ids = [r[0] for r in ids_rows]
            if ids:
                eleves = Eleve.query.filter(Eleve.id.in_(ids), Eleve.ecole_id == ecole_id).all()
                destinataires.extend(eleves)
        elif groupe_type == 'tous':
            destinataires = Eleve.query.filter_by(ecole_id=ecole_id).all()

        if not destinataires:
            flash('Aucun élève trouvé pour ce groupe.', 'warning')
            return redirect(url_for('notifications_bp.notifications'))
    else:
        flash('Veuillez sélectionner un élève ou un groupe.', 'warning')
        return redirect(url_for('notifications_bp.notifications'))

    # Créer une notification par élève
    count = 0
    for eleve in destinataires:
        notif = NotificationParent(
            eleve_id=eleve.id,
            type_notif=type_notif,
            message=message,
            canal=canal,
            statut='envoye',
            ecole_id=ecole_id
        )
        db.session.add(notif)
        count += 1

    db.session.commit()
    flash(f'{count} notification(s) envoyée(s) avec succès en {canal.upper()}.', 'success')
    return redirect(url_for('notifications_bp.notifications'))


@notifications_bp.route('/historique')
@login_required
def historique():
    """API JSON pour l'historique des notifications"""
    ecole_id = get_current_ecole_id()

    filtre_type = request.args.get('type', '')
    filtre_date = request.args.get('date', '')

    query = NotificationParent.query.filter_by(ecole_id=ecole_id)

    if filtre_type:
        query = query.filter_by(type_notif=filtre_type)
    if filtre_date:
        query = query.filter(
            NotificationParent.date_envoi >= f"{filtre_date} 00:00:00",
            NotificationParent.date_envoi <= f"{filtre_date} 23:59:59"
        )

    notifs = query.order_by(NotificationParent.date_envoi.desc()).limit(500).all()

    result = []
    for n in notifs:
        result.append({
            'id': n.id,
            'eleve': f'{n.eleve.prenom} {n.eleve.nom}',
            'classe': n.eleve.classe.nom if n.eleve.classe else '—',
            'type_notif': n.type_notif,
            'type_label': TYPE_LABELS.get(n.type_notif, n.type_notif),
            'message': n.message,
            'canal': n.canal,
            'statut': n.statut,
            'date_envoi': n.date_envoi.strftime('%d/%m/%Y %H:%M') if n.date_envoi else '',
        })

    return jsonify({'notifications': result, 'total': len(result)})


@notifications_bp.route('/eleves/search')
@login_required
def search_eleves():
    """API JSON pour l'autocomplete de recherche d'élève"""
    ecole_id = get_current_ecole_id()
    q = request.args.get('q', '').strip()

    if len(q) < 2:
        return jsonify({'eleves': []})

    eleves = Eleve.query.filter(
        Eleve.ecole_id == ecole_id,
        db.or_(
            Eleve.nom.ilike(f'%{q}%'),
            Eleve.prenom.ilike(f'%{q}%'),
            Eleve.code.ilike(f'%{q}%')
        )
    ).limit(20).all()

    result = []
    for e in eleves:
        classe_nom = e.classe.nom if e.classe else '—'
        result.append({
            'id': e.id,
            'nom': e.nom,
            'prenom': e.prenom,
            'code': e.code,
            'classe': classe_nom,
            'label': f'{e.nom} {e.prenom} ({classe_nom})'
        })

    return jsonify({'eleves': result})
