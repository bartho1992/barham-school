from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
from models import db, Ecole, Eleve, Classe, Document
from app import app, get_current_ecole_id
from datetime import datetime


@app.route('/api/rechercher_eleves')
@login_required
def api_rechercher_eleves():
    """Recherche d'eleves par nom, prenom ou code (pour la page Documents)."""
    ecole_id = get_current_ecole_id()
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    like = f'%{q}%'
    eleves = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        db.or_(
            Eleve.nom.ilike(like),
            Eleve.prenom.ilike(like),
            Eleve.code.ilike(like)
        )
    ).order_by(Eleve.nom, Eleve.prenom).limit(15).all()
    return jsonify([
        {
            'id': e.id,
            'code': e.code,
            'nom': e.nom,
            'prenom': e.prenom,
            'classe': e.classe.nom if e.classe else '-'
        }
        for e in eleves
    ])


@app.route('/documents/billet_entree/<int:eleve_id>')
@login_required
def billet_entree(eleve_id):
    """Genere un billet d'entree imprimable pour un eleve."""
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    eleve = Eleve.query.filter_by(id=eleve_id, ecole_id=ecole_id).first_or_404()
    motif = request.args.get('motif', '')
    return render_template('documents/billet_entree.html',
                           ecole=ecole, eleve=eleve, motif=motif,
                           maintenant=datetime.now())
