from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from models import db, Ecole, Eleve, Paiement, Classe, CategorieTarif, Scolarite, TarifService, AbonnementService
from app import app, get_current_ecole_id
from sqlalchemy.orm import joinedload
from datetime import datetime
# import pandas as pd  # Non necessaire, retire pour eviter dependance lourde

try:
    import requests
except ImportError:
    requests = None

MOIS_SCOLAIRES = ['Inscription', 'Octobre', 'Novembre', 'Decembre', 'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin']
MOIS_CALENDAIRES = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
                    'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre']

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '')

def _bypass_licence_check():
    return current_user.role in ('super_users', 'dev')

def _check_parametres_access(ecole_id):
    """Verifie l'acces aux parametres : dev/super_users toujours ok, sinon licence active requise"""
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return redirect(url_for('abonnement'))
    return None

def _check_parametres_access_json(ecole_id):
    """Version JSON pour les appels AJAX"""
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'error': 'Licence expiree', 'redirect': url_for('abonnement')}), 403
    return None

def _montant_scolarite_mois(scolarite, mois):
    if not scolarite:
        return 0
    if mois == 'Inscription':
        return scolarite.inscription or 0
    return getattr(scolarite, mois.lower(), 0) or 0

def _mois_dans_abonnement(abo, mois):
    if mois == 'Inscription':
        return abo.categorie.type_categorie == 'inscription'
    if abo.categorie.type_categorie != 'mensuel':
        return False
    try:
        idx_mois = MOIS_CALENDAIRES.index(mois)
        idx_debut = MOIS_CALENDAIRES.index(abo.mois_debut)
        idx_fin = MOIS_CALENDAIRES.index(abo.mois_fin)
    except ValueError:
        return True
    if idx_debut <= idx_fin:
        return idx_debut <= idx_mois <= idx_fin
    return idx_mois >= idx_debut or idx_mois <= idx_fin

def _montant_service_mois(cat, tarif, abo, mois):
    if not abo or not tarif:
        return 0
    if not _mois_dans_abonnement(abo, mois):
        return 0
    if abo.montant_personnalise is not None and cat.type_categorie == 'mensuel' and mois != 'Inscription':
        return abo.montant_personnalise or 0
    if mois == 'Inscription':
        return tarif.inscription or 0
    return getattr(tarif, mois.lower(), 0) or 0

def _index_mois_scolaire(mois):
    try:
        return MOIS_SCOLAIRES.index(mois)
    except ValueError:
        return None

def _build_ligne_financiere(eleve, annee, categories, scolarites_map, tarifs_services_map, abonnements_by_eleve, paiements):
    if not eleve.classe:
        return None

    scolarite = scolarites_map.get(eleve.classe_id)
    abonnements = abonnements_by_eleve.get(eleve.id, [])
    abonnement_par_categorie = {abo.categorie_id: abo for abo in abonnements if abo.actif}

    cat_lines = []
    cat_lines_by_id = {}
    for cat in categories:
        abo = abonnement_par_categorie.get(cat.id)
        tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
        statut = 'inactif'
        if abo and tarif:
            statut = 'actif'
        elif abo and not tarif:
            statut = 'sans_tarif'
        cat_line = {
            'cat': cat,
            'due': 0,
            'paye': 0,
            'reste': 0,
            'statut': statut
        }
        cat_lines.append(cat_line)
        cat_lines_by_id[cat.id] = cat_line

    mois_details = {
        mois: {'due': 0, 'paye': 0, 'reste': 0, 'cumul': 0}
        for mois in MOIS_SCOLAIRES
    }

    dues = []
    total_du = 0
    for mois in MOIS_SCOLAIRES:
        du_scolarite = _montant_scolarite_mois(scolarite, mois)
        if du_scolarite > 0:
            dues.append({
                'kind': 'scolarite',
                'month': mois,
                'month_index': _index_mois_scolaire(mois),
                'remaining': du_scolarite,
                'paid': 0,
                'amount': du_scolarite
            })
            mois_details[mois]['due'] += du_scolarite
            total_du += du_scolarite

        for cat in categories:
            abo = abonnement_par_categorie.get(cat.id)
            tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
            montant = _montant_service_mois(cat, tarif, abo, mois)
            if montant <= 0:
                continue
            dues.append({
                'kind': 'service',
                'category_id': cat.id,
                'month': mois,
                'month_index': _index_mois_scolaire(mois),
                'remaining': montant,
                'paid': 0,
                'amount': montant
            })
            cat_lines_by_id[cat.id]['due'] += montant
            mois_details[mois]['due'] += montant
            total_du += montant

    paiements_tries = sorted(
        paiements,
        key=lambda p: (((p.date_paiement.isoformat() if p.date_paiement else '')), p.id or 0)
    )
    total_paye = sum((p.montant or 0) for p in paiements_tries)

    for paiement in paiements_tries:
        restant = paiement.montant or 0
        type_paiement = (paiement.type_paiement or '').strip()
        idx_cible = _index_mois_scolaire(type_paiement)

        if idx_cible is not None:
            for due in dues:
                if due['month_index'] is None or due['month_index'] > idx_cible or due['remaining'] <= 0:
                    continue
                allocation = min(restant, due['remaining'])
                if allocation <= 0:
                    continue
                due['remaining'] -= allocation
                due['paid'] += allocation
                mois_details[due['month']]['paye'] += allocation
                if due['kind'] == 'service':
                    cat_lines_by_id[due['category_id']]['paye'] += allocation
                restant -= allocation
                if restant <= 0:
                    break
        else:
            for cat in categories:
                if cat.nom != type_paiement:
                    continue
                for due in dues:
                    if due['kind'] != 'service' or due.get('category_id') != cat.id or due['remaining'] <= 0:
                        continue
                    allocation = min(restant, due['remaining'])
                    if allocation <= 0:
                        continue
                    due['remaining'] -= allocation
                    due['paid'] += allocation
                    mois_details[due['month']]['paye'] += allocation
                    cat_lines_by_id[cat.id]['paye'] += allocation
                    restant -= allocation
                    if restant <= 0:
                        break
                break

    scolarite_due = sum(
        due['amount'] for due in dues
        if due['kind'] == 'scolarite'
    )
    scolarite_paye = sum(
        due['paid'] for due in dues
        if due['kind'] == 'scolarite'
    )

    cumul = 0
    mois_payes = set()
    for mois in MOIS_SCOLAIRES:
        details = mois_details[mois]
        details['reste'] = max(details['due'] - details['paye'], 0)
        cumul += details['reste']
        details['cumul'] = cumul
        if details['paye'] > 0:
            mois_payes.add(mois)

    mois_affiche = ''
    for mois in MOIS_SCOLAIRES:
        if mois_details[mois]['reste'] > 0:
            mois_affiche = mois
            break
    if not mois_affiche:
        for mois in reversed(MOIS_SCOLAIRES):
            if mois_details[mois]['due'] > 0:
                mois_affiche = mois
                break
    details_affiches = mois_details.get(mois_affiche, {'due': 0, 'paye': 0, 'reste': 0, 'cumul': 0})
    if not mois_affiche and total_du > 0:
        details_affiches = {
            'due': total_du,
            'paye': min(total_paye, total_du),
            'reste': total_reste,
            'cumul': total_reste
        }
        mois_affiche = 'Total'

    services_due = sum(cl['due'] for cl in cat_lines)
    services_paye = sum(cl['paye'] for cl in cat_lines)
    for cl in cat_lines:
        cl['reste'] = max(cl['due'] - cl['paye'], 0)
        if cl['statut'] == 'sans_tarif':
            continue
        if cl['due'] <= 0 and cl['paye'] <= 0:
            cl['statut'] = 'inactif'
        elif cl['reste'] > 0:
            cl['statut'] = 'impaye'
        else:
            cl['statut'] = 'paye'

    total_reste = max(total_du - min(total_paye, total_du), 0)

    nb_mois_actifs = sum(1 for mois in MOIS_SCOLAIRES if mois_details[mois]['due'] > 0)
    montant_mois = (total_du / nb_mois_actifs) if nb_mois_actifs else 0

    date_limite = ''
    try:
        annees = (annee or '').split('-')
        date_limite = f"30/06/{annees[1] if len(annees) > 1 else '2026'}"
    except Exception:
        pass

    return {
        'eleve': eleve,
        'scolarite_due': scolarite_due,
        'scolarite_paye': scolarite_paye,
        'scolarite_reste': max(scolarite_due - scolarite_paye, 0),
        'cat_lines': cat_lines,
        'total_du': total_du,
        'total_paye': total_paye,
        'total_reste': total_reste,
        'du_affiche': details_affiches['due'],
        'avance_affiche': details_affiches['paye'],
        'reste_affiche': details_affiches['reste'],
        'cumul_affiche': total_reste,
        'mois_affiche': mois_affiche or '-',
        'montant_mois': montant_mois,
        'date_limite': date_limite,
        'paye_au_moins_un': total_paye > 0,
        'mois_payes': mois_payes,
        'mois_details': mois_details,
        'nb_impayes': sum(1 for cl in cat_lines if cl['reste'] > 0) + (1 if max(scolarite_due - scolarite_paye, 0) > 0 else 0),
        'services_due': services_due,
        'services_paye': services_paye
    }

@app.route('/finances/gestion')
@login_required
def finances_hub():
    """Page unique avec onglets : Finances, Impayes, Paiements, Nouveau paiement, Inscription"""
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    return render_template('finances/hub.html', ecole=e)

@app.route('/finances')
@login_required
def finances():
    import sys
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    embed = request.args.get('embed')
    print(f"[DIAG-FINANCES] ecole_id={ecole_id}, annee={annee}", file=sys.stderr)
    recent_paiements = Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).options(
        joinedload(Paiement.eleve).joinedload(Eleve.classe)
    ).order_by(Paiement.date_paiement.desc()).limit(20).all()
    total_encaisse = db.session.query(db.func.sum(Paiement.montant)).filter_by(annee_scolaire=annee, ecole_id=ecole_id).scalar() or 0
    today_encaisse = db.session.query(db.func.sum(Paiement.montant)).filter(
        db.func.date(Paiement.date_paiement) == datetime.now().date(),
        Paiement.annee_scolaire == annee,
        Paiement.ecole_id == ecole_id
    ).scalar() or 0
    categories = CategorieTarif.query.filter_by(ecole_id=ecole_id).order_by(CategorieTarif.nom).all()
    
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).order_by(Eleve.nom).all()
    eleve_ids = [eleve.id for eleve in eleves]
    print(f"[DIAG-FINANCES] eleves trouves={len(eleves)}, ids={eleve_ids[:5]}...", file=sys.stderr)
    scolarites_map = {s.classe_id: s for s in Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all()}
    print(f"[DIAG-FINANCES] scolarites_map={list(scolarites_map.keys())[:5]}... nb={len(scolarites_map)}", file=sys.stderr)
    tarifs_services_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        tarifs_services_map[(t.classe_id, t.categorie_id)] = t
    abonnements_map = {}
    if eleve_ids:
        abonnements = AbonnementService.query.filter(
            AbonnementService.actif == True,
            AbonnementService.eleve_id.in_(eleve_ids)
        ).options(joinedload(AbonnementService.categorie)).all()
    else:
        abonnements = []
    for a in abonnements:
        abonnements_map.setdefault(a.eleve_id, []).append(a)
    paiements_par_eleve = {}
    for p in Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        paiements_par_eleve.setdefault(p.eleve_id, []).append(p)
    
    lignes_paiements = []
    for eleve in eleves:
        ligne = _build_ligne_financiere(
            eleve, annee, categories, scolarites_map, tarifs_services_map,
            abonnements_map, paiements_par_eleve.get(eleve.id, [])
        )
        if ligne:
            lignes_paiements.append(ligne)
        else:
            print(f"[DIAG-FINANCES] eleve {eleve.nom} skipped (pas de classe?)", file=sys.stderr)
    if lignes_paiements:
        first = lignes_paiements[0]
        print(f"[DIAG-FINANCES] 1ere ligne: du_affiche={first['du_affiche']}, avance_affiche={first['avance_affiche']}, reste_affiche={first['reste_affiche']}, cumul_affiche={first['cumul_affiche']}, mois_affiche={first['mois_affiche']}, total_du={first['total_du']}", file=sys.stderr)
    
    mois_list = MOIS_SCOLAIRES
    
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    eleves_list = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).order_by(Eleve.nom, Eleve.prenom).all()
    
    return render_template('finances/index.html', ecole=e, paiements=recent_paiements, total_encaisse=total_encaisse,
        today_encaisse=today_encaisse, categories=categories, lignes_paiements=lignes_paiements, classes=classes, mois_list=mois_list, eleves_list=eleves_list, embed=embed,
        diag_nb_eleves=len(eleves), diag_nb_scolarites=len(scolarites_map), diag_annee=annee, diag_ecole_id=ecole_id)

@app.route('/api/tarifs/<int:eleve_id>/<mois>')
@login_required
def api_tarifs(eleve_id, mois):
    """Retourne les tarifs pour un eleve et un mois donnes"""
    eleve = Eleve.query.get_or_404(eleve_id)
    if not eleve.classe:
        return jsonify({'error': 'Eleve sans classe'}), 400
    is_inscription = (mois.lower() == 'inscription')
    type_cat = 'inscription' if is_inscription else 'mensuel'
    ecole_id = get_current_ecole_id()
    scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=_annee_courante(Ecole.query.get(ecole_id))).first()
    montant_scolarite = 0
    if scolarite:
        if is_inscription:
            montant_scolarite = scolarite.inscription or 0
        else:
            montant_scolarite = getattr(scolarite, mois.lower(), 0) or 0
    ordre_mois = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                  'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    services = []
    total_services = 0
    if is_inscription:
        categories_insc = CategorieTarif.query.filter_by(type_categorie='inscription').all()
        for cat in categories_insc:
            services.append({'categorie_id': cat.id, 'nom': cat.nom, 'montant': 0})
            total_services += 0
    else:
        abonnements = AbonnementService.query.filter_by(
            eleve_id=eleve_id
        ).join(CategorieTarif).all()
        for abo in abonnements:
            if abo.categorie.type_categorie == 'inscription':
                # Service unique: verifier si le tarif inscription est defini
                tarif = TarifService.query.filter_by(
                    classe_id=eleve.classe_id, categorie_id=abo.categorie.id, annee_scolaire=_annee_courante(Ecole.query.get(get_current_ecole_id()))
                ).first()
                montant_service = (tarif.inscription or 0) if tarif else 0
                if montant_service > 0:
                    services.append({'categorie_id': abo.categorie.id, 'nom': abo.categorie.nom, 'montant': montant_service})
                    total_services += montant_service
                continue
            try:
                idx_mois = ordre_mois.index(mois)
                idx_debut = ordre_mois.index(abo.mois_debut)
                idx_fin = ordre_mois.index(abo.mois_fin)
                if idx_debut <= idx_fin:
                    dans_periode = idx_debut <= idx_mois <= idx_fin
                else:
                    dans_periode = idx_mois >= idx_debut or idx_mois <= idx_fin
            except ValueError:
                dans_periode = True
            if not dans_periode:
                continue
            cat = abo.categorie
            tarif = TarifService.query.filter_by(
                classe_id=eleve.classe_id, categorie_id=cat.id,
                annee_scolaire=_annee_courante(Ecole.query.get(get_current_ecole_id()))
            ).first()
            if abo.montant_personnalise is not None:
                montant_service = abo.montant_personnalise
            elif tarif:
                montant_service = getattr(tarif, mois.lower(), 0) or 0
            else:
                montant_service = 0
            if montant_service > 0:
                services.append({'categorie_id': cat.id, 'nom': cat.nom, 'montant': montant_service})
                total_services += montant_service
    total_du = montant_scolarite + total_services
    deja_paye = db.session.query(db.func.sum(Paiement.montant)).filter_by(
        eleve_id=eleve_id, type_paiement=mois,
        annee_scolaire=_annee_courante(Ecole.query.get(get_current_ecole_id()))
    ).scalar() or 0
    reste = max(total_du - deja_paye, 0)
    return jsonify({
        'eleve': f"{eleve.prenom} {eleve.nom}",
        'classe': eleve.classe.nom if eleve.classe else None,
        'mois': mois,
        'montant_scolarite': montant_scolarite,
        'services': services,
        'total_services': total_services,
        'total_du': total_du,
        'deja_paye': deja_paye,
        'reste': reste
    })

@app.route('/api/tarifs-cumules/<int:eleve_id>/<mois>')
@login_required
def api_tarifs_cumules(eleve_id, mois):
    """Retourne les tarifs cumules : mois selectionne + tous les mois impayes precedents"""
    ecole_id = get_current_ecole_id(); annee = _annee_courante(Ecole.query.get(ecole_id))
    eleve = Eleve.query.get_or_404(eleve_id)
    if not eleve.classe:
        return jsonify({'error': 'Eleve sans classe'}), 400
    
    mois_scolaires = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    
    scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=annee).first()
    paiements = Paiement.query.filter_by(eleve_id=eleve_id, annee_scolaire=annee).all()
    paye_par_mois = {}
    for p in paiements:
        paye_par_mois[p.type_paiement] = paye_par_mois.get(p.type_paiement, 0) + p.montant
    
    try:
        idx_selection = mois_scolaires.index(mois)
    except ValueError:
        return jsonify({'error': 'Mois invalide'}), 400
    
    ordre_mois = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                  'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    
    def _services_du_mois(m):
        """Calcule les services (cantine, transport...) dus pour un mois donne."""
        services_mois = []
        total_srv = 0
        if m == 'Inscription':
            for cat in CategorieTarif.query.filter_by(type_categorie='inscription').all():
                services_mois.append({'nom': cat.nom, 'montant': 0})
            return services_mois, 0
        abonnements = AbonnementService.query.filter_by(eleve_id=eleve_id).join(CategorieTarif).all()
        for abo in abonnements:
            cat = abo.categorie
            if cat.type_categorie == 'inscription':
                continue
            try:
                idx_m = ordre_mois.index(m)
                idx_debut = ordre_mois.index(abo.mois_debut)
                idx_fin = ordre_mois.index(abo.mois_fin)
                if idx_debut <= idx_fin:
                    dans_periode = idx_debut <= idx_m <= idx_fin
                else:
                    dans_periode = idx_m >= idx_debut or idx_m <= idx_fin
            except ValueError:
                dans_periode = True
            if not dans_periode:
                continue
            tarif = TarifService.query.filter_by(
                classe_id=eleve.classe_id, categorie_id=cat.id, annee_scolaire=annee
            ).first()
            if abo.montant_personnalise is not None:
                montant = abo.montant_personnalise
            elif tarif:
                montant = getattr(tarif, m.lower(), 0) or 0
            else:
                montant = 0
            if montant > 0:
                services_mois.append({'nom': cat.nom, 'montant': montant})
                total_srv += montant
        return services_mois, total_srv
    
    mois_a_payer = []
    total_scolarite = 0
    total_services_global = 0
    
    for i in range(0, idx_selection + 1):
        m = mois_scolaires[i]
        tarif_m = scolarite.inscription if m == 'Inscription' else (getattr(scolarite, m.lower(), 0) or 0) if scolarite else 0
        services_mois, total_srv_mois = _services_du_mois(m)
        
        du_mois = tarif_m + total_srv_mois
        if du_mois <= 0:
            continue
        
        # Paiement deja effectue pour ce mois : allocation scolarite d'abord, puis services
        paye = paye_par_mois.get(m, 0)
        scol_reste = max(tarif_m - paye, 0)
        reste_pour_services = max(paye - tarif_m, 0)
        srv_reste = max(total_srv_mois - reste_pour_services, 0)
        reste_m = scol_reste + srv_reste
        
        # Inclure le mois si un reliquat existe (scolarite OU services) ou si c'est le mois selectionne
        if reste_m > 0 or m == mois:
            mois_a_payer.append({
                'mois': m,
                'tarif': tarif_m,
                'deja_paye': paye,
                'reste': scol_reste,
                'services': services_mois,
                'total_services': srv_reste
            })
            total_scolarite += scol_reste
            total_services_global += srv_reste
    
    total_du = total_scolarite + total_services_global
    
    return jsonify({
        'eleve': f"{eleve.prenom} {eleve.nom}",
        'classe': eleve.classe.nom,
        'mois': mois,
        'mois_a_payer': mois_a_payer,
        'total_scolarite': total_scolarite,
        'total_services': total_services_global,
        'total_du': total_du
    })

@app.route('/api/eleves/<int:eleve_id>/services')
@login_required
def api_services_eleve(eleve_id):
    """Retourne les services abonnes d'un eleve"""
    abonnements = AbonnementService.query.filter_by(eleve_id=eleve_id, actif=True).all()
    return jsonify([{
        'id': a.id,
        'categorie_id': a.categorie_id,
        'nom': a.categorie.nom,
        'type': a.categorie.type_categorie
    } for a in abonnements])

@app.route('/finances/paiement-groupe', methods=['GET', 'POST'])
@login_required
def paiement_groupe():
    """Paiement groupé : paie le même mois pour plusieurs élèves en une fois"""
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    
    eleve_ids = request.form.getlist('eleve_ids[]')
    mois = request.form.get('mois')
    montant_par_eleve_str = request.form.get('montant_par_eleve', '').strip()
    mode_paiement = request.form.get('mode_paiement', 'Especes')
    
    if not eleve_ids or not mois:
        flash('Selectionnez au moins un eleve et un mois.', 'danger')
        return redirect(url_for('impayes'))
    
    is_inscription = (mois.lower() == 'inscription')
    ordre_mois = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                  'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    
    nb_ok = 0
    nb_skip = 0
    total_percu = 0
    
    for eleve_id_str in eleve_ids:
        try:
            eleve_id = int(eleve_id_str)
        except ValueError:
            nb_skip += 1
            continue
        
        eleve = Eleve.query.get(eleve_id)
        if not eleve or not eleve.classe:
            nb_skip += 1
            continue
        
        # Calculer le montant attendu (scolarité + services)
        scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=annee).first()
        montant_scolarite = 0
        if scolarite:
            if is_inscription:
                montant_scolarite = scolarite.inscription or 0
            else:
                montant_scolarite = getattr(scolarite, mois.lower(), 0) or 0
        
        total_services = 0
        if is_inscription:
            # Pas de services pour l'inscription dans le paiement groupé
            pass
        else:
            abonnements = AbonnementService.query.filter_by(
                eleve_id=eleve_id, actif=True
            ).join(CategorieTarif).filter(CategorieTarif.type_categorie == 'mensuel').all()
            for abo in abonnements:
                try:
                    idx_mois = ordre_mois.index(mois)
                    idx_debut = ordre_mois.index(abo.mois_debut)
                    idx_fin = ordre_mois.index(abo.mois_fin)
                    if idx_debut <= idx_fin:
                        dans_periode = idx_debut <= idx_mois <= idx_fin
                    else:
                        dans_periode = idx_mois >= idx_debut or idx_mois <= idx_fin
                except ValueError:
                    dans_periode = True
                if not dans_periode:
                    continue
                cat = abo.categorie
                tarif = TarifService.query.filter_by(
                    classe_id=eleve.classe_id, categorie_id=cat.id, annee_scolaire=annee
                ).first()
                if abo.montant_personnalise is not None:
                    total_services += abo.montant_personnalise
                elif tarif:
                    total_services += getattr(tarif, mois.lower(), 0) or 0
        
        montant_attendu = montant_scolarite + total_services
        
        # Montant à payer : soit le montant fixe saisi, soit le tarif exact
        if montant_par_eleve_str:
            montant = float(montant_par_eleve_str)
        else:
            montant = montant_attendu
        
        if montant <= 0:
            nb_skip += 1
            continue
        
        # Calculer le reste
        deja_paye = db.session.query(db.func.sum(Paiement.montant)).filter_by(
            eleve_id=eleve_id, type_paiement=mois, annee_scolaire=annee
        ).scalar() or 0
        
        # Vérifier si déjà payé
        if deja_paye >= montant_attendu and not montant_par_eleve_str:
            nb_skip += 1
            continue
        
        montant_restant = max(montant_attendu - deja_paye - montant, 0)
        
        p = Paiement(
            eleve_id=eleve_id, montant=montant, type_paiement=mois,
            montant_attendu=montant_attendu, montant_restant=montant_restant,
            caissier=current_user.username, annee_scolaire=annee,
            mode_paiement=mode_paiement
        )
        db.session.add(p)
        total_percu += montant
        nb_ok += 1
    
    db.session.commit()
    flash(f'Paiement groupe effectue : {nb_ok} eleve(s) paye(s) pour {mois} ({nb_skip} ignores). Total percu : {total_percu:,.0f} FCFA', 'success')
    return redirect(url_for('impayes'))

@app.route('/finances/paiement', methods=['GET', 'POST'])
@login_required
def paiement_ajouter():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    categories = CategorieTarif.query.order_by(CategorieTarif.type_categorie, CategorieTarif.nom).all()
    if request.method == 'POST':
        eleve_id = request.form.get('eleve_id')
        mois = request.form.get('mois')
        montant_verse = float(request.form.get('montant', 0))
        eleve = Eleve.query.get_or_404(eleve_id)
        is_inscription = (mois.lower() == 'inscription')
        scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=annee).first()
        montant_scolarite = 0
        if scolarite:
            if is_inscription:
                montant_scolarite = scolarite.inscription or 0
            else:
                montant_scolarite = getattr(scolarite, mois.lower(), 0) or 0
        ordre_mois = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                      'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
        total_services = 0
        if is_inscription:
            service_montants = request.form.getlist('service_montant[]')
            for m_str in service_montants:
                total_services += float(m_str) if m_str else 0
        else:
            abonnements = AbonnementService.query.filter_by(
                eleve_id=eleve_id, actif=True
            ).join(CategorieTarif).filter(CategorieTarif.type_categorie == 'mensuel').all()
            for abo in abonnements:
                try:
                    idx_mois = ordre_mois.index(mois)
                    idx_debut = ordre_mois.index(abo.mois_debut)
                    idx_fin = ordre_mois.index(abo.mois_fin)
                    if idx_debut <= idx_fin:
                        dans_periode = idx_debut <= idx_mois <= idx_fin
                    else:
                        dans_periode = idx_mois >= idx_debut or idx_mois <= idx_fin
                except ValueError:
                    dans_periode = True
                if not dans_periode:
                    continue
                cat = abo.categorie
                tarif = TarifService.query.filter_by(
                    classe_id=eleve.classe_id, categorie_id=cat.id, annee_scolaire=annee
                ).first()
                if abo.montant_personnalise is not None:
                    total_services += abo.montant_personnalise
                elif tarif:
                    total_services += getattr(tarif, mois.lower(), 0) or 0
        montant_attendu = montant_scolarite + total_services
        deja_paye = db.session.query(db.func.sum(Paiement.montant)).filter_by(
            eleve_id=eleve_id, type_paiement=mois, annee_scolaire=annee
        ).scalar() or 0
        montant_restant = max(montant_attendu - deja_paye - montant_verse, 0)
        p = Paiement(
            eleve_id=eleve_id, montant=montant_verse, type_paiement=mois,
            montant_attendu=montant_attendu, montant_restant=montant_restant,
            caissier=current_user.username, annee_scolaire=annee,
            mode_paiement=request.form.get('mode_paiement', 'Especes')
        )
        db.session.add(p)
        db.session.commit()
        flash('Paiement enregistre avec succes', 'success')
        return redirect(url_for('paiement_recu', id=p.id))
    return render_template('finances/form.html', ecole=e, categories=categories)

@app.route('/finances/recu/<int:id>')
@login_required
def paiement_recu(id):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    p = Paiement.query.get_or_404(id)
    return render_template('finances/recu.html', paiement=p, ecole=e)

@app.route('/finances/paiement/annuler/<int:id>', methods=['POST'])
@login_required
def paiement_annuler(id):
    """Annule un paiement (reserve aux super_users)"""
    ecole_id = get_current_ecole_id()
    check = _check_parametres_access(ecole_id)
    if check: return check
    p = Paiement.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Paiement annule avec succes', 'success')
    return redirect(request.referrer or url_for('finances_liste'))

@app.route('/api/eleve/<int:eleve_id>/statut-paiements')
@login_required
def api_eleve_statut_paiements(eleve_id):
    """Retourne le statut de paiement (paye/impaye) pour chaque mois de l'annee scolaire"""
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    eleve = Eleve.query.get_or_404(eleve_id)
    categories = CategorieTarif.query.filter_by(ecole_id=ecole_id).order_by(CategorieTarif.nom).all()
    scolarites_map = {}
    if eleve.classe_id:
        scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=annee, ecole_id=ecole_id).first()
        if scolarite:
            scolarites_map[eleve.classe_id] = scolarite
    tarifs_services_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        tarifs_services_map[(t.classe_id, t.categorie_id)] = t
    abonnements = AbonnementService.query.filter_by(eleve_id=eleve_id, actif=True).options(joinedload(AbonnementService.categorie)).all()
    paiements = Paiement.query.filter_by(eleve_id=eleve_id, annee_scolaire=annee, ecole_id=ecole_id).all()
    ligne = _build_ligne_financiere(
        eleve, annee, categories, scolarites_map, tarifs_services_map,
        {eleve_id: abonnements}, paiements
    )
    
    resultat = {}
    for mois in MOIS_SCOLAIRES:
        details = ligne['mois_details'].get(mois, {}) if ligne else {}
        tarif_mois = details.get('due', 0)
        total_paye = details.get('paye', 0)
        impaye = details.get('reste', 0)
        resultat[mois] = {
            'tarif': tarif_mois,
            'paye': impaye == 0 and tarif_mois > 0,
            'total_paye': total_paye,
            'impaye': impaye
        }
    
    return jsonify({'paiements': resultat, 'eleve_id': eleve_id, 'annee': annee})

@app.route('/finances/list')
@login_required
def finances_liste():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    embed = request.args.get('embed')
    q = Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id)
    type_p = request.args.get('type_paiement')
    if type_p: q = q.filter_by(type_paiement=type_p)
    ps = q.options(joinedload(Paiement.eleve).joinedload(Eleve.classe)).join(Paiement.eleve).order_by(Eleve.nom.asc(), Paiement.date_paiement.desc()).all()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    eleves_list = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).order_by(Eleve.nom, Eleve.prenom).all()
    return render_template('finances/liste.html', paiements=ps, ecole=e, classes=classes, eleves_list=eleves_list, embed=embed)

@app.route('/finances/paiements/supprimer-bulk', methods=['POST'])
@login_required
def finances_paiements_supprimer_bulk():
    if current_user.role not in ('dev', 'super_users'): flash('Accès réservé','danger'); return redirect(url_for('dashboard'))
    embed = request.args.get('embed')
    ids = request.form.getlist('paiement_ids[]')
    if not ids: flash('Aucun paiement sélectionné', 'warning'); return redirect(url_for('finances_liste', embed=embed))
    from models import Paiement
    pids = [int(i) for i in ids]
    count = Paiement.query.filter(Paiement.id.in_(pids)).delete(synchronize_session=False)
    db.session.commit()
    flash(f'{count} paiement(s) supprimé(s)', 'success')
    return redirect(url_for('finances_liste', embed=embed))

@app.route('/finances/impayes')
@login_required
def impayes():
    """Tableau des impayes : eleves x categories de services"""
    import sys
    print("===== impayES V2 (categories) =====", file=sys.stderr)
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    
    # Categories de services
    categories = CategorieTarif.query.filter_by(ecole_id=ecole_id).order_by(CategorieTarif.nom).all()
    
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).order_by(Eleve.nom).all()
    eleve_ids = [eleve.id for eleve in eleves]
    
    # Map: classe_id -> Scolarite
    scolarites_map = {}
    for s in Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        scolarites_map[s.classe_id] = s
    
    # Map: (classe_id, categorie_id) -> TarifService
    tarifs_services_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        tarifs_services_map[(t.classe_id, t.categorie_id)] = t
    
    abonnements_map = {}
    if eleve_ids:
        abonnements = AbonnementService.query.filter(
            AbonnementService.actif == True,
            AbonnementService.eleve_id.in_(eleve_ids)
        ).options(joinedload(AbonnementService.categorie)).all()
    else:
        abonnements = []
    for a in abonnements:
        abonnements_map.setdefault(a.eleve_id, []).append(a)
    
    paiements_map = {}
    for p in Paiement.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all():
        paiements_map.setdefault(p.eleve_id, []).append(p)
    
    lignes = []
    total_global = 0
    
    for eleve in eleves:
        ligne = _build_ligne_financiere(
            eleve, annee, categories, scolarites_map, tarifs_services_map,
            abonnements_map, paiements_map.get(eleve.id, [])
        )
        if ligne:
            total_global += ligne['total_reste']
            lignes.append(ligne)
    
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    eleves_list = Eleve.query.filter_by(ecole_id=ecole_id).options(joinedload(Eleve.classe)).order_by(Eleve.nom, Eleve.prenom).all()
    
    return render_template('finances/impayes.html',
                         lignes=lignes, ecole=e, categories=categories, classes=classes,
                         total_impayes_global=total_global, nb_eleves=len(lignes), eleves_list=eleves_list,
                         mois_list=MOIS_SCOLAIRES)

@app.route('/finances/parametres')
@login_required
def parametres_financiers():
    # Accessible a tous les utilisateurs avec une licence
    from models import Licence
    ecole_id = get_current_ecole_id()
    if not _bypass_licence_check():
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            flash('Vous devez avoir un abonnement actif pour acceder aux paramètres.', 'danger')
            return redirect(url_for('abonnement'))
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    categories = CategorieTarif.query.filter_by(ecole_id=ecole_id).order_by(CategorieTarif.type_categorie, CategorieTarif.nom).all()
    categories_mensuel = CategorieTarif.query.filter_by(ecole_id=ecole_id, type_categorie='mensuel').all()
    categories_inscription = CategorieTarif.query.filter_by(ecole_id=ecole_id, type_categorie='inscription').all()
    scolarites = Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).order_by(Scolarite.ordre, Scolarite.classe_id).all()
    tarifs_services = TarifService.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).order_by(TarifService.classe_id, TarifService.categorie_id).all()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    abonnements_ids = [a.eleve_id for a in AbonnementService.query.filter_by(actif=True).all()]
    eleves_ecole_ids = [el.id for el in Eleve.query.filter_by(ecole_id=ecole_id).all()]
    abonnements = AbonnementService.query.filter(AbonnementService.actif == True, AbonnementService.eleve_id.in_(eleves_ecole_ids)).order_by(AbonnementService.date_debut.desc()).all() if eleves_ecole_ids else []
    return render_template('finances/parametres.html',
                         ecole=e, categories=categories, categories_mensuel=categories_mensuel,
                         categories_inscription=categories_inscription, scolarites=scolarites,
                         tarifs_services=tarifs_services, classes=classes, abonnements=abonnements)

@app.route('/finances/parametres/categorie/ajouter', methods=['POST'])
@login_required
def categorie_ajouter():
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    nom = request.form.get('nom')
    type_categorie = request.form.get('type_categorie')
    if not nom or not type_categorie:
        return jsonify({'success': False, 'message': 'Champs manquants'}), 400
    categorie = CategorieTarif(nom=nom.upper(), type_categorie=type_categorie.strip(), ecole_id=ecole_id)
    db.session.add(categorie)
    db.session.commit()
    flash('Categorie ajoutee avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='categories'))

@app.route('/finances/parametres/categorie/supprimer/<int:id>', methods=['POST'])
@login_required
def categorie_supprimer(id):
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    categorie = CategorieTarif.query.get_or_404(id)
    TarifService.query.filter_by(categorie_id=id).delete()
    AbonnementService.query.filter_by(categorie_id=id).delete()
    db.session.delete(categorie)
    db.session.commit()
    flash('Categorie supprimee avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='categories'))

@app.route('/finances/parametres/abonnement/ajouter', methods=['POST'])
@login_required
def abonnement_ajouter():
    ecole_id = get_current_ecole_id()
    check = _check_parametres_access(ecole_id)
    if check: return check
    eleve_id = request.form.get('eleve_id')
    categorie_id = request.form.get('categorie_id')
    mois_debut = request.form.get('mois_debut')
    mois_fin = request.form.get('mois_fin')
    montant_str = request.form.get('montant_personnalise', '').strip()
    montant_personnalise = float(montant_str) if montant_str else None
    abo = AbonnementService(
        eleve_id=eleve_id, categorie_id=categorie_id,
        mois_debut=mois_debut, mois_fin=mois_fin,
        montant_personnalise=montant_personnalise, actif=True
    )
    db.session.add(abo)
    db.session.commit()
    flash('Abonnement ajoute avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='abonnements'))

@app.route('/finances/parametres/abonnement/supprimer/<int:id>', methods=['POST'])
@login_required
def abonnement_supprimer(id):
    ecole_id = get_current_ecole_id()
    check = _check_parametres_access(ecole_id)
    if check: return check
    abo = AbonnementService.query.get_or_404(id)
    db.session.delete(abo)
    db.session.commit()
    flash('Abonnement supprime', 'success')
    return redirect(url_for('parametres_financiers', _anchor='abonnements'))

@app.route('/api/scolarite/<int:classe_id>')
@login_required
def api_scolarite(classe_id):
    """Retourne les montants de scolarite pour une classe"""
    ecole_id = get_current_ecole_id()
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=_annee_courante(Ecole.query.get(ecole_id))).first()
    if not scolarite:
        return jsonify({'inscription': 0, 'janvier': 0, 'fevrier': 0, 'mars': 0, 'avril': 0,
            'mai': 0, 'juin': 0, 'juillet': 0, 'aout': 0, 'septembre': 0,
            'octobre': 0, 'novembre': 0, 'decembre': 0, 'total_annuel': 0})
    return jsonify({'inscription': scolarite.inscription, 'janvier': scolarite.janvier,
        'fevrier': scolarite.fevrier, 'mars': scolarite.mars, 'avril': scolarite.avril,
        'mai': scolarite.mai, 'juin': scolarite.juin, 'juillet': scolarite.juillet,
        'aout': scolarite.aout, 'septembre': scolarite.septembre,
        'octobre': scolarite.octobre, 'novembre': scolarite.novembre,
        'decembre': scolarite.decembre, 'total_annuel': scolarite.total_annuel})

@app.route('/api/tarif-service/<int:classe_id>/<int:categorie_id>')
@login_required
def api_tarif_service(classe_id, categorie_id):
    """Retourne les montants de tarif service pour une classe et une categorie"""
    ecole_id = get_current_ecole_id()
    tarif = TarifService.query.filter_by(classe_id=classe_id, categorie_id=categorie_id,
        annee_scolaire=_annee_courante(Ecole.query.get(ecole_id))).first()
    if not tarif:
        return jsonify({'inscription': 0, 'janvier': 0, 'fevrier': 0, 'mars': 0, 'avril': 0,
            'mai': 0, 'juin': 0, 'juillet': 0, 'aout': 0, 'septembre': 0,
            'octobre': 0, 'novembre': 0, 'decembre': 0, 'total_annuel': 0})
    return jsonify({'inscription': tarif.inscription, 'janvier': tarif.janvier,
        'fevrier': tarif.fevrier, 'mars': tarif.mars, 'avril': tarif.avril,
        'mai': tarif.mai, 'juin': tarif.juin, 'juillet': tarif.juillet,
        'aout': tarif.aout, 'septembre': tarif.septembre,
        'octobre': tarif.octobre, 'novembre': tarif.novembre,
        'decembre': tarif.decembre, 'total_annuel': tarif.total_annuel})

@app.route('/finances/parametres/scolarite/sauvegarder', methods=['POST'])
@login_required
def scolarite_sauvegarder():
    """Sauvegarde les scolarites pour toutes les classes"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            flash('Vous devez avoir un abonnement actif.', 'danger')
            return redirect(url_for('abonnement'))
    mois_list = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
    annee = _annee_courante(Ecole.query.get(ecole_id))
    save_count = 0
    classes = Classe.query.all()
    for classe in classes:
        has_data = any(request.form.get(f'{mois}_{classe.id}') is not None for mois in mois_list)
        if not has_data: continue
        scolarite = Scolarite.query.filter_by(classe_id=classe.id, annee_scolaire=annee, ecole_id=ecole_id).first()
        if not scolarite:
            scolarite = Scolarite(classe_id=classe.id, annee_scolaire=annee, ecole_id=ecole_id)
            db.session.add(scolarite)
        for mois in mois_list:
            field_name = f'{mois}_{classe.id}'
            montant = request.form.get(field_name, '')
            if montant != '':
                try: setattr(scolarite, mois, float(montant))
                except ValueError: pass
        save_count += 1
    db.session.commit()
    flash(f'{save_count} scolarite(s) sauvegardee(s) avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='scolarite'))

@app.route('/finances/parametres/scolarite/ajouter-ligne', methods=['POST'])
@login_required
def scolarite_ajouter_ligne():
    """Ajoute une ou plusieurs nouvelles lignes de scolarite"""
    ecole_id = get_current_ecole_id()
    err = _check_parametres_access_json(ecole_id)
    if err: return err
    annee = _annee_courante(Ecole.query.get(ecole_id))
    noms_classes = request.form.get('noms_classes', '').strip()
    if not noms_classes:
        flash('Veuillez saisir au moins un nom de classe', 'warning')
        return redirect(url_for('parametres_financiers', _anchor='scolarite'))
    lignes = [l.strip() for l in noms_classes.replace('\n', ',').split(',') if l.strip()]
    ajoutees = 0
    existe_deja = []
    # Calculer le prochain ordre disponible
    max_ordre = db.session.query(db.func.max(Scolarite.ordre)).filter_by(annee_scolaire=annee).scalar() or 0
    for nom in lignes:
        classe = Classe.query.filter_by(nom=nom, ecole_id=ecole_id).first()
        if not classe:
            classe = Classe(nom=nom, ecole_id=ecole_id)
            db.session.add(classe)
            db.session.flush()
        scolarite = Scolarite.query.filter_by(classe_id=classe.id, annee_scolaire=annee, ecole_id=ecole_id).first()
        if scolarite:
            existe_deja.append(nom)
        else:
            max_ordre += 1
            scolarite = Scolarite(classe_id=classe.id, annee_scolaire=annee, ecole_id=ecole_id, ordre=max_ordre)
            db.session.add(scolarite)
            ajoutees += 1
    db.session.commit()
    msg_parts = []
    if ajoutees > 0:
        msg_parts.append(f'{ajoutees} ligne(s) de scolarite ajoutee(s) avec succes')
    if existe_deja:
        msg_parts.append(f'{len(existe_deja)} classe(s) ont deja une scolarite')
    if msg_parts:
        flash('. '.join(msg_parts), 'success' if ajoutees > 0 else 'info')
    else:
        flash('Aucune ligne ajoutee', 'info')
    return redirect(url_for('parametres_financiers', _anchor='scolarite'))

@app.route('/api/scolarite/sauvegarder/<int:classe_id>', methods=['POST'])
@login_required
def api_scolarite_sauvegarder(classe_id):
    """Sauvegarde les montants de scolarite pour une classe (AJAX)"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Donnees invalides'}), 400
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).first()
    if not scolarite:
        max_ordre = db.session.query(db.func.max(Scolarite.ordre)).filter_by(annee_scolaire=annee, ecole_id=ecole_id).scalar() or 0
        scolarite = Scolarite(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id, ordre=max_ordre + 1)
        db.session.add(scolarite)
    mois_list = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
    for mois in mois_list:
        if mois in data:
            setattr(scolarite, mois, float(data[mois]))
    db.session.commit()
    return jsonify({'success': True, 'total_annuel': scolarite.total_annuel})

@app.route('/api/scolarite/reinitialiser/<int:classe_id>', methods=['POST'])
@login_required
def api_scolarite_reinitialiser(classe_id):
    """Remet a zero les montants de scolarite pour une classe (AJAX)"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).first()
    if scolarite:
        mois_list = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
        for mois in mois_list:
            setattr(scolarite, mois, 0)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/scolarite/supprimer/<int:classe_id>', methods=['POST'])
@login_required
def api_scolarite_supprimer(classe_id):
    """Supprime une ligne de scolarite (AJAX)"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).first()
    if scolarite:
        db.session.delete(scolarite)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/scolarite/reinitialiser/tout', methods=['POST'])
@login_required
def api_scolarite_reinitialiser_tout():
    """Remet a zero toutes les scolarites (AJAX)"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarites = Scolarite.query.filter_by(annee_scolaire=annee, ecole_id=ecole_id).all()
    for s in scolarites:
        mois_list = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
        for mois in mois_list:
            setattr(s, mois, 0)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/scolarite/reorder', methods=['POST'])
@login_required
def api_scolarite_reorder():
    """Reordonne les lignes de scolarite (AJAX)"""
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if not _bypass_licence_check():
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({'success': False, 'message': 'Donnees invalides'}), 400
    for idx, scolarite_id in enumerate(data['ids']):
        scolarite = Scolarite.query.get(scolarite_id)
        if scolarite:
            scolarite.ordre = idx
    db.session.commit()
    return jsonify({'success': True})

@app.route('/finances/parametres/tarif-service/sauvegarder', methods=['POST'])
@login_required
def tarif_service_sauvegarder():
    """Sauvegarde les tarifs de service pour une classe et une categorie"""
    ecole_id = get_current_ecole_id()
    err = _check_parametres_access_json(ecole_id)
    if err: return err
    annee = _annee_courante(Ecole.query.get(ecole_id))
    classe_id = request.form.get('classe_id')
    categorie_id = request.form.get('categorie_id')
    if not classe_id or not categorie_id:
        flash('Classe et categorie requises', 'warning')
        return redirect(url_for('parametres_financiers', _anchor='categories'))
    tarif = TarifService.query.filter_by(classe_id=classe_id, categorie_id=categorie_id, annee_scolaire=annee, ecole_id=ecole_id).first()
    if tarif:
        flash('Ce tarif existe deja.', 'info')
        return redirect(url_for('parametres_financiers', _anchor='categories'))
    tarif = TarifService(classe_id=classe_id, categorie_id=categorie_id, annee_scolaire=annee, ecole_id=ecole_id)
    mois_list = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin',
                 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre']
    for mois in mois_list:
        montant = request.form.get(mois, '')
        if montant:
            try: setattr(tarif, mois, float(montant))
            except ValueError: pass
    db.session.add(tarif)
    db.session.commit()
    flash('Ligne ajoutee avec succes.', 'success')
    return redirect(url_for('parametres_financiers', _anchor='categories'))

@app.route('/finances/parametres/tarif-service/supprimer/<int:id>', methods=['POST'])
@login_required
def tarif_service_supprimer(id):
    ecole_id = get_current_ecole_id()
    err = _check_parametres_access(ecole_id)
    if err: return err
    tarif = TarifService.query.get_or_404(id)
    db.session.delete(tarif)
    db.session.commit()
    flash('Tarif de service supprime avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='categories'))

@app.route('/admin/fix-ecole-id')
@login_required
def admin_fix_ecole_id():
    """Corrige les enregistrements sans ecole_id ou avec le mauvais ecole_id"""
    if current_user.role not in ('dev', 'super_users'):
        flash('Acces reserve', 'danger')
        return redirect(url_for('dashboard'))
    ecole_id = get_current_ecole_id()
    
    resultats = []
    # Corriger Scolarite
    nb = Scolarite.query.filter(Scolarite.ecole_id != ecole_id).update({Scolarite.ecole_id: ecole_id}, synchronize_session=False)
    resultats.append(f'Scolarites corrigees: {nb}')
    # Corriger TarifService
    nb2 = TarifService.query.filter(TarifService.ecole_id != ecole_id).update({TarifService.ecole_id: ecole_id}, synchronize_session=False)
    resultats.append(f'Tarifs services corriges: {nb2}')
    # Corriger CategorieTarif
    nb3 = CategorieTarif.query.filter(CategorieTarif.ecole_id != ecole_id).update({CategorieTarif.ecole_id: ecole_id}, synchronize_session=False)
    resultats.append(f'Categories corrigees: {nb3}')
    db.session.commit()
    
    flash(f'Migration ecole_id={ecole_id} terminee. ' + ' | '.join(resultats), 'success')
    return redirect(url_for('finances'))
