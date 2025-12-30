from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models import Student, RiskScore
from ..services.study_planner import build_study_plan_for_student
from .guards import student_required

bp = Blueprint("student", __name__)

def _student_from_token():
    user_id = int(get_jwt_identity())
    student = Student.query.filter_by(user_id=user_id).first()
    return student

def _latest_risk(student_id: int):
    return (
        RiskScore.query
        .filter_by(student_id=student_id)
        .order_by(RiskScore.generated_at.desc())
        .first()
    )

# NEW: contract alias
@bp.get("/student/dashboard")
@jwt_required()
@student_required
def student_dashboard():
    return student_progress()

@bp.get("/student/progress")
@jwt_required()
@student_required
def student_progress():
    student = _student_from_token()
    if not student:
        return {"error": "Student profile missing"}, 404

    latest = _latest_risk(student.id)

    return {
        "student": {"student_id": student.id, "name": student.name},
        "latest_update": latest.generated_at.isoformat() if latest else None,
        "latest_risk": float(latest.risk_probability) if latest else None,
        "progress": {
            "assignments_completed_pct": 55,
            "attendance_pct": 78,
            "lms_logins_last_7d": 9,
        }
    }, 200


@bp.get("/student/study-plan")
@jwt_required()
@student_required
def student_study_plan():
    student = _student_from_token()
    if not student:
        return {"error": "Student profile missing"}, 404

    exam_id = request.args.get("exam_id", type=int)
    if not exam_id:
        return {"error": "exam_id is required"}, 400

    plan = build_study_plan_for_student(student_id=student.id, exam_id=exam_id)
    return plan, 200


# Optional endpoint (no DB changes). It just accepts feedback so frontend can call it.
@bp.post("/student/study-plan/feedback")
@jwt_required()
@student_required
def study_plan_feedback():
    student = _student_from_token()
    if not student:
        return {"error": "Student profile missing"}, 404

    data = request.get_json(force=True) or {}
    # Accept anything for now (demo-safe)
    return {"ok": True, "received": data}, 200
