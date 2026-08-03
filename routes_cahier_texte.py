from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models import db, Ecole, Classe, Matiere, CahierTexte
from helpers import get_current_ecole_id, get_current_annee

cahier_texte_bp = Blueprint('cahier_texte_bp', __name__, url_prefix='/cahier-texte')


@cahier_texte_bp.route('/')
@login_required
def cahier_texte():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()
    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()
    return render_template('cahier_texte/index.html',
        ecole=ecole, classes=classes, matieres=matieres, annee=annee)


@cahier_texte_bp.route('/ajouter', methods=['POST'])
@login_required
def cahier_texte_ajouter():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    classe_id = request.form.get('classe_id', type=int)
    matiere_id = request.form.get('matiere_id', type=int)
    date_seance = request.form.get('date_seance', '').strip()
    contenu = request.form.get('contenu', '').strip()
    devoirs = request.form.get('devoirs', '').strip()
    observations = request.form.get('observations', '').strip()
    enseignant = request.form.get('enseignant', '').strip()

    # Validation
    if not classe_id or not matiere_id or not date_seance or not contenu:
        flash('Classe, matière, date et contenu sont obligatoires.', 'danger')
        return redirect(url_for('cahier_texte_bp.cahier_texte'))

    # Vérifier que la classe appartient à l'école
    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non autorisée.', 'danger')
        return redirect(url_for('cahier_texte_bp.cahier_texte'))

    # Vérifier que la matière appartient à l'école
    matiere = Matiere.query.filter_by(id=matiere_id, ecole_id=ecole_id).first()
    if not matiere:
        flash('Matière non autorisée.', 'danger')
        return redirect(url_for('cahier_texte_bp.cahier_texte'))

    seance = CahierTexte(
        classe_id=classe_id,
        matiere_id=matiere_id,
        date_seance=date_seance,
        contenu=contenu,
        devoirs=devoirs if devoirs else None,
        observations=observations if observations else None,
        enseignant=enseignant if enseignant else None,
        annee_scolaire=annee,
        ecole_id=ecole_id
    )
    db.session.add(seance)
    db.session.commit()
    flash('Séance ajoutée avec succès.', 'success')
    return redirect(url_for('cahier_texte_bp.cahier_texte', classe_id=classe_id, matiere_id=matiere_id))


@cahier_texte_bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def cahier_texte_supprimer(id):
    ecole_id = get_current_ecole_id()
    seance = CahierTexte.query.get_or_404(id)
    if seance.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('cahier_texte_bp.cahier_texte'))

    classe_id = seance.classe_id
    matiere_id = seance.matiere_id
    db.session.delete(seance)
    db.session.commit()
    flash('Séance supprimée.', 'success')
    return redirect(url_for('cahier_texte_bp.cahier_texte', classe_id=classe_id, matiere_id=matiere_id))


@cahier_texte_bp.route('/classe/<int:classe_id>/<int:matiere_id>')
@login_required
def cahier_texte_api(classe_id, matiere_id):
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    # Vérifier que la classe appartient à l'école
    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        return jsonify({'error': 'Classe non autorisée'}), 403

    # Vérifier que la matière appartient à l'école
    matiere = Matiere.query.filter_by(id=matiere_id, ecole_id=ecole_id).first()
    if not matiere:
        return jsonify({'error': 'Matière non autorisée'}), 403

    seances = CahierTexte.query.filter_by(
        classe_id=classe_id,
        matiere_id=matiere_id,
        ecole_id=ecole_id,
        annee_scolaire=annee
    ).order_by(CahierTexte.date_seance.desc()).all()

    return jsonify([{
        'id': s.id,
        'date_seance': s.date_seance,
        'contenu': s.contenu,
        'devoirs': s.devoirs,
        'observations': s.observations,
        'enseignant': s.enseignant,
        'matiere': s.matiere.nom if s.matiere else '',
        'classe': s.classe.nom if s.classe else ''
    } for s in seances])
