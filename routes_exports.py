from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Ecole, Eleve, Paiement, Classe, Matiere, Note, Scolarite, TarifService, CategorieTarif, AbonnementService
from helpers import get_current_ecole_id, get_current_annee
from sqlalchemy import func
from datetime import datetime

exports_bp = Blueprint('exports_bp', __name__, url_prefix='/exports')

# --- PAGE D'ACCUEIL DES EXPORTS ---
@exports_bp.route('/')
@login_required
def index():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    return render_template('exports/index.html', ecole=ecole, classes=classes)

# --- ETAT FINANCIER ---
@exports_bp.route('/etat-financier')
@login_required
def etat_financier():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()

    mois_noms = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre']

    # Recettes par mois (tous paiements confondus)
    recettes_par_mois = {}
    total_annuel = 0
    for m in mois_noms:
        total = db.session.query(func.sum(Paiement.montant)).filter_by(
            annee_scolaire=annee, ecole_id=ecole_id, type_paiement=m
        ).scalar() or 0
        recettes_par_mois[m] = total
        total_annuel += total

    # Recettes par type de paiement
    types_paiements = db.session.query(
        Paiement.type_paiement, func.sum(Paiement.montant)
    ).filter_by(
        annee_scolaire=annee, ecole_id=ecole_id
    ).group_by(Paiement.type_paiement).order_by(Paiement.type_paiement).all()

    return render_template('exports/etat_financier.html',
                           ecole=ecole, annee=annee,
                           mois_noms=mois_noms,
                           recettes_par_mois=recettes_par_mois,
                           total_annuel=total_annuel,
                           types_paiements=types_paiements)

# --- RELEVE DE NOTES ---
@exports_bp.route('/releve-notes/<int:classe_id>/<int:trimestre>')
@login_required
def releve_notes(classe_id, trimestre):
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()
    classe = Classe.query.get_or_404(classe_id)

    if classe.ecole_id != ecole_id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('exports_bp.index'))

    eleves = Eleve.query.filter_by(
        classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id
    ).order_by(Eleve.nom, Eleve.prenom).all()

    matieres = Matiere.query.filter_by(ecole_id=ecole_id).order_by(Matiere.nom).all()

    # Construire les données par élève
    data = []
    for eleve in eleves:
        notes = Note.query.filter_by(
            eleve_id=eleve.id, classe_id=classe_id, trimestre=trimestre,
            annee_scolaire=annee
        ).all()

        notes_dict = {n.matiere_id: n for n in notes}
        moyennes = {}
        total_pondere = 0
        total_coef = 0

        for mat in matieres:
            n = notes_dict.get(mat.id)
            if n and n.moyenne is not None:
                moyennes[mat.id] = {
                    'nom': mat.nom,
                    'moyenne': n.moyenne,
                    'coef': mat.coefficient
                }
                total_pondere += n.moyenne * mat.coefficient
                total_coef += mat.coefficient
            else:
                moyennes[mat.id] = {
                    'nom': mat.nom,
                    'moyenne': None,
                    'coef': mat.coefficient
                }

        moyenne_generale = round(total_pondere / total_coef, 2) if total_coef > 0 else 0

        data.append({
            'eleve': eleve,
            'moyennes': moyennes,
            'moyenne_generale': moyenne_generale,
            'total_coef_utilises': total_coef
        })

    # Classement
    data.sort(key=lambda x: x['moyenne_generale'], reverse=True)
    for i, d in enumerate(data):
        d['rang'] = i + 1

    return render_template('exports/releve_notes.html',
                           ecole=ecole, annee=annee,
                           classe=classe, trimestre=trimestre,
                           matieres=matieres, data=data)

# --- LISTE DES ELEVES ---
@exports_bp.route('/liste-eleves')
@login_required
def liste_eleves():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()
    classe_id = request.args.get('classe_id', type=int)

    query = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    )

    if classe_id:
        query = query.filter_by(classe_id=classe_id)

    eleves = query.order_by(Eleve.nom, Eleve.prenom).all()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()

    return render_template('exports/liste_eleves.html',
                           ecole=ecole, annee=annee,
                           eleves=eleves, classes=classes,
                           classe_id=classe_id)

# --- STATISTIQUES GLOBALES ---
@exports_bp.route('/statistiques')
@login_required
def statistiques():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    annee = get_current_annee()

    # Nb total d'élèves
    nb_eleves = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).count()

    # Nb classes
    nb_classes = Classe.query.filter_by(ecole_id=ecole_id).count()

    # Répartition Filles/Garçons
    nb_garcons = Eleve.query.filter_by(ecole_id=ecole_id, sexe='M').filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).count()
    nb_filles = Eleve.query.filter_by(ecole_id=ecole_id, sexe='F').filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).count()

    pct_garcons = round(nb_garcons / nb_eleves * 100, 1) if nb_eleves > 0 else 0
    pct_filles = round(nb_filles / nb_eleves * 100, 1) if nb_eleves > 0 else 0

    # Effectif par classe
    effectif_par_classe = []
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    for cl in classes:
        nb = Eleve.query.filter_by(classe_id=cl.id, ecole_id=ecole_id).filter(
            db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
        ).count()
        nb_g = Eleve.query.filter_by(classe_id=cl.id, sexe='M', ecole_id=ecole_id).filter(
            db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
        ).count()
        nb_f = Eleve.query.filter_by(classe_id=cl.id, sexe='F', ecole_id=ecole_id).filter(
            db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
        ).count()
        effectif_par_classe.append({
            'classe': cl,
            'total': nb,
            'garcons': nb_g,
            'filles': nb_f
        })

    # Taux de recouvrement des paiements
    # Total attendu (scolarité + services) vs total payé
    total_attendu = 0
    total_paye = db.session.query(func.sum(Paiement.montant)).filter_by(
        annee_scolaire=annee, ecole_id=ecole_id
    ).scalar() or 0

    # Total attendu = somme des scolarités + tarifs services pour les élèves abonnés
    eleves_all = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).all()

    scolarites_map = {s.classe_id: s for s in Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all()}
    tarifs_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        tarifs_map[(t.classe_id, t.categorie_id)] = t

    eleve_ids = [e.id for e in eleves_all]
    abonnements_map = {}
    if eleve_ids:
        abs_list = AbonnementService.query.filter(
            AbonnementService.actif == True,
            AbonnementService.eleve_id.in_(eleve_ids)
        ).all()
        for a in abs_list:
            abonnements_map.setdefault(a.eleve_id, set()).add(a.categorie_id)

    for eleve in eleves_all:
        if not eleve.classe:
            continue
        scol = scolarites_map.get(eleve.classe_id)
        if scol:
            total_attendu += scol.total_annuel
        abos = abonnements_map.get(eleve.id, set())
        for cat_id in abos:
            tarif = tarifs_map.get((eleve.classe_id, cat_id))
            if tarif:
                total_attendu += tarif.total_annuel

    taux_recouvrement = round(total_paye / total_attendu * 100, 1) if total_attendu > 0 else 0

    return render_template('exports/statistiques.html',
                           ecole=ecole, annee=annee,
                           nb_eleves=nb_eleves, nb_classes=nb_classes,
                           nb_garcons=nb_garcons, nb_filles=nb_filles,
                           pct_garcons=pct_garcons, pct_filles=pct_filles,
                           effectif_par_classe=effectif_par_classe,
                           total_attendu=total_attendu, total_paye=total_paye,
                           taux_recouvrement=taux_recouvrement)
