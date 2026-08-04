from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ecole, Classe, Matiere, Personnel, EmploiDuTemps, DisponibiliteEnseignant, GrilleHoraire
from helpers import get_current_ecole_id, get_current_annee
import random

edt_bp = Blueprint('edt_bp', __name__, url_prefix='/edt')

JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
CRENEAUX = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00']


# ============================================================
# ROUTES EXISTANTES (conservées et enrichies)
# ============================================================

@edt_bp.route('/')
@login_required
def edt():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()
    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()
    personnels = Personnel.query.filter_by(ecole_id=ecole_id).order_by(Personnel.nom, Personnel.prenom).all()

    classe_id = request.args.get('classe_id', type=int)
    classe_selectionnee = None
    creneaux_edt = {}
    edt_list = []
    personnels = Personnel.query.filter_by(ecole_id=ecole_id).order_by(Personnel.nom).all()
    grille = {}
    if classe_id:
        classe_selectionnee = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
        edt_list = EmploiDuTemps.query.filter_by(
            classe_id=classe_id, ecole_id=ecole_id, annee_scolaire=annee
        ).order_by(EmploiDuTemps.jour, EmploiDuTemps.heure_debut).all()
        for e in edt_list:
            creneaux_edt[(e.jour, e.heure_debut)] = e
        grille_entries = GrilleHoraire.query.filter_by(classe_id=classe_id, ecole_id=ecole_id).all()
        grille = {g.matiere_id: g.heures_par_semaine for g in grille_entries}

    return render_template('edt/index.html',
        ecole=ecole, classes=classes, matieres=matieres,
        classe_id=classe_id, classe_selectionnee=classe_selectionnee,
        jours=JOURS, creneaux=CRENEAUX,
        creneaux_edt=creneaux_edt, edt_list=edt_list, personnels=personnels, grille=grille)


@edt_bp.route('/ajouter', methods=['POST'])
@login_required
def edt_ajouter():
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    classe_id = request.form.get('classe_id', type=int)
    matiere_id = request.form.get('matiere_id', type=int)
    personnel_id = request.form.get('personnel_id', type=int)
    jour = request.form.get('jour', '').strip()
    heure_debut = request.form.get('heure_debut', '').strip()
    heure_fin = request.form.get('heure_fin', '').strip()
    salle = request.form.get('salle', '').strip()
    enseignant = request.form.get('enseignant', '').strip()
    couleur = request.form.get('couleur', '#3b82f6').strip()

    if not classe_id or not jour or not heure_debut or not heure_fin:
        flash('Classe, jour et horaires obligatoires.', 'danger')
        return redirect(url_for('edt_bp.edt', classe_id=classe_id))

    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non autorisée.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    perso = None
    if personnel_id:
        perso = Personnel.query.filter_by(id=personnel_id, ecole_id=ecole_id).first()
        if not perso:
            flash('Personnel non autorisé.', 'danger')
            return redirect(url_for('edt_bp.edt', classe_id=classe_id))
        if not enseignant:
            enseignant = f"{perso.prenom} {perso.nom}"

    if not enseignant:
        enseignant = None

    creneau = EmploiDuTemps(
        classe_id=classe_id,
        matiere_id=matiere_id if matiere_id else None,
        personnel_id=personnel_id if personnel_id else None,
        jour=jour,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        salle=salle or None,
        enseignant=enseignant,
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


# ============================================================
# NOUVELLES ROUTES — Grille horaire
# ============================================================

@edt_bp.route('/grille/<int:classe_id>')
@login_required
def edt_grille(classe_id):
    ecole_id = get_current_ecole_id()
    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non trouvée.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()
    grille_entries = GrilleHoraire.query.filter_by(
        classe_id=classe_id, ecole_id=ecole_id
    ).all()
    grille_existante = {g.matiere_id: g.heures_par_semaine for g in grille_entries}

    return render_template('edt/grille.html',
        classe=classe, matieres=matieres, grille_existante=grille_existante)


@edt_bp.route('/grille/sauvegarder', methods=['POST'])
@login_required
def edt_grille_sauvegarder():
    ecole_id = get_current_ecole_id()
    classe_id = request.form.get('classe_id', type=int)

    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non trouvée.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    heures_dict = {}
    for key in request.form:
        if key.startswith('heures_'):
            matiere_id_str = key[len('heures_'):]
            try:
                matiere_id = int(matiere_id_str)
                heures_dict[matiere_id] = int(request.form.get(key, 0) or 0)
            except ValueError:
                pass

    GrilleHoraire.query.filter_by(classe_id=classe_id, ecole_id=ecole_id).delete()

    for matiere_id, nb_heures in heures_dict.items():
        if nb_heures > 0:
            grille = GrilleHoraire(
                classe_id=classe_id,
                matiere_id=matiere_id,
                heures_par_semaine=nb_heures,
                ecole_id=ecole_id
            )
            db.session.add(grille)

    db.session.commit()
    flash('Grille horaire enregistrée avec succès.', 'success')
    return redirect(url_for('edt_bp.edt', classe_id=classe_id))


# ============================================================
# NOUVELLES ROUTES — Disponibilités des enseignants
# ============================================================

@edt_bp.route('/disponibilites/<int:personnel_id>')
@login_required
def edt_disponibilites(personnel_id):
    ecole_id = get_current_ecole_id()
    personnel = Personnel.query.filter_by(id=personnel_id, ecole_id=ecole_id).first()
    if not personnel:
        flash('Personnel non trouvé.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    dispo_entries = DisponibiliteEnseignant.query.filter_by(
        personnel_id=personnel_id, ecole_id=ecole_id
    ).all()
    disponibilites = {}
    for d in dispo_entries:
        disponibilites[(d.jour, d.heure_debut)] = d.disponible

    dispo_dict = {}
    for jour in JOURS:
        for creneau in CRENEAUX:
            debut, fin = creneau.split('-')
            dispo_dict[f"{jour}|{debut}|{fin}"] = disponibilites.get((jour, debut), False)

    return render_template('edt/disponibilites.html',
        personnel=personnel, jours=JOURS, creneaux=CRENEAUX,
        dispo_dict=dispo_dict)


@edt_bp.route('/disponibilites/sauvegarder', methods=['POST'])
@login_required
def edt_disponibilites_sauvegarder():
    ecole_id = get_current_ecole_id()
    personnel_id = request.form.get('personnel_id', type=int)

    personnel = Personnel.query.filter_by(id=personnel_id, ecole_id=ecole_id).first()
    if not personnel:
        flash('Personnel non trouvé.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    DisponibiliteEnseignant.query.filter_by(
        personnel_id=personnel_id, ecole_id=ecole_id
    ).delete()

    for jour in JOURS:
        for creneau in CRENEAUX:
            debut = creneau.split('-')[0]
            fin = creneau.split('-')[1]
            field_name = f"dispo_{jour}|{debut}|{fin}"
            est_disponible = request.form.get(field_name) == 'on'

            dispo = DisponibiliteEnseignant(
                personnel_id=personnel_id,
                jour=jour,
                heure_debut=debut,
                heure_fin=fin,
                disponible=est_disponible,
                ecole_id=ecole_id
            )
            db.session.add(dispo)

    db.session.commit()
    flash('Disponibilités enregistrées avec succès.', 'success')
    return redirect(url_for('edt_bp.edt'))


# ============================================================
# NOUVELLE ROUTE — Génération automatique de l'EDT
# ============================================================

@edt_bp.route('/generer/<int:classe_id>', methods=['POST'])
@login_required
def edt_generer(classe_id):
    ecole_id = get_current_ecole_id()
    annee = get_current_annee()

    classe = Classe.query.filter_by(id=classe_id, ecole_id=ecole_id).first()
    if not classe:
        flash('Classe non trouvée.', 'danger')
        return redirect(url_for('edt_bp.edt'))

    grille = GrilleHoraire.query.filter_by(classe_id=classe_id, ecole_id=ecole_id).all()
    if not grille:
        flash("Configurez d'abord la grille horaire", 'warning')
        return redirect(url_for('edt_bp.edt', classe_id=classe_id))

    EmploiDuTemps.query.filter_by(classe_id=classe_id, ecole_id=ecole_id).delete()

    heures_a_placer = {g.matiere_id: g.heures_par_semaine for g in grille}

    personnels = Personnel.query.filter_by(ecole_id=ecole_id).all()
    dispos = {}
    for p in personnels:
        d = DisponibiliteEnseignant.query.filter_by(
            personnel_id=p.id, ecole_id=ecole_id, disponible=True
        ).all()
        dispos[p.id] = set((d.jour, d.heure_debut) for d in d)

    tous_creneaux = []
    for jour in JOURS:
        for creneau in CRENEAUX:
            parts = creneau.split('-')
            debut = parts[0]
            fin = parts[1]
            tous_creneaux.append((jour, debut, fin))
    random.shuffle(tous_creneaux)

    nb_places = 0
    matieres = list(heures_a_placer.keys())

    for jour, debut, fin in tous_creneaux:
        if sum(heures_a_placer.values()) == 0:
            break
        random.shuffle(matieres)
        for mat_id in matieres:
            if heures_a_placer[mat_id] <= 0:
                continue
            prof_trouve = None
            for p in personnels:
                if (jour, debut) in dispos.get(p.id, set()):
                    prof_trouve = p
                    break
            if prof_trouve:
                matiere = Matiere.query.get(mat_id)
                creneau = EmploiDuTemps(
                    classe_id=classe_id,
                    matiere_id=mat_id,
                    personnel_id=prof_trouve.id,
                    enseignant=f"{prof_trouve.prenom} {prof_trouve.nom}",
                    jour=jour,
                    heure_debut=debut,
                    heure_fin=fin,
                    annee_scolaire=annee,
                    ecole_id=ecole_id
                )
                db.session.add(creneau)
                heures_a_placer[mat_id] -= 1
                nb_places += 1
                break

    db.session.commit()
    flash(f"{nb_places} créneaux générés automatiquement", 'success')
    return redirect(url_for('edt_bp.edt', classe_id=classe_id))
