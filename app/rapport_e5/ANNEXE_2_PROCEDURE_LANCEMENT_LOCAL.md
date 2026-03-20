# Annexe 2 - Procedure de lancement local sous Windows et PowerShell

Cette annexe est autonome. Elle decrit une procedure de demonstration locale complete.

## Prerequis

1. Windows avec PowerShell.
2. Python 3.11 ou 3.12.
3. Keras 3.x avec backend PyTorch (`torch`).
4. Les dependances du fichier `requirements.txt` installees dans l'environnement de travail.

## Lancement de l'application

Depuis PowerShell :

```powershell
Set-Location "c:\Users\Utilisateur\Documents\Simplon - 2025\Bertrand-Debuggage-application-15092025\app"
python app.py
```

Puis ouvrir :

1. `http://127.0.0.1:5000/` pour l'application ;
2. `http://127.0.0.1:5000/health` pour l'etat JSON ;
3. `http://127.0.0.1:5000/monitoring` pour le tableau de bord local.

## Lancement des tests

Sous PowerShell, avec un environnement Conda charge par VS Code, la commande suivante permet d'eviter les plugins pytest parasites :

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest test_app.py -q
```

Resultat attendu :

```text
19 passed
```

## Demonstration conseillee devant le jury

1. Uploader une image de taille superieure a `224x224`.
2. Montrer que la prediction s'affiche sans erreur.
3. Cliquer sur un bouton de feedback.
4. Ouvrir `/monitoring` pour montrer la mise a jour des statistiques.
5. Ouvrir `http://127.0.0.1:5000/dashboard/` pour montrer le tableau de bord Flask-Monitoring-Dashboard (temps de reponse par route, volumetrie).
6. Dans un second terminal PowerShell, lancer MLflow UI :

```powershell
cd "c:\Users\Utilisateur\Documents\Simplon - 2025\Bertrand-Debuggage-application-15092025\app"
mlflow ui --backend-store-uri mlruns/ --port 5001
```

7. Ouvrir `http://127.0.0.1:5001`, filtrer par `feedback` et montrer l'evolution de l'accuracy.
8. Soumettre plusieurs feedbacks incorrects et ouvrir `logs\app.log` pour montrer la ligne `CRITICAL Accuracy dropped below 60%`.
9. Lancer les tests depuis PowerShell et montrer `19 passed` :

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest test_app.py -q
```

10. Consulter `http://127.0.0.1:5000/alerts` pour voir l'historique JSON des alertes.
11. Consulter `http://127.0.0.1:5000/retrain/status` pour verifier si un reentrainement est conseille.
12. Declencher l'export pour reentrainement :

```powershell
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:5000/retrain/export
```

Puis, si le reentrainement est confirme, lancer le fine-tuning du modele :

```powershell
python retrain.py --min-feedback 10
```

## Consultation des dashboards

1. **Flask-Monitoring-Dashboard** : ouvrir `http://127.0.0.1:5000/dashboard/`
   apres le lancement de l'application.

2. **MLflow UI** (dans un second terminal) :

```powershell
cd "c:\Users\Utilisateur\Documents\Simplon - 2025\Bertrand-Debuggage-application-15092025\app"
mlflow ui --backend-store-uri mlruns/ --port 5001
```