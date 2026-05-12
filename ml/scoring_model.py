import os

import joblib
import numpy as np
import shap

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "trust_model.pkl")

FEATURE_NAMES = [
    "bvn_confidence", "nin_watchlisted", "liveness_score", "doc_authentic",
    "phone_name_match", "txn_count_90d", "avg_txn_amount", "txn_failure_rate",
    "channel_diversity", "dispute_count", "topup_frequency", "telco_borrow_repaid",
    "income_stability", "bounce_count_90d", "aml_risk_level",
]

FEATURE_DISPLAY_NAMES = {
    "bvn_confidence":      "BVN identity confidence",
    "nin_watchlisted":     "NIN watchlist status",
    "liveness_score":      "Liveness check score",
    "doc_authentic":       "Document authenticity",
    "phone_name_match":    "Phone name match",
    "txn_count_90d":       "Transactions in last 90 days",
    "avg_txn_amount":      "Average transaction amount",
    "txn_failure_rate":    "Transaction failure rate",
    "channel_diversity":   "Payment channel diversity",
    "dispute_count":       "Dispute history",
    "topup_frequency":     "Airtime top-up frequency",
    "telco_borrow_repaid": "Telco credit repayment",
    "income_stability":    "Income stability",
    "bounce_count_90d":    "Bounced payments (90 days)",
    "aml_risk_level":      "AML risk screening",
}

_model = None
_explainer = None


def _load() -> None:
    global _model, _explainer
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        _explainer = shap.TreeExplainer(_model)


def predict_score(features: dict) -> float:
    _load()
    x = np.array([[features.get(f, 0.5) for f in FEATURE_NAMES]])
    prob = _model.predict_proba(x)[0][1]
    return prob * 100


def _shap_vals_and_ranked(features: dict):
    """Shared SHAP computation used by explain_score and get_shap_details."""
    _load()
    x = np.array([[features.get(f, 0.5) for f in FEATURE_NAMES]])
    shap_vals = _explainer.shap_values(x)
    if isinstance(shap_vals, list):
        vals = shap_vals[1][0]
    else:
        vals = shap_vals[0]
    ranked = sorted(zip(FEATURE_NAMES, vals), key=lambda t: abs(t[1]), reverse=True)
    max_abs = max(abs(v) for _, v in ranked) or 1.0
    return ranked, max_abs


def explain_score(features: dict) -> list[str]:
    ranked, max_abs = _shap_vals_and_ranked(features)
    drivers = []
    for feat, val in ranked[:3]:
        label = FEATURE_DISPLAY_NAMES[feat]
        pts = round(val / max_abs * 99)
        prefix = "+" if pts >= 0 else ""
        drivers.append(f"{label} → {prefix}{pts} pts")
    return drivers


def get_shap_details(features: dict) -> list[dict]:
    """Return all 15 features sorted by absolute SHAP contribution (descending).

    Each entry: {feature, display_name, value, contribution (−99..+99), direction}
    """
    ranked, max_abs = _shap_vals_and_ranked(features)
    result = []
    for feat, val in ranked:
        pts = round(val / max_abs * 99)
        result.append({
            "feature": feat,
            "display_name": FEATURE_DISPLAY_NAMES[feat],
            "value": round(features.get(feat, 0.5), 4),
            "contribution": pts,
            "direction": "positive" if pts >= 0 else "negative",
        })
    return result
