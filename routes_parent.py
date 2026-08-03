from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Ecole, Eleve, Classe, Matiere, Note, Paiement, Assiduite
from helpers import get_current_ecole_id, get_current_annee

parent_bp = Blueprint('parent_bp', __name__, url_prefix='/parent')


@parent_bp.route('/')
def parent_login():
    """Page d'accueil parent : saisie du code d'accès"""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    return render_template('parent/login.html', ecole=ecole)


@parent_bp.route('/acces', methods=['POST'])
def parent_acces():
    """Vérifie le code_parent et ouvre le portail si valide"""
    code = request.form.get('code_parent', '').strip()
    if not code:
        flash('Veuillez entrer votre code d\'accès.', 'danger')
        return redirect(url_for('parent_bp.parent_login'))

    ecole_id = get_current_ecole_id()
    eleve = Eleve.query.filter_by(code_parent=code, ecole_id=ecole_id).first()

    if not eleve:
        flash('Code d\'accès invalide. Veuillez réessayer.', 'danger')
        return redirect(url_for('parent_bp.parent_login'))

    session['parent_eleve_id'] = eleve.id
    flash(f'Bienvenue, portail de {eleve.prenom} {eleve.nom}.', 'success')
    return redirect(url_for('parent_bp.parent_portail'))


@parent_bp.route('/portail')
def parent_portail():
    """Portail parent : infos élève, notes, paiements, absences"""
    eleve_id = session.get('parent_eleve_id')
    if not eleve_id:
        flash('Veuillez vous connecter avec votre code d\'accès.', 'warning')
        return redirect(url_for('parent_bp.parent_login'))

    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()

    eleve = Eleve.query.get(eleve_id)
    if not eleve or eleve.ecole_id != ecole_id:
        session.pop('parent_eleve_id', None)
        flash('Élève introuvable.', 'danger')
        return redirect(url_for('parent_bp.parent_login'))

    # --- Notes par trimestre (moyennes par matière) ---
    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()
    notes_par_trimestre = {}
    for trimestre in [1, 2, 3]:
        notes_trim = Note.query.filter_by(
            eleve_id=eleve_id, trimestre=trimestre, annee_scolaire=annee
        ).all()
        notes_dict = {}
        for note in notes_trim:
            matiere = Matiere.query.get(note.matiere_id) if note.matiere_id else None
            nom_matiere = matiere.nom if matiere else '—'
            notes_dict[nom_matiere] = note
        # Calculer la moyenne générale du trimestre
        tp, tc = 0, 0
        for note in notes_trim:
            if note.moyenne:
                mat = Matiere.query.get(note.matiere_id)
                coef = mat.coefficient if mat else 1
                tp += note.moyenne * coef
                tc += coef
        moyenne_trim = round(tp / tc, 2) if tc > 0 else None
        notes_par_trimestre[trimestre] = {
            'notes': notes_dict,
            'moyenne': moyenne_trim
        }

    # --- Paiements récents (20 derniers) ---
    paiements = Paiement.query.filter_by(
        eleve_id=eleve_id, annee_scolaire=annee, ecole_id=ecole_id
    ).order_by(Paiement.date_paiement.desc()).limit(20).all()

    # --- Absences récentes (20 dernières) ---
    absences = Assiduite.query.filter_by(
        eleve_id=eleve_id, annee_scolaire=annee, ecole_id=ecole_id
    ).order_by(Assiduite.date_evenement.desc()).limit(20).all()

    return render_template('parent/portail.html',
                         ecole=ecole, eleve=eleve,
                         notes_par_trimestre=notes_par_trimestre,
                         matieres=matieres,
                         paiements=paiements,
                         absences=absences,
                         annee=annee)


@parent_bp.route('/deconnexion')
def parent_deconnexion():
    """Déconnexion : efface la session parent"""
    session.pop('parent_eleve_id', None)
    flash('Vous avez été déconnecté du portail parent.', 'info')
    return redirect(url_for('parent_bp.parent_login'))
