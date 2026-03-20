import os
import io
import base64
import logging
from datetime import datetime as _dt
from functools import lru_cache

# Configuration du backend Keras : le modele a ete entraine avec PyTorch
os.environ['KERAS_BACKEND'] = 'torch'

from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename

import numpy as np
import mlflow

from PIL import Image

from database_models import Feedback, FeedbackDatabase
from logging_config import setup_logging, setup_monitoring_alerts

# ---------------- Config ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}
CLASSES = ['desert', 'forest', 'meadow', 'mountain']
MODEL_PATH = os.path.join(BASE_DIR, "models", "final_cnn.keras")
DATABASE_PATH = os.path.join(BASE_DIR, "feedback.db")
MLFLOW_TRACKING_DIR = os.path.join(BASE_DIR, "mlruns")
MONITORING_THRESHOLDS = {
    "feedback_volume_warning": 20,
    "accuracy_warning": 75.0,
    "accuracy_critical": 60.0,
}
MIN_FEEDBACKS_FOR_RETRAIN = 10

# Historique des alertes en memoire (persistance volatile, se remet a zero au redemarrage)
ALERT_HISTORY: list = []
_MAX_ALERT_HISTORY = 50

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

prediction_logger = setup_logging(app, logging.INFO)
setup_monitoring_alerts(app)
feedback_db = FeedbackDatabase(DATABASE_PATH)

# ---------------- Flask-Monitoring-Dashboard (config seulement - bind() apres les routes) ----------------
import flask_monitoringdashboard as monitor_dashboard
_FMD_CONFIG = os.path.join(BASE_DIR, "fmd_config.cfg")
monitor_dashboard.config.init_from(file=_FMD_CONFIG)

# ---------------- MLflow ----------------
MLFLOW_DB_URI = f"sqlite:///{os.path.join(BASE_DIR, 'mlflow.db')}"
mlflow.set_tracking_uri(MLFLOW_DB_URI)
mlflow.set_experiment("satellite-classification")


@lru_cache(maxsize=1)
def get_model():
    """Charge le modele Keras uniquement au premier besoin."""
    import keras
    from keras.layers import RandomContrast

    _original_init = RandomContrast.__init__

    def _patched_init(self, **kwargs):
        kwargs.pop('value_range', None)
        _original_init(self, **kwargs)

    RandomContrast.__init__ = _patched_init
    try:
        model = keras.saving.load_model(MODEL_PATH, compile=False)
    finally:
        RandomContrast.__init__ = _original_init

    return model


# ---------------- Utils ----------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def to_data_url(pil_img: Image.Image, fmt="JPEG") -> str:
    buffer = io.BytesIO()
    pil_img.save(buffer, format=fmt)
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/jpeg" if fmt.upper() == "JPEG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{b64}"


def preprocess_from_pil(pil_img: Image.Image) -> np.ndarray:
    img = pil_img.convert("RGB")
    img = img.resize((224, 224), Image.Resampling.LANCZOS)
    img_array = np.asarray(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def build_monitoring_snapshot() -> dict:
    """Construit un instantane et declenche des alertes proactives si necessaire."""
    stats = feedback_db.get_statistics()
    total_feedbacks = stats.get("total_feedbacks", 0)
    accuracy = stats.get("accuracy", 0.0)

    if accuracy <= MONITORING_THRESHOLDS["accuracy_critical"] and total_feedbacks > 0:
        service_status = "critical"
        app.logger.critical(
            "ALERTE CRITIQUE: accuracy=%.1f%% (seuil=%.1f%%) sur %d feedbacks"
            " — reentrainement recommande",
            accuracy,
            MONITORING_THRESHOLDS["accuracy_critical"],
            total_feedbacks,
        )
        _record_alert("critical", accuracy, total_feedbacks)
    elif accuracy <= MONITORING_THRESHOLDS["accuracy_warning"] and total_feedbacks > 0:
        service_status = "warning"
        app.logger.warning(
            "ALERTE WARNING: accuracy=%.1f%% (seuil=%.1f%%) sur %d feedbacks",
            accuracy,
            MONITORING_THRESHOLDS["accuracy_warning"],
            total_feedbacks,
        )
        _record_alert("warning", accuracy, total_feedbacks)
    else:
        service_status = "healthy"

    return {
        "service_status": service_status,
        "model_path": MODEL_PATH,
        "model_exists": os.path.exists(MODEL_PATH),
        "feedback_count": total_feedbacks,
        "accuracy": accuracy,
        "thresholds": MONITORING_THRESHOLDS,
        "predicted_distribution": stats.get("predicted_distribution", {}),
        "user_distribution": stats.get("user_distribution", {}),
    }


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


def _record_alert(level: str, accuracy: float, feedback_count: int) -> None:
    """Persiste l'alerte dans ALERT_HISTORY et trace un run MLflow."""
    ALERT_HISTORY.append({
        "timestamp": _dt.now().isoformat(timespec="seconds"),
        "level": level,
        "accuracy": accuracy,
        "feedback_count": feedback_count,
        "message": (
            f"Accuracy {accuracy:.1f}% en dessous du seuil"
            f" {MONITORING_THRESHOLDS['accuracy_' + level]:.1f}%"
        ),
    })
    # Conserver uniquement les N dernieres alertes
    del ALERT_HISTORY[:-_MAX_ALERT_HISTORY]
    log_to_mlflow(
        "alert",
        level=level,
        accuracy=accuracy,
        feedback_count=float(feedback_count),
    )


# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def index():
    return render_template("upload.html")


@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return redirect("/")

    file = request.files["file"]
    if file.filename is None or file.filename == "" or not allowed_file(secure_filename(file.filename)):
        return redirect("/")

    try:
        raw = file.read()
        pil_img = Image.open(io.BytesIO(raw))
        img_array = preprocess_from_pil(pil_img)

        probs = get_model().predict(img_array, verbose=0)[0]
        cls_idx = int(np.argmax(probs))
        label = CLASSES[cls_idx]
        conf = float(probs[cls_idx])
        # Redimensionner en thumbnail 224x224 pour le data URL :
        # evite HTTP 413 sur les grandes images ( > 16 MB)
        thumb = pil_img.resize((224, 224), Image.Resampling.LANCZOS)
        image_data_url = to_data_url(thumb, fmt="JPEG")
        image_filename = secure_filename(file.filename)

        app.logger.info(
            "Prediction generated for file=%s label=%s confidence=%.3f",
            image_filename, label, conf,
        )
        prediction_logger.info(
            "file=%s predicted_label=%s confidence=%.3f",
            image_filename, label, conf,
        )

        log_to_mlflow(
            "prediction",
            predicted_label=label,
            confidence=conf,
            filename=image_filename,
        )

        return render_template(
            "result.html",
            image_data_url=image_data_url,
            image_filename=image_filename,
            predicted_label=label,
            confidence=conf,
            classes=CLASSES,
        )
    except (OSError, RuntimeError, ValueError):
        app.logger.exception("Prediction failed")
        return redirect("/")


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        user_feedback = request.form.get("user_feedback")
        predicted_label = request.form.get("predicted_label")
        if user_feedback not in CLASSES or predicted_label not in CLASSES:
            app.logger.warning(
                "Invalid feedback payload user_feedback=%s predicted_label=%s",
                user_feedback, predicted_label,
            )
            return redirect("/")

        confidence = float(request.form.get("confidence", 0.0))
        image_data = request.form.get("image_data", "")
        image_filename = request.form.get("image_filename", "")

        feedback_record = Feedback(
            image_filename=image_filename,
            image_data_url=image_data,
            predicted_label=predicted_label,
            user_label=user_feedback,
            confidence_score=confidence,
        )
        saved = feedback_db.save_feedback(feedback_record)

        app.logger.info(
            "Feedback received prediction=%s user_choice=%s confidence=%.3f saved=%s",
            predicted_label, user_feedback, confidence, saved,
        )
        prediction_logger.info(
            "feedback file=%s predicted_label=%s user_label=%s confidence=%.3f saved=%s",
            image_filename, predicted_label, user_feedback, confidence, saved,
        )

        # Verifier les seuils apres chaque feedback (alerte proactive)
        snapshot = build_monitoring_snapshot()

        log_to_mlflow(
            "feedback",
            predicted_label=predicted_label,
            user_label=user_feedback,
            confidence=confidence,
            is_correct=float(predicted_label == user_feedback),
            accuracy=snapshot["accuracy"],
            feedback_count=snapshot["feedback_count"],
        )

        return render_template(
            "feedback_ok.html",
            user_feedback=user_feedback,
            predicted_label=predicted_label,
            confidence=confidence,
            feedback_saved=saved,
            feedback_id=feedback_record.id,
        )

    return render_template("feedback_ok.html")


@app.route("/health", methods=["GET"])
def healthcheck():
    snapshot = build_monitoring_snapshot()
    return {
        "status": snapshot["service_status"],
        "model_path": snapshot["model_path"],
        "model_exists": snapshot["model_exists"],
        "feedback_count": snapshot["feedback_count"],
        "accuracy": snapshot["accuracy"],
    }


@app.route("/monitoring", methods=["GET"])
def monitoring_dashboard():
    snapshot = build_monitoring_snapshot()
    recent_alerts = list(reversed(ALERT_HISTORY[-10:]))
    return render_template("monitoring.html", snapshot=snapshot, alert_history=recent_alerts)


@app.route("/alerts", methods=["GET"])
def alerts():
    """Retourne l'historique des alertes en JSON."""
    return {
        "alerts": list(reversed(ALERT_HISTORY[-50:])),
        "count": len(ALERT_HISTORY),
    }


@app.route("/retrain/status", methods=["GET"])
def retrain_status():
    """Indique si un reentrainement est recommande."""
    snapshot = build_monitoring_snapshot()
    retraining_needed = (
        snapshot["accuracy"] <= MONITORING_THRESHOLDS["accuracy_critical"]
        and snapshot["feedback_count"] >= MIN_FEEDBACKS_FOR_RETRAIN
    )
    return {
        "retraining_needed": retraining_needed,
        "reason": (
            f"accuracy {snapshot['accuracy']:.1f}% en dessous du seuil critique"
            f" {MONITORING_THRESHOLDS['accuracy_critical']:.1f}%"
        ) if retraining_needed else "Modele performant — seuil non atteint",
        "feedback_count": snapshot["feedback_count"],
        "accuracy": snapshot["accuracy"],
        "min_feedbacks_required": MIN_FEEDBACKS_FOR_RETRAIN,
        "export_endpoint": "/retrain/export",
    }


@app.route("/retrain/export", methods=["POST"])
def retrain_export():
    """Exporte les feedbacks corriges au format JSON pour le reentrainement."""
    export_path = os.path.join(BASE_DIR, "retraining_data.json")
    exported = feedback_db.export_for_retraining(export_path)
    snapshot = build_monitoring_snapshot()
    log_to_mlflow(
        "retrain_trigger",
        accuracy=snapshot["accuracy"],
        feedback_count=float(snapshot["feedback_count"]),
        export_path=export_path,
    )
    return {
        "exported": exported,
        "export_path": export_path if exported else None,
        "feedback_count": snapshot["feedback_count"],
        "accuracy": snapshot["accuracy"],
        "next_step": "Lancer 'python retrain.py' pour fine-tuner le modele.",
    }


# ---------------- Flask-Monitoring-Dashboard bind (apres les routes) ----------------
monitor_dashboard.bind(app)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
