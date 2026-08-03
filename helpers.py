from flask import session
from models import Ecole

def get_current_ecole_id():
    if 'ecole_id' in session:
        return session['ecole_id']
    ecole = Ecole.query.first()
    if ecole:
        session['ecole_id'] = ecole.id
        return ecole.id
    return 1

def get_current_annee():
    ecole_id = get_current_ecole_id()
    ecole = Ecole.query.get(ecole_id)
    if ecole and ecole.annee_scolaire and str(ecole.annee_scolaire).strip():
        return str(ecole.annee_scolaire).strip()
    annee_session = session.get('annee_scolaire')
    if annee_session:
        return str(annee_session)
    from models import AnneeScolaire
    active = AnneeScolaire.query.filter_by(ecole_id=ecole_id, active=True).first()
    if active:
        return str(active.annee)
    derniere = AnneeScolaire.query.filter_by(ecole_id=ecole_id).order_by(AnneeScolaire.id.desc()).first()
    if derniere:
        return str(derniere.annee)
    return '2024-2025'
