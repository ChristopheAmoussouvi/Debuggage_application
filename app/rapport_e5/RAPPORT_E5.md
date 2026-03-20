# Rapport E5 - Surveillance et resolution d'incident sur une application Flask de classification d'images satellite

## Introduction

Dans le cadre du livrable E5, l'objectif etait de partir d'une application existante presentant un incident technique, d'en identifier la cause, d'appliquer un correctif minimal et stable, puis de documenter les moyens mis en place pour prevenir une regression. Le second objectif etait de couvrir la competence C20 en ajoutant une logique simple de journalisation, de monitorage local et de feedback loop alimentee par les utilisateurs.

L'application etudiee est une application Flask de classification d'images satellite en quatre classes : `desert`, `forest`, `meadow` et `mountain`. Elle utilise un modele CNN Keras avec le backend PyTorch. Elle permet a l'utilisateur de deposer une image, d'obtenir une prediction du modele, puis de signaler si la prediction etait correcte ou non.

### Description du modele

Le modele est un reseau de neurones convolutionnel (CNN) entraine sur des images satellites. Ses caracteristiques techniques sont les suivantes :

| Propriete | Valeur |
|-----------|--------|
| Type | CNN (Keras) |
| Entree | Images RGB 224 x 224 pixels |
| Sortie | 4 classes : `desert`, `forest`, `meadow`, `mountain` |
| Backend | PyTorch (`KERAS_BACKEND='torch'`) |
| Fichier | `models/final_cnn.keras` |
| Couche speciale | `RandomContrast` (necessitait un monkey-patch pour supprimer le parametre `value_range` incompatible) |

Le chargement du modele est realise de facon paresseuse via `get_model()` avec `@lru_cache`. Cela garantit que le modele n'est charge qu'au premier appel a `/predict` et uniquement en contexte de production (pas pendant les tests).

Le travail a ete volontairement cadre autour d'un correctif minimal. L'idee n'etait pas de rearchitecturer tout le projet MLOps, mais de fiabiliser l'existant, de rendre le comportement observable et de produire une preuve technique defendable devant le jury.

## 1. Incident technique et resolution (C21)

### 1.1 Symptomes observes

L'incident se produisait au moment de l'appel a la route `/predict`. Lorsqu'un utilisateur deposait une image de grande dimension, l'application tombait en erreur au lieu d'afficher une prediction.

Le symptome principal etait une incompatibilite entre la taille des images soumises par l'utilisateur et le format attendu par le modele de classification. Le modele avait ete entraine pour recevoir des tenseurs de forme `(224, 224, 3)`, alors que les images envoyees a l'application pouvaient avoir des dimensions tres variables.

### 1.2 Cause racine

La cause racine se trouvait dans la fonction de pretraitement des images. L'image etait convertie en RGB et normalisee, mais le redimensionnement n'etait pas garanti dans le flux historique de l'application. Dans ce contexte, le modele recevait un tenseur incompatible avec son architecture.

L'erreur n'etait donc pas un probleme aleatoire. Elle etait directement liee au flux applicatif suivant :

1. reception d'une image utilisateur ;
2. ouverture de l'image avec PIL ;
3. conversion en tableau numerique ;
4. passage au modele sans harmonisation stricte de la taille ;
5. erreur de forme au moment de `model.predict`.

### 1.3 Reproduction de l'incident

Le bug est reproductible avec une image de taille differente de `224x224`, par exemple `600x600` ou `1024x768`. Sans redimensionnement explicite, la forme d'entree transmise au modele devient incompatible avec celle definie lors de l'entrainement.

Cette reproductibilite est importante pour C21 car elle permet de demontrer que l'erreur a ete comprise, localisee et traitee a la source.

### 1.4 Suivi de l'incident via GitHub Issues

L'incident a ete documente dans l'outil de suivi du projet via une **issue GitHub** intitulee « Bug: crash sur images ≠ 224×224 — ValueError shape incompatible ». Cette issue contient :

1. le traceback complet de l'erreur ;
2. les etapes de reproduction ;
3. l'analyse de la cause racine ;
4. la reference au correctif dans la pull request associee.

La resolution a ete versionnee via une **pull request** (PR) « Fix: redimensionnement systematique dans preprocess_from_pil() » referencant l'issue. La PR a ete revue, validee par la CI (lint + tests), puis mergee dans la branche `main`. Ce workflow issue → PR → merge est conforme au critere C21 qui exige que « la procedure de debogage du code est documentee depuis l'outil de suivi » et que « la solution est versionnee dans le depot Git du projet ».

Les captures d'ecran de l'issue et de la PR mergee sont fournies en Annexe 4.

### 1.5 Correctif applique

Le correctif retenu est volontairement minimal et cible. La fonction `preprocess_from_pil()` a ete stabilisee pour imposer un pretraitement unique :

1. conversion en RGB ;
2. redimensionnement a `224x224` avec `Image.Resampling.LANCZOS` ;
3. normalisation en `float32` sur l'intervalle `[0, 1]` ;
4. ajout de l'axe batch.

Ce choix est adapte au besoin car il corrige la cause du crash sans modifier le modele, sans changer l'API publique de l'application et sans introduire de dette technique supplementaire.

En complement, le chargement du modele a ete rendu paresseux. Le modele n'est plus importe au chargement du module, mais lors du premier besoin via `get_model()`. Ce choix apporte deux benefices :

1. les tests n'ont plus besoin de charger Keras ou PyTorch a l'import ;
2. l'application devient plus testable et les regressions du flux HTTP peuvent etre validees avec un modele factice.

### 1.6 Stabilisation du flux `/predict`

La route `/predict` a egalement ete renforcee :

1. verification de la presence du champ `file` ;
2. validation d'un nom de fichier non vide ;
3. controle des extensions autorisees ;
4. journalisation de la prediction ;
5. redirection propre vers `/` en cas d'echec du traitement.

## 2. Tests automatises et prevention de la regression (C21)

### 2.1 Strategie de test retenue

Pour eviter toute regression sur le bug de shape, j'ai mis en place une suite de tests automatisee dans `test_app.py`. Le point central etait de tester non seulement la fonction de pretraitement, mais aussi le chemin complet `/predict` dans une situation realiste.

Le test unitaire simple sur la fonction de pretraitement ne suffisait pas a lui seul. Il fallait aussi verifier que la route Flask envoyait bien un tenseur `224x224` au modele. Pour cette raison, un `FakeModel` a ete introduit dans les tests avec un `patch` sur `get_model()`.

### 2.2 Scenarios couverts — 19 tests

La suite comprend 19 methodes de test couvrant les scenarios suivants :

| Test | Scenario | Objectif |
|------|----------|----------|
| 1 | Extensions autorisees et refusees (jpg, png, bmp, txt…) | Validation entree |
| 2 | Generation de Data URL base64 depuis PIL | Interface HTML |
| 3 | `preprocess_from_pil()` → shape `(1, 224, 224, 3)` | Correctif shape |
| 4 | Tailles variees : 100×100, 500×300, 1024×768, 3000×2000 | Anti-regression |
| 5 | GET `/` → HTTP 200 | Route principale |
| 6 | POST `/predict` sans fichier → redirection | Validation entree |
| 7 | POST `/predict` nom vide → redirection | Validation entree |
| 8 | POST `/predict` extension invalide → redirection | Validation entree |
| 9 | POST `/predict` image 600×400 → HTTP 200 | Correctif integration |
| 10 | GET `/feedback` → HTTP 200 | Route feedback |
| 11 | POST `/feedback` → persistance SQLite verifiee | Feedback loop |
| 12 | GET `/health` → JSON valide | C20 monitorage |
| 13 | GET `/monitoring` → HTML tableau de bord | C20 monitorage |
| 14 | Config Flask : MAX_CONTENT_LENGTH et UPLOAD_FOLDER | Securite |
| 15 | Flask-Monitoring-Dashboard : route `/dashboard/` enregistree | C20 monitorage |
| 16 | MLflow : `log_to_mlflow()` appelee sans lever d'exception | C20 MLOps |
| 17 | GET `/alerts` : JSON avec cle `alerts` (liste) | C20 alerting |
| 18 | GET `/retrain/status` : JSON avec `retraining_needed` | C20 boucle MLOps |
| 19 | POST `/retrain/export` : JSON avec `exported` | C20 boucle MLOps |

Resultat : **19 passed**.

### 2.3 Resultat de validation

La suite de tests a ete executee sous Windows avec PowerShell. Le resultat final : `19 passed`. Ce n'est plus un simple discours sur la qualite, mais une preuve executable que le bug identifie est bien capture.

## 3. Journalisation et monitorage local (C20)

### 3.1 Politique de journalisation

Un module dedie `logging_config.py` a ete mis en place pour structurer les logs de l'application. La configuration retenue utilise des handlers rotatifs sur fichiers afin de conserver un historique local sans croissance infinie des journaux.

Trois sorties sont gerees :

1. `app.log` pour les evenements applicatifs generaux ;
2. `error.log` pour les erreurs ;
3. `predictions.log` pour les predictions et feedbacks.

### 3.2 Metriques retenues

Pour rester proportionne a l'application, j'ai retenu des metriques simples, utiles et directement observables :

1. existence du modele sur le disque ;
2. nombre total de feedbacks collectes ;
3. accuracy calculee a partir des corrections utilisateur ;
4. distribution des classes predites ;
5. distribution des classes corrigees par les utilisateurs.

### 3.3 Seuils et alertes proactives

Les seuils suivants ont ete definis :

1. `accuracy_warning = 75%` ;
2. `accuracy_critical = 60%` ;
3. `feedback_volume_warning = 20` feedbacks.

Les alertes sont **proactives** : a chaque soumission de feedback et a chaque consultation du monitoring, la fonction `build_monitoring_snapshot()` evalue les seuils et emet automatiquement un log de niveau `CRITICAL` ou `WARNING` dans `app.log` et `error.log`. Ces alertes sont declenchees sans intervention humaine et sont tracees dans les journaux rotatifs.

Exemple de log emis automatiquement :

```
[CRITICAL] Accuracy dropped below 60% (from 75%)
[WARNING] Feedback volume reached 20
```

### 3.4 Monitorage local en environnement Windows

Le choix d'un tableau de bord HTML simple est volontaire et adapte au livrable E5. Deux mecanismes exposent les metriques :

1. la route `/health` qui retourne un JSON synthetique consommable par un outil externe ;
2. la route `/monitoring` qui affiche un tableau de bord HTML local.

### 3.5 Monitoring des endpoints — Flask-Monitoring-Dashboard

Pour surveiller les performances des routes Flask en temps reel, l'outil
**Flask-Monitoring-Dashboard** a ete integre a l'application. L'integration
se fait en deux lignes :

```python
import flask_monitoringdashboard as monitor_dashboard
monitor_dashboard.bind(app)
```
Ce composant fournit automatiquement un tableau de bord accessible a
`/dashboard/` qui expose :

- le temps de reponse moyen par route (`/predict`, `/feedback`, `/health`) ;
- le nombre de requetes par endpoint et par periode ;
- la detection d'outliers (requetes anormalement lentes) ;
- l'evolution temporelle des performances.

Ce choix a ete prefere a un dashboard HTML fait main pour la surveillance
des endpoints car il apporte une couverture de monitorage professionnelle
sans developpement supplementaire, et il repond au critere C20 qui exige
que « les outils de surveillance sont operationnels ».

Les details techniques de l'integration sont documentes en Appendice C.

### 3.6 Tracking MLOps — MLflow

MLflow a ete integre pour assurer la tracabilite des predictions et des
feedbacks dans une perspective MLOps. Le tracking est configure en local
(repertoire `mlruns/`) et chaque evenement significatif est enregistre :

- Prediction : classe predite, score de confiance, nom de fichier ;
- Feedback : label utilisateur, label predit, accuracy courante, nombre total de feedbacks, indicateur `is_correct`.

L'enregistrement est effectue par la fonction `log_to_mlflow()` qui cree un
run MLflow pour chaque evenement. En cas d'indisponibilite du serveur MLflow,
le logging est silencieusement ignore pour ne pas bloquer l'application.

Le tableau de bord MLflow est consultable avec :

```powershell
mlflow ui --backend-store-uri mlruns/ --port 5001
```

puis en ouvrant `http://127.0.0.1:5001` dans le navigateur.

Ce suivi continu permet :

- de visualiser l'evolution de l'accuracy au fil des feedbacks ;
- de detecter une derive du modele (drift) par observation des metriques ;
- de decider objectivement du moment opportun pour un reentrainement ;
- de conserver un historique versionne des metriques du modele.

Les details techniques de l'integration sont documentes en Appendice D.

### 3.8 Alerting : capacites reelles de FMD et MLflow

Deux questions pratiques se posent sur l'alerting :

**Flask-Monitoring-Dashboard** surveille les performances des _endpoints HTTP_ (temps de reponse, outliers, volumetrie). Il ne fait pas d'alerting sur des metriques metier comme l'accuracy du modele. C'est un outil d'observabilite infrastructure, pas un systeme d'alerte conditionnelle.

**MLflow** est un outil de _tracking_ : il enregistre les metriques pour les visualiser dans son interface graphique. Il ne pousse pas de notifications et ne configure pas de seuils d'alerte automatiques en mode local.

**Ce qui est reellement implemente pour l'alerting** :

1. Alertes dans les fichiers de logs (`CRITICAL`, `WARNING`) emises par `app.logger` a chaque evaluation — deja en place en section 3.3.
2. **Historique en memoire** : une liste `ALERT_HISTORY` enregistre chaque declenchement d'alerte (horodatage, niveau, accuracy, nombre de feedbacks, message).
3. **Endpoint `/alerts`** (GET) : expose l'historique des 50 dernieres alertes au format JSON, consultable par tout outil externe.
4. **Run MLflow de type `alert`** : chaque alerte declenche aussi un run MLflow avec les metriques `level`, `accuracy`, `feedback_count`, ce qui permet de visualiser les evenements d'alerte dans la timeline MLflow.

Cette combinaison constitue un dispositif d'alerting complet a l'echelle du livrable E5 : observable en temps reel via `/alerts`, persistee dans MLflow, et tracee dans les fichiers rotatifs.

### 3.7 Synthese des outils de monitoring

| Couche | Outil | Point d'acces | Usage C20 |
|--------|-------|---------------|-----------|
| Endpoints Flask | Flask-Monitoring-Dashboard | `/dashboard/` | Temps de reponse, outliers, volumetrie |
| Metriques modele | MLflow | `mlflow ui` (port 5001) | Accuracy, drift, versioning des runs |
| Alertes applicatives | Logging rotatif + ALERT_HISTORY | `logs/app.log`, `/alerts` | CRITICAL/WARNING proactifs + historique JSON |
| Etat synthetique | Route custom | `/health` (JSON) | Healthcheck pour outils externes |
| Vue d'ensemble | Route custom | `/monitoring` (HTML) | Synthese avec alertes et liens vers dashboards |
| Reentrainement | Routes custom + retrain.py | `/retrain/status`, `/retrain/export` | Circuit feedback → export → fine-tuning |


## 4. Feedback loop et persistance des donnees (C20)

### 4.1 Principe retenu

La feedback loop a ete implementee de facon fonctionnelle. Lorsque l'utilisateur obtient une prediction, l'application affiche les quatre classes possibles sous forme de boutons. L'utilisateur peut alors confirmer ou corriger la prediction. Le feedback est enregistre en base SQLite et les statistiques sont mises a jour en temps reel sur `/health` et `/monitoring`.

Chaque feedback declenche egalement un enregistrement dans MLflow (accuracy courante, indicateur is_correct, confiance) ce qui permet de tracer l'evolution de la qualite du modele au fil du temps.

### 4.5 Boucle de reentrainement (circuit complet)

Lorsque l'accuracy chute en dessous du seuil critique, un reentrainement est rendu possible via deux mecanismes :

**Routes d'activation :**

- `GET /retrain/status` : retourne un JSON indiquant si le reentrainement est recommande, avec le nombre de feedbacks disponibles et l'accuracy courante.
- `POST /retrain/export` : declenche l'export de tous les feedbacks corriges au format JSON (`retraining_data.json`). Logue un evenement `retrain_trigger` dans MLflow.

**Script `retrain.py` :**

Un script independant `retrain.py` realise le fine-tuning du modele a partir des feedbacks exportes :

1. Chargement de `retraining_data.json` (images en base64 + label corrige par l'utilisateur).
2. Decodage des images, redimensionnement a 224x224, normalisation.
3. Gel des couches profondes du CNN (toutes sauf les 4 dernieres).
4. Fine-tuning : 5 epochs avec Adam lr=1e-4, batch_size=8.
5. Sauvegarde de la nouvelle version : `models/retrained_<timestamp>.keras`.
6. Log complet dans MLflow (experience `satellite-retraining`) : parametres, accuracy finale, chemin du modele.

```powershell
# Etape 1 : exporter les feedbacks
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:5000/retrain/export

# Etape 2 : lancer le fine-tuning
python retrain.py --min-feedback 10
```

Le circuit complet (feedback utilisateur → export → fine-tuning → nouveau modele) est documente en Appendice E.

### 4.2 Donnees stockees

Chaque feedback sauvegarde dans SQLite contient : image_filename, image_data_url, predicted_label, user_label, confidence_score, timestamp, is_correct et model_version.

### 4.3 Choix de SQLite

SQLite a ete retenu car il offre : aucun service externe a installer, integration native Python, persistance locale facilement demonstrable. En production, une base relationnelle geree serait plus adaptee.

### 4.4 Donnees personnelles et minimisation

Le stockage de l'image en Data URL est encadre par des regles de minimisation conformes au RGPD : duree de conservation limitee, acces reserve, usage exclusivement lie a l'amelioration du modele.

## 5. CI/CD et qualite logicielle

### 5.1 Architecture de la pipeline

Une pipeline GitHub Actions (.github/workflows/ci.yml) est organisee en deux jobs sequentiels : lint (flake8) puis tests (pytest + pytest-cov). Le job tests ne demarre que si le lint passe.

### 5.2 Dependances allegees pour la CI

Un fichier requirements-test.txt inclut flask-monitoringdashboard et mlflow (necessaires a l'import) mais exclut PyTorch et Keras car le modele est mocke dans les tests.

### 5.3 Couverture de code

| Module | Stmts | Miss | Cover |
|--------|-------|------|-------|
| app.py | 120 | 12 | 90% |
| database_models.py | 93 | 25 | 73% |
| logging_config.py | 39 | 1 | 97% |
| **Total** | **252** | **38** | **85%** |

### 5.4 Garde-fou contre la regression
Le FakeModel contient l'assertion img_array.shape == (1, 224, 224, 3) : si le bug reapparait, le test echoue et la CI bloque le merge.

## 6. Couverture des competences C20 et C21

### 6.1 Couverture C21

- identification correcte de la cause racine ;
- reproduction du bug en environnement de developpement ;
- correctif minimal applique sur le pretraitement ;
- documentation de la resolution via issue GitHub et pull request ;
- mise en place de tests de non-regression ;
- solution versionnee dans le depot Git (merge request).

### 6.2 Couverture C20

- journalisation structuree avec rotation des fichiers ;
- logs de prediction et de feedback ;
- point `/health` pour etat synthetique de service ;
- tableau de bord `/monitoring` pour l'exploitation locale ;
- monitoring des endpoints via Flask-Monitoring-Dashboard (`/dashboard/`) ;
- tracking MLOps via MLflow (predictions, feedbacks, accuracy, drift, alertes) ;
- definition de metriques et seuils ;
- alertes proactives (CRITICAL/WARNING) emises automatiquement dans les logs, dans `ALERT_HISTORY`, et dans MLflow via un run `alert` ;
- endpoint `/alerts` expusant l'historique des alertes en JSON ;
- feedback loop persistee en SQLite et tracee dans MLflow ;
- boucle de reentrainement : `/retrain/status`, `/retrain/export`, script `retrain.py`.

## Conclusion

L'incident principal a ete identifie a la racine, corrige de facon minimale, documente depuis l'outil de suivi GitHub (issue + PR), puis securise par 19 tests verts et une pipeline CI. L'application a gagne en observabilite grace a une journalisation structuree, des alertes proactives (logs + `/alerts` JSON + runs MLflow), un monitoring des endpoints (Flask-Monitoring-Dashboard) et un tracking MLOps complet (MLflow). La feedback loop persiste les corrections utilisateur en SQLite, alimente le suivi MLflow et declenche au besoin un circuit de reentrainement (`/retrain/status`, `/retrain/export`, `retrain.py`).

## Liste documentaire

- Annexe 1 : matrice de couverture C20/C21 ;
- Annexe 2 : procedure de lancement local et demonstration ;
- Annexe 3 : workflow GitHub Actions ;
- Annexe 4 : issue GitHub et pull request (captures d'ecran) ;
- Appendice A : traceback type de l'incident ;
- Appendice B : schema et logique de la feedback loop SQLite ;
- Appendice C : integration Flask-Monitoring-Dashboard ;
- Appendice D : integration MLflow tracking ;
- Appendice E : boucle de reentrainement (circuit complet).