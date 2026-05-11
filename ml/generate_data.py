import os

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "bvn_confidence", "nin_watchlisted", "liveness_score", "doc_authentic",
    "phone_name_match", "txn_count_90d", "avg_txn_amount", "txn_failure_rate",
    "channel_diversity", "dispute_count", "topup_frequency", "telco_borrow_repaid",
    "income_stability", "bounce_count_90d", "aml_risk_level",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "training_data.csv")

rng = np.random.default_rng(42)


def _trustworthy_profile() -> dict:
    return {
        "bvn_confidence": rng.uniform(0.85, 1.0),
        "nin_watchlisted": 0,
        "liveness_score": rng.uniform(0.75, 1.0),
        "doc_authentic": 1,
        "phone_name_match": 1,
        "txn_count_90d": int(rng.integers(15, 61)),
        "avg_txn_amount": rng.uniform(2000, 50000),
        "txn_failure_rate": rng.uniform(0.0, 0.05),
        "channel_diversity": int(rng.integers(2, 6)),   # 2–5 inclusive
        "dispute_count": 0,
        "topup_frequency": int(rng.integers(5, 16)),
        "telco_borrow_repaid": 1,
        "income_stability": rng.uniform(0.7, 1.0),
        "bounce_count_90d": int(rng.integers(0, 2)),    # 0–1 inclusive
        "aml_risk_level": 0,
        "label": 1,
    }


def _fraudulent_profile() -> dict:
    # txn_count: either low activity (0–5) or velocity spike (20–50)
    if rng.random() < 0.5:
        txn_count = int(rng.integers(0, 6))
    else:
        txn_count = int(rng.integers(20, 51))

    return {
        "bvn_confidence": rng.uniform(0.0, 0.6),
        "nin_watchlisted": int(rng.choice([0, 1], p=[0.6, 0.4])),
        "liveness_score": rng.uniform(0.0, 0.55),
        "doc_authentic": int(rng.choice([0, 1], p=[0.3, 0.7])),     # 30% fake
        "phone_name_match": int(rng.choice([0, 1], p=[0.5, 0.5])),
        "txn_count_90d": txn_count,
        "avg_txn_amount": float(rng.choice([10000, 50000, 100000])),
        "txn_failure_rate": rng.uniform(0.15, 0.8),
        "channel_diversity": 1,
        "dispute_count": int(rng.integers(1, 6)),
        "topup_frequency": int(rng.integers(0, 3)),
        "telco_borrow_repaid": 0,
        "income_stability": rng.uniform(0.0, 0.35),
        "bounce_count_90d": int(rng.integers(3, 11)),
        "aml_risk_level": int(rng.choice([1, 2])),
        "label": 0,
    }


def generate(n_trustworthy: int = 600, n_fraudulent: int = 200) -> pd.DataFrame:
    rows = (
        [_trustworthy_profile() for _ in range(n_trustworthy)]
        + [_fraudulent_profile() for _ in range(n_fraudulent)]
    )
    idx = rng.permutation(len(rows))
    rows = [rows[i] for i in idx]
    return pd.DataFrame(rows, columns=FEATURE_NAMES + ["label"])


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    df = generate()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Generated {len(df)} profiles ({df['label'].sum():.0f} trustworthy, "
          f"{(df['label'] == 0).sum():.0f} fraudulent) → {OUTPUT_PATH}")
