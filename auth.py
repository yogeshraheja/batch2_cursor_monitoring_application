"""Auth helpers for the single admin user."""

from functools import wraps

from flask import (
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plaintext: str) -> str:
    """Return a Werkzeug password hash. Never log ``plaintext``."""
    if not plaintext:
        raise ValueError("Password must not be empty.")
    return generate_password_hash(plaintext)


def verify_password(password_hash: str, plaintext: str) -> bool:
    """Constant-time-ish verify via Werkzeug ``check_password_hash``."""
    if not password_hash or not plaintext:
        return False
    return check_password_hash(password_hash, plaintext)


def authenticate(username: str, password: str) -> bool:
    """
    Validate credentials against configured admin user.
    Returns True only on full match; does not distinguish user vs password.
    """
    expected_user = current_app.config["ADMIN_USERNAME"]
    password_hash = current_app.config["ADMIN_PASSWORD_HASH"]

    if username != expected_user:
        # Still run a hash check against a dummy to reduce timing signal a bit.
        verify_password(password_hash, password)
        return False

    return verify_password(password_hash, password)


def login_user(username: str) -> None:
    session.clear()
    session["user"] = username
    session.permanent = False


def logout_user() -> None:
    session.clear()


def current_user():
    return session.get("user")


def is_authenticated() -> bool:
    return current_user() is not None


def login_required(view):
    """Redirect unauthenticated users to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped
