"""Seed a small demo dataset so the app works immediately.

Usage:
  1) Ensure Postgres is running
  2) cd backend
  3) python scripts/seed_demo.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db
from app.models import User, Advisor, Student, Resource, ExamBlueprint, StudentResponse

app = create_app()

def upsert_user(email: str, password: str, role: str):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(email=email, role=role, password_hash="")
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
    return u

with app.app_context():
    # Advisor
    u_adv = upsert_user("advisor@pass.local", "advisor123", "advisor")
    adv = Advisor.query.filter_by(user_id=u_adv.id).first()
    if not adv:
        adv = Advisor(user_id=u_adv.id, name="Dr. Advisor")
        db.session.add(adv)
        db.session.flush()

    # Students
    students = []
    for i, name in enumerate(["Alex Student", "Sam Learner", "Mina Kim", "Omar Ali"], start=1):
        email = f"student{i}@pass.local"
        u_stu = upsert_user(email, "student123", "student")
        stu = Student.query.filter_by(user_id=u_stu.id).first()
        if not stu:
            stu = Student(user_id=u_stu.id, advisor_id=adv.id, name=name, department="CENG", cohort_year=2023)
            db.session.add(stu)
            db.session.flush()
        students.append(stu)

    # Resources
    demo_resources = [
        ("Algorithms", "Big-O Notation (Video)", "https://www.youtube.com/watch?v=V6mKVRU1evU", "video"),
        ("Algorithms", "Sorting Practice (Quiz)", "https://www.hackerrank.com/domains/algorithms", "practice"),
        ("Data Structures", "Stacks & Queues (Article)", "https://www.geeksforgeeks.org/stack-data-structure/", "article"),
        ("Graphs", "Graph Traversal (Video)", "https://www.youtube.com/watch?v=tWVWeAqZ0WU", "video"),
    ]
    for topic, title, url, typ in demo_resources:
        if not Resource.query.filter_by(topic_tag=topic, title=title).first():
            db.session.add(Resource(topic_tag=topic, title=title, url=url, type=typ))

    # Exam blueprint and responses (exam_id=1)
    blueprint = [
        (1, "Data Structures"),
        (2, "Algorithms"),
        (3, "Algorithms"),
        (4, "Graphs"),
        (5, "Data Structures"),
    ]
    for qid, topic in blueprint:
        if not ExamBlueprint.query.filter_by(exam_id=1, question_id=qid).first():
            db.session.add(ExamBlueprint(exam_id=1, question_id=qid, topic_tag=topic))

    # Responses for student1 (Alex): good at DS, weak at Algorithms
    s1 = students[0]
    resp = {1: True, 2: False, 3: False, 4: True, 5: True}
    for qid, is_correct in resp.items():
        if not StudentResponse.query.filter_by(exam_id=1, student_id=s1.id, question_id=qid).first():
            db.session.add(StudentResponse(exam_id=1, student_id=s1.id, question_id=qid, is_correct=is_correct))

    db.session.commit()
    print("Seed complete.")
    print("Login accounts:")
    print("  Advisor: advisor@pass.local / advisor123")
    print("  Student1: student1@pass.local / student123")
