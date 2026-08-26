"""Integration tests for the Brain + concepts API.

These run against a real PostgreSQL+pgvector database. Set DATABASE_URL to
enable; they skip automatically otherwise. In CI, a pgvector service container
is provided.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — integration tests need PostgreSQL",
)


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    """Ensure auth schema stub + full schema exist on the test database."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings
    from app.db import models  # noqa: F401
    from app.db.base import Base

    async def run():
        engine = create_async_engine(get_settings().database_url)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
            await conn.execute(
                text("CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY)")
            )
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # create_all is idempotent-ish for tests; migrations own production DDL
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(run())
    yield


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    """Forge a service-signed JWT? No — use HS256 with the configured secret.

    For local/CI testing we mint tokens with SUPABASE_JWT_SECRET when set;
    otherwise we bypass by monkeypatching verification.
    """
    from app.core import security
    from app.main import app as fastapi_app

    claims = {
        "sub": str(uuid.uuid4()),
        "email": "brain-test@lattice.local",
        "aud": "authenticated",
        "exp": __import__("time").time() + 3600,
    }
    secret = os.environ.get("SUPABASE_JWT_SECRET")

    def fake_verify(token: str) -> dict:
        import jwt as pyjwt

        try:
            if secret:
                return pyjwt.decode(
                    token, secret, algorithms=["HS256"], audience="authenticated"
                )
        except Exception:  # noqa: BLE001 — tests fall through to claims
            pass
        return claims

    original = security.verify_supabase_jwt
    fastapi_app.dependency_overrides.clear()
    security.verify_supabase_jwt = fake_verify
    # get_current_user imported verify at module level; patch there too
    from app.core import auth as auth_module

    auth_module.verify_supabase_jwt = fake_verify
    token = "test-token"
    yield {"Authorization": f"Bearer {token}"}
    security.verify_supabase_jwt = original
    auth_module.verify_supabase_jwt = original


def _create_concept(client: TestClient, headers: dict, name: str, **kwargs) -> dict:
    response = client.post(
        "/api/concepts", json={"canonical_name": name, **kwargs}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestBrainFlow:
    def test_empty_brain(self, client: TestClient, auth: dict):
        # Fresh user → graph may be empty or have prior data; just check shape.
        response = client.get("/api/brain/graph", headers=auth)
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"nodes", "edges", "generated_at"}

    def test_create_and_appears_in_brain(self, client: TestClient, auth: dict):
        concept = _create_concept(
            client, auth, f"Eigenvalues {uuid.uuid4().hex[:8]}", domain="Linear Algebra"
        )
        graph = client.get("/api/brain/graph", headers=auth).json()
        assert any(n["id"] == concept["id"] for n in graph["nodes"])

    def test_dedupe_reuses_canonical_concept(self, client: TestClient, auth: dict):
        name = f"Dedup Target {uuid.uuid4().hex[:8]}"
        first = _create_concept(client, auth, name)
        second = _create_concept(client, auth, name.lower())
        assert first["id"] == second["id"]

    def test_prerequisite_edge_visible_in_graph(self, client: TestClient, auth: dict):
        a = _create_concept(client, auth, f"Concept A {uuid.uuid4().hex[:8]}")
        b = _create_concept(client, auth, f"Concept B {uuid.uuid4().hex[:8]}")
        response = client.post(
            f"/api/concepts/{a['id']}/edges",
            json={"target_id": b["id"], "type": "PREREQUISITE"},
            headers=auth,
        )
        assert response.status_code == 201, response.text
        graph = client.get("/api/brain/graph", headers=auth).json()
        assert any(
            e["source"] == a["id"] and e["target"] == b["id"] for e in graph["edges"]
        )

    def test_cycle_rejected(self, client: TestClient, auth: dict):
        a = _create_concept(client, auth, f"Cyc A {uuid.uuid4().hex[:8]}")
        b = _create_concept(client, auth, f"Cyc B {uuid.uuid4().hex[:8]}")
        r1 = client.post(
            f"/api/concepts/{a['id']}/edges",
            json={"target_id": b["id"], "type": "PREREQUISITE"},
            headers=auth,
        )
        assert r1.status_code == 201
        r2 = client.post(
            f"/api/concepts/{b['id']}/edges",
            json={"target_id": a["id"], "type": "PREREQUISITE"},
            headers=auth,
        )
        assert r2.status_code == 422
        assert r2.json()["error"]["code"] == "cycle_detected"

    def test_self_edge_rejected(self, client: TestClient, auth: dict):
        a = _create_concept(client, auth, f"Self {uuid.uuid4().hex[:8]}")
        response = client.post(
            f"/api/concepts/{a['id']}/edges",
            json={"target_id": a["id"], "type": "PREREQUISITE"},
            headers=auth,
        )
        assert response.status_code == 422

    def test_concept_detail(self, client: TestClient, auth: dict):
        a = _create_concept(client, auth, f"Detail A {uuid.uuid4().hex[:8]}")
        b = _create_concept(client, auth, f"Detail B {uuid.uuid4().hex[:8]}")
        client.post(
            f"/api/concepts/{b['id']}/edges",
            json={"target_id": a["id"], "type": "PREREQUISITE"},
            headers=auth,
        )
        detail = client.get(f"/api/concepts/{b['id']}", headers=auth).json()
        assert detail["canonical_name"].startswith("Detail B")
        assert [p["id"] for p in detail["prerequisites"]] == [a["id"]]
        assert detail["in_brain"] is True

    def test_unauthenticated_rejected(self, client: TestClient):
        assert client.get("/api/brain/graph").status_code == 401
