"""Unit tests for in-memory server store and validation."""

import pytest

from servers import (
    AUTH_KEY,
    AUTH_LOCALHOST,
    AUTH_PASSWORD,
    ServerStore,
    ValidationError,
    validate_server_payload,
)


def test_store_crud():
    store = ServerStore()
    payload = validate_server_payload(
        name="web",
        host="10.0.0.5",
        port=22,
        ssh_user="ops",
        auth_type=AUTH_PASSWORD,
        password="secret-demo",
    )
    server = store.add(payload)
    assert store.get(server.id) is not None
    assert len(store.list()) == 1

    public = server.public_dict()
    assert "password" not in public
    assert "private_key" not in public
    assert public["has_password"] is True

    updated = store.update(
        server.id,
        validate_server_payload(
            name="web-2",
            host="10.0.0.6",
            port=2222,
            ssh_user="ops",
            auth_type=AUTH_PASSWORD,
            password="",
            require_secrets=False,
        ),
    )
    assert updated.name == "web-2"
    assert updated.host == "10.0.0.6"
    assert updated.port == 2222
    assert updated.password == "secret-demo"  # kept

    assert store.delete(server.id) is True
    assert store.get(server.id) is None
    assert store.delete("missing") is False


def test_validate_password_mode_requires_fields():
    with pytest.raises(ValidationError):
        validate_server_payload(auth_type=AUTH_PASSWORD, host="h", ssh_user="u")
    with pytest.raises(ValidationError):
        validate_server_payload(
            auth_type=AUTH_PASSWORD, host="h", ssh_user="", password="x"
        )


def test_validate_key_mode():
    payload = validate_server_payload(
        host="lab.example",
        ssh_user="ops",
        auth_type=AUTH_KEY,
        private_key="-----BEGIN KEY-----\nabc\n-----END KEY-----",
    )
    assert payload["auth_type"] == AUTH_KEY
    assert payload["private_key"].startswith("-----BEGIN")


def test_validate_localhost_skips_ssh():
    payload = validate_server_payload(auth_type=AUTH_LOCALHOST)
    assert payload["auth_type"] == AUTH_LOCALHOST
    assert payload["password"] is None
    assert payload["private_key"] is None


def test_reject_path_traversal_host():
    with pytest.raises(ValidationError, match="path-like"):
        validate_server_payload(
            host="../etc/passwd",
            ssh_user="u",
            auth_type=AUTH_PASSWORD,
            password="x",
        )
    with pytest.raises(ValidationError):
        validate_server_payload(
            host="/tmp/evil",
            ssh_user="u",
            auth_type=AUTH_PASSWORD,
            password="x",
        )


def test_port_range():
    with pytest.raises(ValidationError):
        validate_server_payload(
            host="a.b",
            port=0,
            ssh_user="u",
            auth_type=AUTH_PASSWORD,
            password="x",
        )
    with pytest.raises(ValidationError):
        validate_server_payload(
            host="a.b",
            port=70000,
            ssh_user="u",
            auth_type=AUTH_PASSWORD,
            password="x",
        )


def test_server_repr_hides_secrets():
    store = ServerStore()
    server = store.add(
        validate_server_payload(
            host="h.example",
            ssh_user="u",
            auth_type=AUTH_PASSWORD,
            password="super-secret",
        )
    )
    text = repr(server)
    assert "super-secret" not in text
