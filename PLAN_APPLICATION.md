# Plan Détaillé — Barham School App

> Application SaaS de gestion scolaire (ERP) développée avec Flask.
> **URL de production** : `https://barhamschool.pythonanywhere.com/`
> **Dépôt GitHub** : `https://github.com/bartho1992/barham-school.git`

---

## 1. Vue d'ensemble

**Barham School** est une application web de gestion scolaire complète (ERP) en mode **SaaS multi-établissement**. Chaque école a ses propres données isolées par `ecole_id`. L'application couvre la gestion des élèves, des classes, des notes, des finances (paiements, scolarité, impayés), du personnel, des documents officiels, des emplois du temps, des examens, des conseils de classe, de la messagerie interne, des notifications aux parents, et d'un portail parent.

**Rôles utilisateurs** : `dev` (développeur, tous les droits), `super_users` (admin école), `user` (enseignant/comptable).

---

## 2. Stack technique

| Couche | Technologie |
|---|---|
| Backend | Python 3.11+, Flask 3.1 |
| Base de données | SQLite (via SQLAlchemy ORM) |
| Authentification | Flask-Login (sessions) |
| Frontend | Jinja2, Bootstrap 5, CSS custom (1828 lignes), Vanilla JS |
| Excel | openpyxl (import/export) |
| Emails | smtplib (SMTP configurable par école) |
| Déploiement | PythonAnywhere (production), GitHub (versionnement) |

**Dépendances Python** : Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug, openpyxl, gunicorn.

---

## 3. Architecture du projet

```
Barham School app/
├── app.py                  # Point d'entrée Flask, config, context processors, before_request
├── models.py               # 24 modèles SQLAlchemy
├── helpers.py              # get_current_ecole_id(), get_current_annee()
├── mailer.py               # Envoi d'emails SMTP
├── system_logger.py        # Logs structurés (activité, connexions, erreurs)
├── backup_manager.py       # Sauvegardes/restaurations SQLite
├── pa_wsgi.py              # Point d'entrée WSGI PythonAnywhere
│
├── routes_auth.py          # Authentification (login, logout, register, dashboard)
├── routes_eleves.py        # CRUD élèves, assiduité, import Excel
├── routes_classes.py       # CRUD classes, matières
├── routes_notes.py         # Saisie notes, bulletins
├── routes_finances.py      # Paiements, impayés, paramètres (scolarité, services, abonnements)
├── routes_personnel.py     # CRUD personnel, salaires
├── routes_admin.py         # Admin dev : écoles, users, backups, logs, sécurité
├── routes_documents.py     # Génération documents (billets, certificats, cartes, etc.)
├── routes_licence.py       # Activation/génération de licences
├── routes_saas.py          # Abonnement SaaS, pricing, checkout, factures
├── routes_messagerie.py    # Blueprint messagerie interne
├── routes_edt.py           # Blueprint emploi du temps
├── routes_examens.py       # Blueprint examens
├── routes_notifications.py # Blueprint notifications SMS/WhatsApp parents
├── routes_parent.py        # Blueprint portail parent
├── routes_cahier_texte.py  # Blueprint cahier de textes
├── routes_exports.py       # Blueprint exports (états financiers, relevés, stats)
├── routes_archives.py      # Blueprint archivage par année scolaire
├── routes_api.py           # Blueprint API REST v1 (token auth)
├── routes_conseil.py       # Blueprint conseil de classe
│
├── templates/              # 91 templates Jinja2 (18 dossiers)
│   ├── base.html           # Layout principal (sidebar + navbar)
│   ├── login.html          # Connexion
│   ├── dashboard.html      # Tableau de bord
│   ├── eleves/             # index, form, fiche, assiduite
│   ├── classes/            # index, form, matieres
│   ├── notes/              # index, saisir, bulletins
│   ├── finances/           # index, liste, impayes, form, parametres, recu, hub
│   ├── personnel/          # index, form, salaire
│   ├── documents/          # 16 templates de documents scolaires
│   ├── saas/               # pricing, abonnement, checkout, facture, tutoriel
│   ├── admin/              # users, logs, backups, licences, sécurité, email
│   └── [messages, edt, examens, notifications, parent, cahier_texte, exports, archives, conseil]/
│
├── static/
│   ├── css/style.css       # Design system complet (variables CSS, animations, composants)
│   └── js/main.js          # JS utilitaire
│
├── school.db               # Base SQLite (développement local)
└── requirements.txt        # Dépendances
```

---

## 4. Modèles de données (24 modèles)

### 4.1 École et utilisateurs

| Modèle | Champs clés | Description |
|---|---|---|
| **Ecole** | id, nom, adresse, tel, email, annee_scolaire, zone, type_ecole, directeur, slogan, autorisation, code_etablissement, ia, ief, session_timeout, max_login_attempts, smtp_* | Établissement scolaire |
| **User** | id, username, password_hash, role (dev/super_users/user), ecole_id (FK) | Utilisateurs (Flask-Login) |
| **LoginAttempt** | username, ip_address, timestamp, success | Journal des tentatives de connexion |
| **AnneeScolaire** | id, annee, active, ecole_id (FK) | Années scolaires |

### 4.2 Élèves et scolarité

| Modèle | Champs clés | Description |
|---|---|---|
| **Eleve** | id, code (unique), prenom, nom, sexe, photo, classe_id (FK), ecole_id (FK), tel, code_parent, date_naissance, lieu_naissance, tuteur, adresse, situation, annee_scolaire | Élèves |
| **Classe** | id, nom, niveau, effectif, ordre, ecole_id (FK) | Classes |
| **Matiere** | id, nom, domaine, coefficient, ecole_id (FK) | Matières enseignées |
| **Assiduite** | id, eleve_id (FK), classe_id (FK), ecole_id (FK), date_evenement, type_evenement (Absent/Retard), motif, justifie, annee_scolaire | Absences et retards |

### 4.3 Notes et évaluations

| Modèle | Champs clés | Description |
|---|---|---|
| **Note** | id, eleve_id (FK), matiere_id (FK), classe_id (FK), trimestre (1/2/3), controle, composition, moyenne, rang, appreciation, annee_scolaire | Notes par trimestre |
| **Bulletin** | id, eleve_id (FK), classe_id (FK), trimestre, moyenne_generale, rang, moyenne_classe, decision, absences, annee_scolaire | Bulletins trimestriels |

### 4.4 Finances

| Modèle | Champs clés | Description |
|---|---|---|
| **Scolarite** | id, classe_id (FK), ecole_id (FK), inscription + 12 mois (janvier..decembre), annee_scolaire, ordre | Tarifs de scolarité par classe |
| **CategorieTarif** | id, nom, type_categorie (mensuel/inscription), ecole_id (FK) | Catégories de services (Cantine, Transport...) |
| **TarifService** | id, classe_id (FK), categorie_id (FK), ecole_id (FK), inscription + 12 mois, annee_scolaire | Tarifs des services par classe |
| **AbonnementService** | id, eleve_id (FK), categorie_id (FK), actif, mois_debut, mois_fin, montant_personnalise | Abonnements élèves aux services |
| **Paiement** | id, eleve_id (FK), type_paiement (mois ou catégorie), montant, montant_attendu, montant_restant, caissier, mode_paiement, date_paiement, annee_scolaire, ecole_id (FK) | Paiements enregistrés |

### 4.5 Personnel

| Modèle | Champs clés | Description |
|---|---|---|
| **Personnel** | id, code, prenom, nom, fonction, tel, salaire_fixe, taux_impot, ecole_id (FK) | Employés |
| **Salaire** | id, personnel_id (FK), mois, salaire_brut, impot, primes, salaire_net, annee_scolaire | Salaires mensuels |

### 4.6 Documents

| Modèle | Champs clés | Description |
|---|---|---|
| **Document** | id, type_doc, eleve_id (FK), personnel_id (FK), contenu, token_verification, qr_code_url, date_expiration, statut, ecole_id (FK) | Documents générés avec QR code |

### 4.7 Licence et SaaS

| Modèle | Champs clés | Description |
|---|---|---|
| **Licence** | id, cle (unique), date_expiration, active, ecole_id (FK), plan (starter/standard/premium), eleves_max, personnel_max, essai, modules, prix_paye, devise, mode_paiement | Licences d'utilisation |
| **FactureLicence** | id, ecole_id (FK), licence_id (FK), numero (FC-YYYYMM-XXXX), plan, duree_mois, montant, devise, statut, mode_paiement | Factures |
| **TransactionLicence** | id, ecole_id (FK), facture_id (FK), montant, devise, passerelle (wave/orange_money/stripe/manual), statut, reference | Transactions de paiement |

### 4.8 Modules complémentaires

| Modèle | Champs clés | Description |
|---|---|---|
| **EmploiDuTemps** | id, classe_id (FK), matiere_id (FK), enseignant, jour, heure_debut, heure_fin, salle, couleur, annee_scolaire, ecole_id (FK) | Créneaux EDT |
| **Examen** | id, classe_id (FK), matiere_id (FK), type_examen, trimestre, date_examen, heure_debut, duree_minutes, salle, surveillant, coefficient, annee_scolaire, ecole_id (FK) | Planning examens |
| **ConseilClasse** | id, classe_id (FK), trimestre, date_conseil, president, observations_generales, annee_scolaire, ecole_id (FK) | Conseils de classe |
| **AppreciationConseil** | id, conseil_id (FK), eleve_id (FK), appreciation, decision, moyenne_generale, rang, absences, retards | Appréciations par élève |
| **Message** | id, expediteur_id (FK), destinataire_id (FK), sujet, contenu, lu, date_envoi, ecole_id (FK) | Messagerie interne |
| **CahierTexte** | id, classe_id (FK), matiere_id (FK), enseignant, date_seance, contenu, devoirs, observations, annee_scolaire, ecole_id (FK) | Cahier de textes |
| **NotificationParent** | id, eleve_id (FK), type_notif (absence/retard/paiement/evenement), message, canal (sms/whatsapp), statut, date_envoi, ecole_id (FK) | Notifications aux parents |

---

## 5. Modules fonctionnels et routes principales

### 5.1 Authentification (`/`, `/login`, `/logout`, `/register`)
- Connexion avec protection anti brute-force (limite de tentatives + verrouillage temporaire)
- Inscription auto : création école + utilisateur admin + licence essai 30 jours
- Timeout de session configurable par école

### 5.2 Dashboard (`/`)
- KPIs : total élèves, encaissements, impayés, absences du jour
- Graphiques et tableaux de bord
- Paiements récents, assiduité récente

### 5.3 Élèves (`/eleves`)
- Liste avec filtres (classe, recherche texte)
- Ajout/modification/suppression (avec photo)
- Fiche détaillée par élève
- Import Excel intelligent (détection automatique des colonnes)
- Téléchargement de modèle Excel

### 5.4 Assiduité (`/assiduite`)
- Saisie quotidienne des absences/retards par classe
- Statistiques et historique

### 5.5 Classes et matières (`/classes`, `/matieres`)
- CRUD classes (simple ou par lot)
- CRUD matières avec coefficient
- Réorganisation par drag & drop

### 5.6 Notes (`/notes`, `/bulletins`)
- Saisie des notes par classe/trimestre/matière
- Calcul automatique des moyennes et rangs
- Bulletins détaillés

### 5.7 Finances (`/finances`)
- **Tableau des finances** : DU (montant dû), AVANCE (versé), RESTE (reste à payer), CUMUL (total restant)
- **Tableau des impayés** : détail par catégorie de service
- **Paiement** : formulaire de paiement individuel ou groupé
- **Liste des paiements** : historique avec filtres
- **Reçu** : génération de reçu après paiement
- **Annulation** : suppression de paiement (super_users)
- **Paramètres** : configuration des scolarités, catégories de services, tarifs, abonnements

#### Logique de calcul financier (fonction centrale `_build_ligne_financiere()`)
1. Pour chaque élève, calcule les montants dus par mois (scolarité + services abonnés)
2. Alloue chronologiquement chaque paiement aux échéances impayées (scolarité prioritaire)
3. Détermine l'échéance de référence : premier mois avec reste > 0, ou dernier mois dû
4. DU = montant de l'échéance de référence | AVANCE = déjà payé sur cette échéance | RESTE = échéance - payé | CUMUL = total général restant

### 5.8 Personnel (`/personnel`)
- CRUD personnel (enseignants, administratifs)
- Gestion des salaires mensuels (brut, primes, impôt, net)

### 5.9 Documents (`/documents`)
- 13 types de documents : billet d'entrée/sortie/renvoi, certificat de scolarité, carte scolaire, attestation, convocation, avertissement, reçu, mise en demeure, attestation de travail, transfert
- QR code de vérification sur chaque document
- Impression optimisée

### 5.10 Administration (`/admin`)
- Gestion des écoles et utilisateurs
- Année scolaire : changement global dans la session
- Sauvegardes : créer, télécharger, restaurer, supprimer
- Logs système : visualisation, stats, purge
- Sécurité : timeout, IP whitelist, tentatives max
- Email : configuration SMTP par école + test
- Maintenance : infos BDD, SQL brut, exports JSON
- Import CSV élèves

### 5.11 Licence (`/licence`, `/admin/licences`)
- Activation par clé de licence
- Génération de licences (admin)
- Plans : starter (150 élèves max), standard (500), premium (illimité)

### 5.12 SaaS / Abonnement (`/pricing`, `/abonnement`, `/abonnement/checkout`)
- Page de tarifs publique
- Checkout avec sélection du plan et de la durée
- Paiement via Wave, Orange Money, ou Stripe
- Factures numérotées (FC-YYYYMM-XXXX)
- Essai gratuit 30 jours
- Webhook de confirmation de paiement
- Admin : validation/refus manuel des paiements

### 5.13 Messagerie interne (`/messages`)
- Envoi/réception de messages entre utilisateurs
- Indicateur de messages non lus
- Boîte de réception et messages envoyés

### 5.14 Emploi du temps (`/edt`)
- Création de créneaux par classe/matière/jour/heure
- Code couleur par matière
- Vue par classe

### 5.15 Examens (`/examens`)
- Planning des examens par classe et trimestre
- Créneaux avec date, heure, durée, salle, surveillant

### 5.16 Conseil de classe (`/conseil`)
- Création de conseils par classe/trimestre
- Saisie des appréciations et décisions par élève
- Récupération automatique des moyennes et rangs

### 5.17 Cahier de textes (`/cahier-texte`)
- Enregistrement des séances par classe/matière/date
- Contenu de la séance, devoirs, observations

### 5.18 Notifications parents (`/notifications`)
- Envoi de notifications SMS/WhatsApp aux parents
- Types : absence, retard, paiement, événement
- Historique des envois

### 5.19 Portail parent (`/parent`)
- Connexion par code parent unique
- Consultation des notes, paiements, absences de l'enfant

### 5.20 Exports (`/exports`)
- État financier (recettes par mois et type)
- Relevé de notes détaillé
- Liste des élèves
- Statistiques globales

### 5.21 Archives (`/archives`)
- Archivage des données par année scolaire
- Consultation des archives

### 5.22 API REST (`/api/v1`)
- Authentification par token
- Endpoints : infos école, classes, élèves, notes, solde financier, statistiques
- Pagination et filtres

### 5.23 Etablissement et utilisateurs
- `/etablissement` : gestion du profil école (tout utilisateur)
- `/utilisateurs` : gestion des utilisateurs de l'école (tout utilisateur)

### 5.24 Tutoriel (`/tutoriel`)
- Page publique de présentation et guide d'utilisation

---

## 6. Règles métier et contraintes

1. **Isolation par école** : toutes les requêtes sont filtrées par `ecole_id` pour éviter les fuites de données entre établissements.
2. **Licence obligatoire** : un `before_request` vérifie la licence active pour toutes les routes (sauf routes libres : login, register, pricing, tutoriel). Les rôles `dev` et `super_users` contournent cette vérification.
3. **Année scolaire active** : stockée en session. Les élèves sans `annee_scolaire` sont inclus dans les listes (pour rétrocompatibilité).
4. **Mois scolaires** : `['Inscription', 'Octobre', 'Novembre', 'Decembre', 'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin']`
5. **Sidebar** : fixe à 185px, non réductible (la fonctionnalité de réduction a été supprimée).
6. **Barre d'actions groupées** : dans Paramètres > Scolarité, les actions (supprimer, réinitialiser) apparaissent dans une barre collante en bas quand des lignes sont sélectionnées.
7. **Cache CSS** : version incrémentée dans l'URL du style pour forcer le rafraîchissement (`?v=X`).

---

## 7. Sécurité

- Mots de passe hashés (werkzeug `generate_password_hash`)
- Protection brute-force : max tentatives + verrouillage temporaire (configurable par école)
- IP whitelist optionnelle par école
- Timeout de session configurable
- Tokens de vérification uniques pour les documents (QR codes)
- Isolation stricte des données par `ecole_id`

---

## 8. Déploiement

- **Développement** : `python app.py` → `http://127.0.0.1:5001`
- **Production** : PythonAnywhere (`pa_wsgi.py`)
- **Versionnement** : Git → GitHub (`bartho1992/barham-school`)
- **Workflow** : modifications locales → `git push origin master` → `git pull` sur PythonAnywhere → Reload
