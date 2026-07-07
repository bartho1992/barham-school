from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from models import db, Ecole, Eleve, Paiement, Classe, CategorieTarif, Scolarite, TarifService, AbonnementService
from app import app, get_current_ecole_id
from datetime import datetime
# import pandas as pd  # Non necessaire, retire pour eviter dependance lourde

try:
    import requests
except ImportError:
    requests = None

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '')

def _check_parametres_access(ecole_id):
    """Verifie l'acces aux parametres : super_users toujours ok, user = licence active requise"""
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return redirect(url_for('abonnement'))
    return None

def _check_parametres_access_json(ecole_id):
    """Version JSON pour les appels AJAX"""
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'error': 'Licence expiree', 'redirect': url_for('abonnement')}), 403
    return None

@app.route('/finances')
@login_required
def finances():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    recent_paiements = Paiement.query.filter_by(annee_scolaire=annee).order_by(Paiement.date_paiement.desc()).limit(20).all()
    total_encaisse = db.session.query(db.func.sum(Paiement.montant)).filter_by(annee_scolaire=annee).scalar() or 0
    today_encaisse = db.session.query(db.func.sum(Paiement.montant)).filter(db.func.date(Paiement.date_paiement) == datetime.now().date(), Paiement.annee_scolaire == annee).scalar() or 0
    categories = CategorieTarif.query.order_by(CategorieTarif.nom).all()
    
    # Calculer les lignes eleves pour le suivi paiement
    mois_scolaires = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).order_by(Eleve.nom).all()
    scolarites_map = {s.classe_id: s for s in Scolarite.query.filter_by(annee_scolaire=annee).all()}
    tarifs_services_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee).all():
        tarifs_services_map[(t.classe_id, t.categorie_id)] = t
    abonnements_map = {}
    for a in AbonnementService.query.filter_by(actif=True).all():
        abonnements_map.setdefault(a.eleve_id, set()).add(a.categorie_id)
    paiements_map = {}
    for p in Paiement.query.filter_by(annee_scolaire=annee).all():
        if p.eleve_id not in paiements_map:
            paiements_map[p.eleve_id] = {}
        key = p.type_paiement or ''
        paiements_map[p.eleve_id][key] = paiements_map[p.eleve_id].get(key, 0) + p.montant
    
    lignes_paiements = []
    for eleve in eleves:
        if not eleve.classe: continue
        scol = scolarites_map.get(eleve.classe_id)
        payes = paiements_map.get(eleve.id, {})
        abos = abonnements_map.get(eleve.id, set())
        scolarite_due = scol.total_annuel if scol else 0
        scolarite_paye = sum(payes.get(m, 0) for m in mois_scolaires)
        
        # Donnees par mois pour la scolarite
        mois_details = {}
        for m in mois_scolaires:
            if m == 'Inscription':
                due_m = scol.inscription if scol else 0
            else:
                due_m = getattr(scol, m.lower(), 0) if scol else 0
            paye_m = payes.get(m, 0)
            reste_m = max(due_m - paye_m, 0)
            mois_details[m] = {'due': due_m, 'paye': paye_m, 'reste': reste_m}
        
        cat_lines = []
        services_due = 0
        services_paye = 0
        for cat in categories:
            tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
            is_abonne = cat.id in abos
            if not tarif or not is_abonne:
                cat_lines.append({'cat': cat, 'due': 0, 'paye': 0, 'reste': 0})
                continue
            due = tarif.total_annuel
            paye = payes.get(cat.nom, 0)
            reste = max(due - paye, 0)
            services_due += due
            services_paye += paye
            cat_lines.append({'cat': cat, 'due': due, 'paye': paye, 'reste': reste})
        total_du = scolarite_due + services_due
        total_paye = scolarite_paye + services_paye
        total_reste = max(total_du - total_paye, 0)
        nb_mois_actifs = len([m for m in mois_scolaires if m == 'Inscription' and scol and scol.inscription > 0 or m != 'Inscription' and scol and getattr(scol, m.lower(), 0) > 0]) if scol else 0
        for cat in categories:
            tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
            if tarif and cat.id in abos:
                for m in ['inscription','janvier','fevrier','mars','avril','mai','juin','octobre','novembre','decembre']:
                    if getattr(tarif, m, 0) > 0: nb_mois_actifs = max(nb_mois_actifs, 10)
        if nb_mois_actifs < 1: nb_mois_actifs = 10
        montant_mois = total_du / nb_mois_actifs if total_du > 0 else 0
        date_limite = ''
        try:
            annees = annee.split('-') if annee else ['2025','2026']
            date_limite = f'30/06/{annees[1] if len(annees) > 1 else "2026"}'
        except: pass
        lignes_paiements.append({
            'eleve': eleve, 'total_du': total_du, 'total_paye': total_paye,
            'total_reste': total_reste, 'montant_mois': montant_mois,
            'date_limite': date_limite, 'cat_lines': cat_lines,
            'paye_au_moins_un': total_paye > 0,
            'mois_payes': set(payes.keys()),
            'mois_details': mois_details,
        })
    
    # Mois distincts des paiements pour le filtre
    mois_paiements = sorted(set(
        p.type_paiement for p in Paiement.query.filter_by(annee_scolaire=annee).all() if p.type_paiement
    ))
    mois_scolaires_filtre = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    mois_list = [m for m in mois_scolaires_filtre if m in mois_paiements] or mois_scolaires_filtre
    
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.nom).all()
    
    return render_template('finances/index.html', ecole=e, paiements=recent_paiements, total_encaisse=total_encaisse,
        today_encaisse=today_encaisse, categories=categories, lignes_paiements=lignes_paiements, classes=classes, mois_list=mois_list)

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
    
    mois_a_payer = []
    for i in range(0, idx_selection + 1):
        m = mois_scolaires[i]
        tarif_m = scolarite.inscription if m == 'Inscription' else (getattr(scolarite, m.lower(), 0) or 0) if scolarite else 0
        if tarif_m > 0:
            deja = paye_par_mois.get(m, 0)
            reste_m = tarif_m - deja
            if reste_m > 0 or m == mois:
                mois_a_payer.append({
                    'mois': m,
                    'tarif': tarif_m,
                    'deja_paye': deja,
                    'reste': reste_m
                })
    
    total_scolarite = 0
    total_services_global = 0
    ordre_mois = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                  'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']
    
    for item in mois_a_payer:
        m = item['mois']
        is_inscr = (m == 'Inscription')
        services_mois = []
        total_srv_mois = 0
        
        if is_inscr:
            # Services inscription : toutes les categories definies dans parametres, champ vide
            categories_insc = CategorieTarif.query.filter_by(type_categorie='inscription').all()
            for cat in categories_insc:
                services_mois.append({'nom': cat.nom, 'montant': 0})
                total_srv_mois += 0
        else:
            abonnements = AbonnementService.query.filter_by(
                eleve_id=eleve_id
            ).join(CategorieTarif).all()
            for abo in abonnements:
                cat = abo.categorie
                # Inscription-type service: montant unique, seulement dans le mois Inscription
                if cat.type_categorie == 'inscription':
                    continue
                # Mensuel: verifier la periode d'abonnement
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
                    total_srv_mois += montant
        
        item['services'] = services_mois
        item['total_services'] = total_srv_mois
        total_scolarite += item['reste']
        total_services_global += total_srv_mois
    
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
    
    # Mois de la sequence scolaire
    mois_scolaires = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    
    # Recuperer la scolarite de la classe de l'eleve
    scolarite = None
    if eleve.classe:
        scolarite = Scolarite.query.filter_by(classe_id=eleve.classe_id, annee_scolaire=annee).first()
    
    # Recuperer tous les paiements de l'eleve pour cette annee
    paiements = Paiement.query.filter_by(eleve_id=eleve_id, annee_scolaire=annee).all()
    
    # Total paye par mois
    paye_par_mois = {}
    for p in paiements:
        mois_key = p.type_paiement
        paye_par_mois[mois_key] = paye_par_mois.get(mois_key, 0) + p.montant
    
    resultat = {}
    for mois in mois_scolaires:
        # Tarif du mois
        tarif_mois = 0
        if scolarite:
            if mois == 'Inscription':
                tarif_mois = scolarite.inscription or 0
            else:
                tarif_mois = getattr(scolarite, mois.lower(), 0) or 0
        
        total_paye = paye_par_mois.get(mois, 0)
        resultat[mois] = {
            'tarif': tarif_mois,
            'paye': total_paye >= tarif_mois if tarif_mois > 0 else False,
            'total_paye': total_paye,
            'impaye': max(tarif_mois - total_paye, 0) if tarif_mois > 0 else 0
        }
    
    return jsonify({'paiements': resultat, 'eleve_id': eleve_id, 'annee': annee})

@app.route('/finances/list')
@login_required
def finances_liste():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    q = Paiement.query.filter_by(annee_scolaire=annee)
    type_p = request.args.get('type_paiement')
    if type_p: q = q.filter_by(type_paiement=type_p)
    ps = q.order_by(Paiement.date_paiement.desc()).all()
    return render_template('finances/liste.html', paiements=ps, ecole=e)

@app.route('/finances/impayes')
@login_required
def impayes():
    """Tableau des impayes : eleves x categories de services"""
    import sys
    print("===== impayES V2 (categories) =====", file=sys.stderr)
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    
    mois_scolaires = ['Inscription','Octobre','Novembre','Decembre','Janvier','Fevrier','Mars','Avril','Mai','Juin']
    
    # Categories de services
    categories = CategorieTarif.query.order_by(CategorieTarif.nom).all()
    
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(Eleve.annee_scolaire == annee, Eleve.annee_scolaire == None, Eleve.annee_scolaire == '')
    ).order_by(Eleve.nom).all()
    
    # Map: classe_id -> Scolarite
    scolarites_map = {}
    for s in Scolarite.query.filter_by(annee_scolaire=annee).all():
        scolarites_map[s.classe_id] = s
    
    # Map: (classe_id, categorie_id) -> TarifService
    tarifs_services_map = {}
    for t in TarifService.query.filter_by(annee_scolaire=annee).all():
        tarifs_services_map[(t.classe_id, t.categorie_id)] = t
    
    # Map: eleve_id -> {categorie_id} (active subscriptions)
    abonnements_map = {}
    for a in AbonnementService.query.filter_by(actif=True).all():
        if a.eleve_id not in abonnements_map:
            abonnements_map[a.eleve_id] = set()
        abonnements_map[a.eleve_id].add(a.categorie_id)
    
    # Map: eleve_id -> {type_paiement: total_paye}
    paiements_map = {}
    for p in Paiement.query.filter_by(annee_scolaire=annee).all():
        if p.eleve_id not in paiements_map:
            paiements_map[p.eleve_id] = {}
        key = p.type_paiement or ''
        paiements_map[p.eleve_id][key] = paiements_map[p.eleve_id].get(key, 0) + p.montant
    
    lignes = []
    total_global = 0
    
    for eleve in eleves:
        if not eleve.classe: continue
        scol = scolarites_map.get(eleve.classe_id)
        payes = paiements_map.get(eleve.id, {})
        abos = abonnements_map.get(eleve.id, set())
        
        # --- Scolarité (due et paye) ---
        scolarite_due = scol.total_annuel if scol else 0
        scolarite_paye = sum(payes.get(m, 0) for m in mois_scolaires)
        
        # --- Services (categories) ---
        cat_lines = []
        services_due = 0
        services_paye = 0
        for cat in categories:
            tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
            is_abonne = cat.id in abos
            if not tarif or not is_abonne:
                cat_lines.append({
                    'cat': cat, 'due': 0, 'paye': 0, 'reste': 0,
                    'statut': 'inactif' if not is_abonne else 'sans_tarif'
                })
                continue
            due = tarif.total_annuel
            paye = payes.get(cat.nom, 0)
            reste = max(due - paye, 0)
            services_due += due
            services_paye += paye
            cat_lines.append({
                'cat': cat, 'due': due, 'paye': paye, 'reste': reste,
                'statut': 'impaye' if reste > 0 else 'paye'
            })
        
        # --- Totaux ---
        total_du = scolarite_due + services_due
        total_paye = scolarite_paye + services_paye
        total_reste = max(total_du - total_paye, 0)
        nb_mois_actifs = len([m for m in mois_scolaires if (scol.inscription if m == 'Inscription' else getattr(scol, m.lower(), 0) or 0) > 0]) if scol else 0
        # Ajouter mois pour services
        for cat in categories:
            tarif = tarifs_services_map.get((eleve.classe_id, cat.id))
            if tarif and cat.id in abos:
                for m in ['inscription','janvier','fevrier','mars','avril','mai','juin',
                          'juillet','aout','septembre','octobre','novembre','decembre']:
                    if getattr(tarif, m, 0) > 0:
                        nb_mois_actifs = max(nb_mois_actifs, 10)  # 10 school months
        if nb_mois_actifs < 1: nb_mois_actifs = 10
        montant_mois = total_du / nb_mois_actifs if total_du > 0 else 0
        
        # --- Déterminer date limite ---
        from datetime import datetime
        date_limite = ''
        try:
            annees = annee.split('-') if annee else ['2025','2026']
            date_limite = f'30/06/{annees[1] if len(annees) > 1 else "2026"}'
        except: pass
        
        ligne = {
            'eleve': eleve,
            'scolarite_due': scolarite_due,
            'scolarite_paye': scolarite_paye,
            'scolarite_reste': max(scolarite_due - scolarite_paye, 0),
            'cat_lines': cat_lines,
            'total_du': total_du,
            'total_paye': total_paye,
            'total_reste': total_reste,
            'montant_mois': montant_mois,
            'date_limite': date_limite,
            'nb_impayes': sum(1 for cl in cat_lines if cl['reste'] > 0) + (1 if scol and max(scolarite_due - scolarite_paye, 0) > 0 else 0),
        }
        total_global += total_reste
        lignes.append(ligne)
    
    return render_template('finances/impayes.html',
                         lignes=lignes, ecole=e, categories=categories,
                         total_impayes_global=total_global, nb_eleves=len(lignes))

@app.route('/finances/parametres')
@login_required
def parametres_financiers():
    # Accessible a tous les utilisateurs avec une licence
    from models import Licence
    ecole_id = get_current_ecole_id()
    if current_user.role != 'super_users':
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            flash('Vous devez avoir un abonnement actif pour acceder aux paramètres.', 'danger')
            return redirect(url_for('abonnement'))
    e = Ecole.query.get(ecole_id); annee = _annee_courante(e)
    categories = CategorieTarif.query.order_by(CategorieTarif.type_categorie, CategorieTarif.nom).all()
    categories_mensuel = CategorieTarif.query.filter_by(type_categorie='mensuel').all()
    categories_inscription = CategorieTarif.query.filter_by(type_categorie='inscription').all()
    scolarites = Scolarite.query.filter_by(annee_scolaire=annee).order_by(Scolarite.ordre, Scolarite.classe_id).all()
    tarifs_services = TarifService.query.filter_by(annee_scolaire=annee).order_by(TarifService.classe_id, TarifService.categorie_id).all()
    classes = Classe.query.order_by(Classe.nom).all()
    abonnements = AbonnementService.query.filter_by(actif=True).order_by(AbonnementService.date_debut.desc()).all()
    return render_template('finances/parametres.html',
                         ecole=e, categories=categories, categories_mensuel=categories_mensuel,
                         categories_inscription=categories_inscription, scolarites=scolarites,
                         tarifs_services=tarifs_services, classes=classes, abonnements=abonnements)

@app.route('/finances/parametres/categorie/ajouter', methods=['POST'])
@login_required
def categorie_ajouter():
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    nom = request.form.get('nom')
    type_categorie = request.form.get('type_categorie')
    if not nom or not type_categorie:
        return jsonify({'success': False, 'message': 'Champs manquants'}), 400
    categorie = CategorieTarif(nom=nom.upper(), type_categorie=type_categorie.strip())
    db.session.add(categorie)
    db.session.commit()
    flash('Categorie ajoutee avec succes', 'success')
    return redirect(url_for('parametres_financiers', _anchor='categories'))

@app.route('/finances/parametres/categorie/supprimer/<int:id>', methods=['POST'])
@login_required
def categorie_supprimer(id):
    ecole_id = get_current_ecole_id()
    # Alow all users with active licence
    if current_user.role != 'super_users':
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
    if current_user.role != 'super_users':
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
        scolarite = Scolarite.query.filter_by(classe_id=classe.id, annee_scolaire=annee).first()
        if not scolarite:
            scolarite = Scolarite(classe_id=classe.id, annee_scolaire=annee)
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
        scolarite = Scolarite.query.filter_by(classe_id=classe.id, annee_scolaire=annee).first()
        if scolarite:
            existe_deja.append(nom)
        else:
            max_ordre += 1
            scolarite = Scolarite(classe_id=classe.id, annee_scolaire=annee, ordre=max_ordre)
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
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Donnees invalides'}), 400
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee).first()
    if not scolarite:
        max_ordre = db.session.query(db.func.max(Scolarite.ordre)).filter_by(annee_scolaire=annee).scalar() or 0
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
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee).first()
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
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarite = Scolarite.query.filter_by(classe_id=classe_id, annee_scolaire=annee).first()
    if scolarite:
        db.session.delete(scolarite)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/scolarite/reinitialiser/tout', methods=['POST'])
@login_required
def api_scolarite_reinitialiser_tout():
    """Remet a zero toutes les scolarites (AJAX)"""
    # Alow all users with active licence
    if current_user.role != 'super_users':
        from models import Licence
        lic = Licence.licence_active_for_ecole(ecole_id)
        if not lic:
            return jsonify({'success': False, 'message': 'Abonnement requis'}), 403
    ecole_id = get_current_ecole_id()
    annee = _annee_courante(Ecole.query.get(ecole_id))
    scolarites = Scolarite.query.filter_by(annee_scolaire=annee).all()
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
    # Alow all users with active licence
    if current_user.role != 'super_users':
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
    tarif = TarifService.query.filter_by(classe_id=classe_id, categorie_id=categorie_id, annee_scolaire=annee).first()
    if tarif:
        flash('Ce tarif existe deja.', 'info')
        return redirect(url_for('parametres_financiers', _anchor='categories'))
    tarif = TarifService(classe_id=classe_id, categorie_id=categorie_id, annee_scolaire=annee)
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
