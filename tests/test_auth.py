"""Unit tests for admin auth, session, and route protection."""

from auth import hash_password, verify_password
from config import ConfigError, load_admin_config

TEST_PASSWORD = "test-pass-not-for-prod"
TEST_USERNAME = "admin"


def test_hash_password_rejects_empty():
    try:
        hash_password("")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_verify_password_helper(password_hash):
    assert verify_password(password_hash, TEST_PASSWORD) is True
    assert verify_password(password_hash, "wrong") is False
    assert verify_password(password_hash, "") is False
    assert verify_password("", TEST_PASSWORD) is False


def test_load_admin_config_requires_hash():
    try:
        load_admin_config({"ADMIN_USERNAME": "admin", "SECRET_KEY": "x"})
        assert False, "expected ConfigError"
    except ConfigError as exc:
        assert "ADMIN_PASSWORD_HASH" in str(exc)


def test_load_admin_config_ok(password_hash):
    cfg = load_admin_config(
        {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD_HASH": password_hash,
            "SECRET_KEY": "x",
        }
    )
    assert cfg["ADMIN_USERNAME"] == "admin"
    assert cfg["ADMIN_PASSWORD_HASH"] == password_hash
    assert cfg["SESSION_COOKIE_HTTPONLY"] is True


def test_login_success_sets_session(client):
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/overview" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("user") == TEST_USERNAME


def test_login_failure_no_session(client):
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert sess.get("user") is None


def test_login_failure_unknown_user_no_session(client):
    response = client.post(
        "/login",
        data={"username": "not-admin", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as sess:
        assert sess.get("user") is None


def test_logout_clears_session(client):
    client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("user") is None


def test_protected_overview_redirects(client):
    response = client.get("/overview", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_protected_detail_redirects(client):
    response = client.get("/servers/demo", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_protected_add_server_redirects(client):
    response = client.get("/servers/add", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_authenticated_can_view_overview(client):
    client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    response = client.get("/overview")
    assert response.status_code == 200
    assert b"Overview" in response.data


def test_logout_invalidates_protected_access(client):
    client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    client.get("/logout")
    response = client.get("/overview", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page_is_public(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data
