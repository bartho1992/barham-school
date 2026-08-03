from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from models import db, Classe, Matiere, Examen, Ecole
from helpers import get_current_ecole_id, get_current_annee

examens_bp = Blueprint('examens_bp', __name__, url_prefix='/examens')

@examens_bp.route('/')
@login_required
def examens():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()
    ecole = Ecole.query.get(ecole_id)
    classe_id = request.args.get('classe_id', '')
    trimestre = request.args.get('trimestre', '1')
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()
    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()
    return render_template(
        'examens/index.html',
        ecole=ecole,
        classes=classes,
        matieres=matieres,
        annee=annee,
        classe_id=classe_id,
        trimestre=trimestre
    )

@examens_bp.route('/ajouter', methods=['POST'])
@login_required
def examen_ajouter():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()
    classe_id = request.form.get('classe_id')
    trimestre = request.form.get('trimestre', 1)
    try:
        examen = Examen(
            classe_id=classe_id,
            matiere_id=request.form.get('matiere_id'),
            type_examen=request.form.get('type_examen', 'Composition'),
            trimestre=trimestre,
            date_examen=request.form.get('date_examen'),
            heure_debut=request.form.get('heure_debut'),
            duree_minutes=request.form.get('duree_minutes', 120),
            salle=request.form.get('salle', ''),
            surveillant=request.form.get('surveillant', ''),
            annee_scolaire=annee,
            ecole_id=ecole_id
        )
        db.session.add(examen)
        db.session.commit()
        flash('Examen ajouté avec succès', 'success')
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('examens_bp.examens', classe_id=classe_id, trimestre=trimestre))

@examens_bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def examen_supprimer(id):
    ecole_id = get_current_ecole_id()
    examen = Examen.query.get_or_404(id)
    if examen.ecole_id != ecole_id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('examens_bp.examens'))
    classe_id = examen.classe_id
    trimestre = examen.trimestre
    db.session.delete(examen)
    db.session.commit()
    flash('Examen supprimé', 'success')
    return redirect(url_for('examens_bp.examens', classe_id=classe_id, trimestre=trimestre))

@examens_bp.route('/classe/<int:classe_id>/<int:trimestre>')
@login_required
def examens_classe_api(classe_id, trimestre):
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()
    examens = Examen.query.filter_by(
        classe_id=classe_id,
        trimestre=trimestre,
        ecole_id=ecole_id,
        annee_scolaire=annee
    ).order_by(Examen.date_examen, Examen.heure_debut).all()

    result = []
    for e in examens:
        result.append({
            'id': e.id,
            'date_examen': e.date_examen,
            'heure_debut': e.heure_debut,
            'matiere': e.matiere.nom if e.matiere else '',
            'duree_minutes': e.duree_minutes,
            'salle': e.salle or '',
            'surveillant': e.surveillant or '',
            'type_examen': e.type_examen
        })
    return jsonify(result)
