from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import Student, RiskScore
from ..services.study_planner import build_study_plan_for_student

bp = Blueprint("student", __name__)

def require_role(role: str):
    claims = get_jwt()
    if claims.get("role") != role:
        return None, ({"error": "Forbidden"}, 403)

    user_id = int(get_jwt_identity())
    return {"user_id": user_id, "role": claims.get("role")}, None

@bp.get("/student/progress")
@jwt_required()
def student_progress():
    ident, err = require_role("student")
    if err:
        return err

    student = Student.query.filter_by(user_id=ident["user_id"]).first()
    if not student:
        return {"error": "Student profile missing"}, 404

    latest = student.risk_scores[0] if student.risk_scores else None

    # MVP: return minimal signals (extend later with grades/attendance tables)
    return {
        "student": {"student_id": student.id, "name": student.name},
        "latest_update": latest.generated_at.isoformat() if latest else None,
        "progress": {
            "assignments_completed_pct": 55,
            "attendance_pct": 78,
            "lms_logins_last_7d": 9,
        }
    }

@bp.get("/student/study-plan")
@jwt_required()
def student_study_plan():
    ident, err = require_role("student")
    if err:
        return err
    student = Student.query.filter_by(user_id=ident["user_id"]).first()
    if not student:
        return {"error": "Student profile missing"}, 404

    exam_id = request.args.get("exam_id", type=int)
    if not exam_id:
        return {"error": "exam_id is required"}, 400

    plan = build_study_plan_for_student(student_id=student.id, exam_id=exam_id)
    return plan
