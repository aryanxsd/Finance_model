import tempfile
import unittest
from pathlib import Path

from finance_api import create_app


class FinanceApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test_finance.db"
        self.app = create_app({"TESTING": True, "DATABASE_PATH": str(database_path)})
        self.client = self.app.test_client()
        self.admin_headers = {"Authorization": "Bearer admin-token"}
        self.analyst_headers = {"Authorization": "Bearer analyst-token"}
        self.viewer_headers = {"Authorization": "Bearer viewer-token"}

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_viewer_can_access_dashboard_but_not_records(self):
        summary_response = self.client.get("/api/dashboard/summary", headers=self.viewer_headers)
        self.assertEqual(summary_response.status_code, 200)

        records_response = self.client.get("/api/records", headers=self.viewer_headers)
        self.assertEqual(records_response.status_code, 403)

        users_response = self.client.get("/api/users", headers=self.viewer_headers)
        self.assertEqual(users_response.status_code, 403)

    def test_analyst_can_filter_records(self):
        response = self.client.get(
            "/api/records?type=income&category=Salary",
            headers=self.analyst_headers,
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["data"][0]["category"], "Salary")

    def test_records_endpoint_supports_pagination_and_search(self):
        response = self.client.get(
            "/api/records?search=consulting&page=1&page_size=2",
            headers=self.analyst_headers,
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["pagination"]["page"], 1)
        self.assertEqual(payload["pagination"]["page_size"], 2)
        self.assertEqual(payload["filters"]["search"], "consulting")
        self.assertEqual(payload["data"][0]["notes"], "API consulting")

    def test_admin_can_create_and_update_record(self):
        create_response = self.client.post(
            "/api/records",
            headers=self.admin_headers,
            json={
                "amount": 3000,
                "type": "income",
                "category": "Investments",
                "date": "2026-03-20",
                "notes": "Mutual fund redemption",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        record_id = create_response.get_json()["data"]["id"]

        update_response = self.client.patch(
            f"/api/records/{record_id}",
            headers=self.admin_headers,
            json={"notes": "Updated note"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.get_json()["data"]["notes"], "Updated note")

    def test_admin_can_delete_record_with_soft_delete_behavior(self):
        create_response = self.client.post(
            "/api/records",
            headers=self.admin_headers,
            json={
                "amount": 410,
                "type": "expense",
                "category": "Meals",
                "date": "2026-03-18",
                "notes": "Team lunch",
            },
        )
        record_id = create_response.get_json()["data"]["id"]

        delete_response = self.client.delete(f"/api/records/{record_id}", headers=self.admin_headers)
        self.assertEqual(delete_response.status_code, 200)

        get_response = self.client.get(f"/api/records/{record_id}", headers=self.analyst_headers)
        self.assertEqual(get_response.status_code, 404)

    def test_analyst_cannot_create_record(self):
        response = self.client.post(
            "/api/records",
            headers=self.analyst_headers,
            json={
                "amount": 100,
                "type": "expense",
                "category": "Food",
                "date": "2026-03-20",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_validation_errors_return_400(self):
        response = self.client.post(
            "/api/records",
            headers=self.admin_headers,
            json={
                "amount": -10,
                "type": "expense",
                "category": "Food",
                "date": "2026-03-20",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Amount", response.get_json()["error"]["message"])

    def test_invalid_pagination_returns_400(self):
        response = self.client.get(
            "/api/records?page=0&page_size=200",
            headers=self.analyst_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_manage_users(self):
        create_response = self.client.post(
            "/api/users",
            headers=self.admin_headers,
            json={
                "name": "Riya Ops",
                "email": "riya@example.com",
                "role": "viewer",
                "status": "active",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        new_user_id = create_response.get_json()["data"]["id"]

        patch_response = self.client.patch(
            f"/api/users/{new_user_id}",
            headers=self.admin_headers,
            json={"role": "analyst"},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.get_json()["data"]["role"], "analyst")

        get_response = self.client.get(f"/api/users/{new_user_id}", headers=self.admin_headers)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.get_json()["data"]["email"], "riya@example.com")

    def test_authenticated_user_can_fetch_profile(self):
        response = self.client.get("/api/users/me", headers=self.analyst_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["role"], "analyst")

    def test_dashboard_summary_matches_seeded_data(self):
        response = self.client.get("/api/dashboard/summary", headers=self.analyst_headers)
        payload = response.get_json()["data"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["total_income"], 18800.0)
        self.assertEqual(payload["total_expenses"], 3170.5)
        self.assertEqual(payload["net_balance"], 15629.5)

    def test_dashboard_recent_activity_and_trends_are_available(self):
        recent_response = self.client.get("/api/dashboard/recent-activity?limit=3", headers=self.viewer_headers)
        self.assertEqual(recent_response.status_code, 200)
        self.assertEqual(recent_response.get_json()["count"], 3)

        trends_response = self.client.get("/api/dashboard/trends", headers=self.viewer_headers)
        trends_payload = trends_response.get_json()
        self.assertEqual(trends_response.status_code, 200)
        self.assertGreaterEqual(trends_payload["count"], 1)
        self.assertIn("month", trends_payload["data"][0])
        self.assertIn("net_balance", trends_payload["data"][0])

    def test_rate_limit_returns_429_after_threshold(self):
        limited_app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(Path(self.temp_dir.name) / "rate_limit.db"),
                "RATE_LIMIT_MAX_REQUESTS": 2,
                "RATE_LIMIT_WINDOW_SECONDS": 60,
            }
        )
        client = limited_app.test_client()
        headers = {"Authorization": "Bearer analyst-token"}

        first = client.get("/api/dashboard/summary", headers=headers)
        second = client.get("/api/dashboard/summary", headers=headers)
        third = client.get("/api/dashboard/summary", headers=headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)
        self.assertEqual(third.get_json()["error"]["details"]["limit"], 2)

    def test_inactive_user_token_is_rejected(self):
        create_response = self.client.post(
            "/api/users",
            headers=self.admin_headers,
            json={
                "name": "Dormant User",
                "email": "dormant@example.com",
                "role": "viewer",
                "status": "inactive",
            },
        )
        token = create_response.get_json()["data"]["api_token"]
        response = self.client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
