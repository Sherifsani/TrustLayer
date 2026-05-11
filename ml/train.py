import os
import sys

# Allow running as `python ml/train.py` from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split

from ml.generate_data import FEATURE_NAMES, OUTPUT_PATH

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# The 5 transaction-timeline features the anomaly detector watches
ANOMALY_FEATURE_NAMES = [
    "txn_count_90d",
    "avg_txn_amount",
    "txn_failure_rate",
    "bounce_count_90d",
    "dispute_count",
]


def train_trust_model(df: pd.DataFrame) -> None:
    X = df[FEATURE_NAMES].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingClassifier(
        n_estimators=100, max_depth=4, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    print("=== Trust Model (GradientBoostingClassifier) ===")
    print(classification_report(y_test, preds))
    print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")

    path = os.path.join(MODELS_DIR, "trust_model.pkl")
    joblib.dump(model, path)
    print(f"Saved → {path}")


def train_anomaly_model(df: pd.DataFrame) -> None:
    # Train only on trustworthy profiles so the forest learns normal behaviour
    trustworthy = df[df["label"] == 1]
    X = trustworthy[ANOMALY_FEATURE_NAMES].values

    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)

    path = os.path.join(MODELS_DIR, "anomaly_model.pkl")
    joblib.dump(model, path)
    print(f"Saved → {path}")


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)

    print(f"Loading training data from {OUTPUT_PATH} …")
    df = pd.read_csv(OUTPUT_PATH)
    print(f"  {len(df)} rows loaded ({df['label'].sum():.0f} trustworthy, "
          f"{(df['label'] == 0).sum():.0f} fraudulent)")

    train_trust_model(df)
    train_anomaly_model(df)
    print("\nTraining complete. Both models saved.")
