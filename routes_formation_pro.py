from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Ecole, Eleve, FilierePro, ModulePro, SessionFormation, InscriptionSession, EvaluationModulePro
from app import get_current_ecole_id
from datetime import datetime

fpro_bp = Blueprint('fpro_bp', __name__)

# ─── Helpers ───────────────────────────────────────────────

def _ecole_id():
    return get_current_ecole_id()

def _ecole():
    return Ecole.query.get(_ecole_id())

# ─── Hub Formation Pro ────────────────────────────────────

@fpro_bp.route('/formation-pro')
@login_required
def hub():
    ecole_id = _ecole_id()
    filieres = FilierePro.query.filter_by(ecole_id=ecole_id).order_by(FilierePro.nom).all()
    sessions_actives = SessionFormation.query.filter_by(ecole_id=ecole_id).filter(
        SessionFormation.statut.in_(['ouverte', 'en_cours'])
    ).order_by(SessionFormation.date_debut.desc()).all()
    return render_template('formation_pro/hub.html',
                         ecole=_ecole(), filieres=filieres,
                         sessions_actives=sessions_actives)

# ─── Filières ─────────────────────────────────────────────

@fpro_bp.route('/formation-pro/filieres')
@login_required
def filieres():
    ecole_id = _ecole_id()
    filieres = FilierePro.query.filter_by(ecole_id=ecole_id).order_by(FilierePro.nom).all()
    return render_template('formation_pro/filieres.html',
                         ecole=_ecole(), filieres=filieres,
                         embed=request.args.get('embed'))

@fpro_bp.route('/formation-pro/filiere/ajouter', methods=['POST'])
@login_required
def filiere_ajouter():
    ecole_id = _ecole_id()
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom de la filière est requis', 'danger')
        return redirect(url_for('fpro_bp.hub'))
    f = FilierePro(
        nom=nom,
        description=request.form.get('description', '').strip(),
        duree_mois=int(request.form.get('duree_mois', 6)),
        ecole_id=ecole_id
    )
    db.session.add(f)
    db.session.commit()
    flash('Filière ajoutée avec succès', 'success')
    return redirect(url_for('fpro_bp.hub'))

@fpro_bp.route('/formation-pro/filiere/<int:id>/modifier', methods=['POST'])
@login_required
def filiere_modifier(id):
    ecole_id = _ecole_id()
    f = FilierePro.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    f.nom = request.form.get('nom', f.nom).strip()
    f.description = request.form.get('description', f.description).strip()
    f.duree_mois = int(request.form.get('duree_mois', f.duree_mois))
    f.actif = request.form.get('actif') == '1'
    db.session.commit()
    flash('Filière modifiée', 'success')
    return redirect(url_for('fpro_bp.hub'))

@fpro_bp.route('/formation-pro/filiere/<int:id>/supprimer', methods=['POST'])
@login_required
def filiere_supprimer(id):
    ecole_id = _ecole_id()
    f = FilierePro.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    if f.modules.count() > 0 or f.sessions.count() > 0:
        flash('Supprimez d\'abord les modules et sessions de cette filière', 'danger')
        return redirect(url_for('fpro_bp.hub'))
    db.session.delete(f)
    db.session.commit()
    flash('Filière supprimée', 'success')
    return redirect(url_for('fpro_bp.hub'))

# ─── Modules ──────────────────────────────────────────────

@fpro_bp.route('/formation-pro/filiere/<int:filiere_id>/modules')
@login_required
def modules(filiere_id):
    ecole_id = _ecole_id()
    filiere = FilierePro.query.filter_by(id=filiere_id, ecole_id=ecole_id).first_or_404()
    modules = filiere.modules.all()
    return render_template('formation_pro/modules.html',
                         ecole=_ecole(), filiere=filiere, modules=modules,
                         embed=request.args.get('embed'))

@fpro_bp.route('/formation-pro/module/ajouter', methods=['POST'])
@login_required
def module_ajouter():
    ecole_id = _ecole_id()
    filiere_id = request.form.get('filiere_id', type=int)
    filiere = FilierePro.query.filter_by(id=filiere_id, ecole_id=ecole_id).first_or_404()
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom du module est requis', 'danger')
        return redirect(url_for('fpro_bp.modules', filiere_id=filiere_id))
    m = ModulePro(
        filiere_id=filiere_id,
        nom=nom,
        duree_heures=int(request.form.get('duree_heures', 30)),
        coefficient=float(request.form.get('coefficient', 1)),
        ordre=int(request.form.get('ordre', filiere.modules.count() + 1)),
        description=request.form.get('description', '').strip(),
        ecole_id=ecole_id
    )
    db.session.add(m)
    db.session.commit()
    flash('Module ajouté', 'success')
    return redirect(url_for('fpro_bp.modules', filiere_id=filiere_id))

@fpro_bp.route('/formation-pro/module/<int:id>/modifier', methods=['POST'])
@login_required
def module_modifier(id):
    ecole_id = _ecole_id()
    m = ModulePro.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    m.nom = request.form.get('nom', m.nom).strip()
    m.duree_heures = int(request.form.get('duree_heures', m.duree_heures))
    m.coefficient = float(request.form.get('coefficient', m.coefficient))
    m.ordre = int(request.form.get('ordre', m.ordre))
    m.description = request.form.get('description', m.description).strip()
    db.session.commit()
    flash('Module modifié', 'success')
    return redirect(url_for('fpro_bp.modules', filiere_id=m.filiere_id))

@fpro_bp.route('/formation-pro/module/<int:id>/supprimer', methods=['POST'])
@login_required
def module_supprimer(id):
    ecole_id = _ecole_id()
    m = ModulePro.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    fid = m.filiere_id
    db.session.delete(m)
    db.session.commit()
    flash('Module supprimé', 'success')
    return redirect(url_for('fpro_bp.modules', filiere_id=fid))

# ─── Sessions ─────────────────────────────────────────────

@fpro_bp.route('/formation-pro/filiere/<int:filiere_id>/sessions')
@login_required
def sessions(filiere_id):
    ecole_id = _ecole_id()
    filiere = FilierePro.query.filter_by(id=filiere_id, ecole_id=ecole_id).first_or_404()
    sessions = filiere.sessions.all()
    return render_template('formation_pro/sessions.html',
                         ecole=_ecole(), filiere=filiere, sessions=sessions,
                         embed=request.args.get('embed'))

@fpro_bp.route('/formation-pro/session/ajouter', methods=['POST'])
@login_required
def session_ajouter():
    ecole_id = _ecole_id()
    filiere_id = request.form.get('filiere_id', type=int)
    filiere = FilierePro.query.filter_by(id=filiere_id, ecole_id=ecole_id).first_or_404()
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom de la session est requis', 'danger')
        return redirect(url_for('fpro_bp.sessions', filiere_id=filiere_id))
    s = SessionFormation(
        filiere_id=filiere_id,
        nom=nom,
        date_debut=request.form.get('date_debut', ''),
        date_fin=request.form.get('date_fin', ''),
        ecole_id=ecole_id
    )
    db.session.add(s)
    db.session.commit()
    flash('Session créée', 'success')
    return redirect(url_for('fpro_bp.sessions', filiere_id=filiere_id))

@fpro_bp.route('/formation-pro/session/<int:id>/modifier', methods=['POST'])
@login_required
def session_modifier(id):
    ecole_id = _ecole_id()
    s = SessionFormation.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    s.nom = request.form.get('nom', s.nom).strip()
    s.date_debut = request.form.get('date_debut', s.date_debut)
    s.date_fin = request.form.get('date_fin', s.date_fin)
    s.statut = request.form.get('statut', s.statut)
    db.session.commit()
    flash('Session modifiée', 'success')
    return redirect(url_for('fpro_bp.sessions', filiere_id=s.filiere_id))

@fpro_bp.route('/formation-pro/session/<int:id>/supprimer', methods=['POST'])
@login_required
def session_supprimer(id):
    ecole_id = _ecole_id()
    s = SessionFormation.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    fid = s.filiere_id
    db.session.delete(s)
    db.session.commit()
    flash('Session supprimée', 'success')
    return redirect(url_for('fpro_bp.sessions', filiere_id=fid))

# ─── Inscriptions ─────────────────────────────────────────

@fpro_bp.route('/formation-pro/session/<int:session_id>/inscriptions')
@login_required
def inscriptions(session_id):
    ecole_id = _ecole_id()
    session = SessionFormation.query.filter_by(id=session_id, ecole_id=ecole_id).first_or_404()
    inscrits = InscriptionSession.query.filter_by(session_id=session_id, ecole_id=ecole_id).order_by(
        InscriptionSession.date_inscription.desc()
    ).all()
    # Eleves non inscrits a cette session
    eleves_libres = Eleve.query.filter_by(ecole_id=ecole_id).filter(
        ~Eleve.id.in_([i.eleve_id for i in inscrits])
    ).order_by(Eleve.nom, Eleve.prenom).all()
    return render_template('formation_pro/inscriptions.html',
                         ecole=_ecole(), session=session, inscrits=inscrits,
                         eleves_libres=eleves_libres,
                         embed=request.args.get('embed'))

@fpro_bp.route('/formation-pro/inscription/ajouter', methods=['POST'])
@login_required
def inscription_ajouter():
    ecole_id = _ecole_id()
    eleve_id = request.form.get('eleve_id', type=int)
    session_id = request.form.get('session_id', type=int)
    session = SessionFormation.query.filter_by(id=session_id, ecole_id=ecole_id).first_or_404()
    eleve = Eleve.query.filter_by(id=eleve_id, ecole_id=ecole_id).first_or_404()
    
    existante = InscriptionSession.query.filter_by(
        eleve_id=eleve_id, session_id=session_id, ecole_id=ecole_id
    ).first()
    if existante:
        flash('Cet élève est déjà inscrit à cette session', 'warning')
        return redirect(url_for('fpro_bp.inscriptions', session_id=session_id))
    
    ins = InscriptionSession(
        eleve_id=eleve_id, session_id=session_id, ecole_id=ecole_id
    )
    db.session.add(ins)
    db.session.commit()
    flash(f'{eleve.prenom} {eleve.nom} inscrit(e) à la session', 'success')
    return redirect(url_for('fpro_bp.inscriptions', session_id=session_id))

@fpro_bp.route('/formation-pro/inscription/<int:id>/statut', methods=['POST'])
@login_required
def inscription_statut(id):
    ecole_id = _ecole_id()
    ins = InscriptionSession.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    ins.statut = request.form.get('statut', ins.statut)
    db.session.commit()
    flash('Statut mis à jour', 'success')
    return redirect(url_for('fpro_bp.inscriptions', session_id=ins.session_id))

@fpro_bp.route('/formation-pro/inscription/<int:id>/supprimer', methods=['POST'])
@login_required
def inscription_supprimer(id):
    ecole_id = _ecole_id()
    ins = InscriptionSession.query.filter_by(id=id, ecole_id=ecole_id).first_or_404()
    sid = ins.session_id
    # Supprimer les evaluations liees
    EvaluationModulePro.query.filter_by(inscription_id=id, ecole_id=ecole_id).delete()
    db.session.delete(ins)
    db.session.commit()
    flash('Inscription retirée', 'success')
    return redirect(url_for('fpro_bp.inscriptions', session_id=sid))

# ─── Évaluations ──────────────────────────────────────────

@fpro_bp.route('/formation-pro/inscription/<int:inscription_id>/evaluations')
@login_required
def evaluations(inscription_id):
    ecole_id = _ecole_id()
    ins = InscriptionSession.query.filter_by(id=inscription_id, ecole_id=ecole_id).first_or_404()
    session = ins.session
    filiere = session.filiere
    modules = filiere.modules.all()
    
    evals = EvaluationModulePro.query.filter_by(
        inscription_id=inscription_id, ecole_id=ecole_id
    ).all()
    evals_map = {(e.module_id, e.type_eval): e for e in evals}
    
    return render_template('formation_pro/evaluations.html',
                         ecole=_ecole(), inscription=ins,
                         session=session, filiere=filiere,
                         modules=modules, evals_map=evals_map,
                         embed=request.args.get('embed'))

@fpro_bp.route('/formation-pro/evaluation/sauvegarder', methods=['POST'])
@login_required
def evaluation_sauvegarder():
    ecole_id = _ecole_id()
    inscription_id = request.form.get('inscription_id', type=int)
    ins = InscriptionSession.query.filter_by(id=inscription_id, ecole_id=ecole_id).first_or_404()
    
    for key, val in request.form.items():
        if key.startswith('note_'):
            parts = key.split('_')
            if len(parts) >= 3:
                module_id = int(parts[1])
                type_eval = '_'.join(parts[2:])  # Controle, Examen, Rattrapage
                note = float(val) if val else 0
                
                existing = EvaluationModulePro.query.filter_by(
                    inscription_id=inscription_id, module_id=module_id,
                    type_eval=type_eval, ecole_id=ecole_id
                ).first()
                if existing:
                    existing.note = note
                else:
                    db.session.add(EvaluationModulePro(
                        inscription_id=inscription_id,
                        module_id=module_id,
                        type_eval=type_eval,
                        note=note,
                        ecole_id=ecole_id
                    ))
    db.session.commit()
    flash('Notes enregistrées', 'success')
    return redirect(url_for('fpro_bp.evaluations', inscription_id=inscription_id))
