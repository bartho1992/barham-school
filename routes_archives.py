from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import (
    db, Ecole, AnneeScolaire, Classe, Eleve, Note, Paiement, Bulletin,
    Assiduite, CahierTexte, NotificationParent, Message
)
from helpers import get_current_ecole_id, get_current_annee
from sqlalchemy import text, inspect

archives_bp = Blueprint('archives_bp', __name__, url_prefix='/archives')


def _ensure_archive_tables():
    """Crée les tables _archive si elles n'existent pas déjà."""
    inspector = inspect(db.engine)
    existing = inspector.get_table_names()

    archive_defs = {
        'assiduite_archive': """
            CREATE TABLE IF NOT EXISTS assiduite_archive (
                id INTEGER PRIMARY KEY,
                eleve_id INTEGER NOT NULL,
                classe_id INTEGER,
                ecole_id INTEGER NOT NULL DEFAULT 1,
                date_evenement TEXT NOT NULL,
                type_evenement TEXT NOT NULL DEFAULT 'Absent',
                motif TEXT,
                justifie BOOLEAN DEFAULT 0,
                annee_scolaire TEXT DEFAULT '2024-2025',
                created_at DATETIME
            )
        """,
        'cahier_texte_archive': """
            CREATE TABLE IF NOT EXISTS cahier_texte_archive (
                id INTEGER PRIMARY KEY,
                classe_id INTEGER NOT NULL,
                matiere_id INTEGER NOT NULL,
                enseignant TEXT,
                date_seance TEXT NOT NULL,
                contenu TEXT NOT NULL,
                devoirs TEXT,
                observations TEXT,
                annee_scolaire TEXT DEFAULT '2024-2025',
                ecole_id INTEGER NOT NULL DEFAULT 1
            )
        """,
        'notification_parent_archive': """
            CREATE TABLE IF NOT EXISTS notification_parent_archive (
                id INTEGER PRIMARY KEY,
                eleve_id INTEGER NOT NULL,
                type_notif TEXT NOT NULL,
                message TEXT NOT NULL,
                canal TEXT DEFAULT 'sms',
                statut TEXT DEFAULT 'envoye',
                date_envoi DATETIME,
                ecole_id INTEGER NOT NULL DEFAULT 1
            )
        """,
        'message_archive': """
            CREATE TABLE IF NOT EXISTS message_archive (
                id INTEGER PRIMARY KEY,
                expediteur_id INTEGER NOT NULL,
                destinataire_id INTEGER,
                sujet TEXT NOT NULL,
                contenu TEXT NOT NULL,
                lu BOOLEAN DEFAULT 0,
                date_envoi DATETIME,
                ecole_id INTEGER NOT NULL DEFAULT 1
            )
        """
    }

    for table_name, ddl in archive_defs.items():
        if table_name not in existing:
            db.session.execute(text(ddl))
    db.session.commit()


@archives_bp.route('/')
@login_required
def archives():
    ecole_id = get_current_ecole_id()
    current_annee = get_current_annee()
    ecole = Ecole.query.get(ecole_id)

    # Récupérer toutes les années scolaires distinctes depuis les élèves
    annees_eleves = db.session.query(Eleve.annee_scolaire).filter(
        Eleve.ecole_id == ecole_id,
        Eleve.annee_scolaire.isnot(None),
        Eleve.annee_scolaire != ''
    ).distinct().order_by(Eleve.annee_scolaire.desc()).all()

    # Récupérer aussi depuis AnneeScolaire
    annees_db = AnneeScolaire.query.filter_by(ecole_id=ecole_id).order_by(AnneeScolaire.annee.desc()).all()

    # Fusionner et dédupliquer
    seen = set()
    annees_list = []
    for row in annees_eleves:
        a = row[0]
        if a and a not in seen:
            seen.add(a)
            annees_list.append(a)
    for an in annees_db:
        if an.annee and an.annee not in seen:
            seen.add(an.annee)
            annees_list.append(an.annee)

    # Préparer les stats pour chaque année
    stats_annees = []
    for annee in annees_list:
        if annee == current_annee:
            continue  # on n'archive pas l'année courante

        nb_classes = db.session.query(Eleve.classe_id).filter(
            Eleve.ecole_id == ecole_id,
            Eleve.annee_scolaire == annee
        ).distinct().count()

        nb_eleves = Eleve.query.filter_by(
            ecole_id=ecole_id,
            annee_scolaire=annee
        ).count()

        nb_paiements = Paiement.query.filter_by(
            ecole_id=ecole_id,
            annee_scolaire=annee
        ).count()

        # Vérifier si déjà archivée (données non critiques déplacées)
        _ensure_archive_tables()
        deja_archivee = False
        try:
            cnt = db.session.execute(
                text("SELECT COUNT(*) FROM assiduite_archive WHERE ecole_id = :eid AND annee_scolaire = :a"),
                {'eid': ecole_id, 'a': annee}
            ).scalar()
            if cnt and cnt > 0:
                deja_archivee = True
        except:
            pass

        stats_annees.append({
            'annee': annee,
            'nb_classes': nb_classes,
            'nb_eleves': nb_eleves,
            'nb_paiements': nb_paiements,
            'deja_archivee': deja_archivee
        })

    return render_template('archives/index.html',
        ecole=ecole,
        current_annee=current_annee,
        stats_annees=stats_annees)


@archives_bp.route('/archiver/<annee>', methods=['POST'])
@login_required
def archiver_annee(annee):
    ecole_id = get_current_ecole_id()
    current_annee = get_current_annee()

    if annee == current_annee:
        flash("Impossible d'archiver l'année scolaire en cours.", 'danger')
        return redirect(url_for('archives_bp.archives'))

    _ensure_archive_tables()

    try:
        # 1. Déplacer Assiduite
        db.session.execute(text("""
            INSERT INTO assiduite_archive (id, eleve_id, classe_id, ecole_id, date_evenement, type_evenement, motif, justifie, annee_scolaire, created_at)
            SELECT id, eleve_id, classe_id, ecole_id, date_evenement, type_evenement, motif, justifie, annee_scolaire, created_at
            FROM assiduite WHERE ecole_id = :eid AND annee_scolaire = :a
        """), {'eid': ecole_id, 'a': annee})
        db.session.execute(text("DELETE FROM assiduite WHERE ecole_id = :eid AND annee_scolaire = :a"),
                           {'eid': ecole_id, 'a': annee})

        # 2. Déplacer CahierTexte
        db.session.execute(text("""
            INSERT INTO cahier_texte_archive (id, classe_id, matiere_id, enseignant, date_seance, contenu, devoirs, observations, annee_scolaire, ecole_id)
            SELECT id, classe_id, matiere_id, enseignant, date_seance, contenu, devoirs, observations, annee_scolaire, ecole_id
            FROM cahier_texte WHERE ecole_id = :eid AND annee_scolaire = :a
        """), {'eid': ecole_id, 'a': annee})
        db.session.execute(text("DELETE FROM cahier_texte WHERE ecole_id = :eid AND annee_scolaire = :a"),
                           {'eid': ecole_id, 'a': annee})

        # 3. Déplacer NotificationParent
        db.session.execute(text("""
            INSERT INTO notification_parent_archive (id, eleve_id, type_notif, message, canal, statut, date_envoi, ecole_id)
            SELECT id, eleve_id, type_notif, message, canal, statut, date_envoi, ecole_id
            FROM notification_parent WHERE ecole_id = :eid
        """), {'eid': ecole_id})
        # Notifications : pas de annee_scolaire direct, on les archive toutes pour l'école
        # On ne supprime que celles liées à des élèves de l'année
        db.session.execute(text("""
            DELETE FROM notification_parent WHERE ecole_id = :eid
            AND eleve_id IN (SELECT id FROM eleve WHERE ecole_id = :eid2 AND annee_scolaire = :a)
        """), {'eid': ecole_id, 'eid2': ecole_id, 'a': annee})

        # 4. Déplacer Message
        db.session.execute(text("""
            INSERT INTO message_archive (id, expediteur_id, destinataire_id, sujet, contenu, lu, date_envoi, ecole_id)
            SELECT id, expediteur_id, destinataire_id, sujet, contenu, lu, date_envoi, ecole_id
            FROM message WHERE ecole_id = :eid
        """), {'eid': ecole_id})
        db.session.execute(text("DELETE FROM message WHERE ecole_id = :eid"),
                           {'eid': ecole_id})

        db.session.commit()
        flash(f"Année scolaire {annee} archivée avec succès.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'archivage : {str(e)}", 'danger')

    return redirect(url_for('archives_bp.archives'))


@archives_bp.route('/consulter/<annee>')
@login_required
def consulter_annee(annee):
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)

    # Classes de l'année
    classes_ids = db.session.query(Eleve.classe_id).filter(
        Eleve.ecole_id == ecole_id,
        Eleve.annee_scolaire == annee,
        Eleve.classe_id.isnot(None)
    ).distinct().all()
    classes_ids = [c[0] for c in classes_ids if c[0]]

    classes_data = []
    total_eleves = 0
    total_paiements_montant = 0.0
    total_notes = 0

    for cid in classes_ids:
        classe = Classe.query.get(cid)
        nom_classe = classe.nom if classe else f"Classe #{cid}"

        nb_eleves = Eleve.query.filter_by(
            ecole_id=ecole_id, annee_scolaire=annee, classe_id=cid
        ).count()

        nb_paiements = Paiement.query.filter_by(
            ecole_id=ecole_id, annee_scolaire=annee
        ).filter(Paiement.eleve_id.in_(
            db.session.query(Eleve.id).filter_by(classe_id=cid, annee_scolaire=annee)
        )).count()

        montant_paiements = db.session.query(db.func.sum(Paiement.montant)).filter(
            Paiement.ecole_id == ecole_id,
            Paiement.annee_scolaire == annee
        ).filter(Paiement.eleve_id.in_(
            db.session.query(Eleve.id).filter_by(classe_id=cid, annee_scolaire=annee)
        )).scalar() or 0.0

        nb_notes = Note.query.filter_by(
            annee_scolaire=annee, classe_id=cid
        ).count()

        classes_data.append({
            'nom': nom_classe,
            'nb_eleves': nb_eleves,
            'nb_paiements': nb_paiements,
            'montant_paiements': montant_paiements,
            'nb_notes': nb_notes
        })

        total_eleves += nb_eleves
        total_paiements_montant += montant_paiements
        total_notes += nb_notes

    # Stats archivées (non critiques)
    _ensure_archive_tables()
    nb_assiduite = 0
    nb_cahier = 0
    nb_notifs = 0
    nb_messages = 0
    try:
        nb_assiduite = db.session.execute(
            text("SELECT COUNT(*) FROM assiduite_archive WHERE ecole_id = :eid AND annee_scolaire = :a"),
            {'eid': ecole_id, 'a': annee}
        ).scalar() or 0
        nb_cahier = db.session.execute(
            text("SELECT COUNT(*) FROM cahier_texte_archive WHERE ecole_id = :eid AND annee_scolaire = :a"),
            {'eid': ecole_id, 'a': annee}
        ).scalar() or 0
        nb_notifs = db.session.execute(
            text("SELECT COUNT(*) FROM notification_parent_archive WHERE ecole_id = :eid"),
            {'eid': ecole_id}
        ).scalar() or 0
        nb_messages = db.session.execute(
            text("SELECT COUNT(*) FROM message_archive WHERE ecole_id = :eid"),
            {'eid': ecole_id}
        ).scalar() or 0
    except:
        pass

    stats = {
        'total_eleves': total_eleves,
        'total_classes': len(classes_data),
        'total_paiements_montant': total_paiements_montant,
        'total_notes': total_notes,
        'nb_assiduite': nb_assiduite,
        'nb_cahier': nb_cahier,
        'nb_notifs': nb_notifs,
        'nb_messages': nb_messages,
    }

    return render_template('archives/consulter.html',
        ecole=ecole, annee=annee, classes_data=classes_data, stats=stats)
