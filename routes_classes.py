from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Ecole, Classe, Matiere
from app import app, get_current_ecole_id

@app.route('/classes')
@login_required
def classes():
    ecole_id = get_current_ecole_id()
    embed = request.args.get('embed')
    return render_template('classes/index.html', classes=Classe.query.filter_by(ecole_id=ecole_id).order_by(Classe.ordre, Classe.nom).all(), ecole=Ecole.query.get(ecole_id), embed=embed)

@app.route('/classes/ajouter', methods=['GET','POST'])
@login_required
def classe_ajouter():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    embed = request.args.get('embed')
    if request.method == 'POST':
        mode = request.form.get('mode', 'simple')
        niveau = request.form.get('niveau', '')
        type_classe = request.form.get('type_classe', 'secondaire')
        if mode == 'multiple':
            noms_texte = request.form.get('noms', '').strip()
            if not noms_texte:
                flash('Veuillez saisir au moins un nom de classe', 'warning')
                return redirect(url_for('classe_ajouter', embed=embed))
            noms = [n.strip() for n in noms_texte.replace('\r', '\n').replace(',', '\n').split('\n') if n.strip()]
            if not noms:
                flash('Aucun nom valide saisi', 'warning')
                return redirect(url_for('classe_ajouter', embed=embed))
            ajoutes = 0
            ignores = []
            for nom in noms:
                if Classe.query.filter_by(nom=nom, ecole_id=ecole_id).first():
                    ignores.append(nom)
                    continue
                db.session.add(Classe(nom=nom, niveau=niveau, type_classe=type_classe, ecole_id=ecole_id))
                ajoutes += 1
            db.session.commit()
            if ajoutes > 0:
                flash(f'{ajoutes} classe(s) ajoutee(s) avec succes', 'success')
            if ignores:
                flash(f'{len(ignores)} deja existante(s) : {", ".join(ignores)}', 'info')
            return redirect(url_for('classes', embed=embed))
        else:
            db.session.add(Classe(nom=request.form.get('nom'), niveau=niveau, type_classe=type_classe, ecole_id=ecole_id))
            db.session.commit(); flash('Classe ajoutee','success'); return redirect(url_for('classes', embed=embed))
    return render_template('classes/form.html', ecole=e, embed=embed)

@app.route('/classes/modifier/<int:id>', methods=['GET','POST'])
@login_required
def classe_modifier(id):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); c = Classe.query.get_or_404(id)
    embed = request.args.get('embed')
    if c.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('classes', embed=embed))
    if request.method == 'POST':
        c.nom=request.form.get('nom'); c.niveau=request.form.get('niveau'); c.type_classe=request.form.get('type_classe', 'secondaire')
        db.session.commit(); flash('Classe modifiée','success'); return redirect(url_for('classes', embed=embed))
    return render_template('classes/form.html', classe=c, ecole=e, embed=embed)

@app.route('/classes/supprimer/<int:id>', methods=['POST'])
@login_required
def classe_supprimer(id):
    ecole_id = get_current_ecole_id()
    c = Classe.query.get_or_404(id)
    if c.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('classes', embed=request.args.get('embed')))
    from models import Eleve, Note, Scolarite, TarifService
    Eleve.query.filter_by(classe_id=id).update({'classe_id': None})
    Note.query.filter_by(classe_id=id).delete()
    Scolarite.query.filter_by(classe_id=id).delete()
    TarifService.query.filter_by(classe_id=id).delete()
    db.session.delete(c); db.session.commit(); flash('Supprimée','success'); return redirect(url_for('classes', embed=request.args.get('embed')))

@app.route('/classes/supprimer-bulk', methods=['POST'])
@login_required
def classes_supprimer_bulk():
    if current_user.role not in ('dev', 'super_users'): flash('Accès réservé','danger'); return redirect(url_for('dashboard'))
    ecole_id = get_current_ecole_id()
    ids = request.form.getlist('classe_ids[]')
    if not ids:
        flash('Aucune classe sélectionnée', 'warning')
        return redirect(url_for('classes', embed=request.args.get('embed')))
    ids_int = [int(i) for i in ids]
    from models import Eleve, Note, Scolarite, TarifService
    Eleve.query.filter(Eleve.classe_id.in_(ids_int)).update({'classe_id': None}, synchronize_session=False)
    Note.query.filter(Note.classe_id.in_(ids_int)).delete(synchronize_session=False)
    Scolarite.query.filter(Scolarite.classe_id.in_(ids_int)).delete(synchronize_session=False)
    TarifService.query.filter(TarifService.classe_id.in_(ids_int)).delete(synchronize_session=False)
    count = Classe.query.filter(Classe.id.in_(ids_int), Classe.ecole_id == ecole_id).delete(synchronize_session=False)
    db.session.commit()
    flash(f'{count} classe(s) supprimée(s) avec succès', 'success')
    return redirect(url_for('classes', embed=request.args.get('embed')))

@app.route('/classes/reorder', methods=['POST'])
@login_required
def classes_reorder():
    """Réordonner les classes par drag & drop"""
    ecole_id = get_current_ecole_id()
    ids = request.json.get('ids', [])
    if not ids:
        return jsonify({'ok': False, 'error': 'Aucun ID'}), 400
    for idx, cid in enumerate(ids):
        Classe.query.filter_by(id=cid, ecole_id=ecole_id).update({'ordre': idx})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/matieres')
@login_required
def matieres():
    ecole_id = get_current_ecole_id()
    embed = request.args.get('embed')
    if not embed:
        return redirect(url_for('administration'))
    return render_template('classes/matieres.html', matieres=Matiere.query.filter_by(ecole_id=ecole_id).all(), ecole=Ecole.query.get(ecole_id), embed=embed)

@app.route('/matieres/ajouter', methods=['GET','POST'])
@login_required
def matiere_ajouter():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    embed = request.args.get('embed')
    if request.method == 'POST':
        db.session.add(Matiere(nom=request.form.get('nom'), domaine=request.form.get('domaine'), coefficient=request.form.get('coefficient',1), ecole_id=ecole_id))
        db.session.commit(); flash('Matière ajoutée','success'); return redirect(url_for('matieres', embed=embed))
    return render_template('classes/matiere_form.html', ecole=e, embed=embed)

@app.route('/matieres/modifier/<int:id>', methods=['GET','POST'])
@login_required
def matiere_modifier(id):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    m = Matiere.query.get_or_404(id)
    embed = request.args.get('embed')
    if m.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('matieres', embed=embed))
    if request.method == 'POST':
        m.nom = request.form.get('nom')
        m.domaine = request.form.get('domaine')
        m.coefficient = request.form.get('coefficient', 1)
        db.session.commit(); flash('Matière modifiée','success'); return redirect(url_for('matieres', embed=embed))
    return render_template('classes/matiere_form.html', matiere=m, ecole=e, embed=embed)

@app.route('/matieres/supprimer/<int:id>', methods=['POST'])
@login_required
def matiere_supprimer(id):
    ecole_id = get_current_ecole_id()
    m = Matiere.query.get_or_404(id)
    if m.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('matieres', embed=request.args.get('embed')))
    from models import Note
    Note.query.filter_by(matiere_id=id).delete()
    db.session.delete(m); db.session.commit(); flash('Matière supprimée','success')
    return redirect(url_for('matieres', embed=request.args.get('embed')))

@app.route('/matieres/supprimer-bulk', methods=['POST'])
@login_required
def matiere_supprimer_bulk():
    if current_user.role not in ('dev', 'super_users'): flash('Accès réservé','danger'); return redirect(url_for('dashboard'))
    ecole_id = get_current_ecole_id()
    ids = request.form.getlist('matiere_ids[]')
    if not ids:
        flash('Aucune matière sélectionnée', 'warning')
        return redirect(url_for('matieres', embed=request.args.get('embed')))
    ids_int = [int(i) for i in ids]
    from models import Note
    Note.query.filter(Note.matiere_id.in_(ids_int)).delete(synchronize_session=False)
    count = Matiere.query.filter(Matiere.id.in_(ids_int), Matiere.ecole_id == ecole_id).delete(synchronize_session=False)
    db.session.commit()
    flash(f'{count} matière(s) supprimée(s)', 'success')
    return redirect(url_for('matieres', embed=request.args.get('embed')))
