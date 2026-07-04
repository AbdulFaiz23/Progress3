from django.test import TestCase, Client
from lms.models import User
import json
from unittest.mock import patch, MagicMock

class ReportsAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="pw", role="admin")
        self.student = User.objects.create_user(username="student", password="pw", role="student")
        
        # Get tokens
        resp = self.client.post("/api/auth/login", json.dumps({"username": "admin", "password": "pw"}), content_type="application/json")
        self.admin_token = resp.json()["access_token"]
        
        resp = self.client.post("/api/auth/login", json.dumps({"username": "student", "password": "pw"}), content_type="application/json")
        self.student_token = resp.json()["access_token"]

    @patch('lms.api_reports.get_mongo_db')
    def test_daily_active_users(self, mock_db):
        """Test GET /api/reports/daily-active-users returns aggregated data"""
        mock_mongo = MagicMock()
        mock_db.return_value = mock_mongo
        mock_mongo.activity_logs.aggregate.return_value = [
            {"_id": "2026-07-04", "active_users": 5},
            {"_id": "2026-07-03", "active_users": 10},
        ]

        auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        response = self.client.get("/api/reports/daily-active-users", **auth_headers)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["date"], "2026-07-04")
        self.assertEqual(data[0]["active_users"], 5)
        
        # Student should be rejected
        auth_headers_student = {"HTTP_AUTHORIZATION": f"Bearer {self.student_token}"}
        response2 = self.client.get("/api/reports/daily-active-users", **auth_headers_student)
        self.assertEqual(response2.status_code, 403)
