"""
Tests for Money OS Backend API
tests/test_api.py
"""

import os
import base64
import pytest
import sqlite3

TEST_DB_PATH = "test_money_os.db"
os.environ["DATABASE_PATH"] = TEST_DB_PATH
os.environ["ADMIN_PASSWORD"] = "test_secret_pass"

from app import app, init_db, get_db, limiter


@pytest.fixture
def client():
    """Create and configure a test client with a fresh test database."""
    app.config["TESTING"] = True

    # Reset rate limiter storage between tests
    try:
        limiter.reset()
    except Exception:
        pass

    # Ensure clean test DB
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    with app.app_context():
        init_db()

    with app.test_client() as client:
        yield client

    # Cleanup test DB after test
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


# --------------------------------------------------------------------------
# 1. Health & Static Routes
# --------------------------------------------------------------------------
def test_health_check(client):
    """GET /health must return status ok with 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_page(client):
    """GET / must serve the Money OS HTML page with 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Know where your money goes before the month ends." in response.data
    assert b"Money OS" in response.data


def test_404_page(client):
    """Unknown URLs must return the styled 404 page."""
    response = client.get("/non-existent-page-url")
    assert response.status_code == 404
    assert b"PAGE_STATUS ......... 404 NOT FOUND" in response.data


def test_404_api_json(client):
    """Unknown /api/ route returns JSON error."""
    response = client.get("/api/unknown_route")
    assert response.status_code == 404
    assert "error" in response.get_json()


# --------------------------------------------------------------------------
# 2. Budget API (/api/budget)
# --------------------------------------------------------------------------
def test_budget_valid_default(client):
    """POST /api/budget with RM 1200 calculates 600 needs, 360 wants, 240 savings."""
    response = client.post("/api/budget", json={"income": 1200})
    assert response.status_code == 200
    data = response.get_json()
    assert data["income"] == 1200.0
    assert data["needs"] == 600.0
    assert data["wants"] == 360.0
    assert data["savings"] == 240.0


def test_budget_zero_income(client):
    """POST /api/budget with RM 0 is valid and returns zeroes."""
    response = client.post("/api/budget", json={"income": 0})
    assert response.status_code == 200
    data = response.get_json()
    assert data["needs"] == 0.0
    assert data["wants"] == 0.0
    assert data["savings"] == 0.0


def test_budget_max_boundary(client):
    """POST /api/budget with RM 1,000,000 is accepted."""
    response = client.post("/api/budget", json={"income": 1000000})
    assert response.status_code == 200
    data = response.get_json()
    assert data["needs"] == 500000.0


def test_budget_negative_income(client):
    """POST /api/budget with negative income returns 400 Bad Request."""
    response = client.post("/api/budget", json={"income": -50})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_budget_exceeds_max(client):
    """POST /api/budget exceeding 1,000,000 returns 400."""
    response = client.post("/api/budget", json={"income": 1000001})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_budget_non_numeric(client):
    """POST /api/budget with string returns 400."""
    response = client.post("/api/budget", json={"income": "invalid_number"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_budget_missing_income(client):
    """POST /api/budget without income field returns 400."""
    response = client.post("/api/budget", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


# --------------------------------------------------------------------------
# 3. Waitlist API (/api/waitlist)
# --------------------------------------------------------------------------
def test_waitlist_valid_signup(client):
    """POST /api/waitlist with valid email adds user and returns 201."""
    response = client.post("/api/waitlist", json={"email": "student@um.edu.my"})
    assert response.status_code == 201
    assert "message" in response.get_json()


def test_waitlist_duplicate_email(client):
    """POST /api/waitlist with duplicate email returns 409 Conflict."""
    email = "duplicate@taylors.edu.my"
    first = client.post("/api/waitlist", json={"email": email})
    assert first.status_code == 201

    second = client.post("/api/waitlist", json={"email": email})
    assert second.status_code == 409
    assert "error" in second.get_json()


def test_waitlist_invalid_email(client):
    """POST /api/waitlist with invalid email format returns 400."""
    response = client.post("/api/waitlist", json={"email": "not-an-email"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_waitlist_missing_email(client):
    """POST /api/waitlist with missing email returns 400."""
    response = client.post("/api/waitlist", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


# --------------------------------------------------------------------------
# 4. Questions API (/api/questions)
# --------------------------------------------------------------------------
def test_question_valid_submission(client):
    """POST /api/questions with valid data saves and returns 201."""
    payload = {
        "name": "Adam Harith",
        "email": "adam@monash.edu.my",
        "message": "Can I tweak the 50/30/20 ratio for semester break?"
    }
    response = client.post("/api/questions", json=payload)
    assert response.status_code == 201
    assert "message" in response.get_json()


def test_question_missing_name(client):
    """POST /api/questions missing name returns 400."""
    payload = {
        "name": "",
        "email": "adam@monash.edu.my",
        "message": "Valid question message here."
    }
    response = client.post("/api/questions", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_question_invalid_email(client):
    """POST /api/questions with invalid email returns 400."""
    payload = {
        "name": "Adam",
        "email": "bad-email",
        "message": "Valid question message here."
    }
    response = client.post("/api/questions", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_question_too_short(client):
    """POST /api/questions with message < 10 characters returns 400."""
    payload = {
        "name": "Adam",
        "email": "adam@monash.edu.my",
        "message": "Hi"
    }
    response = client.post("/api/questions", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_question_too_long(client):
    """POST /api/questions with message > 1000 characters returns 400."""
    payload = {
        "name": "Adam",
        "email": "adam@monash.edu.my",
        "message": "x" * 1001
    }
    response = client.post("/api/questions", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


# --------------------------------------------------------------------------
# 5. Stats API (/api/stats)
# --------------------------------------------------------------------------
def test_stats_api(client):
    """GET /api/stats reflects accurately created waitlists and budgets."""
    client.post("/api/waitlist", json={"email": "u1@student.my"})
    client.post("/api/waitlist", json={"email": "u2@student.my"})
    client.post("/api/budget", json={"income": 1200})

    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["waitlist_count"] == 2
    assert data["budgets_created"] == 1


# --------------------------------------------------------------------------
# 6. Admin Authentication & CSV
# --------------------------------------------------------------------------
def test_admin_unauthorized(client):
    """GET /admin/waitlist without credentials returns 401."""
    response = client.get("/admin/waitlist")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_admin_wrong_password(client):
    """GET /admin/waitlist with incorrect password returns 401."""
    auth_header = "Basic " + base64.b64encode(b"admin:wrongpassword").decode("ascii")
    response = client.get("/admin/waitlist", headers={"Authorization": auth_header})
    assert response.status_code == 401


def test_admin_authorized(client):
    """GET /admin/waitlist with correct password returns 200 HTML."""
    auth_header = "Basic " + base64.b64encode(b"admin:test_secret_pass").decode("ascii")
    response = client.get("/admin/waitlist", headers={"Authorization": auth_header})
    assert response.status_code == 200
    assert b"Money OS Administration" in response.data
    assert b"Download CSV" in response.data


def test_admin_csv_export(client):
    """GET /admin/export-csv returns CSV file with attachment header."""
    client.post("/api/waitlist", json={"email": "export_test@student.my"})
    auth_header = "Basic " + base64.b64encode(b"admin:test_secret_pass").decode("ascii")
    response = client.get("/admin/export-csv", headers={"Authorization": auth_header})
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"export_test@student.my" in response.data
    assert "attachment" in response.headers["Content-Disposition"]


# --------------------------------------------------------------------------
# 7. Rate Limiting Test
# --------------------------------------------------------------------------
def test_rate_limiting(client):
    """
    Exceeding 10 POST requests per minute from the same IP
    must return HTTP 429 Too Many Requests with JSON error.
    """
    # Send 10 valid requests (allowed)
    for i in range(10):
        res = client.post("/api/budget", json={"income": 1000 + i})
        assert res.status_code == 200

    # 11th request must trigger rate limit 429
    res_11 = client.post("/api/budget", json={"income": 1500})
    assert res_11.status_code == 429
    assert "error" in res_11.get_json()
