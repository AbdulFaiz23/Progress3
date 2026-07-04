from ninja import Router
from ninja.errors import HttpError
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
        raise HttpError(403, "Admin or Instructor access required")

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
        raise HttpError(403, "Admin or Instructor access required")

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

@router.get("/daily-active-users", auth=JWTAuth())
def daily_active_users(request):
    if request.auth.role not in ['admin', 'instructor']:
        raise HttpError(403, "Admin or Instructor access required")

    db = get_mongo_db()
    if db is None:
        return 500, {"detail": "Analytics database unavailable"}

    pipeline = [
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": "$timestamp"}}},
                    "user_id": "$user_id"
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.date",
                "active_users": {"$sum": 1}
            }
        },
        {"$sort": {"_id": -1}},
        {"$limit": 30}
    ]
    
    result = list(db.activity_logs.aggregate(pipeline))
    return [{"date": r["_id"], "active_users": r["active_users"]} for r in result]
