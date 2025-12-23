from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from ..models import User

bp = Blueprint("auth", __name__)

@bp.post("/login")
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return {"error": "Invalid email or password"}, 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )
    return {"access_token": access_token, "role": user.role}


@bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role")

    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}, 404

    payload = {"id": user.id, "email": user.email, "role": role}

    if role == "student" and user.student:
        payload["student_id"] = user.student.id
        payload["name"] = user.student.name

    if role == "advisor" and user.advisor:
        payload["advisor_id"] = user.advisor.id
        payload["name"] = user.advisor.name

    return payload
