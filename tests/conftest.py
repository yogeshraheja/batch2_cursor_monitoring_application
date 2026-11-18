"""Pytest fixtures — fixture hashes only, no real secrets."""

import pytest

from auth import hash_password
from app import create_app

# Known demo password used only inside tests (never a production secret).
TEST_PASSWORD = "test-pass-not-for-prod"
TEST_USERNAME = "admin"


@pytest.fixture
def password_hash():
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def app(password_hash):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "ADMIN_USERNAME": TEST_USERNAME,
            "ADMIN_PASSWORD_HASH": password_hash,
            "WTF_CSRF_ENABLED": False,  # exercise auth; CSRF covered separately if needed
            "SESSION_COOKIE_HTTPONLY": True,
            "SKIP_SSH_COLLECT": True,
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_app(password_hash):
    """App with CSRF enabled for form-token checks."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "ADMIN_USERNAME": TEST_USERNAME,
            "ADMIN_PASSWORD_HASH": password_hash,
            "WTF_CSRF_ENABLED": True,
        }
    )
