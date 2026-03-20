# Changelog — Application Flask Classification Satellite

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [1.1.0] — 2026-03-20

### Corrigé (C21 — Résolution d'incident)

- **Bug critique** : `preprocess_from_pil()` ne redimensionnait pas l'image avant l'inférence.
  Toute image hors 224×224 px provoquait un `ValueError` (incompatibilité de shape avec le CNN).
  **Correctif** : ajout de `img.resize((224, 224), Image.Resampling.LANCZOS)`.

- **Windows / MLflow** : URI `file://C:\...` interprétée comme schéma `c:` → `KeyError`.
  **Correctif** : migration vers `sqlite:///mlflow.db` dans `app.py` et `retrain.py`.

- **HTTP 413** : image haute résolution encodée en base64 dépassait la limite de 16 Mo.
  **Correctif** : thumbnail 224×224 utilisé pour le data URL du formulaire de feedback.

- **Flask-MonitoringDashboard** : `OSError: [Errno 22]` sur Windows (timestamp epoch 0).
  **Correctif** : patch `_safe_fromtimestamp()` dans `views/deployment.py`.

- **Flask-MonitoringDashboard** : aucune métrique enregistrée (`monitor_level=0`).
  **Correctif** : `fmd_config.cfg` avec `MONITOR_LEVEL=3` ; `bind()` déplacé après les routes.

### Ajouté (C20 — Surveillance)

- Feedback loop SQLite (`database_models.py`) + export JSON pour réentraînement
- Endpoints `/health`, `/monitoring`, `/alerts`, `/retrain/status`, `/retrain/export`
- Historique des alertes en mémoire (`ALERT_HISTORY`)
- Script de réentraînement `retrain.py` (fine-tuning MLflow)
- Pipeline CI/CD GitHub Actions (lint flake8 + pytest + coverage)

---

## [1.0.0] — 2025-10-04

### Initial

- Application Flask de classification d'images satellite (4 classes : desert, forest, meadow, mountain)
- Modèle CNN `final_cnn.keras` (PyTorch backend via Keras)
- Route `/predict` — upload et inférence
- Journalisation structurée (`logging_config.py`)
