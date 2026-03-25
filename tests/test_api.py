import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

# --- Mock the model before importing main ---
mock_model = MagicMock()
mock_model.predict.return_value = ["positive"]
mock_model.predict_proba.return_value = np.array([[0.05, 0.0, 0.95]])
mock_model.classes_ = np.array(["negative", "neutral", "positive"])

with patch("builtins.open", MagicMock()), \
     patch("pickle.load", return_value=mock_model), \
     patch("os.path.exists", return_value=True):
    from main import app

client = TestClient(app)


# ── Unit Tests ──────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPredictEndpoint:
    def test_positive_review(self):
        mock_model.predict_proba.return_value = np.array([[0.02, 0.03, 0.95]])
        response = client.post("/predict", json={"review": "This product is amazing! I love it."})
        assert response.status_code == 200
        data = response.json()
        assert data["sentiment"] == "positive"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_negative_review(self):
        mock_model.predict_proba.return_value = np.array([[0.90, 0.05, 0.05]])
        mock_model.classes_ = np.array(["negative", "neutral", "positive"])
        response = client.post("/predict", json={"review": "Terrible product, waste of money."})
        assert response.status_code == 200
        data = response.json()
        assert data["sentiment"] == "negative"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_empty_review_returns_400(self):
        response = client.post("/predict", json={"review": "   "})
        assert response.status_code == 400

    def test_missing_review_field_returns_422(self):
        response = client.post("/predict", json={})
        assert response.status_code == 422

    def test_response_schema(self):
        mock_model.predict_proba.return_value = np.array([[0.1, 0.1, 0.8]])
        response = client.post("/predict", json={"review": "Good product."})
        assert response.status_code == 200
        data = response.json()
        assert "sentiment" in data
        assert "confidence" in data
        assert isinstance(data["sentiment"], str)
        assert isinstance(data["confidence"], float)

    def test_confidence_rounded(self):
        mock_model.predict_proba.return_value = np.array([[0.049999, 0.0, 0.950001]])
        response = client.post("/predict", json={"review": "Great!"})
        data = response.json()
        assert len(str(data["confidence"]).split(".")[-1]) <= 4


# ── Integration Tests ────────────────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_endpoint_reachable(self):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self):
        response = client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_contains_expected_keys(self):
        # Trigger a predict first so counters are populated
        mock_model.predict_proba.return_value = np.array([[0.05, 0.0, 0.95]])
        client.post("/predict", json={"review": "Nice!"})
        response = client.get("/metrics")
        body = response.text
        assert "sentiment_requests_total" in body
        assert "sentiment_request_latency_seconds" in body
        assert "sentiment_cpu_usage_percent" in body
        assert "sentiment_memory_usage_bytes" in body


class TestPredictIntegration:
    def test_multiple_requests_accumulate_metrics(self):
        mock_model.predict_proba.return_value = np.array([[0.05, 0.0, 0.95]])
        for _ in range(5):
            client.post("/predict", json={"review": "Test review."})
        response = client.get("/metrics")
        assert "sentiment_requests_total" in response.text

    def test_error_increments_error_counter(self):
        mock_model.predict_proba.side_effect = RuntimeError("Model exploded")
        response = client.post("/predict", json={"review": "Test"})
        assert response.status_code == 500
        # Reset side effect
        mock_model.predict_proba.side_effect = None
        mock_model.predict_proba.return_value = np.array([[0.05, 0.0, 0.95]])
        metrics_resp = client.get("/metrics")
        assert "sentiment_prediction_errors_total" in metrics_resp.text
