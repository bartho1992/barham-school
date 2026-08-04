from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, CompteComptable, EcritureComptable
from app import app, get_current_ecole_id
from datetime import datetime


def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '')


def _bypass_licence_check():
    return current_user.role in ('super_users', 'dev')


def _format_montant(valeur):
    """Format montant avec separateur d'espace pour les milliers (francais)."""
    if valeur is None:
        return "0"
    return f"{valeur:,.0f}".replace(",", " ")


def _solde_compte(compte, ecole_id):
    """
    Calcule solde = total_debit - total_credit pour un compte.
    Les regles de presentation (debiteur/crediteur) sont gerees cote affichage.
    """
    total_debit = db.session.query(db.func.coalesce(db.func.sum(EcritureComptable.montant), 0)).filter(
        EcritureComptable.compte_debit_id == compte.id,
        EcritureComptable.ecole_id == ecole_id
    ).scalar()

    total_credit = db.session.query(db.func.coalesce(db.func.sum(EcritureComptable.montant), 0)).filter(
        EcritureComptable.compte_credit_id == compte.id,
        EcritureComptable.ecole_id == ecole_id
    ).scalar()

    solde = total_debit - total_credit
    return solde, total_debit, total_credit


def _classe_from_numero(numero):
    """Retourne la classe comptable (1 a 9) a partir du numero de compte."""
    for ch in str(numero):
        if ch.isdigit() and ch != '0':
            return int(ch)
    return None


def _nature_du_solde(nature_compte):
    """
    Retourne si un compte est normalement debiteur ou crediteur.
    Actif (2,3,5) et Charge (6): debiteur = positif quand debit > credit
    Passif (1,4) et Produit (7): crediteur = positif quand credit > debit
    """
    if nature_compte in ('actif', 'charge'):
        return 'debiteur'
    if nature_compte in ('passif', 'produit'):
        return 'crediteur'
    return 'debiteur'


# ==============================================================================
# 1. Accueil comptabilite
# ==============================================================================
@app.route('/comptabilite/')
@login_required
def comptabilite_accueil():
    ecole_id = get_current_ecole_id()

    # Totaux par nature (sur les comptes de classe, niveau 1)
    comptes_classe = CompteComptable.query.filter_by(ecole_id=ecole_id, niveau=1).all()
    totaux_nature = {}
    for nature in ('actif', 'passif', 'charge', 'produit'):
        totaux_nature[nature] = 0.0
    for c in comptes_classe:
        solde, _, _ = _solde_compte(c, ecole_id)
        sens = _nature_du_solde(c.nature)
        if sens == 'crediteur':
            solde_abs = -solde  # un solde negatif devient un solde crediteur positif
        else:
            solde_abs = solde
        totaux_nature[c.nature] = totaux_nature.get(c.nature, 0.0) + abs(solde_abs)

    # 10 dernieres ecritures
    dernieres_ecritures = EcritureComptable.query.filter_by(ecole_id=ecole_id) \
        .order_by(EcritureComptable.date_ecriture.desc(), EcritureComptable.id.desc()) \
        .limit(10).all()

    return render_template('comptabilite/index.html',
                           total_actif=totaux_nature.get('actif', 0),
                           total_passif=totaux_nature.get('passif', 0),
                           total_charges=totaux_nature.get('charge', 0),
                           total_produits=totaux_nature.get('produit', 0),
                           totaux_nature=totaux_nature,
                           dernieres_ecritures=dernieres_ecritures,
                           format_montant=_format_montant)


# ==============================================================================
# 2. Plan comptable
# ==============================================================================
@app.route('/comptabilite/plan')
@login_required
def comptabilite_plan():
    ecole_id = get_current_ecole_id()
    filtre_nature = request.args.get('nature', '').strip()

    query = CompteComptable.query.filter_by(ecole_id=ecole_id)
    if filtre_nature:
        query = query.filter_by(nature=filtre_nature)

    comptes = query.order_by(CompteComptable.numero).all()

    # Grouper par classe
    plan = {}
    for c in comptes:
        classe = _classe_from_numero(c.numero)
        if classe is None:
            classe = 0
        if classe not in plan:
            plan[classe] = []
        plan[classe].append(c)

    # Trier les classes 1..9
    plan = dict(sorted(plan.items()))

    return render_template('comptabilite/plan.html',
                           plan=plan,
                           filtre_nature=filtre_nature,
                           format_montant=_format_montant)


# ==============================================================================
# 3. Detail d'un compte
# ==============================================================================
@app.route('/comptabilite/compte/<int:id>')
@login_required
def comptabilite_compte_detail(id):
    ecole_id = get_current_ecole_id()
    compte = CompteComptable.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()

    solde, total_debit, total_credit = _solde_compte(compte, ecole_id)
    sens = _nature_du_solde(compte.nature)

    # Ecritures liees
    ecritures = EcritureComptable.query.filter_by(ecole_id=ecole_id) \
        .filter(
            db.or_(
                EcritureComptable.compte_debit_id == compte.id,
                EcritureComptable.compte_credit_id == compte.id
            )
        ) \
        .order_by(EcritureComptable.date_ecriture.desc(), EcritureComptable.id.desc()) \
        .all()

    return render_template('comptabilite/compte.html',
                           compte=compte,
                           solde=solde,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           sens=sens,
                           ecritures=ecritures,
                           format_montant=_format_montant)


# ==============================================================================
# 4. Liste des ecritures
# ==============================================================================
@app.route('/comptabilite/ecritures')
@login_required
def comptabilite_ecritures():
    ecole_id = get_current_ecole_id()

    date_debut = request.args.get('date_debut', '').strip()
    date_fin = request.args.get('date_fin', '').strip()
    compte_id = request.args.get('compte_id', '').strip()
    type_filter = request.args.get('type', '').strip()

    query = EcritureComptable.query.filter_by(ecole_id=ecole_id)

    if date_debut:
        try:
            d = datetime.strptime(date_debut, '%Y-%m-%d')
            query = query.filter(EcritureComptable.date_ecriture >= d)
        except ValueError:
            pass

    if date_fin:
        try:
            d = datetime.strptime(date_fin, '%Y-%m-%d')
            query = query.filter(EcritureComptable.date_ecriture <= d)
        except ValueError:
            pass

    if compte_id:
        try:
            cid = int(compte_id)
            query = query.filter(
                db.or_(
                    EcritureComptable.compte_debit_id == cid,
                    EcritureComptable.compte_credit_id == cid
                )
            )
        except ValueError:
            pass

    if type_filter:
        query = query.filter_by(type_ecriture=type_filter)

    ecritures = query.order_by(
        EcritureComptable.date_ecriture.desc(),
        EcritureComptable.id.desc()
    ).all()

    # Liste des comptes pour le filtre
    comptes = CompteComptable.query.filter_by(ecole_id=ecole_id) \
        .order_by(CompteComptable.numero).all()

    return render_template('comptabilite/ecritures.html',
                           ecritures=ecritures,
                           comptes=comptes,
                           date_debut=date_debut,
                           date_fin=date_fin,
                           compte_id=compte_id,
                           type_filter=type_filter,
                           format_montant=_format_montant)


# ==============================================================================
# 5. Nouvelle ecriture
# ==============================================================================
@app.route('/comptabilite/ecriture/nouvelle', methods=['GET', 'POST'])
@login_required
def comptabilite_ecriture_nouvelle():
    ecole_id = get_current_ecole_id()

    if request.method == 'POST':
        date_str = request.form.get('date_ecriture', '').strip()
        libelle = request.form.get('libelle', '').strip()
        reference = request.form.get('reference', '').strip()
        montant_str = request.form.get('montant', '').strip()
        compte_debit_id = request.form.get('compte_debit_id', '').strip()
        compte_credit_id = request.form.get('compte_credit_id', '').strip()

        erreurs = []

        if not date_str:
            erreurs.append("La date est obligatoire.")
        if not libelle:
            erreurs.append("Le libelle est obligatoire.")
        if not montant_str:
            erreurs.append("Le montant est obligatoire.")
        if not compte_debit_id:
            erreurs.append("Le compte de debit est obligatoire.")
        if not compte_credit_id:
            erreurs.append("Le compte de credit est obligatoire.")

        montant = 0
        try:
            montant = float(montant_str)
            if montant <= 0:
                erreurs.append("Le montant doit etre superieur a 0.")
        except (ValueError, TypeError):
            erreurs.append("Le montant est invalide.")

        if compte_debit_id and compte_credit_id and compte_debit_id == compte_credit_id:
            erreurs.append("Le compte de debit et de credit doivent etre differents.")

        if erreurs:
            for err in erreurs:
                flash(err, 'danger')
        else:
            try:
                date_ecriture = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash("Format de date invalide. Utilisez AAAA-MM-JJ.", 'danger')
                return redirect(url_for('comptabilite_ecriture_nouvelle'))

            ecriture = EcritureComptable(
                ecole_id=ecole_id,
                date_ecriture=date_ecriture,
                libelle=libelle,
                reference=reference or None,
                montant=montant,
                compte_debit_id=int(compte_debit_id),
                compte_credit_id=int(compte_credit_id),
                type_ecriture='manuelle',
                annee_scolaire=_annee_courante(None)
            )
            db.session.add(ecriture)
            db.session.commit()
            flash("Ecriture comptable creee avec succes.", 'success')
            return redirect(url_for('comptabilite_ecritures'))

    # GET : on prepare la liste des comptes pour les selects
    comptes = CompteComptable.query.filter_by(ecole_id=ecole_id) \
        .order_by(CompteComptable.numero).all()

    today = datetime.now().strftime('%Y-%m-%d')

    return render_template('comptabilite/ecriture_form.html',
                           comptes=comptes,
                           today=today)


# ==============================================================================
# 6. Grand livre
# ==============================================================================
@app.route('/comptabilite/grand-livre')
@login_required
def comptabilite_grand_livre():
    ecole_id = get_current_ecole_id()
    compte_id_str = request.args.get('compte_id', '').strip()

    comptes = CompteComptable.query.filter_by(ecole_id=ecole_id) \
        .order_by(CompteComptable.numero).all()

    compte_selectionne = None
    ecritures = []
    solde_progressif = 0.0

    if compte_id_str:
        try:
            cid = int(compte_id_str)
            compte_selectionne = CompteComptable.query.filter_by(
                id=cid, ecole_id=ecole_id
            ).first()

            if compte_selectionne:
                ecritures = EcritureComptable.query.filter_by(ecole_id=ecole_id) \
                    .filter(
                        db.or_(
                            EcritureComptable.compte_debit_id == compte_selectionne.id,
                            EcritureComptable.compte_credit_id == compte_selectionne.id
                        )
                    ) \
                    .order_by(EcritureComptable.date_ecriture.asc(), EcritureComptable.id.asc()) \
                    .all()

                sens = _nature_du_solde(compte_selectionne.nature)
        except ValueError:
            pass

    return render_template('comptabilite/grand_livre.html',
                           comptes=comptes,
                           compte_selectionne=compte_selectionne,
                           ecritures=ecritures,
                           format_montant=_format_montant)


# ==============================================================================
# 7. Balance des comptes
# ==============================================================================
@app.route('/comptabilite/balance')
@login_required
def comptabilite_balance():
    ecole_id = get_current_ecole_id()

    comptes = CompteComptable.query.filter_by(ecole_id=ecole_id) \
        .order_by(CompteComptable.numero).all()

    lignes = []
    totaux_par_classe = {}
    total_general_debit = 0.0
    total_general_credit = 0.0
    total_general_solde_debiteur = 0.0
    total_general_solde_crediteur = 0.0

    for compte in comptes:
        solde, total_debit, total_credit = _solde_compte(compte, ecole_id)
        sens = _nature_du_solde(compte.nature)

        if sens == 'debiteur':
            solde_debiteur = max(solde, 0)
            solde_crediteur = max(-solde, 0)
        else:
            solde_debiteur = max(-solde, 0)
            solde_crediteur = max(solde, 0)

        ligne = {
            'compte': compte,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'solde': solde,
            'sens': sens,
            'solde_debiteur': solde_debiteur,
            'solde_crediteur': solde_crediteur,
        }
        lignes.append(ligne)

        classe = _classe_from_numero(compte.numero) or 0
        if classe not in totaux_par_classe:
            totaux_par_classe[classe] = {
                'debit': 0, 'credit': 0,
                'solde_debiteur': 0, 'solde_crediteur': 0
            }
        tc = totaux_par_classe[classe]
        tc['debit'] += total_debit
        tc['credit'] += total_credit
        tc['solde_debiteur'] += solde_debiteur
        tc['solde_crediteur'] += solde_crediteur

        total_general_debit += total_debit
        total_general_credit += total_credit
        total_general_solde_debiteur += solde_debiteur
        total_general_solde_crediteur += solde_crediteur

    totaux_par_classe = dict(sorted(totaux_par_classe.items()))

    return render_template('comptabilite/balance.html',
                           lignes=lignes,
                           totaux_par_classe=totaux_par_classe,
                           total_general_debit=total_general_debit,
                           total_general_credit=total_general_credit,
                           total_general_solde_debiteur=total_general_solde_debiteur,
                           total_general_solde_crediteur=total_general_solde_crediteur,
                           format_montant=_format_montant)


# ==============================================================================
# 8. Bilan comptable
# ==============================================================================
@app.route('/comptabilite/bilan')
@login_required
def comptabilite_bilan():
    ecole_id = get_current_ecole_id()

    def _solde_classe(classe_numero):
        """Calcule le solde cumule (debit - credit) de tous les comptes d'une classe."""
        comptes_classe_list = CompteComptable.query.filter_by(ecole_id=ecole_id) \
            .filter(CompteComptable.numero.like(f'{classe_numero}%')).all()
        total = 0.0
        for c in comptes_classe_list:
            s, _, _ = _solde_compte(c, ecole_id)
            total += s
        return total

    # ACTIF : presente avec valeurs positives (debit > credit)
    actif = {}
    actif['20-29 Immobilisations'] = max(_solde_classe(2), 0)
    actif['30-39 Stocks'] = max(_solde_classe(3), 0)
    # Classe 4 : comptes de nature actif
    solde_41 = _solde_classe(41)
    solde_409 = _solde_classe(409)
    actif['40-48 Creances'] = max(solde_409, 0) + max(solde_41, 0)
    actif['50-59 Tresorerie'] = max(_solde_classe(5), 0)

    # Capitaux propres (classe 1) : solde negatif = credit > debit = benefice
    resultat_classe_1 = _solde_classe(1)

    # Si resultat_classe_1 > 0, cela signifie que le debit > credit sur la classe 1,
    # donc les pertes (139) depassent le capital → perte nette a l'actif
    if resultat_classe_1 > 0:
        actif['Resultat net (perte)'] = resultat_classe_1

    total_actif = sum(actif.values())
    actif['TOTAL ACTIF'] = total_actif

    # PASSIF : presente avec valeurs positives (credit > debit)
    passif_dict = {}

    # Capitaux propres = -solde (car solde negatif pour credit > debit)
    if resultat_classe_1 < 0:
        passif_dict['Capitaux propres'] = -resultat_classe_1
    else:
        # Perte nette, mais on peut avoir du capital residuel positif
        cp = _solde_classe(10) + _solde_classe(11) + _solde_classe(12)
        passif_dict['Capitaux propres'] = max(-cp, 0)

    # Dettes (classe 4 passif) : solde negatif = credit > debit → -solde donne positif
    passif_dict['Dettes fournisseurs (40)'] = max(-_solde_classe(40), 0)
    passif_dict['Dettes personnel (42)'] = max(-_solde_classe(42), 0)
    passif_dict['Dettes sociales (43)'] = max(-_solde_classe(43), 0)
    passif_dict['Dettes fiscales (44)'] = max(-_solde_classe(44), 0)
    passif_dict['Autres dettes (46-48)'] = max(-(_solde_classe(46) + _solde_classe(47) + _solde_classe(48)), 0)

    total_passif = sum(passif_dict.values())
    passif_dict['TOTAL PASSIF'] = total_passif

    return render_template('comptabilite/bilan.html',
                           actif=actif,
                           passif_dict=passif_dict,
                           format_montant=_format_montant)


# ==============================================================================
# 9. Compte de resultat
# ==============================================================================
@app.route('/comptabilite/resultat')
@login_required
def comptabilite_resultat():
    ecole_id = get_current_ecole_id()

    # CHARGES : classes 6 et 8 (charges)
    charges = {}
    comptes_charge = CompteComptable.query.filter_by(ecole_id=ecole_id, nature='charge', niveau=1) \
        .filter(
            db.or_(
                CompteComptable.numero.like('6%'),
                CompteComptable.numero.like('8%')
            )
        ).all()

    total_charges = 0.0
    for c in comptes_charge:
        solde, _, _ = _solde_compte(c, ecole_id)
        # Pour une charge, solde debit - credit, normalement positif
        charges[c.numero] = {
            'libelle': c.libelle,
            'solde': solde if solde > 0 else 0
        }
        total_charges += charges[c.numero]['solde']

    # PRODUITS : classes 7 et 8 (produits)
    produits = {}
    comptes_produit = CompteComptable.query.filter_by(ecole_id=ecole_id, nature='produit', niveau=1) \
        .filter(
            db.or_(
                CompteComptable.numero.like('7%'),
                CompteComptable.numero.like('8%')
            )
        ).all()

    total_produits = 0.0
    for c in comptes_produit:
        solde, _, _ = _solde_compte(c, ecole_id)
        # Pour un produit, solde debit - credit, normalement negatif
        produits[c.numero] = {
            'libelle': c.libelle,
            'solde': -solde if solde < 0 else 0  # on inverse pour afficher positif
        }
        total_produits += produits[c.numero]['solde']

    resultat = total_produits - total_charges

    return render_template('comptabilite/resultat.html',
                           charges=charges,
                           total_charges=total_charges,
                           produits=produits,
                           total_produits=total_produits,
                           resultat=resultat,
                           format_montant=_format_montant)
