# Annexe 1 - Matrice de couverture C20 et C21

Cette annexe peut etre lue seule. Elle synthétise la correspondance entre les attendus du referentiel et les elements effectivement implementes.

## C21 - Resolution d'incident

| Attendu referentiel | Couverture dans le projet |
| --- | --- |
| Cause du probleme identifiee | Bug de shape entre images utilisateur et entree modele `224x224` |
| Probleme reproduit en environnement de dev | Reproduction avec images `600x600`, `1024x768`, `3000x2000` |
| Procedure de debogage documentee depuis l'outil de suivi | Issue GitHub « Bug: crash sur images ≠ 224×224 » avec traceback et etapes de reproduction |
| Solution explicitee etape par etape | Redimensionnement impose dans `preprocess_from_pil()` |
| Solution versionnee dans le depot Git | PR « Fix: redimensionnement systematique » → merge dans `main` |
| Tests anti-regression | `test_app.py`, 19 tests verts, FakeModel avec assertion shape |

## C20 - Surveillance d'application

| Attendu referentiel | Couverture dans le projet |
| --- | --- |
| Metriques et seuils listes | Accuracy (75%/60%), volume de feedback (20), distribution des classes |
| Choix techniques justifies | Logging rotatif, SQLite, dashboard local HTML, Keras + PyTorch backend |
| Outils operationnels en local | `/health` JSON, `/monitoring` HTML, logs dans `logs/` |
| Outils de surveillance operationnels | Flask-Monitoring-Dashboard (`/dashboard/`), MLflow tracking (`mlruns/`), `/health`, `/monitoring` |
| Journalisation integree au code | `logging_config.py` : app.log, error.log, predictions.log |
| Alertes configurees et en etat de marche | Alertes proactives CRITICAL/WARNING emises dans les logs a chaque feedback |
| Feedback loop alimentee | Enregistrement image + prediction + label utilisateur en SQLite |
| Suivi MLOps des metriques du modele | MLflow log chaque prediction et feedback (accuracy, confidence, is_correct) |

## Points de demonstration orale conseilles

1. Montrer l'issue GitHub et la PR mergee.
2. Montrer une image de grande taille et expliquer pourquoi le bug se produisait.
3. Ouvrir `test_app.py` et montrer le test qui verifie la forme `(1, 224, 224, 3)`.
4. Lancer l'application puis visiter `/monitoring`.
5. Soumettre plusieurs feedbacks incorrects et montrer l'alerte CRITICAL dans `logs/app.log`.
6. Visiter `/monitoring` pour montrer le statut rouge « critical ».
7. Ouvrir `/dashboard/` pour montrer les metriques de performance Flask-Monitoring-Dashboard.
8. Dans un second terminal, lancer `mlflow ui --backend-store-uri mlruns/ --port 5001` puis ouvrir `http://127.0.0.1:5001` pour visualiser l'historique des runs.
9. Dans MLflow UI, filtrer par `feedback` et montrer l'evolution de l'accuracy au fil des soumissions.
10. Consulter `/alerts` pour montrer l'historique des alertes emises en JSON.
11. Consulter `/retrain/status` pour montrer l'indicateur `retraining_needed`.
12. Declencher `POST /retrain/export` et montrer le fichier `retraining_data.json` genere.