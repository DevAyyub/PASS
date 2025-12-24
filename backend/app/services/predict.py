import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .. import db
from ..models import Student, RiskScore

# Bundle produced by your training script
# backend/app/services/predict.py -> parents[2] == backend/
BUNDLE_PATH = Path(__file__).resolve().parents[2] / "models" / "risk_model.joblib"


def _load_bundle():
    """
    Loads the saved training bundle:
      {
        "model": LGBMClassifier,
        "feature_columns": [...],
        "categorical_features": [...],
        "threshold": 0.5,
        ...
      }
    """
    if not BUNDLE_PATH.exists():
        return None
    try:
        return joblib.load(BUNDLE_PATH)
    except Exception:
        return None


def _demo_feature_row_for_student(student_id: int, feature_cols: list[str], cat_cols: set[str]) -> dict:
    """
    MVP placeholder: later replace with real DB feature engineering.
    For now, generate deterministic values per student id (stable between runs).
    """
    rng = np.random.default_rng(student_id)

    row = {}
    for f in feature_cols:
        if f in cat_cols:
            row[f] = f"cat_{student_id % 5}"  # deterministic category-like strings
        else:
            row[f] = float(rng.uniform(0, 1))
    return row


def _ensure_df_schema(df: pd.DataFrame, feature_cols: list[str], cat_cols: set[str]) -> pd.DataFrame:
    """
    Ensures df has exactly feature_cols in the same order.
    - creates missing cols with safe defaults
    - drops extra cols
    - sets categorical dtypes as 'category'
    - coerces numeric cols safely
    """
    X = df.copy()

    # add missing
    for c in feature_cols:
        if c not in X.columns:
            X[c] = "unknown" if c in cat_cols else 0.0

    # keep only in correct order
    X = X[feature_cols]

    # enforce categorical dtype
    for c in feature_cols:
        if c in cat_cols:
            X[c] = X[c].astype(str).str.strip().astype("category")

    # numeric columns: coerce bad strings to NaN then fill with 0
    for c in feature_cols:
        if c not in cat_cols:
            X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0.0)

    return X


def run_batch_risk_prediction(student_ids: list[int] | None = None) -> int:
    """
    Predicts risk for students and upserts into risk_scores:
    - If a RiskScore exists for a student, update the latest row (and refresh generated_at)
    - Else, create a new RiskScore row
    """
    bundle = _load_bundle()
    if bundle is None:
        # keep app functional even if model not present on teammate machine
        return _fallback_batch(student_ids)

    model = bundle["model"]
    feature_cols: list[str] = bundle["feature_columns"]
    cat_cols = set(bundle.get("categorical_features", []))
    threshold = float(bundle.get("threshold", 0.5))

    q = Student.query
    if student_ids:
        q = q.filter(Student.id.in_(student_ids))
    students = q.all()

    # Build demo feature rows (replace later with real DB feature engineering)
    rows = [_demo_feature_row_for_student(s.id, feature_cols, cat_cols) for s in students]
    X = _ensure_df_schema(pd.DataFrame(rows), feature_cols, cat_cols)

    probs = model.predict_proba(X)[:, 1]
    _preds = (probs >= threshold).astype(int)  # not stored currently, but kept if you want later

    # Global feature importance (simple MVP XAI)
    importances = getattr(model, "feature_importances_", None)
    top_json = None
    if importances is not None:
        top_idx = np.argsort(importances)[::-1][:6]
        top_factors = [
            {"feature": feature_cols[i], "importance": float(importances[i])}
            for i in top_idx
        ]
        top_json = json.dumps(top_factors)

    created_or_updated = 0

    for s, p in zip(students, probs, strict=False):
        # Use generated_at for "latest" (more semantically correct than id)
        existing = (
            RiskScore.query.filter_by(student_id=s.id)
            .order_by(RiskScore.generated_at.desc())
            .first()
        )

        if existing:
            existing.risk_probability = float(p)
            existing.top_factors_json = top_json
            existing.generated_at = datetime.utcnow()  # ✅ refresh timestamp on update
        else:
            rs = RiskScore(
                student_id=s.id,
                risk_probability=float(p),
                top_factors_json=top_json,
            )
            db.session.add(rs)

        created_or_updated += 1

    db.session.commit()
    return created_or_updated


def _fallback_batch(student_ids: list[int] | None) -> int:
    """
    Deterministic fallback if model bundle is missing.
    Still does upsert + refresh generated_at for consistency.
    """
    q = Student.query
    if student_ids:
        q = q.filter(Student.id.in_(student_ids))
    students = q.all()

    created_or_updated = 0

    top = json.dumps(
        [
            {"feature": "Grade_1st_Sem", "importance": 0.42},
            {"feature": "Attendance", "importance": 0.31},
            {"feature": "LMS_Logins", "importance": 0.27},
        ]
    )

    for s in students:
        p = (s.id * 37 % 100) / 100.0

        existing = (
            RiskScore.query.filter_by(student_id=s.id)
            .order_by(RiskScore.generated_at.desc())
            .first()
        )

        if existing:
            existing.risk_probability = float(p)
            existing.top_factors_json = top
            existing.generated_at = datetime.utcnow()  # ✅ refresh timestamp on update
        else:
            rs = RiskScore(
                student_id=s.id,
                risk_probability=float(p),
                top_factors_json=top,
            )
            db.session.add(rs)

        created_or_updated += 1

    db.session.commit()
    return created_or_updated
