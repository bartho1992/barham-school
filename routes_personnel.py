from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from models import db, Ecole, Personnel, Salaire
from app import app, get_current_ecole_id

def _annee_courante(e):
    return session.get('annee_scolaire', e.annee_scolaire if e else '2024-2025')

@app.route('/personnel')
@login_required
def personnel():
    ecole_id = get_current_ecole_id()
    return render_template('personnel/index.html', personnels=Personnel.query.all(), ecole=Ecole.query.get(ecole_id))

@app.route('/personnel/ajouter', methods=['GET','POST'])
@login_required
def personnel_ajouter():
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id)
    
    last_p = Personnel.query.order_by(Personnel.id.desc()).first()
    next_id = (last_p.id + 1) if last_p else 1
    auto_code = f"P{next_id:03d}"
    
    if request.method == 'POST':
        code = request.form.get('code') or auto_code
        db.session.add(Personnel(code=code, prenom=request.form.get('prenom'), nom=request.form.get('nom'),
            fonction=request.form.get('fonction'), tel=request.form.get('tel'),
            salaire_fixe=float(request.form.get('salaire_fixe',0)), taux_impot=float(request.form.get('taux_impot',5))))
        db.session.commit(); flash('Personnel ajouté','success'); return redirect(url_for('personnel'))
    return render_template('personnel/form.html', ecole=e, auto_code=auto_code)

@app.route('/personnel/salaire/<int:id>', methods=['GET','POST'])
@login_required
def personnel_salaire(id):
    ecole_id = get_current_ecole_id()
    e = Ecole.query.get(ecole_id); p = Personnel.query.get_or_404(id); annee = _annee_courante(e)
    if request.method == 'POST':
        brut=float(request.form.get('salaire_brut',0)); impot=brut*(p.taux_impot/100)
        primes=float(request.form.get('primes',0)); net=brut-impot+primes
        db.session.add(Salaire(personnel_id=id, mois=request.form.get('mois'), salaire_brut=brut, impot=impot, primes=primes, salaire_net=net, annee_scolaire=annee))
        db.session.commit(); flash('Salaire enregistré','success'); return redirect(url_for('personnel'))
    return render_template('personnel/salaire.html', personnel=p, salaires=Salaire.query.filter_by(personnel_id=id, annee_scolaire=annee).all(), ecole=e)