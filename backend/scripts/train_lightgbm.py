"""Train LightGBM on a dropout dataset CSV and save model for the backend.

For your class:
  - Download the UCI dataset (or any similar CSV) and put it into: backend/data/dropout.csv
  - Ensure the CSV contains a binary target column named 'target' (0/1)
  - Run: python scripts/train_lightgbm.py

This script saves:
  - backend/models/lgbm_model.joblib
  - backend/models/feature_names.json
"""
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from lightgbm import LGBMClassifier

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "dropout.csv"
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "lgbm_model.joblib"
FEATURES_PATH = Path(__file__).resolve().parents[1] / "models" / "feature_names.json"

def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing dataset at {DATA_PATH}. Create backend/data/dropout.csv first.")

    df = pd.read_csv(DATA_PATH)
    if "target" not in df.columns:
        raise ValueError("CSV must contain a binary 'target' column (0/1). Rename your label column to target.")

    # Basic cleaning (you'll customize in your project)
    df = df.dropna(axis=0)
    y = df["target"].astype(int)
    X = df.drop(columns=["target"])

    # One-hot encode categorical columns
    X = pd.get_dummies(X, drop_first=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = LGBMClassifier(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    print(f"ROC-AUC: {auc:.4f}")
    print(classification_report(y_test, (proba >= 0.5).astype(int)))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    FEATURES_PATH.write_text(json.dumps(list(X.columns)))

    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved features to: {FEATURES_PATH}")

if __name__ == "__main__":
    main()
