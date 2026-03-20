#!/usr/bin/env python3
"""
Script de reentrainement (fine-tuning) base sur les feedbacks utilisateur.

Prerequis :
  - Avoir exporte les feedbacks via POST /retrain/export
    (cela cree retraining_data.json dans le dossier app/)
  - Avoir installe torch, keras, pillow, mlflow

Usage :
  python retrain.py
  python retrain.py --min-feedback 20 --output models/retrained_v2.keras

Principe :
  1. Charge retraining_data.json (genere par FeedbackDatabase.export_for_retraining).
  2. Decode les images base64, les redimensionne a 224x224.
  3. Charge le modele CNN existant (final_cnn.keras).
  4. Gele toutes les couches sauf les 4 dernieres (fine-tuning leger).
  5. Reentrainement sur 5 epochs avec Adam lr=1e-4.
  6. Sauvegarde de la nouvelle version du modele.
  7. Log de l'experience dans MLflow (experience satellite-retraining).
"""

import argparse
import base64
import io
import json
import os
from datetime import datetime

import mlflow
import numpy as np
from PIL import Image

# ---------------- Constantes ----------------
os.environ["KERAS_BACKEND"] = "torch"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_EXPORT_PATH = os.path.join(BASE_DIR, "retraining_data.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "final_cnn.keras")
CLASSES = ["desert", "forest", "meadow", "mountain"]
MIN_FEEDBACK_DEFAULT = 10


# ---------------- Chargement du modele ----------------
def _load_model(model_path: str):
    """Charge le modele Keras en appliquant le monkey-patch RandomContrast."""
    import keras
    from keras.layers import RandomContrast

    _orig = RandomContrast.__init__

    def _patched(self, **kwargs):
        kwargs.pop("value_range", None)
        _orig(self, **kwargs)

    RandomContrast.__init__ = _patched
    try:
        model = keras.saving.load_model(model_path, compile=False)
    finally:
        RandomContrast.__init__ = _orig
    return model


# ---------------- Preparation des donnees ----------------
def load_feedback_data(export_path: str) -> tuple:
    """
    Charge le fichier JSON exporte et retourne (X, y).

    X : array float32 de forme (N, 224, 224, 3) normalise [0, 1]
    y : array int de classe (index dans CLASSES)
    """
    if not os.path.exists(export_path):
        raise FileNotFoundError(
            f"Fichier d'export introuvable : {export_path}\n"
            "Lancer d'abord : POST /retrain/export"
        )

    with open(export_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        raise ValueError("Aucune donnee de feedback dans le fichier d'export.")

    X, y = [], []
    skipped = 0
    for rec in records:
        label = rec.get("true_label", "")
        if label not in CLASSES:
            skipped += 1
            continue
        try:
            _, b64data = rec["image_data_url"].split(",", 1)
            img_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img = img.resize((224, 224), Image.Resampling.LANCZOS)
            arr = np.asarray(img, dtype=np.float32) / 255.0
            X.append(arr)
            y.append(CLASSES.index(label))
        except Exception as exc:  # noqa: BLE001
            print(f"  Image ignoree (decodage impossible) : {exc}")
            skipped += 1

    print(f"  {len(X)} echantillons charges, {skipped} ignores.")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


# ---------------- Fine-tuning ----------------
def retrain(
    min_feedback: int = MIN_FEEDBACK_DEFAULT,
    output_path: str | None = None,
) -> bool:
    """
    Lance le fine-tuning si le nombre de feedbacks est suffisant.

    Returns:
        True si le reentrainement a ete effectue, False sinon.
    """
    import keras

    print("=== Demarrage du reentrainement ===")

    # 1. Charger les donnees
    X, y = load_feedback_data(FEEDBACK_EXPORT_PATH)

    if len(X) < min_feedback:
        print(
            f"  Pas assez de feedbacks ({len(X)} < {min_feedback})."
            " Reentrainement annule."
        )
        return False

    # 2. Encoder les cibles en one-hot
    y_onehot = keras.utils.to_categorical(y, num_classes=len(CLASSES))

    # 3. Charger le modele de base
    print(f"  Chargement du modele : {MODEL_PATH}")
    model = _load_model(MODEL_PATH)

    # 4. Geler les couches profondes, fine-tuner uniquement les 4 dernieres
    n_frozen = max(0, len(model.layers) - 4)
    for layer in model.layers[:n_frozen]:
        layer.trainable = False
    trainable_layers = [l.name for l in model.layers if l.trainable]
    print(f"  Couches entrainables : {trainable_layers}")

    # 5. Compilation et entrainement
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    # 6. Tracking MLflow
        mlflow.set_tracking_uri(f"sqlite:///{os.path.join(BASE_DIR, 'mlflow.db')}")

    with mlflow.start_run(run_name="fine-tuning"):
        mlflow.log_param("n_samples", len(X))
        mlflow.log_param("n_frozen_layers", n_frozen)
        mlflow.log_param("learning_rate", 1e-4)
        mlflow.log_param("epochs", 5)
        mlflow.log_param("batch_size", 8)
        mlflow.log_param("source_model", MODEL_PATH)

        history = model.fit(
            X,
            y_onehot,
            epochs=5,
            batch_size=8,
            validation_split=0.2,
            verbose=1,
        )

        final_train_acc = history.history["accuracy"][-1]
        final_val_acc = history.history.get("val_accuracy", [None])[-1]
        mlflow.log_metric("final_train_accuracy", final_train_acc)
        if final_val_acc is not None:
            mlflow.log_metric("final_val_accuracy", final_val_acc)

        # 7. Sauvegarde du modele
        if output_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(BASE_DIR, "models", f"retrained_{stamp}.keras")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        model.save(output_path)
        mlflow.log_param("output_model", output_path)
        print(f"  Modele sauvegarde : {output_path}")
        print(f"  Train accuracy finale : {final_train_acc:.3f}")

    return True



# ---------------- Entree principale ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reentrainer le modele CNN a partir des feedbacks utilisateur."
    )
    parser.add_argument(
        "--min-feedback",
        type=int,
        default=MIN_FEEDBACK_DEFAULT,
        help=f"Nombre minimum de feedbacks requis (defaut : {MIN_FEEDBACK_DEFAULT})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Chemin de sauvegarde du modele reentrainement (defaut : models/retrained_<timestamp>.keras)",
    )
    args = parser.parse_args()

    success = retrain(min_feedback=args.min_feedback, output_path=args.output)
    if not success:
        raise SystemExit(1)
