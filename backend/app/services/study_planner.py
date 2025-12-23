from collections import defaultdict
from ..models import ExamBlueprint, StudentResponse, Resource
from .. import db

def build_study_plan_for_student(student_id: int, exam_id: int) -> dict:
    # Load blueprint: question -> topic
    blueprint = ExamBlueprint.query.filter_by(exam_id=exam_id).all()
    if not blueprint:
        return {"error": "No blueprint found for exam_id"}, 404

    q_to_topic = {b.question_id: b.topic_tag for b in blueprint}

    responses = StudentResponse.query.filter_by(exam_id=exam_id, student_id=student_id).all()
    if not responses:
        return {"error": "No responses found for this exam/student"}, 404

    stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in responses:
        topic = q_to_topic.get(r.question_id, "Unknown")
        stats[topic]["total"] += 1
        stats[topic]["correct"] += 1 if r.is_correct else 0

    topic_scores = []
    for topic, s in stats.items():
        pct = 0.0 if s["total"] == 0 else (s["correct"] / s["total"]) * 100.0
        topic_scores.append({"topic": topic, "score_pct": round(pct, 1), "correct": s["correct"], "total": s["total"]})

    topic_scores.sort(key=lambda x: x["score_pct"], reverse=True)

    strengths = [t for t in topic_scores if t["score_pct"] >= 80]
    focus = [t for t in topic_scores if t["score_pct"] < 60]

    # attach resources for focus areas
    focus_with_resources = []
    for t in focus:
        resources = Resource.query.filter_by(topic_tag=t["topic"]).limit(5).all()
        focus_with_resources.append({
            **t,
            "resources": [{"title": r.title, "url": r.url, "type": r.type} for r in resources]
        })

    return {
        "exam_id": exam_id,
        "summary": {
            "strengths": strengths[:3],
            "areas_for_focus": focus_with_resources[:3],
        },
        "all_topics": topic_scores
    }
