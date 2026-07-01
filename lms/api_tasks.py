from ninja import Router
from celery.result import AsyncResult
from lms.auth import JWTAuth, is_instructor, is_admin
from lms.tasks import export_course_report
from lms.models import Course
from django.shortcuts import get_object_or_404

router = Router()

@router.get("/{task_id}/status", auth=JWTAuth())
def get_task_status(request, task_id: str):
    """
    Check the status of a Celery task.
    """
    res = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None
    }

@router.post("/courses/{course_id}/export-report", auth=JWTAuth())
def export_report(request, course_id: int):
    """
    Triggers an async task to generate a course report.
    Accessible to admins and instructors (who own the course).
    """
    if request.auth.role not in ['admin', 'instructor']:
        return 403, {"detail": "Admin or Instructor access required"}

    course = get_object_or_404(Course, id=course_id)
    
    if request.auth.role == 'instructor' and course.instructor != request.auth:
        return 403, {"detail": "You don't own this course"}

    # Trigger async task
    task = export_course_report.delay(course.id)
    
    # Return 202 Accepted immediately
    return 202, {"task_id": task.id, "message": "Report generation started"}
