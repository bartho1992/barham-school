from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ecole, Classe, Matiere, EmploiDuTemps
from helpers import get_current_ecole_id, get_current_annee

edt_bp = Blueprint('edt_bp', __name__, url_prefix='/edt')

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
CRENEAUX = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00']

@edt_bp.route('/')
@login_required
def edt():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()
    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()

    classe_id = request.args.get('classe_id', type=int)
    creneaux_edt = {}
    edt_list = []
    if classe_id:
        edt_list = EmploiDuTemps.query.filter_by(
            classe_id=classe_id, ecole_id=ecole_id, annee_scolaire=annee
        ).order_by(EmploiDuTemps.jour, EmploiDuTemps.heure_debut).all()
        for e in edt_list:
            creneaux_edt[(e.jour, e.heure_debut)] = e

    return render_template('edt/index.html',
        ecole=ecole, classes=classes, matieres=matieres,
        classe_id=classe_id, jours=JOURS, creneaux=CRENEAUX,
        creneaux_edt=creneaux_edt, edt_list=edt_list)


@edt_bp.route('/ajouter', methods=['POST'])
@login_required
def edt_ajouter():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    classe_id = request.form.get('classe_id', type=int)
    matiere_id = request.form.get('matiere_id', type=int)
    jour = request.form.get('jour', '').strip()
    heure_debut = request.form.get('heure_debut', '').strip()
    heure_fin = request.form.get('heure_fin', '').strip()
    salle = request.form.get('salle', '').strip()
    enseignant = request.form.get('enseignant', '').strip()
    couleur = request.form.get('couleur', '#3b82f6').strip()

    if not classe_id or not jour or not heure_debut or not heure_fin:
        flash('Classe, jour et horaires obligatoires.', 'danger')
        return redirect(url_for('edt_bp.edt', classe_id=classe_id))

    # Vérifier que la classe appartient à l'école
    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non autorisée.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    # Créer le créneau
    creneau = EmploiDuTemps(
        classe_id=classe_id,
        matiere_id=matiere_id if matiere_id else None,
        jour=jour,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        salle=salle or None,
        enseignant=enseignant or None,
        couleur=couleur or '#3b82f6',
        annee_scolaire=annee,
        ecole_id=ecole_id
    )
    db.session.add(creneau)
    db.session.commit()
    flash('Créneau ajouté avec succès.', 'success')
    return redirect(url_for('edt_bp.edt', classe_id=classe_id))


@edt_bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def edt_supprimer(id):
    ecole_id = get_current_ecole_id()
    creneau = EmploiDuTemps.query.get_or_404(id)
    if creneau.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    classe_id = creneau.classe_id
    db.session.delete(creneau)
    db.session.commit()
    flash('Créneau supprimé.', 'success')
    return redirect(url_for('edt_bp.edt', classe_id=classe_id))


@edt_bp.route('/classe/<int:classe_id>')
@login_required
def edt_classe_api(classe_id):
    """API JSON pour récupérer l'EDT d'une classe"""
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        return jsonify({'error': 'Classe non trouvée'}), 404

    edt_list = EmploiDuTemps.query.filter_by(
        classe_id=classe_id, ecole_id=ecole_id, annee_scolaire=annee
    ).order_by(EmploiDuTemps.jour, EmploiDuTemps.heure_debut).all()

    result = []
    for e in edt_list:
        result.append({
            'id': e.id,
            'jour': e.jour,
            'heure_debut': e.heure_debut,
            'heure_fin': e.heure_fin,
            'salle': e.salle or '',
            'enseignant': e.enseignant or '',
            'couleur': e.couleur or '#3b82f6',
            'matiere': {
                'id': e.matiere.id if e.matiere else None,
                'nom': e.matiere.nom if e.matiere else '—',
            }
        })

    return jsonify({'classe': classe.nom, 'creneaux': result})
