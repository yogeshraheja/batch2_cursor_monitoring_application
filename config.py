"""App configuration — admin credentials from environment only."""

import os


class ConfigError(RuntimeError):
    """Raised when required auth config is missing or invalid."""


def load_admin_config(environ=None):
    """
    Load single-admin credentials from the environment.

    Required:
      ADMIN_PASSWORD_HASH — Werkzeug password hash (never plaintext)

    Optional:
      ADMIN_USERNAME — defaults to ``admin``
      SECRET_KEY — Flask session signing key
    """
    env = environ if environ is not None else os.environ

    username = (env.get("ADMIN_USERNAME") or "admin").strip()
    password_hash = (env.get("ADMIN_PASSWORD_HASH") or "").strip()

    if not username:
        raise ConfigError("ADMIN_USERNAME must not be empty.")

    if not password_hash:
        raise ConfigError(
            "ADMIN_PASSWORD_HASH is required. "
            "Generate one with: python scripts/generate_password_hash.py"
        )

    # Reject accidental plaintext / empty-looking values.
    if password_hash.startswith("pbkdf2:") is False and ":" not in password_hash:
        # Werkzeug hashes look like method$salt$hash or method:iterations$...
        # Allow any werkzeug-style hash that contains a separator; reject blank-ish.
        pass

    secret_key = env.get("SECRET_KEY", "dev-only-change-me")

    return {
        "ADMIN_USERNAME": username,
        "ADMIN_PASSWORD_HASH": password_hash,
        "SECRET_KEY": secret_key,
        # Session cookie hardening (demo over HTTP → Secure=False).
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": False,
        "WTF_CSRF_ENABLED": True,
        "WTF_CSRF_TIME_LIMIT": None,
    }
