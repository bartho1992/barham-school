"""
Barham School — Messagerie interne
Blueprint messages_bp, prefix /messages
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Message, User, Ecole
from helpers import get_current_ecole_id
from datetime import datetime, timezone

messages_bp = Blueprint('messages_bp', __name__, url_prefix='/messages')


@messages_bp.route('/')
@login_required
def messages():
    """Boîte de réception (inbox)"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    msg_recus = Message.query.filter_by(
        destinataire_id=current_user.id,
        ecole_id=ecole_id
    ).order_by(Message.date_envoi.desc()).all()

    non_lus_count = Message.query.filter_by(
        destinataire_id=current_user.id,
        lu=False,
        ecole_id=ecole_id
    ).count()

    return render_template('messages/index.html',
                           ecole=ecole,
                           messages=msg_recus,
                           onglet='inbox',
                           non_lus_count=non_lus_count)


@messages_bp.route('/envoyes')
@login_required
def messages_envoyes():
    """Messages envoyés"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    msg_envoyes = Message.query.filter_by(
        expediteur_id=current_user.id,
        ecole_id=ecole_id
    ).order_by(Message.date_envoi.desc()).all()

    non_lus_count = Message.query.filter_by(
        destinataire_id=current_user.id,
        lu=False,
        ecole_id=ecole_id
    ).count()

    return render_template('messages/index.html',
                           ecole=ecole,
                           messages=msg_envoyes,
                           onglet='envoyes',
                           non_lus_count=non_lus_count)


@messages_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def message_nouveau():
    """Formulaire nouveau message (GET) — POST redirige vers /envoyer"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    users = User.query.filter_by(ecole_id=ecole_id).order_by(User.username).all()

    # Pré-remplissage pour "Répondre"
    reply_to = request.args.get('reply_to', type=int)
    reply_sujet = request.args.get('sujet', '')

    return render_template('messages/nouveau.html',
                           ecole=ecole,
                           users=users,
                           reply_to=reply_to,
                           reply_sujet=reply_sujet)


@messages_bp.route('/envoyer', methods=['POST'])
@login_required
def message_envoyer():
    """Envoyer un message"""
    ecole_id = get_current_ecole_id()
    destinataire_id = request.form.get('destinataire_id', type=int)
    sujet = request.form.get('sujet', '').strip()
    contenu = request.form.get('contenu', '').strip()

    if not destinataire_id:
        flash('Veuillez sélectionner un destinataire.', 'warning')
        return redirect(url_for('messages_bp.message_nouveau'))

    if not sujet:
        flash('Veuillez saisir un sujet.', 'warning')
        return redirect(url_for('messages_bp.message_nouveau'))

    if not contenu:
        flash('Veuillez saisir un message.', 'warning')
        return redirect(url_for('messages_bp.message_nouveau'))

    destinataire = User.query.filter_by(id=destinataire_id, ecole_id=ecole_id).first()
    if not destinataire:
        flash('Destinataire introuvable.', 'danger')
        return redirect(url_for('messages_bp.message_nouveau'))

    msg = Message(
        expediteur_id=current_user.id,
        destinataire_id=destinataire_id,
        sujet=sujet,
        contenu=contenu,
        ecole_id=ecole_id
    )
    db.session.add(msg)
    db.session.commit()

    flash('Message envoyé avec succès.', 'success')
    return redirect(url_for('messages_bp.messages_envoyes'))


@messages_bp.route('/<int:id>')
@login_required
def message_lire(id):
    """Lire un message (marquer comme lu si destinataire)"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    msg = Message.query.get_or_404(id)

    # Vérifier que l'utilisateur est expéditeur ou destinataire
    if msg.expediteur_id != current_user.id and msg.destinataire_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('messages_bp.messages'))

    if msg.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('messages_bp.messages'))

    # Marquer comme lu si on est le destinataire
    if msg.destinataire_id == current_user.id and not msg.lu:
        msg.lu = True
        db.session.commit()

    return render_template('messages/lire.html',
                           ecole=ecole,
                           message=msg)


@messages_bp.route('/non_lus/count')
@login_required
def messages_non_lus_count():
    """API JSON : nombre de messages non lus (badge sidebar)"""
    ecole_id = get_current_ecole_id()
    count = Message.query.filter_by(
        destinataire_id=current_user.id,
        lu=False,
        ecole_id=ecole_id
    ).count()
    return jsonify({'non_lus': count})
