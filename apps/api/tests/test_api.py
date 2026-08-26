from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_ok(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body


def test_protected_route_requires_token(client: TestClient):
    response = client.get("/api/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["request_id"]  # correlation id always present


def test_error_schema_is_stable(client: TestClient):
    """Every failure uses { error: { code, message }, request_id }."""
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"error", "request_id"}
    assert set(body["error"].keys()) == {"code", "message"}


def test_request_id_echoed(client: TestClient):
    response = client.get("/api/health", headers={"x-request-id": "test-123"})
    assert response.headers["x-request-id"] == "test-123"
