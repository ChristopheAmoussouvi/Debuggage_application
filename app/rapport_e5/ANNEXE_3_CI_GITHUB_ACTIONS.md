# Annexe 3 — Workflow GitHub Actions (CI)

Cette annexe est autonome. Elle documente la logique de CI retenue pour le projet et les choix techniques associes.

## Objectif

La CI a pour objectif d'empecher l'integration d'un changement qui casserait :

1. le correctif du bug `224x224` ;
2. la feedback loop SQLite ;
3. les routes critiques de l'application Flask ;
4. la qualite minimale du code (lint).

## Architecture du workflow

Le workflow est compose de **deux jobs separes** :

1. **lint** — verification flake8 de la qualite du code ;
2. **tests** — execution de la suite pytest avec mesure de couverture.

Le job `tests` ne demarre que si le job `lint` passe (`needs: lint`). Cette separation permet d'obtenir un retour rapide sur les erreurs de syntaxe avant de lancer les tests plus longs.

## Fichier requirements-test.txt

Un fichier de dependances dedie a ete cree pour la CI. Il exclut volontairement PyTorch et Keras (~2 Go) car :

- le modele est mocke dans les tests via `FakeModel` ;
- le chargement reel du modele est differe via `get_model()` avec `@lru_cache` ;
- cela reduit le temps d'installation CI de plusieurs minutes a quelques secondes.

```
flask==3.0.3
flask-monitoringdashboard==3.1.1
mlflow==2.14.3
numpy==1.26.4
pillow==10.4.0
werkzeug==3.0.4
pytest==8.3.2
pytest-cov==5.0.0
flake8==7.1.1
```

## Configuration flake8

Un fichier `.flake8` a la racine du projet definit :

- `max-line-length = 120` ;
- exclusion des dossiers non pertinents (`__pycache__`, `htmlcov`, `models`) ;
- autorisation de E402 sur app.py uniquement (les imports sont places apres os.environ['KERAS_BACKEND'] pour forcer le backend PyTorch avant tout import de Keras).

## Workflow complet

```yaml
name: CI – Tests de non-regression E5

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    name: Lint (flake8)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./app
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: app/requirements-test.txt

      - name: Install test dependencies
        run: pip install -r requirements-test.txt

      - name: Flake8 – verification qualite
        run: flake8 --count --show-source --statistics

  tests:
    name: Tests de regression (pytest + coverage)
    needs: lint
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./app
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: app/requirements-test.txt

      - name: Install test dependencies
        run: pip install -r requirements-test.txt

      - name: Run pytest with coverage
        run: |
          python -m pytest test_app.py -v \
            --tb=short \
            -p pytest_cov \
            --cov=app \
            --cov=database_models \
            --cov=logging_config \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-fail-under=60

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: app/htmlcov/
          retention-days: 14
```

## Resultats obtenus en local

La CI a ete validee localement sous Windows (PowerShell, Python 3.12, Conda) :

- **flake8** : 0 erreur, 0 warning ;
- **pytest** : 14 tests passes ;
- **couverture** : 85% globale (seuil minimal fixe a 60%).

```
Name                 Stmts   Miss  Cover   Missing
--------------------------------------------------
app.py                 108     10    91%   47-49, 126, 128, 218-220, 237-242, 306
database_models.py      93     25    73%   135-137, 175-176, 225-227, 239-261, 266, 271-276
logging_config.py       39      1    97%   72
--------------------------------------------------
TOTAL                  240     36    85%
```

## Choix du seuil de couverture a 60%

Le seuil `--cov-fail-under=60` a ete fixe volontairement bas pour deux raisons :

1. certaines branches de `database_models.py` concernent l'export CSV et des cas d'erreur difficilement simulables en test unitaire ;
2. un seuil trop eleve dans un contexte pedagogique risque de bloquer la CI pour des raisons non liees a la regression ciblee.

Le seuil actuel (85% atteint) depasse largement le minimum fixe. En production, il serait pertinent de le relever progressivement a 75% puis 80%.

## Upload de l'artefact de couverture

Le rapport HTML de couverture est uploade comme artefact GitHub Actions (`coverage-report`), conserve 14 jours. Cela permet a tout relecteur de consulter visuellement les lignes couvertes et non couvertes sans re-executer les tests.

## Interet pour le livrable E5

Cette CI repond au critere C21 de prevention de la regression : tout push ou pull request declenche automatiquement le lint et les tests. Si le bug `224x224` reapparaissait, le `FakeModel` dont l'assertion `img_array.shape == (1, 224, 224, 3)` echouerait immediatement et la CI bloquerait l'integration.