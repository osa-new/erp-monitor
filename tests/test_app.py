"""
Basic test suite for ERP Monitor.
Run with:  pytest tests/ -v
"""
import pytest
import json
from app import create_app, db as _db


@pytest.fixture(scope="session")
def app():
    """Create a test Flask app with an in-memory SQLite DB."""
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("SECRET_KEY", "test-secret")
    os.environ.setdefault("API_KEY", "test-api-key")
    os.environ.setdefault("ADMIN_PASSWORD", "testpass")

    application = create_app()
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    # Stop the background scheduler during tests
    if application.extensions.get("scheduler"):
        try:
            application.extensions["scheduler"].shutdown()
        except Exception:
            pass

    with application.app_context():
        _db.create_all()
        yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers():
    return {"X-API-Key": "test-api-key", "Content-Type": "application/json"}


# ── Auth ────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_get_token_with_credentials(self, client):
        res = client.post("/auth/token", json={"username": "admin", "password": "testpass"})
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data

    def test_get_token_with_api_key(self, client, auth_headers):
        res = client.post("/auth/token", headers=auth_headers)
        assert res.status_code == 200

    def test_get_token_bad_credentials(self, client):
        res = client.post("/auth/token", json={"username": "admin", "password": "wrong"})
        assert res.status_code == 401

    def test_protected_route_no_auth(self, client):
        res = client.get("/api/endpoints")
        assert res.status_code == 401

    def test_protected_route_with_api_key(self, client, auth_headers):
        res = client.get("/api/endpoints", headers=auth_headers)
        assert res.status_code == 200

    def test_protected_route_with_jwt(self, client):
        token_res = client.post("/auth/token", json={"username": "admin", "password": "testpass"})
        token = token_res.get_json()["access_token"]
        res = client.get("/api/endpoints", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200


# ── Endpoints CRUD ──────────────────────────────────────────────────────────

class TestEndpoints:
    def test_list_empty(self, client, auth_headers, app):
        # Clear seeded data for isolation
        with app.app_context():
            from app.models import MonitoredEndpoint
            MonitoredEndpoint.query.delete()
            _db.session.commit()

        res = client.get("/api/endpoints", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json() == []

    def test_create_endpoint(self, client, auth_headers):
        res = client.post("/api/endpoints", headers=auth_headers, json={
            "name": "Test Service",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "expected_status": 200,
            "timeout": 5,
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Test Service"
        assert data["status"] == "unknown"
        return data["id"]

    def test_create_endpoint_missing_fields(self, client, auth_headers):
        res = client.post("/api/endpoints", headers=auth_headers, json={"name": "No URL"})
        assert res.status_code == 400

    def test_get_endpoint(self, client, auth_headers):
        create = client.post("/api/endpoints", headers=auth_headers, json={
            "name": "Fetch Me", "url": "https://example.com"
        })
        ep_id = create.get_json()["id"]
        res = client.get(f"/api/endpoints/{ep_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()["id"] == ep_id

    def test_update_endpoint(self, client, auth_headers):
        create = client.post("/api/endpoints", headers=auth_headers, json={
            "name": "To Update", "url": "https://example.com"
        })
        ep_id = create.get_json()["id"]
        res = client.put(f"/api/endpoints/{ep_id}", headers=auth_headers, json={"name": "Updated Name"})
        assert res.status_code == 200
        assert res.get_json()["name"] == "Updated Name"

    def test_delete_endpoint(self, client, auth_headers):
        create = client.post("/api/endpoints", headers=auth_headers, json={
            "name": "To Delete", "url": "https://example.com"
        })
        ep_id = create.get_json()["id"]
        res = client.delete(f"/api/endpoints/{ep_id}", headers=auth_headers)
        assert res.status_code == 200
        gone = client.get(f"/api/endpoints/{ep_id}", headers=auth_headers)
        assert gone.status_code == 404


# ── Stats & Logs ─────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_endpoint(self, client, auth_headers):
        res = client.get("/api/stats", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "endpoints_total" in data
        assert "endpoints_up" in data

    def test_logs_endpoint(self, client, auth_headers):
        res = client.get("/api/logs", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "results" in data
        assert "total" in data

    def test_alerts_endpoint(self, client, auth_headers):
        res = client.get("/api/alerts", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


# ── Dashboard ────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_loads(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"ERP MONITOR" in res.data

    def test_dashboard_no_auth_required(self, client):
        # Dashboard is publicly viewable
        res = client.get("/")
        assert res.status_code == 200
