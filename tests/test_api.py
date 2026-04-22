"""
API integration tests using FastAPI TestClient — 32 test cases.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db

# ─── Test Database Setup ─────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test_tax.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    from backend import models  # noqa
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    import os
    if os.path.exists("./test_tax.db"):
        os.remove("./test_tax.db")


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def registered_user(client):
    """Register a test user once per session."""
    client.post("/auth/register", json={
        "email": "apitest@example.com",
        "password": "testpassword123",
        "full_name": "API Test User",
    })
    return {"email": "apitest@example.com", "password": "testpassword123"}


@pytest.fixture(scope="session")
def auth_token(client, registered_user):
    """Get auth token — reused across tests."""
    resp = client.post("/auth/login", json=registered_user)
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════
# Health Check — 2 tests
# ══════════════════════════════════════════════════════

def test_health_check_status_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_check_has_version(client):
    resp = client.get("/health")
    assert "version" in resp.json()


# ══════════════════════════════════════════════════════
# Auth — Register — 5 tests
# ══════════════════════════════════════════════════════

def test_register_new_user_success(client):
    resp = client.post("/auth/register", json={
        "email": "brand_new@example.com",
        "password": "password123",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "brand_new@example.com"
    assert "id" in data


def test_register_response_excludes_password(client):
    """Hashed password must NEVER be returned."""
    resp = client.post("/auth/register", json={
        "email": "nopwleak@example.com",
        "password": "password123",
    })
    data = resp.json()
    assert "hashed_password" not in data
    assert "password" not in data


def test_register_duplicate_email_rejected(client, registered_user):
    resp = client.post("/auth/register", json={
        "email": registered_user["email"],
        "password": "anotherpassword123",
    })
    assert resp.status_code == 400


def test_register_weak_password_rejected(client):
    resp = client.post("/auth/register", json={
        "email": "weakpass@example.com",
        "password": "123",
    })
    assert resp.status_code == 422


def test_register_invalid_email_rejected(client):
    resp = client.post("/auth/register", json={
        "email": "not-an-email",
        "password": "password123",
    })
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════
# Auth — Login — 4 tests
# ══════════════════════════════════════════════════════

def test_login_success_returns_bearer_token(client, registered_user):
    resp = client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_rejected(client, registered_user):
    resp = client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": "totally_wrong_password",
    })
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post("/auth/login", json={
        "email": "ghost@example.com",
        "password": "password123",
    })
    assert resp.status_code == 401


def test_login_missing_fields_rejected(client):
    resp = client.post("/auth/login", json={"email": "x@x.com"})
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════
# Auth — /me endpoint — 4 tests
# ══════════════════════════════════════════════════════

def test_get_me_returns_user_data(client, auth_token):
    resp = client.get("/auth/me", headers=auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data
    assert "id" in data
    assert "hashed_password" not in data


def test_get_me_no_token_returns_403(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 403


def test_get_me_invalid_token_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert resp.status_code == 401


def test_get_me_malformed_header_rejected(client):
    resp = client.get("/auth/me", headers={"Authorization": "NotBearer sometoken"})
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════
# Upload endpoint — 5 tests
# ══════════════════════════════════════════════════════

def test_upload_requires_authentication(client):
    resp = client.post("/api/upload",
                       files={"file": ("stmt.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert resp.status_code == 403


def test_upload_rejects_non_pdf(client, auth_token):
    resp = client.post(
        "/api/upload",
        headers=auth_headers(auth_token),
        files={"file": ("statement.txt", b"text content", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_empty_pdf(client, auth_token):
    resp = client.post(
        "/api/upload",
        headers=auth_headers(auth_token),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400


def test_upload_rejects_oversized_file(client, auth_token):
    """Files > 10MB should be rejected with 413."""
    big_content = b"A" * (11 * 1024 * 1024)  # 11 MB
    resp = client.post(
        "/api/upload",
        headers=auth_headers(auth_token),
        files={"file": ("big.pdf", big_content, "application/pdf")},
    )
    assert resp.status_code == 413


def test_get_uploads_returns_list(client, auth_token):
    resp = client.get("/api/uploads", headers=auth_headers(auth_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════
# Analyze endpoint — 3 tests
# ══════════════════════════════════════════════════════

def test_analyze_requires_authentication(client):
    resp = client.post("/api/analyze", json={"upload_id": 1})
    assert resp.status_code == 403


def test_analyze_nonexistent_upload_returns_404(client, auth_token):
    resp = client.post(
        "/api/analyze",
        headers=auth_headers(auth_token),
        json={"upload_id": 999999},
    )
    assert resp.status_code == 404


def test_analyze_missing_upload_id_rejected(client, auth_token):
    resp = client.post(
        "/api/analyze",
        headers=auth_headers(auth_token),
        json={},
    )
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════
# Deductions endpoint — 3 tests
# ══════════════════════════════════════════════════════

def test_deductions_requires_authentication(client):
    resp = client.get("/api/deductions?upload_id=1")
    assert resp.status_code == 403


def test_deductions_not_found_returns_404(client, auth_token):
    resp = client.get("/api/deductions?upload_id=999999",
                      headers=auth_headers(auth_token))
    assert resp.status_code == 404


def test_deductions_missing_upload_id_rejected(client, auth_token):
    resp = client.get("/api/deductions", headers=auth_headers(auth_token))
    assert resp.status_code == 422


# ══════════════════════════════════════════════════════
# Query endpoint — 3 tests
# ══════════════════════════════════════════════════════

def test_query_requires_authentication(client):
    resp = client.post("/api/query", json={"question": "total health insurance paid"})
    assert resp.status_code == 403


def test_query_missing_question_rejected(client, auth_token):
    resp = client.post("/api/query", headers=auth_headers(auth_token), json={})
    assert resp.status_code == 422


def test_deductions_summary_returns_dict(client, auth_token):
    resp = client.get("/api/deductions/summary", headers=auth_headers(auth_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_uploads_analyzed" in data
    assert "total_deductions_all" in data


# ══════════════════════════════════════════════════════
# OpenAPI docs — 1 test
# ══════════════════════════════════════════════════════

def test_openapi_docs_accessible(client):
    resp = client.get("/docs")
    assert resp.status_code == 200
