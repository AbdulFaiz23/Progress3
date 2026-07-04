from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from lms.models import User, Category, Course, Enrollment, Lesson, Progress
import json
from unittest.mock import patch

class EnrollmentsAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.instructor = User.objects.create_user(username="instructor", password="pw", role="instructor")
        self.instructor2 = User.objects.create_user(username="instructor2", password="pw", role="instructor")
        self.student = User.objects.create_user(username="student", password="pw", role="student")
        
        # Get tokens
        resp = self.client.post("/api/auth/login", json.dumps({"username": "student", "password": "pw"}), content_type="application/json")
        self.student_token = resp.json()["access_token"]
        
        self.category1 = Category.objects.create(name="Cat 1")
        self.category2 = Category.objects.create(name="Cat 2")

    def test_my_courses_no_n_plus_one(self):
        """Test GET /api/enrollments/my-courses does not have N+1 issue"""
        # Create 3 courses and enrollments
        for i in range(3):
            c = Course.objects.create(
                title=f"Course {i}", 
                instructor=self.instructor, 
                category=self.category1
            )
            Enrollment.objects.create(student=self.student, course=c)
        
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/enrollments/my-courses", **auth_headers)
        self.assertEqual(response.status_code, 200)
        query_count_3 = len(ctx.captured_queries)

        # Add 3 more courses and enrollments (total 6)
        for i in range(3, 6):
            c = Course.objects.create(
                title=f"Course {i}", 
                instructor=self.instructor2, 
                category=self.category2
            )
            Enrollment.objects.create(student=self.student, course=c)
            
        with CaptureQueriesContext(connection) as ctx2:
            response2 = self.client.get("/api/enrollments/my-courses", **auth_headers)
        self.assertEqual(response2.status_code, 200)
        query_count_6 = len(ctx2.captured_queries)

        # The query count should be the same (not increasing with enrollments)
        self.assertEqual(query_count_3, query_count_6)

    @patch('lms.api_enrollments.update_learning_analytics')
    def test_enroll_and_progress_invalidate_cache(self, mock_analytics):
        from django.core.cache import cache
        c = Course.objects.create(title="Test Cache Course", instructor=self.instructor, category=self.category1)
        l = Lesson.objects.create(course=c, title="Lesson 1", order=1)
        
        cache_key = f"course:detail:{c.id}"
        cache.set(cache_key, {"test": "data"})
        self.assertIsNotNone(cache.get(cache_key))
        
        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        # Enroll should invalidate
        resp = self.client.post("/api/enrollments", json.dumps({"course_id": c.id}), content_type="application/json", **auth_headers)
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(cache.get(cache_key))
        
        cache.set(cache_key, {"test": "data2"})
        # Mark progress should invalidate
        resp = self.client.post(f"/api/enrollments/{resp.json()['enrollment_id']}/progress", json.dumps({"lesson_id": l.id, "completed": True}), content_type="application/json", **auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(cache.get(cache_key))
        
        # Verify analytics was updated with lesson_id
        mock_analytics.assert_called()
        self.assertEqual(mock_analytics.call_args[1].get('lesson_id'), l.id)
