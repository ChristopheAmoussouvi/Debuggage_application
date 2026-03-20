#!/usr/bin/env python3
"""Configuration de journalisation pour l'application Flask."""

import logging
import logging.handlers
import os


def setup_logging(app, log_level=logging.INFO):
    """Configure des logs rotatifs pour l'application et les predictions."""
    log_dir = os.path.join(app.root_path, "logs")
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app.logger.handlers.clear()
    app.logger.setLevel(log_level)

    app_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(formatter)

    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.addHandler(stream_handler)

    prediction_logger = logging.getLogger("app.predictions")
    prediction_logger.handlers.clear()
    prediction_logger.setLevel(logging.INFO)
    prediction_logger.propagate = False

    prediction_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "predictions.log"),
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    prediction_handler.setLevel(logging.INFO)
    prediction_handler.setFormatter(formatter)
    prediction_logger.addHandler(prediction_handler)

    return prediction_logger


def setup_monitoring_alerts(app, error_threshold=logging.ERROR):
    """Ajoute un filtre simple pour tracer les erreurs critiques."""

    class MonitoringFilter(logging.Filter):
        def filter(self, record):
            if record.levelno >= error_threshold:
                app.logger.warning("Monitoring alert triggered for log level %s", record.levelname)
            return True

    monitoring_filter = MonitoringFilter()
    for handler in app.logger.handlers:
        handler.addFilter(monitoring_filter)
