# backend/app/services/authz.py
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in allowed_roles:
                return jsonify({"error": "forbidden", "details": "insufficient role"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

advisor_required = role_required("advisor")
student_required = role_required("student")

def current_user_id():
    # whatever you set as identity in create_access_token(...)
    return get_jwt_identity()
