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
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///pass.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    cors_origins = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

    db.init_app(app)
    jwt.init_app(app)

    # Import models so tables exist before create_all
    from . import models  # noqa: F401

    # Create tables for MVP (for class projects). For production, use migrations.
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
