# Appendice C — Integration Flask-Monitoring-Dashboard

Cet appendice doit etre lu avec le rapport principal (section 3.5).
Il documente les details techniques de l'integration de Flask-Monitoring-Dashboard.

## Objectif

Surveiller automatiquement les performances des routes Flask sans
developpement supplementaire. Cet outil repond au critere C20 qui exige
des « outils de surveillance operationnels ».

## Integration dans le code

L'integration se fait dans `app.py` apres la creation de l'instance Flask :

```python
import flask_monitoringdashboard as monitor_dashboard
monitor_dashboard.bind(app)
```

Ces deux lignes suffisent a :

- enregistrer la route `/dashboard/` dans l'application Flask ;
- instrumenter automatiquement toutes les routes existantes ;
- stocker les metriques dans une base SQLite locale (`flask_monitoringdashboard.db`).

## Fonctionnalites exposees

Le dashboard accessible a `http://127.0.0.1:5000/dashboard/` fournit :

| Fonctionnalite | Description |
|----------------|-------------|
| Overview | Vue synoptique de toutes les routes avec statut |
| Endpoint details | Temps de reponse moyen, median, P95 par route |
| Request count | Nombre de requetes par endpoint et par periode |
| Outlier detection | Identification des requetes anormalement lentes |
| Timeline | Evolution temporelle des performances |

## Routes surveillees

Les routes suivantes sont automatiquement instrumentees :

| Route | Methode | Role |
|-------|---------|------|
| `/` | GET | Page d'upload |
| `/predict` | POST | Classification d'image |
| `/feedback` | GET/POST | Collecte feedback utilisateur |
| `/health` | GET | Healthcheck JSON |
| `/monitoring` | GET | Dashboard metier |

## Verification par test

Le test `test_flask_monitoring_dashboard_bound` verifie que la route
`/dashboard/` est bien enregistree dans l'application Flask :

```python
def test_flask_monitoring_dashboard_bound(self):
    rules = [rule.rule for rule in app_module.app.url_map.iter_rules()]
    self.assertIn("/dashboard/", rules)
```

## Dependance

`flask-monitoringdashboard` (pip installable, aucune configuration YAML requise)