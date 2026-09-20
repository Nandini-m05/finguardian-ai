import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """One shared client (and event loop) for every test in this file -
    a fresh TestClient per test would open a new event loop each time,
    while the SQLAlchemy engine's pooled connections stay alive between
    tests, causing an asyncpg cross-event-loop error on the second use."""
    with TestClient(app) as c:
        yield c


def _unique_email() -> str:
    return f"pytest-{uuid.uuid4().hex[:8]}@example.com"


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login_flow(client):
    email = _unique_email()
    register_response = client.post(
        "/register", json={"email": email, "password": "testpass123"}
    )
    assert register_response.status_code == 200
    assert register_response.json()["email"] == email

    login_response = client.post(
        "/login", json={"email": email, "password": "testpass123"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_login_wrong_password_rejected(client):
    email = _unique_email()
    client.post("/register", json={"email": email, "password": "correct-password"})
    response = client.post(
        "/login", json={"email": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code in (401, 403)


def test_analyze_requires_auth(client):
    """Confirms /analyze is protected without actually running the pipeline -
    deliberately not testing a real analysis here, since that would spend
    a real Alpha Vantage API call on every single test run."""
    response = client.post("/analyze", json={"symbol": "AAPL"})
    assert response.status_code in (401, 403)
