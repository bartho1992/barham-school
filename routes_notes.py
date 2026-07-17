from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from models import db, Ecole, Eleve, Classe, Matiere, Note
from app import app, get_current_ecole_id

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '')

@app.route('/notes')
@login_required
def notes():
    ecole_id = get_current_ecole_id()
    embed = request.args.get('embed')
    return render_template('notes/index.html', classes=Classe.query.filter_by(ecole_id=ecole_id).all(), ecole=Ecole.query.get(ecole_id), embed=embed)

@app.route('/notes/saisir/<int:classe_id>/<int:trimestre>', methods=['GET','POST'])
@login_required
def notes_saisir(classe_id, trimestre):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); cl = Classe.query.get_or_404(classe_id); annee = _annee_courante(e)
    embed = request.args.get('embed')
    if cl.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('notes', embed=embed))
    
    els = Eleve.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).all()
    mats = Matiere.query.filter_by(ecole_id=ecole_id).all()
    
    selected_matiere_id = request.args.get('matiere_id', type=int)
    if not selected_matiere_id and mats: selected_matiere_id = mats[0].id
    
    if request.method == 'POST':
        m_id = request.form.get('matiere_id')
        for el in els:
            ctrl = request.form.get(f'ctrl_{el.id}')
            comp = request.form.get(f'comp_{el.id}')
            if ctrl != '' or comp != '':
                v_ctrl = float(ctrl) if ctrl else None
                v_comp = float(comp) if comp else None
                v_moy = 0
                if v_ctrl is not None and v_comp is not None: v_moy = (v_ctrl + v_comp*2) / 3
                elif v_ctrl is not None: v_moy = v_ctrl
                elif v_comp is not None: v_moy = v_comp
                
                ex = Note.query.filter_by(eleve_id=el.id, matiere_id=m_id, classe_id=classe_id, trimestre=trimestre, annee_scolaire=annee).first()
                if ex:
                    ex.controle = v_ctrl; ex.composition = v_comp; ex.moyenne = v_moy
                else:
                    db.session.add(Note(eleve_id=el.id, matiere_id=m_id, classe_id=classe_id, trimestre=trimestre, controle=v_ctrl, composition=v_comp, moyenne=v_moy, annee_scolaire=annee))
        db.session.commit(); flash('Notes enregistrées','success')
        return redirect(url_for('notes_saisir', classe_id=classe_id, trimestre=trimestre, matiere_id=m_id, embed=embed))

    nd = {}
    if selected_matiere_id:
        nd = {n.eleve_id: n for n in Note.query.filter_by(classe_id=classe_id, trimestre=trimestre, matiere_id=selected_matiere_id, annee_scolaire=annee).all()}
    return render_template('notes/saisir.html', classe=cl, eleves=els, matieres=mats, trimestre=trimestre, notes_dict=nd, ecole=e, selected_matiere_id=selected_matiere_id, embed=embed)

@app.route('/bulletins')
@login_required
def bulletins():
    ecole_id = get_current_ecole_id()
    embed = request.args.get('embed')
    return render_template('notes/bulletins.html', classes=Classe.query.filter_by(ecole_id=ecole_id).all(), ecole=Ecole.query.get(ecole_id), embed=embed)

@app.route('/bulletins/classe/<int:classe_id>/<int:trimestre>')
@login_required
def bulletin_classe(classe_id, trimestre):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); cl = Classe.query.get_or_404(classe_id); annee = _annee_courante(e)
    if cl.ecole_id != ecole_id: flash('Accès non autorisé','danger'); return redirect(url_for('bulletins'))
    
    els = Eleve.query.filter_by(classe_id=classe_id, annee_scolaire=annee, ecole_id=ecole_id).all(); data = []
    for el in els:
        notes = Note.query.filter_by(eleve_id=el.id, classe_id=classe_id, trimestre=trimestre, annee_scolaire=annee).all()
        tp, tc = 0, 0
        for n in notes:
            if n.moyenne:
                tp += n.moyenne * (n.matiere.coefficient if n.matiere else 1)
                tc += (n.matiere.coefficient if n.matiere else 1)
        data.append({'eleve': el, 'notes': notes, 'moyenne': round(tp/tc, 2) if tc > 0 else 0})
    data.sort(key=lambda x: x['moyenne'], reverse=True)
    for i, b in enumerate(data): b['rang'] = i + 1
    return render_template('notes/bulletin_detail.html', classe=cl, bulletins=data, trimestre=trimestre, ecole=e, embed=request.args.get('embed'))
