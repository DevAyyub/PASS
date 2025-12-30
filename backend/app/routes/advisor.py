import json
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_

from .. import db
from ..models import Advisor, Student, RiskScore, Intervention
from ..services.predict import run_batch_risk_prediction
from .guards import advisor_required

bp = Blueprint("advisor", __name__)

# -----------------------
# Helpers
# -----------------------
def _advisor_from_token():
    user_id = int(get_jwt_identity())
    return Advisor.query.filter_by(user_id=user_id).first()

def _latest_risk_map(student_ids):
    """Return {student_id: latest RiskScore} in ONE query (no N+1)."""
    if not student_ids:
        return {}

    subq = (
        db.session.query(
            RiskScore.student_id.label("student_id"),
            func.max(RiskScore.generated_at).label("max_gen"),
        )
        .filter(RiskScore.student_id.in_(student_ids))
        .group_by(RiskScore.student_id)
        .subquery()
    )

    latest_scores = (
        db.session.query(RiskScore)
        .join(
            subq,
            and_(
                RiskScore.student_id == subq.c.student_id,
                RiskScore.generated_at == subq.c.max_gen,
            ),
        )
        .all()
    )

    return {rs.student_id: rs for rs in latest_scores}

def _students_payload_for_advisor(advisor_id):
    students = Student.query.filter_by(advisor_id=advisor_id).all()
    ids = [s.id for s in students]
    latest_map = _latest_risk_map(ids)

    out = []
    for s in students:
        latest = latest_map.get(s.id)
        out.append({
            "student_id": s.id,
            "name": s.name,
            "department": s.department,
            "risk_probability": float(latest.risk_probability) if latest else None,
            "risk_generated_at": latest.generated_at.isoformat() if latest else None,
        })

    # None last, high risk first
    out.sort(key=lambda x: (x["risk_probability"] is None, -(x["risk_probability"] or -1)))
    return out

# -----------------------
# Contract endpoint
# GET /api/advisor/risk-list
# -----------------------
@bp.get("/advisor/risk-list")
@jwt_required()
@advisor_required
def advisor_risk_list():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    students = _students_payload_for_advisor(advisor.id)
    return {"students": students}, 200

# -----------------------
# Keep existing endpoint
# GET /api/advisor/students
# -----------------------
@bp.get("/advisor/students")
@jwt_required()
@advisor_required
def advisor_students():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    students = _students_payload_for_advisor(advisor.id)
    return {"students": students}, 200

# -----------------------
# Alias: /advisor/student/<id>
# -----------------------
@bp.get("/advisor/student/<int:student_id>")
@jwt_required()
@advisor_required
def advisor_student_alias(student_id: int):
    return advisor_student_detail(student_id)

# -----------------------
# GET /api/advisor/students/<id>
# -----------------------
@bp.get("/advisor/students/<int:student_id>")
@jwt_required()
@advisor_required
def advisor_student_detail(student_id: int):
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = db.session.get(Student, student_id)
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    latest = (
        RiskScore.query
        .filter_by(student_id=student.id)
        .order_by(RiskScore.generated_at.desc())
        .first()
    )

    interventions = (
        Intervention.query
        .filter_by(student_id=student.id, advisor_id=advisor.id)
        .order_by(Intervention.created_at.desc())
        .limit(20)
        .all()
    )

    interventions_payload = [
        {"id": i.id, "note": i.note, "created_at": i.created_at.isoformat()}
        for i in interventions
    ]

    xai = None
    if latest and latest.top_factors_json:
        try:
            xai = json.loads(latest.top_factors_json)
        except Exception:
            xai = None

    return {
        "student": {
            "student_id": student.id,
            "name": student.name,
            "department": student.department,
            "cohort_year": student.cohort_year,
        },
        "latest_risk": {
            "risk_probability": float(latest.risk_probability) if latest else None,
            "generated_at": latest.generated_at.isoformat() if latest else None,
            "top_factors": xai,
        },
        "interventions": interventions_payload,
    }, 200

# -----------------------
# POST /api/advisor/interventions
# body: {"student_id": 1, "note": "..."}
# -----------------------
@bp.post("/advisor/interventions")
@jwt_required()
@advisor_required
def create_intervention_contract():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    note = (data.get("note") or "").strip()

    if not student_id:
        return {"error": "student_id is required"}, 400
    if not note:
        return {"error": "note is required"}, 400

    student = db.session.get(Student, int(student_id))
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    inter = Intervention(advisor_id=advisor.id, student_id=student.id, note=note)
    db.session.add(inter)
    db.session.commit()

    return {
        "ok": True,
        "intervention": {
            "id": inter.id,
            "note": inter.note,
            "created_at": inter.created_at.isoformat(),
        }
    }, 201

# -----------------------
# Keep existing intervention endpoint
# POST /api/advisor/students/<id>/interventions
# body: {"note": "..."}
# -----------------------
@bp.post("/advisor/students/<int:student_id>/interventions")
@jwt_required()
@advisor_required
def add_intervention(student_id: int):
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = db.session.get(Student, student_id)
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    data = request.get_json(silent=True) or {}
    note = (data.get("note") or "").strip()
    if not note:
        return {"error": "note is required"}, 400

    inter = Intervention(advisor_id=advisor.id, student_id=student.id, note=note)
    db.session.add(inter)
    db.session.commit()

    return {"ok": True, "id": inter.id}, 201

# -----------------------
# POST /api/advisor/predict-risk
# -----------------------
@bp.post("/advisor/predict-risk")
@jwt_required()
@advisor_required
def trigger_predict():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    created = run_batch_risk_prediction(student_ids=[s.id for s in advisor.students])
    return {"ok": True, "generated": created}, 200
