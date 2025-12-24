"""
train_lightgbm.py

AI-only training script for PASS using UCI "Predict students' dropout and academic success".
- Robust CSV delimiter detection (, ; \t)
- Maps 3-class target (Dropout/Enrolled/Graduate) -> binary dropout risk (1/0)
- Handles categorical + numeric features
- Saves:
  - models/risk_model.joblib (bundle: model + expected feature columns + categorical columns)
  - reports/metrics.json
  - reports/classification_report.json
  - reports/feature_importance.csv

Run (from PASS/backend):
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python scripts/train_lightgbm.py --data data/UCI_data.csv --outdir models
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


def read_csv_auto(path: Path) -> pd.DataFrame:
    """Try common separators so UCI CSVs (often ';') load correctly."""
    last_exc = None
    for sep in [",", ";", "\t", "|"]:
        try:
            df_try = pd.read_csv(path, sep=sep)
            if df_try.shape[1] > 1:
                return df_try
        except Exception as e:
            last_exc = e
            continue
    # final fallback (pandas will guess with python engine)
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        if last_exc:
            raise last_exc
        raise


def find_target_column(df: pd.DataFrame) -> str:
    """Heuristics for common target column names."""
    candidates = ["Target", "target", "STATUS", "status", "label", "Label", "Outcome", "outcome"]
    for c in candidates:
        if c in df.columns:
            return c
    # case-insensitive "target"
    lowered = {c.lower(): c for c in df.columns}
    if "target" in lowered:
        return lowered["target"]
    # fallback: last column (best-effort)
    return df.columns[-1]


def make_binary_target(y: pd.Series) -> pd.Series:
    """
    Convert target to binary:
      Dropout -> 1
      Enrolled/Graduate (and everything else) -> 0
    Works for string labels and best-effort numeric labels.
    """
    y_norm = y.astype(str).str.strip().str.lower()

    # Common UCI labels:
    # "Dropout", "Enrolled", "Graduate"
    if y_norm.isin(["dropout", "enrolled", "graduate"]).all():
        return (y_norm == "dropout").astype(int)

    # If labels look numeric-as-strings (e.g. "0","1","2"):
    # Try converting; if success, treat value==1 as dropout (conservative)
    try:
        y_num = pd.to_numeric(y_norm, errors="raise")
        # If already binary:
        uniq = sorted(pd.unique(y_num))
        if set(uniq).issubset({0, 1}):
            return (y_num == 1).astype(int)
        # If multiclass numeric: best-effort mapping (treat max as dropout)
        dropout_val = max(uniq)
        return (y_num == dropout_val).astype(int)
    except Exception:
        pass

    # Fallback keyword-based mapping
    return y_norm.apply(lambda s: 1 if "drop" in s else 0).astype(int)


def preprocess_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    - Strips column name whitespace
    - Converts object columns to category
    - Fills missing values (median for numeric, mode/unknown for categorical)
    """
    X = X.copy()
    X.columns = [c.strip() for c in X.columns]

    # Convert object columns to category for LightGBM
    for c in X.columns:
        if X[c].dtype == "object":
            X[c] = X[c].astype(str).str.strip().astype("category")

    # Fill missing values
    for c in X.columns:
        if pd.api.types.is_numeric_dtype(X[c]):
            X[c] = X[c].fillna(X[c].median())
        else:
            mode = X[c].mode(dropna=True)
            fill_val = mode.iloc[0] if len(mode) else "unknown"
            X[c] = X[c].fillna(fill_val)

    return X


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to CSV dataset")
    parser.add_argument("--outdir", type=str, default="models", help="Output directory for model artifacts")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold to convert proba -> class")
    args = parser.parse_args()

    data_path = Path(args.data)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path.resolve()}")

    df = read_csv_auto(data_path)
    df.columns = [c.strip() for c in df.columns]

    target_col = find_target_column(df)
    y_raw = df[target_col]
    X_raw = df.drop(columns=[target_col])

    print(f"✅ Loaded dataset: {data_path}  shape={df.shape}")
    print(f"✅ Target column detected: {target_col}")
    print("✅ Target unique values (first 10):", pd.Series(y_raw.unique()).head(10).tolist())

    # Make binary target
    y = make_binary_target(y_raw)
    dropout_rate = float(y.mean())
    print(f"✅ Binary dropout rate (mean target): {dropout_rate:.3f}")

    X = preprocess_features(X_raw)

    # Identify categorical features for LightGBM
    cat_features = [c for c in X.columns if str(X[c].dtype) in ("category", "object")]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=args.seed,
        stratify=y,
    )

    model = LGBMClassifier(
        n_estimators=800,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.9,
        colsample_bytree=0.9,
        class_weight="balanced",
        random_state=args.seed,
    )

    model.fit(
        X_train,
        y_train,
        categorical_feature=cat_features if len(cat_features) else "auto",
    )

    # Predictions
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= args.threshold).astype(int)

    acc = float(accuracy_score(y_test, pred))
    f1 = float(f1_score(y_test, pred))
    try:
        auc = float(roc_auc_score(y_test, proba))
    except Exception:
        auc = None

    cm = confusion_matrix(y_test, pred).tolist()
    report = classification_report(y_test, pred, output_dict=True)

    metrics = {
        "dataset_path": str(data_path),
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "target_column": target_col,
        "binary_mapping": "Dropout=1, Non-dropout=0",
        "dropout_rate": dropout_rate,
        "threshold": args.threshold,
        "accuracy": acc,
        "f1": f1,
        "roc_auc": auc,
        "confusion_matrix": cm,
    }

    # Feature importance
    fi = (
        pd.DataFrame(
            {"feature": list(X.columns), "importance": model.feature_importances_.astype(int)}
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    # Save artifacts (bundle)
    bundle = {
        "model": model,
        "feature_columns": list(X.columns),
        "categorical_features": cat_features,
        "target_info": {"original_target_column": target_col, "binary": True},
        "threshold": float(args.threshold),
    }

    joblib.dump(bundle, outdir / "risk_model.joblib")
    (reports_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (reports_dir / "classification_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    fi.to_csv(reports_dir / "feature_importance.csv", index=False)

    print("\n✅ Training complete")
    print(f"Saved model bundle: {outdir / 'risk_model.joblib'}")
    print(f"Saved metrics:      {reports_dir / 'metrics.json'}")
    print(f"Saved report:       {reports_dir / 'classification_report.json'}")
    print(f"Saved importance:   {reports_dir / 'feature_importance.csv'}")
    print(f"Accuracy={acc:.4f}  F1={f1:.4f}  ROC-AUC={auc}")


if __name__ == "__main__":
    main()
