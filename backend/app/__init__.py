import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    load_dotenv()

    app = Flask(__name__)

    # --- Core config ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///pass.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- N+1 verification (prints SQL when SQL_ECHO=1) ---
    app.config["SQLALCHEMY_ECHO"] = os.getenv("SQL_ECHO", "0") == "1"

    # --- CORS ---
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    cors_origins = [o.strip() for o in cors_origins if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

    # --- Init extensions ---
    db.init_app(app)
    jwt.init_app(app)

    # --- JWT error responses (JSON) ---
    @jwt.unauthorized_loader
    def _missing_token(msg):
        return {"error": "Missing Authorization Header"}, 401

    @jwt.invalid_token_loader
    def _invalid_token(msg):
        return {"error": "Invalid token"}, 422

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_payload):
        return {"error": "Token expired"}, 401

    # Import models so tables exist before create_all
    from . import models  # noqa: F401

    with app.app_context():
        db.create_all()

    # Register blueprints
    from .routes.auth import bp as auth_bp
    from .routes.advisor import bp as advisor_bp
    from .routes.student import bp as student_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(advisor_bp, url_prefix="/api")
    app.register_blueprint(student_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
