from ninja import NinjaAPI
from lms.api_courses import router as courses_router
from lms.api_enrollments import router as enrollments_router

api = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="REST API untuk Simple LMS menggunakan Django Ninja",
    docs_url="/docs",
)

api.add_router("/courses/", courses_router)
api.add_router("/enrollments/", enrollments_router)