html_content = '''{% extends "base.html" %}

{% block title %}Paramètres Financiers - {{ ecole.nom }}{% endblock %}

{% block content %}
<style>
.tarif-input { text-align: center; font-weight: bold; }
.mois-label { background-color: #007bff; color: white; text-align: center; font-weight: bold; padding: 5px; font-size: 0.75rem; }
.import-section { border: 2px dashed #007bff; padding: 20px; border-radius: 10px; margin: 20px 0; }
</style>

<div class="container-fluid mt-4">
    <h2 class="mb-4">Paramètres Financiers</h2>

    <!-- Section Import Excel -->
    <div class="card mb-4">
        <div class="card-header bg-info text-white">
            <h5>Import Excel</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <div class="import-section">
                        <h6 class="text-primary">Importer Scolarités</h6>
                        <form action="{{ url_for('importer_excel') }}" method="POST" enctype="multipart/form-data">
                            <input type="hidden" name="type_import" value="scolarite">
                            <div class="mb-3">
                                <input type="file" name="fichier_excel" class="form-control" accept=".xlsx,.xls" required>
                                <small class="form-text text-muted">
                                    Format: Classe, Inscription, Janvier, Février, Mars, Avril, Mai, Juin, Juillet, Août, Septembre, Octobre, Novembre, Décembre
                                </small>
                            </div>
                            <button type="submit" class="btn btn-info">Importer Scolarités</button>
                        </form>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="import-section">
                        <h6 class="text-warning">Importer Services</h6>
                        <form action="{{ url_for('importer_excel') }}" method="POST" enctype="multipart/form-data">
                            <input type="hidden" name="type_import" value="services">
                            <div class="mb-3">
                                <input type="file" name="fichier_excel" class="form-control" accept=".xlsx,.xls" required>
                                <small class="form-text text-muted">
                                    Format: Classe, Catégorie, Inscription, Janvier, Février, Mars, Avril, Mai, Juin, Juillet, Août, Septembre, Octobre, Novembre, Décembre
                                </small>
                            </div>
                            <button type="submit" class="btn btn-warning">Importer Services</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <button type="button" class="btn btn-secondary" onclick="telechargerModele('scolarite')">Télécharger Modèle Scolarité</button>
                <button type="button" class="btn btn-secondary" onclick="telechargerModele('services')">Télécharger Modèle Services</button>
            </div>
        </div>
    </div>

    <!-- Section Scolarité -->
    <div class="card mb-4">
        <div class="card-header bg-success text-white">
            <h5>Scolarité</h5>
        </div>
        <div class="card-body">
            <form action="{{ url_for('scolarite_sauvegarder') }}" method="POST">
                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label fw-bold">CLASSE</label>
                        <select name="classe_id" class="form-select" required>
                            <option value="">Sélectionner...</option>
                            {% for classe in classes %}
                            <option value="{{ classe.id }}">{{ classe.nom }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">TOTAL ANNUEL</label>
                        <input type="text" id="totalScolarite" class="form-control bg-light" readonly value="0 FCFA">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">REINITIALISER</label>
                        <select name="reinitialiser" class="form-select">
                            <option value="">NON</option>
                            <option value="on">OUI</option>
                        </select>
                    </div>
                </div>

                <div class="row g-2">
                    <div class="col-md-1 col-3">
                        <div class="mois-label">INSCRIPTION</div>
                        <input type="number" name="inscription" class="form-control tarif-input" id="scol_inscription" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JAN</div>
                        <input type="number" name="janvier" class="form-control tarif-input" id="scol_janvier" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">FEV</div>
                        <input type="number" name="fevrier" class="form-control tarif-input" id="scol_fevrier" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">MAR</div>
                        <input type="number" name="mars" class="form-control tarif-input" id="scol_mars" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">AVR</div>
                        <input type="number" name="avril" class="form-control tarif-input" id="scol_avril" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">MAI</div>
                        <input type="number" name="mai" class="form-control tarif-input" id="scol_mai" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JUI</div>
                        <input type="number" name="juin" class="form-control tarif-input" id="scol_juin" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JUL</div>
                        <input type="number" name="juillet" class="form-control tarif-input" id="scol_juillet" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">AOU</div>
                        <input type="number" name="aout" class="form-control tarif-input" id="scol_aout" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">SEP</div>
                        <input type="number" name="septembre" class="form-control tarif-input" id="scol_septembre" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">OCT</div>
                        <input type="number" name="octobre" class="form-control tarif-input" id="scol_octobre" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">NOV</div>
                        <input type="number" name="novembre" class="form-control tarif-input" id="scol_novembre" value="0" onchange="calculerTotalScolarite()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">DEC</div>
                        <input type="number" name="decembre" class="form-control tarif-input" id="scol_decembre" value="0" onchange="calculerTotalScolarite()">
                    </div>
                </div>

                <div class="row mt-4">
                    <div class="col-md-12">
                        <button type="submit" class="btn btn-success btn-lg w-100">Enregistrer la Scolarité</button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <!-- Section Catégories de Services -->
    <div class="card mb-4">
        <div class="card-header bg-primary text-white">
            <h5>Catégories de Services</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-bordered">
                    <thead class="table-dark">
                        <tr>
                            <th>Catégorie Mensuel</th>
                            <th>Catégorie Inscription</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <form action="{{ url_for('categorie_ajouter') }}" method="POST" class="d-flex gap-2">
                                    <input type="hidden" name="type_categorie" value="mensuel">
                                    <input type="text" name="nom" class="form-control" placeholder="Nom catégorie" required>
                                    <button type="submit" class="btn btn-success">Ajouter</button>
                                </form>
                                <div class="mt-2">
                                    {% for cat in categories_mensuel %}
                                    <span class="badge bg-secondary">{{ cat.nom }}
                                        <form action="{{ url_for('categorie_supprimer', id=cat.id) }}" method="POST" class="d-inline" onsubmit="return confirm('Supprimer?');">
                                            <button type="submit" class="btn btn-sm btn-link text-white p-0 ms-1">×</button>
                                        </form>
                                    </span>
                                    {% endfor %}
                                </div>
                            </td>
                            <td>
                                <form action="{{ url_for('categorie_ajouter') }}" method="POST" class="d-flex gap-2">
                                    <input type="hidden" name="type_categorie" value="inscription">
                                    <input type="text" name="nom" class="form-control" placeholder="Nom catégorie" required>
                                    <button type="submit" class="btn btn-success">Ajouter</button>
                                </form>
                                <div class="mt-2">
                                    {% for cat in categories_inscription %}
                                    <span class="badge bg-secondary">{{ cat.nom }}
                                        <form action="{{ url_for('categorie_supprimer', id=cat.id) }}" method="POST" class="d-inline" onsubmit="return confirm('Supprimer?');">
                                            <button type="submit" class="btn btn-sm btn-link text-white p-0 ms-1">×</button>
                                        </form>
                                    </span>
                                    {% endfor %}
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Section Tarifs de Services -->
    <div class="card mb-4">
        <div class="card-header bg-warning text-dark">
            <h5>Tarifs des Services</h5>
        </div>
        <div class="card-body">
            <form action="{{ url_for('tarif_service_sauvegarder') }}" method="POST">
                <div class="row mb-3">
                    <div class="col-md-4">
                        <label class="form-label fw-bold">CLASSE</label>
                        <select name="classe_id" class="form-select" required>
                            <option value="">Sélectionner...</option>
                            {% for classe in classes %}
                            <option value="{{ classe.id }}">{{ classe.nom }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">CATEGORIE</label>
                        <select name="categorie_id" class="form-select" required>
                            <option value="">Sélectionner...</option>
                            {% for cat in categories %}
                            <option value="{{ cat.id }}">{{ cat.nom }} ({{ cat.type_categorie }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">TOTAL ANNUEL</label>
                        <input type="text" id="totalService" class="form-control bg-light" readonly value="0 FCFA">
                    </div>
                </div>

                <div class="row g-2">
                    <div class="col-md-1 col-3">
                        <div class="mois-label">INSCRIPTION</div>
                        <input type="number" name="inscription" class="form-control tarif-input" id="serv_inscription" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JAN</div>
                        <input type="number" name="janvier" class="form-control tarif-input" id="serv_janvier" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">FEV</div>
                        <input type="number" name="fevrier" class="form-control tarif-input" id="serv_fevrier" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">MAR</div>
                        <input type="number" name="mars" class="form-control tarif-input" id="serv_mars" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">AVR</div>
                        <input type="number" name="avril" class="form-control tarif-input" id="serv_avril" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">MAI</div>
                        <input type="number" name="mai" class="form-control tarif-input" id="serv_mai" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JUI</div>
                        <input type="number" name="juin" class="form-control tarif-input" id="serv_juin" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">JUL</div>
                        <input type="number" name="juillet" class="form-control tarif-input" id="serv_juillet" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">AOU</div>
                        <input type="number" name="aout" class="form-control tarif-input" id="serv_aout" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">SEP</div>
                        <input type="number" name="septembre" class="form-control tarif-input" id="serv_septembre" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">OCT</div>
                        <input type="number" name="octobre" class="form-control tarif-input" id="serv_octobre" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">NOV</div>
                        <input type="number" name="novembre" class="form-control tarif-input" id="serv_novembre" value="0" onchange="calculerTotalService()">
                    </div>
                    <div class="col-md-1 col-3">
                        <div class="mois-label">DEC</div>
                        <input type="number" name="decembre" class="form-control tarif-input" id="serv_decembre" value="0" onchange="calculerTotalService()">
                    </div>
                </div>

                <div class="row mt-4">
                    <div class="col-md-12">
                        <button type="submit" class="btn btn-warning btn-lg w-100">Enregistrer le Tarif de Service</button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <!-- Liste des Scolarités -->
    <div class="card mt-4">
        <div class="card-header bg-success text-white">
            <h5>Scolarités Définies</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead class="table-dark">
                        <tr>
                            <th>Classe</th>
                            <th>Insc.</th>
                            <th>Jan</th>
                            <th>Fev</th>
                            <th>Mar</th>
                            <th>Avr</th>
                            <th>Mai</th>
                            <th>Jui</th>
                            <th>Jul</th>
                            <th>Aou</th>
                            <th>Sep</th>
                            <th>Oct</th>
                            <th>Nov</th>
                            <th>Dec</th>
                            <th>Total</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for scolarite in scolarites %}
                        <tr>
                            <td>{{ scolarite.classe.nom }}</td>
                            <td>{{ "%s"|format(scolarite.inscription) }}</td>
                            <td>{{ "%s"|format(scolarite.janvier) }}</td>
                            <td>{{ "%s"|format(scolarite.fevrier) }}</td>
                            <td>{{ "%s"|format(scolarite.mars) }}</td>
                            <td>{{ "%s"|format(scolarite.avril) }}</td>
                            <td>{{ "%s"|format(scolarite.mai) }}</td>
                            <td>{{ "%s"|format(scolarite.juin) }}</td>
                            <td>{{ "%s"|format(scolarite.juillet) }}</td>
                            <td>{{ "%s"|format(scolarite.aout) }}</td>
                            <td>{{ "%s"|format(scolarite.septembre) }}</td>
                            <td>{{ "%s"|format(scolarite.octobre) }}</td>
                            <td>{{ "%s"|format(scolarite.novembre) }}</td>
                            <td>{{ "%s"|format(scolarite.decembre) }}</td>
                            <td class="fw-bold text-success">{{ "%s"|format(scolarite.total_annuel) }}</td>
                            <td>
                                <form action="{{ url_for('scolarite_supprimer', id=scolarite.id) }}" method="POST" onsubmit="return confirm('Supprimer?');">
                                    <button type="submit" class="btn btn-sm btn-danger">X</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Liste des Tarifs de Services -->
    <div class="card mt-4">
        <div class="card-header bg-warning text-dark">
            <h5>Tarifs de Services Définis</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead class="table-dark">
                        <tr>
                            <th>Classe</th>
                            <th>Cat.</th>
                            <th>Insc.</th>
                            <th>Jan</th>
                            <th>Fev</th>
                            <th>Mar</th>
                            <th>Avr</th>
                            <th>Mai</th>
                            <th>Jui</th>
                            <th>Jul</th>
                            <th>Aou</th>
                            <th>Sep</th>
                            <th>Oct</th>
                            <th>Nov</th>
                            <th>Dec</th>
                            <th>Total</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for tarif in tarifs_services %}
                        <tr>
                            <td>{{ tarif.classe.nom }}</td>
                            <td>{{ tarif.categorie.nom }}</td>
                            <td>{{ "%s"|format(tarif.inscription) }}</td>
                            <td>{{ "%s"|format(tarif.janvier) }}</td>
                            <td>{{ "%s"|format(tarif.fevrier) }}</td>
                            <td>{{ "%s"|format(tarif.mars) }}</td>
                            <td>{{ "%s"|format(tarif.avril) }}</td>
                            <td>{{ "%s"|format(tarif.mai) }}</td>
                            <td>{{ "%s"|format(tarif.juin) }}</td>
                            <td>{{ "%s"|format(tarif.juillet) }}</td>
                            <td>{{ "%s"|format(tarif.aout) }}</td>
                            <td>{{ "%s"|format(tarif.septembre) }}</td>
                            <td>{{ "%s"|format(tarif.octobre) }}</td>
                            <td>{{ "%s"|format(tarif.novembre) }}</td>
                            <td>{{ "%s"|format(tarif.decembre) }}</td>
                            <td class="fw-bold text-success">{{ "%s"|format(tarif.total_annuel) }}</td>
                            <td>
                                <form action="{{ url_for('tarif_service_supprimer', id=tarif.id) }}" method="POST" onsubmit="return confirm('Supprimer?');">
                                    <button type="submit" class="btn btn-sm btn-danger">X</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
function calculerTotalScolarite() {
    const mois = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre'];
    let total = 0;
    mois.forEach(function(m) {
        const val = parseFloat(document.getElementById('scol_' + m).value) || 0;
        total += val;
    });
    document.getElementById('totalScolarite').value = total.toLocaleString('fr-FR') + ' FCFA';
}

function calculerTotalService() {
    const mois = ['inscription', 'janvier', 'fevrier', 'mars', 'avril', 'mai', 'juin', 'juillet', 'aout', 'septembre', 'octobre', 'novembre', 'decembre'];
    let total = 0;
    mois.forEach(function(m) {
        const val = parseFloat(document.getElementById('serv_' + m).value) || 0;
        total += val;
    });
    document.getElementById('totalService').value = total.toLocaleString('fr-FR') + ' FCFA';
}

function telechargerModele(type) {
    window.location.href = '/finances/parametres/modele/' + type;
}

document.addEventListener('DOMContentLoaded', function() {
    calculerTotalScolarite();
    calculerTotalService();
});
</script>
{% endblock %}
'''

with open('templates/finances/parametres.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print('File created successfully')
