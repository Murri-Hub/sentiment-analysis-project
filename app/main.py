import pickle
import time
import os
import psutil
import urllib.request
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentiment Analysis API", version="1.0.0")

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    "sentiment_requests_total",
    "Total number of prediction requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "sentiment_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"]
)
PREDICTION_ERRORS = Counter(
    "sentiment_prediction_errors_total",
    "Total number of prediction errors"
)
CPU_USAGE = Gauge("sentiment_cpu_usage_percent", "CPU usage percent")
MEMORY_USAGE = Gauge("sentiment_memory_usage_bytes", "Memory usage in bytes")

# --- Model Loading ---
MODEL_PATH = os.getenv("MODEL_PATH", "sentimentanalysismodel.pkl")
MODEL_URL = "https://github.com/Profession-AI/progetti-devops/raw/refs/heads/main/Deploy%20e%20monitoraggio%20di%20un%20modello%20di%20sentiment%20analysis%20per%20recensioni/sentimentanalysismodel.pkl"

def load_model():
    if not os.path.exists(MODEL_PATH):
        logger.info(f"Model not found locally, downloading from {MODEL_URL}...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        logger.info("Model downloaded successfully.")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded successfully.")
    return model

model = load_model()

# --- Schemas ---
class ReviewRequest(BaseModel):
    review: str

class PredictionResponse(BaseModel):
    sentiment: str
    confidence: float

# --- Label mapping ---
LABEL_MAP = {
    0: "negative",
    1: "neutral",
    2: "positive",
    "negative": "negative",
    "neutral": "neutral",
    "positive": "positive",
}

def normalize_label(raw_label) -> str:
    if isinstance(raw_label, (int, float)):
        return LABEL_MAP.get(int(raw_label), str(raw_label))
    return LABEL_MAP.get(str(raw_label).lower(), str(raw_label).lower())

# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: ReviewRequest):
    start = time.time()
    try:
        if not request.review.strip():
            raise HTTPException(status_code=400, detail="Review text cannot be empty.")

        proba = None
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba([request.review])[0]
            raw_label = model.classes_[proba.argmax()]
            confidence = float(proba.max())
        else:
            raw_label = model.predict([request.review])[0]
            confidence = 1.0

        sentiment = normalize_label(raw_label)

        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="success").inc()
        return PredictionResponse(sentiment=sentiment, confidence=round(confidence, 4))

    except HTTPException:
        raise
    except Exception as e:
        PREDICTION_ERRORS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/predict", status="error").inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    finally:
        latency = time.time() - start
        REQUEST_LATENCY.labels(endpoint="/predict").observe(latency)
        CPU_USAGE.set(psutil.cpu_percent())
        MEMORY_USAGE.set(psutil.Process(os.getpid()).memory_info().rss)

@app.get("/metrics")
def metrics():
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.Process(os.getpid()).memory_info().rss)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
