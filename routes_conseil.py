from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Ecole, Eleve, Classe, Bulletin, Assiduite, ConseilClasse, AppreciationConseil
from helpers import get_current_ecole_id, get_current_annee

conseil_bp = Blueprint('conseil_bp', __name__, url_prefix='/conseil')

@conseil_bp.route('/')
@login_required
def conseil():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()
    ecole = Ecole.query.get(ecole_id)
    conseils = ConseilClasse.query.filter_by(ecole_id=ecole_id, annee_scolaire=annee).order_by(ConseilClasse.date_conseil.desc()).all()

    # Enrich with count of appreciations
    data = []
    for c in conseils:
        nb_eleves = AppreciationConseil.query.filter_by(conseil_id=c.id).count()
        data.append({'conseil': c, 'nb_eleves': nb_eleves})

    return render_template('conseil/index.html', conseils=data, ecole=ecole)

@conseil_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def conseil_nouveau():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()
    ecole = Ecole.query.get(ecole_id)
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()

    if request.method == 'POST':
        classe_id = request.form.get('classe_id', type=int)
        trimestre = request.form.get('trimestre', type=int)
        date_conseil = request.form.get('date_conseil', '')
        president = request.form.get('president', '')

        if not classe_id or not trimestre:
            flash('Veuillez sélectionner une classe et un trimestre.', 'warning')
            return redirect(url_for('conseil_bp.conseil_nouveau'))

        # Vérifier si un conseil existe déjà pour cette classe/trimestre/année
        existe = ConseilClasse.query.filter_by(
            classe_id=classe_id, trimestre=trimestre,
            annee_scolaire=annee, ecole_id=ecole_id
        ).first()
        if existe:
            flash('Un conseil de classe existe déjà pour cette classe et ce trimestre.', 'warning')
            return redirect(url_for('conseil_bp.conseil_detail', id=existe.id))

        # Créer le conseil
        conseil = ConseilClasse(
            classe_id=classe_id,
            trimestre=trimestre,
            date_conseil=date_conseil,
            president=president,
            annee_scolaire=annee,
            ecole_id=ecole_id
        )
        db.session.add(conseil)
        db.session.flush()

        # Pré-remplir les appréciations pour chaque élève
        eleves = Eleve.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).all()
        for el in eleves:
            bulletin = Bulletin.query.filter_by(
                eleve_id=el.id, classe_id=classe_id,
                trimestre=trimestre, annee_scolaire=annee
            ).first()

            # Compter absences depuis Assiduite
            absences_count = Assiduite.query.filter_by(
                eleve_id=el.id,
                annee_scolaire=annee,
                type_evenement='Absent'
            ).count()
            retards_count = Assiduite.query.filter_by(
                eleve_id=el.id,
                annee_scolaire=annee,
                type_evenement='Retard'
            ).count()

            app = AppreciationConseil(
                conseil_id=conseil.id,
                eleve_id=el.id,
                moyenne_generale=bulletin.moyenne_generale if bulletin else None,
                rang=bulletin.rang if bulletin else None,
                absences=absences_count,
                retards=retards_count,
                decision='Passe'
            )
            db.session.add(app)

        db.session.commit()
        flash('Conseil de classe créé avec succès.', 'success')
        return redirect(url_for('conseil_bp.conseil'))

    return render_template('conseil/nouveau.html', classes=classes, ecole=ecole)

@conseil_bp.route('/<int:id>')
@login_required
def conseil_detail(id):
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    conseil = ConseilClasse.query.get_or_404(id)
    if conseil.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('conseil_bp.conseil'))

    appreciations = AppreciationConseil.query.filter_by(conseil_id=id).join(Eleve).order_by(Eleve.nom, Eleve.prenom).all()

    return render_template('conseil/detail.html', conseil=conseil, appreciations=appreciations, ecole=ecole)

@conseil_bp.route('/<int:id>/sauvegarder', methods=['POST'])
@login_required
def conseil_sauvegarder(id):
    ecole_id = get_current_ecole_id()
    conseil = ConseilClasse.query.get_or_404(id)
    if conseil.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('conseil_bp.conseil'))

    conseil.observations_generales = request.form.get('observations_generales', '')
    conseil.president = request.form.get('president', '')

    appreciations = AppreciationConseil.query.filter_by(conseil_id=id).all()
    for app in appreciations:
        app.appreciation = request.form.get(f'appreciation_{app.id}', '')
        app.decision = request.form.get(f'decision_{app.id}', 'Passe')

    db.session.commit()
    flash('Conseil de classe enregistré avec succès.', 'success')
    return redirect(url_for('conseil_bp.conseil_detail', id=id))

@conseil_bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def conseil_supprimer(id):
    ecole_id = get_current_ecole_id()
    conseil = ConseilClasse.query.get_or_404(id)
    if conseil.ecole_id != ecole_id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('conseil_bp.conseil'))

    AppreciationConseil.query.filter_by(conseil_id=id).delete()
    db.session.delete(conseil)
    db.session.commit()
    flash('Conseil de classe supprimé.', 'success')
    return redirect(url_for('conseil_bp.conseil'))
