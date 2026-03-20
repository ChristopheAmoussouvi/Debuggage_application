# Annexe 4 — Issue GitHub et Pull Request

Cette annexe est autonome. Elle documente le workflow de suivi d'incident
via GitHub Issues et Pull Request, conformement au critere C21.

## Issue GitHub

**Titre** : Bug: crash sur images ≠ 224×224 — ValueError shape incompatible

**Contenu de l'issue** :

1. **Symptome** : la route `/predict` plante avec `ValueError` lorsqu'une image
   de dimensions differentes de 224×224 est soumise.
2. **Traceback** : voir Appendice A.
3. **Reproduction** : soumettre une image 600×600, 1024×768 ou 3000×2000.
4. **Cause racine** : la fonction de pretraitement ne redimensionne pas l'image
   avant de la transmettre au modele CNN.
5. **Impact** : toute image utilisateur hors 224×224 produit un crash HTTP 500.

> *Inserer ici la capture d'ecran de l'issue GitHub ouverte.*

## Pull Request

**Titre** : Fix: redimensionnement systematique dans preprocess_from_pil()

**Branche** : `fix/resize-224x224` → `main`

**Contenu de la PR** :

1. Ajout de `img.resize((224, 224), Image.Resampling.LANCZOS)` dans
   `preprocess_from_pil()`.
2. Chargement paresseux du modele via `get_model()` avec `@lru_cache`.
3. 16 tests de non-regression (dont assertion shape dans FakeModel).
4. CI verte : flake8 0 erreur, pytest 16 passed, couverture 85%.

**Statut** : mergee dans `main` apres validation CI.

> *Inserer ici la capture d'ecran de la PR mergee avec le badge CI vert.*

## Workflow suivi

```mermaid
flowchart LR
    A[Issue ouverte] --> B[Branche fix/resize-224x224]
    B --> C[Correctif + tests]
    C --> D[Push + CI verte]
    D --> E[Pull Request]
    E --> F[Review + merge]
    F --> G[Issue fermee]

Ce workflow issue → branche → PR → CI → merge repond au critere C21 :
« la procedure de debogage du code est documentee depuis l'outil de suivi »
et « la solution est versionnee dans le depot Git du projet ».