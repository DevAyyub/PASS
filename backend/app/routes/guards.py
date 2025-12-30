from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity


def role_required(required_role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") != required_role:
                return {"error": "Forbidden"}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


advisor_required = role_required("advisor")
student_required = role_required("student")


def current_user_id() -> int:
    return int(get_jwt_identity())
