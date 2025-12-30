import json
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_

from ..models import Advisor, Student, RiskScore, Intervention
from .. import db
from ..services.predict import run_batch_risk_prediction
from .guards import advisor_required

bp = Blueprint("advisor", __name__)

def _advisor_from_token():
    user_id = int(get_jwt_identity())
    advisor = Advisor.query.filter_by(user_id=user_id).first()
    return advisor

def _latest_risk_subquery():
    """
    Returns a subquery with latest risk row per student using max(generated_at).
    """
    latest_ts = (
        db.session.query(
            RiskScore.student_id.label("student_id"),
            func.max(RiskScore.generated_at).label("max_generated_at"),
        )
        .group_by(RiskScore.student_id)
        .subquery()
    )

    latest_risk = (
        db.session.query(
            RiskScore.student_id.label("student_id"),
            RiskScore.risk_probability.label("risk_probability"),
            RiskScore.generated_at.label("generated_at"),
            RiskScore.top_factors_json.label("top_factors_json"),
        )
        .join(
            latest_ts,
            and_(
                RiskScore.student_id == latest_ts.c.student_id,
                RiskScore.generated_at == latest_ts.c.max_generated_at,
            ),
        )
        .subquery()
    )
    return latest_risk

# -----------------------------
# NEW: contract endpoint alias
# -----------------------------
@bp.get("/advisor/risk-list")
@jwt_required()
@advisor_required
def advisor_risk_list():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    latest_risk = _latest_risk_subquery()

    rows = (
        db.session.query(
            Student.id,
            Student.name,
            Student.department,
            latest_risk.c.risk_probability,
            latest_risk.c.generated_at,
        )
        .outerjoin(latest_risk, latest_risk.c.student_id == Student.id)
        .filter(Student.advisor_id == advisor.id)
        .all()
    )

    students = []
    for (sid, name, dept, prob, gen_at) in rows:
        students.append({
            "student_id": sid,
            "name": name,
            "department": dept,
            "risk_probability": float(prob) if prob is not None else None,
            "risk_generated_at": gen_at.isoformat() if gen_at else None,
        })

    # sort: None last, high risk first
    students.sort(key=lambda x: (x["risk_probability"] is None, -(x["risk_probability"] or -1)))
    return {"students": students}, 200


# -----------------------------
# Keep your existing endpoint
# (students list) but make it stable
# -----------------------------
@bp.get("/advisor/students")
@jwt_required()
@advisor_required
def advisor_students():
    # Just reuse risk-list logic
    return advisor_risk_list()


# -----------------------------
# NEW: contract alias
# -----------------------------
@bp.get("/advisor/student/<int:student_id>")
@jwt_required()
@advisor_required
def advisor_student_alias(student_id: int):
    return advisor_student_detail(student_id)


@bp.get("/advisor/students/<int:student_id>")
@jwt_required()
@advisor_required
def advisor_student_detail(student_id: int):
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = Student.query.get(student_id)
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


# -----------------------------
# NEW: contract endpoint
# POST /api/advisor/interventions
# body: { "student_id": 1, "note": "..." }
# -----------------------------
@bp.post("/advisor/interventions")
@jwt_required()
@advisor_required
def create_intervention_contract():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    data = request.get_json(force=True) or {}
    student_id = data.get("student_id")
    note = (data.get("note") or "").strip()

    if not student_id:
        return {"error": "student_id is required"}, 400
    if not note:
        return {"error": "note is required"}, 400

    student = Student.query.get(int(student_id))
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    inter = Intervention(advisor_id=advisor.id, student_id=student.id, note=note)
    db.session.add(inter)
    db.session.commit()
    return {"ok": True, "id": inter.id}, 201


# -----------------------------
# Keep your existing endpoint
# -----------------------------
@bp.post("/advisor/students/<int:student_id>/interventions")
@jwt_required()
@advisor_required
def add_intervention(student_id: int):
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = Student.query.get(student_id)
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    data = request.get_json(force=True) or {}
    note = (data.get("note") or "").strip()
    if not note:
        return {"error": "Note required"}, 400

    inter = Intervention(advisor_id=advisor.id, student_id=student.id, note=note)
    db.session.add(inter)
    db.session.commit()
    return {"ok": True, "id": inter.id}, 201


@bp.post("/advisor/predict-risk")
@jwt_required()
@advisor_required
def trigger_predict():
    advisor = _advisor_from_token()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    created = run_batch_risk_prediction(student_ids=[s.id for s in advisor.students])
    return {"ok": True, "generated": created}, 200
