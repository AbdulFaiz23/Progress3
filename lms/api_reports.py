from ninja import Router
from lms.auth import JWTAuth, is_instructor, is_admin
from lms.mongo import get_mongo_db

router = Router()

@router.get("/course-popularity", auth=JWTAuth())
def get_course_popularity(request):
    """
    Returns course popularity based on ENROLLMENT_CREATED activity logs.
    Accessible to admins and instructors.
    """
    if request.auth.role not in ['admin', 'instructor']:
        return 403, {"detail": "Admin or Instructor access required"}

    db = get_mongo_db()
    if db is None:
        return 500, {"detail": "Analytics database unavailable"}

    pipeline = [
        {"$match": {"action": "ENROLLMENT_CREATED"}},
        {"$group": {
            "_id": "$resource_id",
            "enrollment_count": {"$sum": 1},
            "course_title": {"$first": "$metadata.course_title"}
        }},
        {"$sort": {"enrollment_count": -1}}
    ]

    results = list(db.activity_logs.aggregate(pipeline))
    return {"data": results}


@router.get("/student-engagement", auth=JWTAuth())
def get_student_engagement(request):
    """
    Returns average completion percentage per course.
    Accessible to admins and instructors.
    """
    if request.auth.role not in ['admin', 'instructor']:
        return 403, {"detail": "Admin or Instructor access required"}

    db = get_mongo_db()
    if db is None:
        return 500, {"detail": "Analytics database unavailable"}

    pipeline = [
        {"$group": {
            "_id": "$course_id",
            "average_completion": {"$avg": "$completion_percentage"},
            "total_students": {"$sum": 1}
        }},
        {"$sort": {"average_completion": -1}}
    ]

    results = list(db.learning_analytics.aggregate(pipeline))
    return {"data": results}
