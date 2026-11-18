"""In-memory server inventory (lost on process restart)."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


AUTH_PASSWORD = "password"
AUTH_KEY = "key"
AUTH_LOCALHOST = "localhost"
AUTH_TYPES = frozenset({AUTH_PASSWORD, AUTH_KEY, AUTH_LOCALHOST})

# Host must look like a hostname/IP — reject path-like junk.
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)"
    r"(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"|(?:\d{1,3}\.){3}\d{1,3}"
    r"|localhost)$"
)


class ValidationError(ValueError):
    """Raised when server input fails validation."""


@dataclass
class Server:
    """Server inventory entry. Secrets stay in memory only."""

    id: str
    name: str
    host: str
    port: int
    ssh_user: str
    auth_type: str
    password: str | None = field(default=None, repr=False)
    private_key: str | None = field(default=None, repr=False)

    def public_dict(self) -> dict[str, Any]:
        """Safe view for templates — never includes raw passwords/keys."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "ssh_user": self.ssh_user,
            "auth_type": self.auth_type,
            "has_password": bool(self.password),
            "has_key": bool(self.private_key),
            "display_name": self.name or self.host,
        }

    def to_dict(self) -> dict[str, Any]:
        """Full dict including secrets — for internal use / tests only."""
        return asdict(self)


def _validate_host(host: str, auth_type: str) -> str:
    host = (host or "").strip()
    if auth_type == AUTH_LOCALHOST:
        return host or "127.0.0.1"
    if not host:
        raise ValidationError("Host is required.")
    if len(host) > 253:
        raise ValidationError("Host is too long.")
    if ".." in host or "/" in host or "\\" in host or host.startswith("."):
        raise ValidationError("Host looks invalid (path-like values are rejected).")
    if not _HOST_RE.match(host):
        raise ValidationError("Host must be a hostname, IP address, or localhost.")
    return host


def _validate_port(port: Any) -> int:
    try:
        value = int(port)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Port must be an integer.") from exc
    if value < 1 or value > 65535:
        raise ValidationError("Port must be between 1 and 65535.")
    return value


def validate_server_payload(
    *,
    name: str = "",
    host: str = "",
    port: Any = 22,
    ssh_user: str = "",
    auth_type: str = AUTH_PASSWORD,
    password: str | None = None,
    private_key: str | None = None,
    require_secrets: bool = True,
) -> dict[str, Any]:
    """
    Validate and normalize server form fields.

    When ``require_secrets`` is False (edit keep-existing), blank password/key
    are allowed and returned as None so the store can leave prior values.
    """
    auth_type = (auth_type or "").strip().lower()
    if auth_type not in AUTH_TYPES:
        raise ValidationError("Auth type must be password, key, or localhost.")

    name = (name or "").strip()
    if len(name) > 128:
        raise ValidationError("Display name is too long.")

    host = _validate_host(host, auth_type)
    port = _validate_port(port if auth_type != AUTH_LOCALHOST else (port or 22))

    ssh_user = (ssh_user or "").strip()
    password = password if password is not None else ""
    private_key = private_key if private_key is not None else ""
    # Normalize whitespace-only secrets to empty
    if isinstance(password, str):
        password = password  # keep as entered (passwords may have spaces)
    if isinstance(private_key, str):
        private_key = private_key.strip()

    if auth_type == AUTH_LOCALHOST:
        return {
            "name": name or "localhost",
            "host": host or "127.0.0.1",
            "port": 22,
            "ssh_user": "",
            "auth_type": AUTH_LOCALHOST,
            "password": None,
            "private_key": None,
        }

    if not ssh_user:
        raise ValidationError("SSH username is required.")
    if len(ssh_user) > 64:
        raise ValidationError("SSH username is too long.")

    if auth_type == AUTH_PASSWORD:
        if require_secrets and not password:
            raise ValidationError("Password is required for password auth.")
        return {
            "name": name,
            "host": host,
            "port": port,
            "ssh_user": ssh_user,
            "auth_type": AUTH_PASSWORD,
            "password": password or None,
            "private_key": None,
        }

    # key mode — prefer pasted key content in memory (no arbitrary path reads)
    if require_secrets and not private_key:
        raise ValidationError("Private key content is required for key auth.")
    return {
        "name": name,
        "host": host,
        "port": port,
        "ssh_user": ssh_user,
        "auth_type": AUTH_KEY,
        "password": None,
        "private_key": private_key or None,
    }


class ServerStore:
    """Process-local CRUD store. Data is lost on restart."""

    def __init__(self) -> None:
        self._servers: dict[str, Server] = {}

    def list(self) -> list[Server]:
        return list(self._servers.values())

    def get(self, server_id: str) -> Server | None:
        return self._servers.get(server_id)

    def add(self, payload: dict[str, Any]) -> Server:
        server = Server(
            id=uuid.uuid4().hex[:12],
            name=payload["name"],
            host=payload["host"],
            port=payload["port"],
            ssh_user=payload["ssh_user"],
            auth_type=payload["auth_type"],
            password=payload.get("password"),
            private_key=payload.get("private_key"),
        )
        self._servers[server.id] = server
        return server

    def update(self, server_id: str, payload: dict[str, Any]) -> Server | None:
        existing = self._servers.get(server_id)
        if existing is None:
            return None

        password = payload.get("password")
        private_key = payload.get("private_key")
        # Blank secret on edit → keep existing
        if not password:
            password = existing.password
        if not private_key:
            private_key = existing.private_key

        # Clear unused credential when auth type changes
        auth_type = payload["auth_type"]
        if auth_type == AUTH_LOCALHOST:
            password = None
            private_key = None
        elif auth_type == AUTH_PASSWORD:
            private_key = None
        elif auth_type == AUTH_KEY:
            password = None

        updated = Server(
            id=existing.id,
            name=payload["name"],
            host=payload["host"],
            port=payload["port"],
            ssh_user=payload["ssh_user"],
            auth_type=auth_type,
            password=password,
            private_key=private_key,
        )
        self._servers[server_id] = updated
        return updated

    def delete(self, server_id: str) -> bool:
        if server_id not in self._servers:
            return False
        del self._servers[server_id]
        return True

    def clear(self) -> None:
        self._servers.clear()
