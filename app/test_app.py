#!/usr/bin/env python3
"""Tests de regression pour l'application de classification d'images satellite."""

import io
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
from PIL import Image

import app as app_module
from database_models import FeedbackDatabase


class FakeModel:
    """Modele factice pour tester /predict sans charger Keras."""

    def predict(self, img_array, verbose=0):
        _ = verbose
        assert img_array.shape == (1, 224, 224, 3)
        return np.array([[0.05, 0.10, 0.15, 0.70]], dtype=np.float32)


class TestSatelliteClassificationApp(unittest.TestCase):
    """Tests de non-regression pour le bug de shape 224x224 et la feedback loop."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.temp_db_path = os.path.join(self.temp_dir.name, "feedback_test.db")
        self.original_feedback_db = app_module.feedback_db
        app_module.feedback_db = FeedbackDatabase(self.temp_db_path)
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.feedback_db.close()
        app_module.feedback_db = self.original_feedback_db
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_allowed_file_extensions(self):
        self.assertTrue(app_module.allowed_file("image.jpg"))
        self.assertTrue(app_module.allowed_file("image.png"))
        self.assertTrue(app_module.allowed_file("image.jpeg"))
        self.assertTrue(app_module.allowed_file("image.webp"))
        self.assertTrue(app_module.allowed_file("IMAGE.JPG"))

        self.assertFalse(app_module.allowed_file("image.txt"))
        self.assertFalse(app_module.allowed_file("image.bmp"))
        self.assertFalse(app_module.allowed_file("image.gz"))
        self.assertFalse(app_module.allowed_file("image"))

    def test_to_data_url_function(self):
        img = Image.new("RGB", (10, 10), color="red")
        data_url = app_module.to_data_url(img)

        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))
        self.assertIsInstance(data_url, str)
        self.assertGreater(len(data_url), len("data:image/jpeg;base64,"))

    def test_preprocess_from_pil_resizes_to_224(self):
        pil_img = Image.new("RGB", (600, 600), color="blue")
        processed = app_module.preprocess_from_pil(pil_img)

        self.assertEqual(processed.shape, (1, 224, 224, 3))
        self.assertEqual(processed.dtype, np.float32)
        self.assertTrue((processed >= 0).all() and (processed <= 1).all())

    def test_preprocess_from_various_sizes(self):
        for size in [(100, 100), (500, 300), (1024, 768), (3000, 2000)]:
            with self.subTest(size=size):
                pil_img = Image.new("RGB", size, color="green")
                processed = app_module.preprocess_from_pil(pil_img)
                self.assertEqual(processed.shape, (1, 224, 224, 3))

    def test_homepage_access(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_predict_without_file(self):
        response = self.client.post("/predict")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    def test_predict_with_empty_filename(self):
        response = self.client.post("/predict", data={"file": (io.BytesIO(b""), "")})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    def test_predict_with_invalid_extension(self):
        img = Image.new("RGB", (64, 64), color="blue")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="BMP")
        img_buffer.seek(0)

        response = self.client.post("/predict", data={"file": (img_buffer, "test.bmp")})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    @patch.object(app_module, "log_to_mlflow")
    def test_predict_success_uses_resized_input(self, mock_mlflow):
        img = Image.new("RGB", (600, 400), color="purple")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)

        with patch.object(app_module, "get_model", return_value=FakeModel()):
            response = self.client.post(
                "/predict",
                data={"file": (img_buffer, "satellite.jpg")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Classe pr", response.data)
        self.assertIn(b"mountain", response.data)
        mock_mlflow.assert_called_once()

    def test_feedback_page_access(self):
        response = self.client.get("/feedback")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Feedback envoy", response.data)

    @patch.object(app_module, "log_to_mlflow")
    def test_feedback_post_persists_sqlite_record(self, mock_mlflow):
        response = self.client.post(
            "/feedback",
            data={
                "user_feedback": "desert",
                "predicted_label": "mountain",
                "confidence": "0.85",
                "image_data": "data:image/jpeg;base64,test",
                "image_filename": "satellite.jpg",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Feedback envoy", response.data)
        self.assertIn(b"Sauvegarde SQLite:", response.data)

        saved_feedbacks = app_module.feedback_db.get_feedbacks(limit=10)
        self.assertEqual(len(saved_feedbacks), 1)
        self.assertEqual(saved_feedbacks[0].image_filename, "satellite.jpg")
        self.assertEqual(saved_feedbacks[0].predicted_label, "mountain")
        self.assertEqual(saved_feedbacks[0].user_label, "desert")
        # log_to_mlflow peut etre appele plusieurs fois (feedback + alert eventuelle)
        mock_mlflow.assert_any_call(
            "feedback",
            predicted_label="mountain",
            user_label="desert",
            confidence=0.85,
            is_correct=0.0,
            accuracy=unittest.mock.ANY,
            feedback_count=unittest.mock.ANY,
        )

    def test_healthcheck_reports_feedback_count(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "healthy")
        self.assertIn("feedback_count", payload)
        self.assertIn("accuracy", payload)

    def test_monitoring_dashboard_access(self):
        response = self.client.get("/monitoring")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Monitoring local", response.data)
        self.assertIn(b"Etat du service", response.data)

    def test_flask_monitoring_dashboard_bound(self):
        rules = [rule.rule for rule in app_module.app.url_map.iter_rules()]
        self.assertIn("/dashboard/", rules)

    def test_config_values(self):
        with app_module.app.app_context():
            self.assertEqual(app_module.app.config["MAX_CONTENT_LENGTH"], 16 * 1024 * 1024)
            self.assertTrue(
                app_module.app.config["UPLOAD_FOLDER"].endswith(os.path.join("static", "uploads"))
            )

    @patch.object(app_module, "log_to_mlflow")
    def test_log_to_mlflow_does_not_raise(self, mock_mlflow):
        """log_to_mlflow() ne doit pas lever d'exception (logging non-bloquant)."""
        mock_mlflow.return_value = None
        try:
            app_module.log_to_mlflow("test_event", accuracy=99.0, label="desert")
        except Exception as exc:  # noqa: BLE001
            self.fail(f"log_to_mlflow() a leve une exception inattendue : {exc}")

    def test_alerts_endpoint_returns_json(self):
        response = self.client.get("/alerts")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("alerts", payload)
        self.assertIsInstance(payload["alerts"], list)
        self.assertIn("count", payload)

    def test_retrain_status_endpoint(self):
        response = self.client.get("/retrain/status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("retraining_needed", payload)
        self.assertIn("accuracy", payload)
        self.assertIn("feedback_count", payload)

    @patch.object(app_module, "log_to_mlflow")
    def test_retrain_export_returns_json(self, mock_mlflow):
        response = self.client.post("/retrain/export")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("exported", payload)
        self.assertIsInstance(payload["exported"], bool)
        self.assertIn("next_step", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
