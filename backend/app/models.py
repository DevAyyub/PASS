from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'advisor'

    student = db.relationship("Student", back_populates="user", uselist=False)
    advisor = db.relationship("Advisor", back_populates="user", uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Advisor(db.Model):
    __tablename__ = "advisors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)

    user = db.relationship("User", back_populates="advisor")
    students = db.relationship("Student", back_populates="advisor")

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey("advisors.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=True)
    cohort_year = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", back_populates="student")
    advisor = db.relationship("Advisor", back_populates="students")

    risk_scores = db.relationship("RiskScore", back_populates="student", order_by="desc(RiskScore.generated_at)")
    interventions = db.relationship("Intervention", back_populates="student", order_by="desc(Intervention.created_at)")

class RiskScore(db.Model):
    __tablename__ = "risk_scores"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    risk_probability = db.Column(db.Float, nullable=False)

    # store top feature importances as JSON (simple MVP XAI)
    top_factors_json = db.Column(db.Text, nullable=True)

    student = db.relationship("Student", back_populates="risk_scores")

class Intervention(db.Model):
    __tablename__ = "interventions"
    id = db.Column(db.Integer, primary_key=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey("advisors.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", back_populates="interventions")

class Resource(db.Model):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    topic_tag = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    type = db.Column(db.String(50), nullable=True)

class ExamBlueprint(db.Model):
    __tablename__ = "exam_blueprints"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, nullable=False, index=True)
    question_id = db.Column(db.Integer, nullable=False)
    topic_tag = db.Column(db.String(120), nullable=False)

    __table_args__ = (db.UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),)

class StudentResponse(db.Model):
    __tablename__ = "student_responses"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)

    __table_args__ = (db.UniqueConstraint("exam_id", "student_id", "question_id", name="uq_resp"),)
