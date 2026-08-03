from flask import Blueprint, request, jsonify
from models import (
    db, Ecole, Classe, Eleve, Note, Paiement, Bulletin, Assiduite,
    Scolarite, TarifService, AbonnementService, CategorieTarif, Personnel, Matiere
)
from helpers import get_current_ecole_id, get_current_annee
from datetime import datetime

api_bp = Blueprint('api_bp', __name__, url_prefix='/api/v1')


# ── Decorator: token auth ────────────────────────────────────────────
def api_token_required(f):
    """Vérifie le token API dans le header X-API-Token.
    Token attendu = ecole.identifiant (ou 'admin' pour le super admin)."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token', '')
        if not token:
            return jsonify({'error': 'Token API requis (header X-API-Token)'}), 401

        # Vérifier si token == identifiant d'une école
        ecole = Ecole.query.filter_by(identifiant=token).first()
        if not ecole:
            # Fallback : token 'admin' pour un accès dev
            dev = Ecole.query.first()
            if token == 'admin' and dev:
                pass  # autorisé
            else:
                return jsonify({'error': 'Token API invalide'}), 403

        return f(*args, **kwargs)

    return decorated


def _get_ecole_from_token():
    """Détermine l'ecole_id à partir du token API."""
    token = request.headers.get('X-API-Token', '')
    ecole = Ecole.query.filter_by(identifiant=token).first()
    if ecole:
        return ecole.id
    # fallback
    return get_current_ecole_id()


# ── GET /api/v1/ecole/infos ──────────────────────────────────────────
@api_bp.route('/ecole/infos')
@api_token_required
def ecole_infos():
    ecole_id = _get_ecole_from_token()
    ecole = Ecole.query.get(ecole_id)
    if not ecole:
        return jsonify({'error': 'École introuvable'}), 404

    annee = get_current_annee()
    nb_eleves = Eleve.query.filter_by(ecole_id=ecole_id).count()
    nb_classes = Classe.query.filter_by(ecole_id=ecole_id).count()
    nb_personnel = Personnel.query.filter_by(ecole_id=ecole_id).count()

    return jsonify({
        'id': ecole.id,
        'nom': ecole.nom,
        'identifiant': ecole.identifiant,
        'adresse': ecole.adresse,
        'tel': ecole.tel,
        'email': ecole.email,
        'zone': ecole.zone,
        'type_ecole': ecole.type_ecole,
        'directeur': ecole.directeur,
        'slogan': ecole.slogan,
        'autorisation': ecole.autorisation,
        'code_etablissement': ecole.code_etablissement,
        'ia': ecole.ia,
        'ief': ecole.ief,
        'annee_scolaire': ecole.annee_scolaire or annee,
        'annee_active': annee,
        'stats': {
            'nb_eleves': nb_eleves,
            'nb_classes': nb_classes,
            'nb_personnel': nb_personnel
        }
    })


# ── GET /api/v1/classes ──────────────────────────────────────────────
@api_bp.route('/classes')
@api_token_required
def api_classes():
    ecole_id = _get_ecole_from_token()
    classes = Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all()

    result = []
    for c in classes:
        effectif = Eleve.query.filter_by(ecole_id=ecole_id, classe_id=c.id).count()
        result.append({
            'id': c.id,
            'nom': c.nom,
            'niveau': c.niveau,
            'effectif': effectif,
            'ordre': c.ordre
        })

    return jsonify({'classes': result, 'total': len(result)})


# ── GET /api/v1/eleves ───────────────────────────────────────────────
@api_bp.route('/eleves')
@api_token_required
def api_eleves():
    ecole_id = _get_ecole_from_token()
    classe_id = request.args.get('classe_id', type=int)
    search = request.args.get('search', '').strip()
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Eleve.query.filter_by(ecole_id=ecole_id)

    if classe_id:
        query = query.filter_by(classe_id=classe_id)

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Eleve.nom.ilike(like),
                Eleve.prenom.ilike(like),
                Eleve.code.ilike(like)
            )
        )

    total = query.count()
    eleves = query.order_by(Eleve.nom, Eleve.prenom).offset(offset).limit(limit).all()

    result = []
    for e in eleves:
        result.append({
            'id': e.id,
            'code': e.code,
            'prenom': e.prenom,
            'nom': e.nom,
            'sexe': e.sexe,
            'classe_id': e.classe_id,
            'classe_nom': e.classe.nom if e.classe else None,
            'tel': e.tel,
            'tuteur': e.tuteur,
            'date_naissance': e.date_naissance,
            'situation': e.situation,
            'annee_scolaire': e.annee_scolaire,
            'photo': e.photo
        })

    return jsonify({
        'eleves': result,
        'total': total,
        'limit': limit,
        'offset': offset
    })


# ── GET /api/v1/eleves/<id> ──────────────────────────────────────────
@api_bp.route('/eleves/<int:id>')
@api_token_required
def api_eleve_detail(id):
    ecole_id = _get_ecole_from_token()
    e = Eleve.query.filter_by(id=id, ecole_id=ecole_id).first()
    if not e:
        return jsonify({'error': 'Élève introuvable'}), 404

    annee = get_current_annee()

    # Notes par trimestre
    notes_par_trimestre = {}
    for trim in [1, 2, 3]:
        notes_trim = Note.query.filter_by(
            eleve_id=e.id, trimestre=trim, annee_scolaire=annee
        ).all()
        notes_par_trimestre[str(trim)] = [{
            'matiere_id': n.matiere_id,
            'controle': n.controle,
            'composition': n.composition,
            'moyenne': n.moyenne,
            'rang': n.rang,
            'appreciation': n.appreciation
        } for n in notes_trim]

    # Paiements
    paiements = []
    total_paye = 0.0
    for p in e.paiements.filter_by(ecole_id=ecole_id).order_by(Paiement.date_paiement.desc()).all():
        paiements.append({
            'id': p.id,
            'type_paiement': p.type_paiement,
            'montant': p.montant,
            'mode_paiement': p.mode_paiement,
            'date_paiement': p.date_paiement.isoformat() if p.date_paiement else None,
            'caissier': p.caissier,
            'annee_scolaire': p.annee_scolaire
        })
        total_paye += p.montant or 0

    # Absences
    absences = []
    nb_absences = 0
    for a in Assiduite.query.filter_by(eleve_id=e.id, ecole_id=ecole_id).order_by(Assiduite.date_evenement.desc()).limit(100).all():
        absences.append({
            'date': a.date_evenement,
            'type': a.type_evenement,
            'motif': a.motif,
            'justifie': a.justifie
        })
        if a.type_evenement == 'Absent':
            nb_absences += 1

    # Bulletins
    bulletins = []
    for b in Bulletin.query.filter_by(eleve_id=e.id).order_by(Bulletin.trimestre).all():
        bulletins.append({
            'trimestre': b.trimestre,
            'moyenne_generale': b.moyenne_generale,
            'rang': b.rang,
            'moyenne_classe': b.moyenne_classe,
            'decision': b.decision,
            'absences': b.absences
        })

    return jsonify({
        'id': e.id,
        'code': e.code,
        'prenom': e.prenom,
        'nom': e.nom,
        'sexe': e.sexe,
        'date_naissance': e.date_naissance,
        'lieu_naissance': e.lieu_naissance,
        'tuteur': e.tuteur,
        'adresse': e.adresse,
        'tel': e.tel,
        'classe_id': e.classe_id,
        'classe_nom': e.classe.nom if e.classe else None,
        'situation': e.situation,
        'annee_scolaire': e.annee_scolaire,
        'photo': e.photo,
        'notes': notes_par_trimestre,
        'paiements': paiements,
        'total_paye': total_paye,
        'absences': absences,
        'nb_absences': nb_absences,
        'bulletins': bulletins
    })


# ── GET /api/v1/notes/<eleve_id>/<trimestre> ─────────────────────────
@api_bp.route('/notes/<int:eleve_id>/<int:trimestre>')
@api_token_required
def api_notes(eleve_id, trimestre):
    ecole_id = _get_ecole_from_token()
    annee = get_current_annee()

    eleve = Eleve.query.filter_by(id=eleve_id, ecole_id=ecole_id).first()
    if not eleve:
        return jsonify({'error': 'Élève introuvable'}), 404

    notes = Note.query.filter_by(
        eleve_id=eleve_id, trimestre=trimestre, annee_scolaire=annee
    ).all()

    # Récupérer les matières correspondantes (Note n'a pas de relationship explicite)
    matiere_ids = list(set(n.matiere_id for n in notes if n.matiere_id))
    matieres_map = {}
    if matiere_ids:
        matieres = Matiere.query.filter(Matiere.id.in_(matiere_ids)).all()
        matieres_map = {m.id: m for m in matieres}

    result = []
    for n in notes:
        matiere = matieres_map.get(n.matiere_id)
        result.append({
            'matiere_id': n.matiere_id,
            'matiere_nom': matiere.nom if matiere else None,
            'domaine': matiere.domaine if matiere else None,
            'coefficient': matiere.coefficient if matiere else 1,
            'controle': n.controle,
            'composition': n.composition,
            'moyenne': n.moyenne,
            'rang': n.rang,
            'appreciation': n.appreciation
        })

    # Moyenne générale du trimestre
    bulletin = Bulletin.query.filter_by(
        eleve_id=eleve_id, trimestre=trimestre
    ).first()

    return jsonify({
        'eleve_id': eleve_id,
        'eleve_nom': f'{eleve.prenom} {eleve.nom}',
        'trimestre': trimestre,
        'annee_scolaire': annee,
        'notes': result,
        'moyenne_generale': bulletin.moyenne_generale if bulletin else None,
        'rang': bulletin.rang if bulletin else None,
        'decision': bulletin.decision if bulletin else None
    })


# ── GET /api/v1/finances/solde/<eleve_id> ────────────────────────────
@api_bp.route('/finances/solde/<int:eleve_id>')
@api_token_required
def api_solde(eleve_id):
    ecole_id = _get_ecole_from_token()
    annee = get_current_annee()

    eleve = Eleve.query.filter_by(id=eleve_id, ecole_id=ecole_id).first()
    if not eleve:
        return jsonify({'error': 'Élève introuvable'}), 404

    # Scolarité de base par classe
    scolarite = Scolarite.query.filter_by(
        classe_id=eleve.classe_id, ecole_id=ecole_id, annee_scolaire=annee
    ).first()
    total_scolarite = scolarite.total_annuel if scolarite else 0

    # Services (abonnements)
    abonnements = AbonnementService.query.filter_by(
        eleve_id=eleve.id, actif=True
    ).all()
    total_services = 0
    abonnements_detail = []
    for ab in abonnements:
        tarif = TarifService.query.filter_by(
            classe_id=eleve.classe_id, categorie_id=ab.categorie_id,
            ecole_id=ecole_id, annee_scolaire=annee
        ).first()
        montant = ab.montant_personnalise if ab.montant_personnalise is not None else (tarif.total_annuel if tarif else 0)
        total_services += montant
        abonnements_detail.append({
            'categorie_id': ab.categorie_id,
            'categorie_nom': ab.categorie.nom if ab.categorie else None,
            'montant': montant,
            'mois_debut': ab.mois_debut,
            'mois_fin': ab.mois_fin
        })

    montant_attendu = total_scolarite + total_services

    # Total payé
    total_paye = db.session.query(db.func.sum(Paiement.montant)).filter(
        Paiement.eleve_id == eleve.id,
        Paiement.ecole_id == ecole_id,
        Paiement.annee_scolaire == annee
    ).scalar() or 0.0

    solde = total_paye - montant_attendu

    return jsonify({
        'eleve_id': eleve.id,
        'eleve_nom': f'{eleve.prenom} {eleve.nom}',
        'annee_scolaire': annee,
        'scolarite_base': total_scolarite,
        'services': total_services,
        'montant_attendu': montant_attendu,
        'total_paye': total_paye,
        'solde': solde,
        'statut': 'À jour' if solde >= 0 else 'Impayé',
        'abonnements': abonnements_detail
    })


# ── GET /api/v1/stats ────────────────────────────────────────────────
@api_bp.route('/stats')
@api_token_required
def api_stats():
    ecole_id = _get_ecole_from_token()
    annee = get_current_annee()

    nb_eleves = Eleve.query.filter_by(ecole_id=ecole_id).count()
    nb_classes = Classe.query.filter_by(ecole_id=ecole_id).count()
    nb_personnel = Personnel.query.filter_by(ecole_id=ecole_id).count()

    nb_garcons = Eleve.query.filter_by(ecole_id=ecole_id, sexe='M').count()
    nb_filles = Eleve.query.filter_by(ecole_id=ecole_id, sexe='F').count()

    total_paiements = db.session.query(db.func.sum(Paiement.montant)).filter(
        Paiement.ecole_id == ecole_id,
        Paiement.annee_scolaire == annee
    ).scalar() or 0.0

    nb_paiements = Paiement.query.filter_by(
        ecole_id=ecole_id, annee_scolaire=annee
    ).count()

    nb_notes = Note.query.filter_by(
        annee_scolaire=annee
    ).filter(Note.eleve_id.in_(
        db.session.query(Eleve.id).filter_by(ecole_id=ecole_id)
    )).count()

    nb_absences = Assiduite.query.filter_by(
        ecole_id=ecole_id, annee_scolaire=annee, type_evenement='Absent'
    ).count()

    # Répartition par niveau
    niveaux = db.session.query(
        Classe.niveau, db.func.count(Eleve.id)
    ).join(Eleve, Eleve.classe_id == Classe.id).filter(
        Eleve.ecole_id == ecole_id
    ).group_by(Classe.niveau).all()

    repartition_niveaux = {n or 'Non défini': c for n, c in niveaux}

    return jsonify({
        'annee_scolaire': annee,
        'nb_eleves': nb_eleves,
        'nb_classes': nb_classes,
        'nb_personnel': nb_personnel,
        'nb_garcons': nb_garcons,
        'nb_filles': nb_filles,
        'total_paiements': total_paiements,
        'nb_paiements': nb_paiements,
        'nb_notes': nb_notes,
        'nb_absences': nb_absences,
        'repartition_niveaux': repartition_niveaux
    })
