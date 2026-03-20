# Preuves à inclure dans le rapport, les annexes et les appendices

Ce document liste toutes les captures d'écran, extraits de logs et preuves
à produire pour rendre le dossier E5 défendable devant le jury.
Chaque preuve est associée à la section où l'insérer.

---

## 1. Preuves GitHub (C21)

### 1.1 Issue GitHub ouverte
**Où insérer** : Annexe 4 — `ANNEXE_4_ISSUE_ET_PR_GITHUB.md`, sous le titre
« Issue GitHub » → remplacer le placeholder
`> *Insérer ici la capture d'écran de l'issue GitHub ouverte.*`

**Ce qu'on doit voir :**
- Titre de l'issue : « Bug: crash sur images ≠ 224×224 — ValueError shape incompatible »
- Labels (ex. `bug`)
- Statut : `Closed` (ou `Open` si capturé avant la clôture)
- Corps de l'issue : symptômes, traceback, étapes de reproduction

**Comment obtenir :**
1. Ouvrir l'issue sur GitHub.
2. Faire une capture plein écran (Windows : `Win + Maj + S`).

---

### 1.2 Pull Request mergée avec badge CI vert
**Où insérer** : Annexe 4, sous « Pull Request » → remplacer le placeholder
`> *Insérer ici la capture d'écran de la PR mergée avec le badge CI vert.*`

**Ce qu'on doit voir :**
- Titre de la PR : « Fix: redimensionnement systématique dans preprocess_from_pil() »
- Statut : `Merged` (bandeau violet)
- Badge CI vert (jobs `lint` ✓ et `tests` ✓ visibles)
- Référence à l'issue fermée

**Comment obtenir :**
1. Ouvrir la PR sur GitHub après le merge.
2. Si la CI n'est pas encore verte, lancer `git push` après avoir corrigé les
   éventuelles erreurs de lint.

---

### 1.3 CI verte dans GitHub Actions
**Où insérer** : Annexe 3 — `ANNEXE_3_CI_GITHUB_ACTIONS.md`, après le bloc
YAML du workflow (en bas de fichier).

**Ce qu'on doit voir :**
- Liste des jobs : `Lint (flake8)` ✓ et `Tests de regression (pytest + coverage)` ✓
- Durée des jobs (ex. lint : 15 s, tests : 30 s)
- Commit associé

**Comment obtenir :**
1. Aller sur l'onglet « Actions » du dépôt GitHub.
2. Cliquer sur le dernier run réussi.
3. Capturer la page de synthèse des jobs.

---

## 2. Preuves de l'application en fonctionnement (C20 + C21)

### 2.1 Terminal — `16 passed`
**Où insérer** :
- Rapport principal section 2.3
- Annexe 2 — `ANNEXE_2_PROCEDURE_LANCEMENT_LOCAL.md`, après la commande pytest

**Ce qu'on doit voir :**
```
16 passed in X.XXs
```
(pas d'erreurs, pas de warnings)

**Comment obtenir :**
```powershell
Set-Location "c:\Users\Utilisateur\Documents\Simplon - 2025\Bertrand-Debuggage-application-15092025\app"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest test_app.py -q
```

---

### 2.2 Interface `/monitoring` avec statut rouge « critical »
**Où insérer** :
- Rapport principal section 3.4
- Annexe 1 — point 6 de la démonstration

**Ce qu'on doit voir :**
- Tableau de bord HTML affiché dans le navigateur (`http://127.0.0.1:5000/monitoring`)
- Statut affiché en rouge ou orange selon le niveau d'alerte
- Valeurs : accuracy, nombre de feedbacks, distribution des classes

**Comment obtenir :**
1. Lancer l'application : `python app.py`
2. Soumettre plusieurs feedbacks incorrects (au moins 3).
3. Ouvrir `http://127.0.0.1:5000/monitoring` et capturer.

---

### 2.3 Route `/health` — réponse JSON
**Où insérer** : Rapport principal section 3.4

**Ce qu'on doit voir :**
```json
{
  "status": "ok",
  "model_loaded": true,
  "feedback_count": 5,
  "accuracy": 40.0,
  "alert_level": "critical"
}
```

**Comment obtenir :**
1. Ouvrir `http://127.0.0.1:5000/health` dans le navigateur (ou `curl`).
2. Capturer la réponse JSON affichée.

---

### 2.4 Flask-Monitoring-Dashboard (`/dashboard/`)
**Où insérer** :
- Appendice C — `APPENDICE_C_FLASK_MONITORING_DASHBOARD.md`, section « Fonctionnalités exposées »
- Rapport principal section 3.5

**Ce qu'on doit voir :**
- Le tableau de bord FMD ouvert à `http://127.0.0.1:5000/dashboard/`
- Au moins une route visible (ex. `/predict`) avec temps de réponse
- Onglet « Overview » montrant toutes les routes

**Comment obtenir :**
1. Lancer `python app.py`.
2. Faire au moins une requête sur `/predict`.
3. Ouvrir `http://127.0.0.1:5000/dashboard/` et capturer l'onglet « Overview ».

---

### 2.5 MLflow UI — liste des runs
**Où insérer** :
- Appendice D — `APPENDICE_D_MLFLOW_TRACKING.md`, section « Consultation du tracking »
- Rapport principal section 3.6

**Ce qu'on doit voir :**
- Interface MLflow ouverte à `http://127.0.0.1:5001`
- Expérience `satellite-classification` sélectionnée
- Liste des runs avec `run_name` = `prediction` ou `feedback`
- Colonnes `accuracy`, `confidence`, `is_correct` visibles

**Comment obtenir :**
```powershell
# Dans un second terminal
mlflow ui --backend-store-uri mlruns/ --port 5001
```
Puis ouvrir `http://127.0.0.1:5001`.

---

### 2.6 MLflow UI — évolution de l'accuracy
**Où insérer** :
- Annexe 1 — point 9 de la démonstration
- Annexe 2 — étape 7 de la démonstration

**Ce qu'on doit voir :**
- Graphe de l'accuracy en fonction du numéro de run (courbe descendante si
  les feedbacks sont majoritairement incorrects)
- Au moins 3 points de données

**Comment obtenir :**
1. Soumettre plusieurs feedbacks.
2. Dans MLflow UI, filtrer par `feedback`, cliquer sur « Chart view »,
   sélectionner la métrique `accuracy`.
3. Capturer le graphe.

---

## 3. Preuves de journalisation (C20)

### 3.1 Fichier `logs/app.log` — ligne CRITICAL
**Où insérer** :
- Rapport principal section 3.3
- Annexe 1 — point 5 de la démonstration

**Ce qu'on doit voir :**
```
[CRITICAL] Accuracy dropped below 60% (current: 40.0%, feedback_count: 5)
```

**Comment obtenir :**
1. Soumettre au moins 3–5 feedbacks tous incorrects.
2. Ouvrir `logs\app.log` avec un éditeur ou PowerShell :
```powershell
Get-Content logs\app.log | Select-String "CRITICAL"
```

---

### 3.2 Fichier `logs/predictions.log` — entrée de prédiction
**Où insérer** : Rapport principal section 3.1

**Ce qu'on doit voir :**
```
[INFO] Prediction: meadow (0.973) — satellite_001.jpg
```

**Comment obtenir :**
1. Faire une prédiction depuis l'interface.
2. Ouvrir `logs\predictions.log`.

---

## 4. Preuve de la correction du bug (C21)

### 4.1 Capture du traceback original
**Où insérer** : Appendice A — `APPENDICE_A_TRACEBACK_INCIDENT.md`

**Ce qu'on doit voir :**
```
ValueError: Input 0 of layer is incompatible with the layer:
expected shape (None, 224, 224, 3), found shape (None, 600, 600, 3)
```

**Comment obtenir :**
- Si non disponible dans les logs, reproduire le bug sur la version **avant correctif**
  (commenter temporairement le `img.resize((224, 224), ...)` dans `preprocess_from_pil()`).
- Ou capturer depuis les notes de l'issue GitHub.

---

### 4.2 Diff du correctif dans la PR
**Où insérer** : Annexe 4, section « Pull Request »

**Ce qu'on doit voir :**
- Diff GitHub montrant l'ajout de `img.resize((224, 224), Image.Resampling.LANCZOS)`
  dans `preprocess_from_pil()`
- Lignes vertes (ajout) visibles

**Comment obtenir :**
1. Aller sur la PR sur GitHub.
2. Cliquer sur l'onglet « Files changed ».
3. Capturer le diff de `app.py`.

---

## Récapitulatif — liste de toutes les captures à produire

| # | Capture | Section cible | Priorité |
|---|---------|---------------|----------|
| 1 | Issue GitHub ouverte | Annexe 4 | 🔴 Indispensable |
| 2 | PR mergée + badge CI vert | Annexe 4 | 🔴 Indispensable |
| 3 | CI verte dans GitHub Actions | Annexe 3 | 🔴 Indispensable |
| 4 | Terminal `16 passed` | Rapport 2.3 + Annexe 2 | 🔴 Indispensable |
| 5 | `/monitoring` statut rouge | Rapport 3.4 + Annexe 1 | 🔴 Indispensable |
| 6 | `/health` réponse JSON | Rapport 3.4 | 🟡 Recommandé |
| 7 | FMD `/dashboard/` overview | Appendice C + Rapport 3.5 | 🔴 Indispensable |
| 8 | MLflow UI — liste des runs | Appendice D + Rapport 3.6 | 🔴 Indispensable |
| 9 | MLflow UI — courbe accuracy | Annexe 1 point 9 + Annexe 2 | 🟡 Recommandé |
| 10 | `logs/app.log` — CRITICAL | Rapport 3.3 + Annexe 1 | 🟡 Recommandé |
| 11 | `logs/predictions.log` | Rapport 3.1 | 🟢 Optionnel |
| 12 | Traceback original | Appendice A | 🟡 Recommandé |
| 13 | Diff correctif dans la PR | Annexe 4 | 🟡 Recommandé |

---

## Ordre de production conseillé

1. Lancer l'application : `python app.py`
2. Faire 5 prédictions avec des images variées (grandes + petites).
3. Soumettre 5 feedbacks tous **incorrects** pour déclencher l'alerte CRITICAL.
4. Capturer `/monitoring` (rouge), `/health` (JSON), `/dashboard/` (FMD).
5. Dans un second terminal, lancer `mlflow ui --port 5001` et capturer l'UI.
6. Capturer `logs\app.log` avec la ligne CRITICAL.
7. Lancer `python -m pytest test_app.py -q` et capturer `16 passed`.
8. Sur GitHub : capturer l'issue, la PR mergée, et l'onglet Actions.
