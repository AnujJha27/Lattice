"""Integration tests for the Brain + concepts API.

These run against a real PostgreSQL+pgvector database. Set DATABASE_URL to
enable; they skip automatically otherwise. In CI, a pgvector service container
is provided.
"""
from __future__ import annotations

import os
import time
import uuid
from types import SimpleNamespace

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
            auth_schema_exists = await conn.scalar(text(
                "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'auth')"
            ))
            auth_users_exists = await conn.scalar(text(
                "SELECT to_regclass('auth.users') IS NOT NULL"
            )) if auth_schema_exists else False
            if not auth_schema_exists:
                await conn.execute(text("CREATE SCHEMA auth"))
            if not auth_users_exists:
                try:
                    await conn.execute(
                        text("CREATE TABLE auth.users (id uuid PRIMARY KEY)")
                    )
                except Exception:  # noqa: BLE001 — managed auth schemas are not writable
                    pytest.skip("database is not a writable disposable integration database")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # create_all is idempotent-ish for tests; migrations own production DDL
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 — setup errors belong to the environment
        if "permission denied for schema auth" in str(exc).lower():
            pytest.skip("database is not a writable disposable integration database")
        raise
    yield


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


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

    def test_portrait_event_persists_for_new_user(self, client: TestClient, auth: dict):
        response = client.post(
            "/api/portrait/events",
            json={"event_type": "portrait_viewed", "element_id": "concept-id"},
            headers=auth,
        )
        assert response.status_code == 204, response.text
        assert response.content == b""


class TestLearningLoop:
    def test_quiz_attempt_updates_review_queue_and_recommendation(self, client: TestClient, auth: dict, monkeypatch):
        class FakeProvider:
            async def generate_structured(self, *_args, **_kwargs):
                return SimpleNamespace(structured={
                    "question": "Which value is the identity for addition?",
                    "options": ["Zero", "One", "Two"],
                    "answer": 0,
                    "rationale": "Adding zero leaves a number unchanged.",
                })

        monkeypatch.setattr("app.providers.factory.get_llm_provider", lambda: FakeProvider())
        concept = _create_concept(
            client, auth, f"Review loop {uuid.uuid4().hex[:8]}", domain="Mathematics"
        )

        scheduled = client.post(
            "/api/reviews/schedule", json={"concept_id": concept["id"]}, headers=auth
        )
        assert scheduled.status_code == 200, scheduled.text

        quiz_response = client.post(f"/api/concepts/{concept['id']}/quiz", headers=auth)
        assert quiz_response.status_code == 200, quiz_response.text
        quiz = quiz_response.json()
        assert set(quiz) == {"id", "question", "options"}

        attempt = client.post(
            f"/api/quizzes/{quiz['id']}/attempts",
            json={"answer": 0, "confidence": 5, "response_ms": 420},
            headers=auth,
        )
        assert attempt.status_code == 200, attempt.text
        assert attempt.json()["correct"] is True
        assert attempt.json()["next_review_at"] is not None

        due = client.get("/api/reviews/due", headers=auth)
        assert due.status_code == 200, due.text
        assert concept["id"] not in {item["concept_id"] for item in due.json()}

        graph = client.get("/api/brain/graph", headers=auth)
        node = next(node for node in graph.json()["nodes"] if node["id"] == concept["id"])
        assert node["mastery_score"] == 12

        recommendations = client.get("/api/recommendations", headers=auth)
        assert recommendations.status_code == 200, recommendations.text
        recommendation = next(
            item for item in recommendations.json() if item["concept_id"] == concept["id"]
        )
        assert "llm" not in recommendation["factors"]
        assert recommendation["factors"]["mastery"] == 0.12

    def test_portrait_snapshot_tracks_learning_and_discovery(self, client: TestClient, auth: dict):
        def practice(concept_id: str, repetitions: int) -> None:
            quiz_response = client.post(f"/api/concepts/{concept_id}/quiz", headers=auth)
            assert quiz_response.status_code == 200, quiz_response.text
            quiz_id = quiz_response.json()["id"]
            for _ in range(repetitions):
                attempt = client.post(
                    f"/api/quizzes/{quiz_id}/attempts",
                    json={"answer": 0, "confidence": 3},
                    headers=auth,
                )
                assert attempt.status_code == 200, attempt.text

        first = _create_concept(client, auth, f"Lean {uuid.uuid4().hex[:8]}", domain="Formal Methods")
        practice(first["id"], 4)
        sparse = client.get("/api/portrait", headers=auth)
        assert sparse.status_code == 200, sparse.text
        sparse_snapshot_id = sparse.json()["snapshot_id"]
        assert sparse.json()["emerging_threads"] == []

        second = _create_concept(client, auth, f"Types {uuid.uuid4().hex[:8]}", domain="Formal Methods")
        third = _create_concept(client, auth, f"Verification {uuid.uuid4().hex[:8]}", domain="Formal Methods")
        practice(second["id"], 4)
        practice(third["id"], 4)

        mature = client.post("/api/portrait/refresh", headers=auth)
        assert mature.status_code == 202, mature.text
        refresh_job = mature.json()
        for _ in range(40):
            mature = client.get(f"/api/portrait/refresh/{refresh_job['job_id']}", headers=auth)
            assert mature.status_code == 200, mature.text
            if mature.json()["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.1)
        assert mature.json()["status"] == "SUCCEEDED", mature.text
        mature_body = mature.json()["portrait"]
        assert mature_body["snapshot_id"] != sparse_snapshot_id
        assert mature_body["summary"]["emerging_thread"] == "Formal Methods"

        discovery = client.get("/api/discovery/portrait", headers=auth)
        assert discovery.status_code == 200, discovery.text
        assert discovery.json()["snapshot_id"] == mature_body["snapshot_id"]
        assert discovery.json()["summary"]["emerging_thread"] == "Formal Methods"

        practice(first["id"], 1)
        unchanged = client.post("/api/portrait/refresh", headers=auth)
        assert unchanged.status_code == 202, unchanged.text
        unchanged_job = unchanged.json()
        for _ in range(40):
            unchanged = client.get(
                f"/api/portrait/refresh/{unchanged_job['job_id']}", headers=auth
            )
            if unchanged.json()["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.1)
        assert unchanged.json()["status"] == "SUCCEEDED", unchanged.text
        assert unchanged.json()["portrait"]["snapshot_id"] == mature_body["snapshot_id"]
