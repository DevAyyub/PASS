import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .. import db
from ..models import Student, RiskScore

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "lgbm_model.joblib"
FEATURES_PATH = Path(__file__).resolve().parents[2] / "models" / "feature_names.json"

def _load_model():
    if MODEL_PATH.exists() and FEATURES_PATH.exists():
        model = joblib.load(MODEL_PATH)
        feature_names = json.loads(FEATURES_PATH.read_text())
        return model, feature_names
    return None, None

def _demo_feature_row_for_student(student_id: int, feature_names: list[str]) -> dict:
    # MVP placeholder: in a real system you build features from grades/attendance/LMS tables.
    # We generate stable-ish pseudo-random features per student for demo purposes.
    rng = np.random.default_rng(student_id)
    row = {f: float(rng.uniform(0, 1)) for f in feature_names}
    return row

def run_batch_risk_prediction(student_ids: list[int] | None = None) -> int:
    model, feature_names = _load_model()
    if model is None:
        # If no model yet, we still generate a simple "risk" score for demo to keep app functional.
        return _fallback_batch(student_ids)

    q = Student.query
    if student_ids:
        q = q.filter(Student.id.in_(student_ids))
    students = q.all()

    rows = []
    for s in students:
        rows.append(_demo_feature_row_for_student(s.id, feature_names))

    X = pd.DataFrame(rows)[feature_names]
    probs = model.predict_proba(X)[:, 1]

    created = 0
    # global importance as "top factors" (simple MVP XAI)
    importances = getattr(model, "feature_importances_", None)
    if importances is not None:
        top_idx = np.argsort(importances)[::-1][:6]
        top_factors = [{"feature": feature_names[i], "importance": float(importances[i])} for i in top_idx]
        top_json = json.dumps(top_factors)
    else:
        top_json = None

    for s, p in zip(students, probs, strict=False):
        rs = RiskScore(student_id=s.id, risk_probability=float(p), top_factors_json=top_json)
        db.session.add(rs)
        created += 1
    db.session.commit()
    return created

def _fallback_batch(student_ids: list[int] | None) -> int:
    q = Student.query
    if student_ids:
        q = q.filter(Student.id.in_(student_ids))
    students = q.all()
    created = 0
    for s in students:
        # deterministic fallback probability
        p = (s.id * 37 % 100) / 100.0
        rs = RiskScore(student_id=s.id, risk_probability=float(p), top_factors_json=json.dumps([
            {"feature": "Grade_1st_Sem", "importance": 0.42},
            {"feature": "Attendance", "importance": 0.31},
            {"feature": "LMS_Logins", "importance": 0.27},
        ]))
        db.session.add(rs)
        created += 1
    db.session.commit()
    return created
