from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Count


# ================= USER =================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


# ================= CATEGORY =================
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name


# ================= CUSTOM QUERYSET =================
class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        return self.select_related('instructor', 'category') \
                   .prefetch_related('lesson_set') \
                   .annotate(total_lessons=Count('lesson'))


class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self):
        return self.select_related('student', 'course', 'course__instructor', 'course__category') \
                   .prefetch_related('course__lesson_set')


# ================= COURSE =================
class Course(models.Model):
    title = models.CharField(max_length=200)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    objects = CourseQuerySet.as_manager()

    def __str__(self):
        return self.title


# ================= LESSON =================
class Lesson(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        ordering = ['order']


# ================= ENROLLMENT =================
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        unique_together = ('student', 'course')


# ================= PROGRESS =================
class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
