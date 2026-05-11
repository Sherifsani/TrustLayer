import os

import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "anomaly_model.pkl")

# Must match the 5 features used during training in train.py
ANOMALY_FEATURE_NAMES = [
    "txn_count_90d",
    "avg_txn_amount",
    "txn_failure_rate",
    "bounce_count_90d",
    "dispute_count",
]

_model = None


def _load() -> None:
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)


def check_anomaly(features: dict) -> tuple[bool, str | None]:
    _load()
    x = np.array([[features.get(f, 0.5) for f in ANOMALY_FEATURE_NAMES]])
    result = int(_model.predict(x)[0])
    if result == -1:
        return True, "Unusual transaction pattern detected"
    return False, None
