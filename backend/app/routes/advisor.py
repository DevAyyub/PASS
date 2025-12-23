import json
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import Advisor, Student, RiskScore, Intervention
from .. import db
from ..services.predict import run_batch_risk_prediction

bp = Blueprint("advisor", __name__)

def require_role(role: str):
    claims = get_jwt()
    if claims.get("role") != role:
        return None, ({"error": "Forbidden"}, 403)

    user_id = int(get_jwt_identity())
    return {"user_id": user_id, "role": claims.get("role")}, None

@bp.get("/advisor/students")
@jwt_required()
def advisor_students():
    ident, err = require_role("advisor")
    if err:
        return err
    advisor = Advisor.query.filter_by(user_id=ident["user_id"]).first()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    # Get latest risk score per student (simple approach for MVP)
    result = []
    for s in advisor.students:
        latest = s.risk_scores[0] if s.risk_scores else None
        result.append({
            "student_id": s.id,
            "name": s.name,
            "department": s.department,
            "risk_probability": latest.risk_probability if latest else None,
            "risk_generated_at": latest.generated_at.isoformat() if latest else None,
        })

    # sort: None last
    result.sort(key=lambda x: (x["risk_probability"] is None, -(x["risk_probability"] or -1)))
    return {"students": result}

@bp.get("/advisor/students/<int:student_id>")
@jwt_required()
def advisor_student_detail(student_id: int):
    ident, err = require_role("advisor")
    if err:
        return err
    advisor = Advisor.query.filter_by(user_id=ident["user_id"]).first()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = Student.query.get(student_id)
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    latest = student.risk_scores[0] if student.risk_scores else None
    interventions = [
        {"id": i.id, "note": i.note, "created_at": i.created_at.isoformat()}
        for i in student.interventions[:20]
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
            "cohort_year": student.cohort_year
        },
        "latest_risk": {
            "risk_probability": latest.risk_probability if latest else None,
            "generated_at": latest.generated_at.isoformat() if latest else None,
            "top_factors": xai,
        },
        "interventions": interventions
    }

@bp.post("/advisor/students/<int:student_id>/interventions")
@jwt_required()
def add_intervention(student_id: int):
    ident, err = require_role("advisor")
    if err:
        return err
    advisor = Advisor.query.filter_by(user_id=ident["user_id"]).first()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    student = Student.query.get(student_id)
    if not student or student.advisor_id != advisor.id:
        return {"error": "Student not found"}, 404

    data = request.get_json(force=True)
    note = (data.get("note") or "").strip()
    if not note:
        return {"error": "Note required"}, 400

    inter = Intervention(advisor_id=advisor.id, student_id=student.id, note=note)
    db.session.add(inter)
    db.session.commit()
    return {"ok": True, "id": inter.id}

@bp.post("/advisor/predict-risk")
@jwt_required()
def trigger_predict():
    ident, err = require_role("advisor")
    if err:
        return err
    advisor = Advisor.query.filter_by(user_id=ident["user_id"]).first()
    if not advisor:
        return {"error": "Advisor profile missing"}, 404

    # For demo, only predict for advisor's students
    created = run_batch_risk_prediction(student_ids=[s.id for s in advisor.students])
    return {"ok": True, "generated": created}
