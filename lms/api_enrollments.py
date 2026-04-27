from ninja import Router
from ninja.errors import HttpError
from typing import List
from lms.models import Course, Enrollment, Progress, Lesson, User
from lms.schemas import (
    EnrollSchema, ProgressUpdateSchema,
    EnrolledCourseSchema, MessageSchema
)

router = Router(tags=["Enrollments"])


@router.post("", response={201: dict})
def enroll_course(request, payload: EnrollSchema):
    """Daftarkan student ke course."""
    try:
        student = User.objects.get(id=payload.student_id)
    except User.DoesNotExist:
        raise HttpError(404, "Student not found")
    try:
        course = Course.objects.get(id=payload.course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course not found")
    if Enrollment.objects.filter(student=student, course=course).exists():
        raise HttpError(400, "Already enrolled in this course")
    enrollment = Enrollment.objects.create(student=student, course=course)
    return 201, {
        "message": f"Successfully enrolled in '{course.title}'",
        "enrollment_id": enrollment.id,
    }


@router.get("/student/{student_id}", response=List[EnrolledCourseSchema])
def my_courses(request, student_id: int):
    """Lihat semua course yang diikuti student."""
    try:
        student = User.objects.get(id=student_id)
    except User.DoesNotExist:
        raise HttpError(404, "Student not found")

    enrollments = Enrollment.objects.for_student_dashboard().filter(student=student)
    result = []
    for enrollment in enrollments:
        course = enrollment.course
        lessons = list(course.lesson_set.all())
        progresses = {p.lesson_id: p for p in enrollment.progress_set.all()}
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


@router.post("/{enrollment_id}/progress", response=dict)
def mark_progress(request, enrollment_id: int, payload: ProgressUpdateSchema):
    """Mark lesson sebagai selesai atau belum."""
    try:
        enrollment = Enrollment.objects.select_related("course").get(id=enrollment_id)
    except Enrollment.DoesNotExist:
        raise HttpError(404, "Enrollment not found")
    try:
        lesson = Lesson.objects.get(id=payload.lesson_id, course=enrollment.course)
    except Lesson.DoesNotExist:
        raise HttpError(404, "Lesson not found in this course")
    try:
        student = User.objects.get(id=payload.student_id)
    except User.DoesNotExist:
        raise HttpError(404, "Student not found")

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

    return {
        "message": "Progress updated",
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "completed": progress.completed,
        "course_completion": f"{pct}%",
    }