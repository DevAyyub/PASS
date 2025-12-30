from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

def role_required(required_role: str):
    """
    Enforces JWT + role check. Use as decorator:
    @role_required("advisor") or @role_required("student")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role != required_role:
                return {"error": "Forbidden"}, 403

            # keep for convenience if you want later
            _ = get_jwt_identity()
            return fn(*args, **kwargs)
        return wrapper
    return decorator

advisor_required = role_required("advisor")
student_required = role_required("student")
