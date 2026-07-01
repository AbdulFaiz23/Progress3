from ninja import Router, Query
from ninja.errors import HttpError
from typing import Optional
from lms.models import Course, Category, User
from lms.schemas import (
    CourseCreateSchema, CourseUpdateSchema,
    CourseDetailSchema, PaginatedCoursesSchema, MessageSchema
)
from lms.auth import JWTAuth, is_instructor, is_admin, check_course_owner

router = Router(tags=["Courses"])


def serialize_detail(course):
    return {
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
        "lessons": [
            {"id": l.id, "title": l.title, "order": l.order}
            for l in course.lesson_set.all()
        ],
    }


@router.get("", response=PaginatedCoursesSchema)
def list_courses(
    request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
):
    """List all courses dengan pagination dan filter."""
    qs = Course.objects.for_listing()
    if category_id:
        qs = qs.filter(category_id=category_id)
    if search:
        qs = qs.filter(title__icontains=search)
    total = qs.count()
    courses = qs[(page - 1) * page_size: page * page_size]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": c.id,
                "title": c.title,
                "instructor": {
                    "id": c.instructor.id,
                    "username": c.instructor.username,
                    "email": c.instructor.email,
                    "role": c.instructor.role,
                },
                "category": {
                    "id": c.category.id,
                    "name": c.category.name,
                    "parent_id": c.category.parent_id,
                },
                "total_lessons": c.total_lessons,
            }
            for c in courses
        ],
    }


@router.get("/{course_id}", response=CourseDetailSchema)
def get_course(request, course_id: int):
    """Get detail sebuah course."""
    try:
        course = (
            Course.objects
            .select_related("instructor", "category")
            .prefetch_related("lesson_set")
            .get(id=course_id)
        )
    except Course.DoesNotExist:
        raise HttpError(404, "Course not found")
    return serialize_detail(course)


@router.post("", response={201: CourseDetailSchema}, auth=JWTAuth())
@is_instructor
def create_course(request, payload: CourseCreateSchema):
    """Buat course baru."""
    instructor = request.auth
    try:
        category = Category.objects.get(id=payload.category_id)
    except Category.DoesNotExist:
        raise HttpError(404, "Category not found")
    course = Course.objects.create(
        title=payload.title,
        instructor=instructor,
        category=category,
    )
    course = (
        Course.objects
        .select_related("instructor", "category")
        .prefetch_related("lesson_set")
        .get(id=course.id)
    )
    return 201, serialize_detail(course)


@router.patch("/{course_id}", response=CourseDetailSchema, auth=JWTAuth())
def update_course(request, course_id: int, payload: CourseUpdateSchema):
    """Update course."""
    try:
        course = (
            Course.objects
            .select_related("instructor", "category")
            .prefetch_related("lesson_set")
            .get(id=course_id)
        )
    except Course.DoesNotExist:
        raise HttpError(404, "Course not found")

    check_course_owner(request, course)

    if payload.title is not None:
        course.title = payload.title
    if payload.category_id is not None:
        try:
            course.category = Category.objects.get(id=payload.category_id)
        except Category.DoesNotExist:
            raise HttpError(404, "Category not found")
    course.save()
    return serialize_detail(course)


@router.delete("/{course_id}", response=MessageSchema, auth=JWTAuth())
@is_admin
def delete_course(request, course_id: int):
    """Hapus course."""
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course not found")
    title = course.title
    course.delete()
    return {"message": f"Course '{title}' deleted successfully"}