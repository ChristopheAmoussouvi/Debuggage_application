# Appendice D — Integration MLflow Tracking

Cet appendice doit etre lu avec le rapport principal (section 3.6).
Il documente les details techniques de l'integration de MLflow.

## Objectif

Tracer chaque prediction et chaque feedback dans un systeme de tracking
MLOps pour permettre la detection de derive du modele et preparer un
eventuel reentrainement. Cet outil repond au critere C20 qui exige
une « feedback loop dans une approche MLOps ».

## Configuration dans le code

Dans `app.py`, la configuration MLflow est effectuee au demarrage :

```python
import mlflow

MLFLOW_TRACKING_DIR = os.path.join(BASE_DIR, "mlruns")
mlflow.set_tracking_uri(f"file://{MLFLOW_TRACKING_DIR}")
mlflow.set_experiment("satellite-classification")
```
Le tracking est stocke localement dans le repertoire `mlruns/` sous forme
de fichiers — aucun serveur externe n'est necessaire.

## Fonction de logging

La fonction `log_to_mlflow()` cree un run MLflow pour chaque evenement :

```python
def log_to_mlflow(event: str, **params):
    """Enregistre un evenement dans MLflow."""
    try:
        with mlflow.start_run(run_name=event, nested=True):
            for key, value in params.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)
                else:
                    mlflow.log_param(key, str(value))
    except Exception:
        app.logger.debug("MLflow logging skipped (server unavailable)")
```

Le `try/except` garantit que l'application ne plante pas si MLflow
rencontre une erreur — le logging est non-bloquant.

## Evenements traces

### Prediction

Appele dans la route `/predict` apres chaque inference reussie :

```python
log_to_mlflow(
    "prediction",
    predicted_label=label,      # param: classe predite
    confidence=conf,            # metric: score de confiance
    filename=image_filename,    # param: nom du fichier
)
```

### Feedback

Appele dans la route `/feedback` apres chaque soumission :

```python
log_to_mlflow(
    "feedback",
    predicted_label=predicted_label,  # param
    user_label=user_feedback,         # param
    confidence=confidence,            # metric
    is_correct=float(...),            # metric: 1.0 ou 0.0
    accuracy=snapshot["accuracy"],    # metric: accuracy courante
    feedback_count=snapshot[...],     # metric: nombre de feedbacks
)
```

## Schema des donnees MLflow

| Champ | Type MLflow | Exemple |
|-------|-------------|----------|
| `predicted_label` | param | `"meadow"` |
| `user_label` | param | `"forest"` |
| `filename` | param | `"satellite.jpg"` |
| `confidence` | metric | `0.975` |
| `is_correct` | metric | `0.0` |
| `accuracy` | metric | `66.7` |
| `feedback_count` | metric | `3` |

## Consultation du tracking

```powershell
cd app
mlflow ui --backend-store-uri mlruns/ --port 5001
```

Puis ouvrir `http://127.0.0.1:5001`. L'interface permet de :

- voir la liste des runs (un par prediction, un par feedback) ;
- filtrer par `run_name` (`prediction` ou `feedback`) ;
- visualiser l'evolution de `accuracy` au fil des feedbacks ;
- comparer des runs pour detecter une eventuelle derive.
## Verification par test

Les tests `test_predict_success_uses_resized_input` et
`test_feedback_post_persists_sqlite_record` mockent `log_to_mlflow`
et verifient qu'il est appele :

```python
@patch.object(app_module, "log_to_mlflow")
def test_predict_success_uses_resized_input(self, mock_mlflow):
    # ... test de prediction ...
    mock_mlflow.assert_called_once()
```

## Signal de reentrainement

Lorsque la metrique `accuracy` chute sous le seuil critique (60 %),
deux mecanismes se declenchent simultanement :

- Log proactif : `app.logger.critical(...)` dans les fichiers rotatifs ;
- Run MLflow : la metrique `accuracy` est enregistree, permettant
  de visualiser la chute dans l'interface graphique MLflow.

La decision de reentrainer est prise par l'operateur en consultant
l'interface MLflow et en observant la tendance des feedbacks sur la
duree. Les donnees de reentrainement peuvent etre exportees depuis
SQLite via `export_for_retraining()` (voir Appendice B).
