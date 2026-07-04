from ninja import Router
from ninja.errors import HttpError
from typing import List
from lms.models import Course, Enrollment, Progress, Lesson, User
from lms.schemas import (
    EnrollSchema, ProgressUpdateSchema,
    EnrolledCourseSchema, MessageSchema
)
from lms.auth import JWTAuth, is_student
from lms.mongo import log_activity, update_learning_analytics
from lms.tasks import send_enrollment_email, generate_certificate
from lms.api_courses import invalidate_course_cache

router = Router(tags=["Enrollments"])


@router.post("", response={201: dict}, auth=JWTAuth())
@is_student
def enroll_course(request, payload: EnrollSchema):
    """Daftarkan student ke course."""
    student = request.auth
    try:
        course = Course.objects.get(id=payload.course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course not found")
    if Enrollment.objects.filter(student=student, course=course).exists():
        raise HttpError(400, "Already enrolled in this course")
    enrollment = Enrollment.objects.create(student=student, course=course)
    invalidate_course_cache(course.id)
    
    log_activity(
        user=student,
        action="ENROLLMENT_CREATED",
        resource_type="course",
        resource_id=course.id,
        metadata={"course_title": course.title},
        request=request
    )
    send_enrollment_email.delay(student.email, course.title)
    
    return 201, {
        "message": f"Successfully enrolled in '{course.title}'",
        "enrollment_id": enrollment.id,
    }


@router.get("/my-courses", response=List[EnrolledCourseSchema], auth=JWTAuth())
def my_courses(request):
    """Lihat semua course yang diikuti student."""
    student = request.auth

    enrollments = Enrollment.objects.for_student_dashboard().filter(student=student)
    
    # Fetch all progresses for this student to avoid N+1
    all_progresses = Progress.objects.filter(student=student)
    prog_map = {p.lesson_id: p for p in all_progresses}
    
    result = []
    for enrollment in enrollments:
        course = enrollment.course
        lessons = list(course.lesson_set.all())
        progresses = {l.id: prog_map[l.id] for l in lessons if l.id in prog_map}
        course.total_lessons = len(lessons)
        result.append({
            "enrollment_id": enrollment.id,
            "course": {
                "id": course.id,
                "title": course.title,
                "instructor": {
                    "id": course.instructor.id,
                    "username": course.instructor.username,
                    "email": course.instructor.email,
                    "role": course.instructor.role,
                },
                "category": {
                    "id": course.category.id,
                    "name": course.category.name,
                    "parent_id": course.category.parent_id,
                },
                "total_lessons": course.total_lessons,
            },
            "enrolled_at": enrollment.enrolled_at,
            "progress": [
                {
                    "lesson_id": l.id,
                    "lesson_title": l.title,
                    "completed": progresses[l.id].completed if l.id in progresses else False,
                }
                for l in lessons
            ],
        })
    return result


@router.post("/{enrollment_id}/progress", response=dict, auth=JWTAuth())
@is_student
def mark_progress(request, enrollment_id: int, payload: ProgressUpdateSchema):
    """Mark lesson sebagai selesai atau belum."""
    try:
        enrollment = Enrollment.objects.select_related("course", "student").get(id=enrollment_id)
    except Enrollment.DoesNotExist:
        raise HttpError(404, "Enrollment not found")
        
    if enrollment.student != request.auth:
        raise HttpError(403, "Not your enrollment")

    try:
        lesson = Lesson.objects.get(id=payload.lesson_id, course=enrollment.course)
    except Lesson.DoesNotExist:
        raise HttpError(404, "Lesson not found in this course")

    student = request.auth

    progress, created = Progress.objects.get_or_create(
        student=student,
        lesson=lesson,
        defaults={"completed": payload.completed},
    )
    if not created:
        progress.completed = payload.completed
        progress.save()

    total = Lesson.objects.filter(course=enrollment.course).count()
    completed = Progress.objects.filter(
        student=student, lesson__course=enrollment.course, completed=True
    ).count()
    pct = round((completed / total * 100) if total > 0 else 0, 1)
    
    log_activity(
        user=student,
        action="PROGRESS_UPDATED",
        resource_type="lesson",
        resource_id=lesson.id,
        metadata={"completed": payload.completed, "course_id": enrollment.course.id},
        request=request
    )
    update_learning_analytics(student.id, enrollment.course.id, total, completed, lesson_id=lesson.id)

    if pct == 100.0 and payload.completed:
        generate_certificate.delay(student.username, enrollment.course.title)

    invalidate_course_cache(enrollment.course.id)

    return {
        "message": "Progress updated",
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "completed": progress.completed,
        "course_completion": f"{pct}%",
    }