"""Pick local vs SSH collector for a server entry."""

from __future__ import annotations

from typing import Any

from flask import current_app, has_app_context

from collectors.local import collect_local
from collectors.metrics import empty_metrics, format_bytes
from collectors.ssh import collect_remote
from servers import AUTH_LOCALHOST, Server


REFRESH_SECONDS = 8


def collect_for_server(server: Server) -> dict[str, Any]:
    """One collect per request — fine for demo concurrency."""
    if server.auth_type == AUTH_LOCALHOST:
        return collect_local()
    # Avoid multi-second Paramiko timeouts during unit tests unless explicitly wanted.
    if (
        has_app_context()
        and current_app.config.get("TESTING")
        and current_app.config.get("SKIP_SSH_COLLECT", True)
    ):
        return empty_metrics(reachable=False, error="SSH collection skipped in tests")
    return collect_remote(server)


def enrich_for_overview(server: Server, metrics: dict[str, Any]) -> dict[str, Any]:
    """Merge public server fields with a compact metrics snapshot for the table."""
    row = server.public_dict()
    row["reachable"] = bool(metrics.get("reachable"))
    row["status"] = "reachable" if row["reachable"] else "unreachable"
    cpu = metrics.get("cpu_percent")
    mem = (metrics.get("memory") or {}).get("percent")
    row["cpu_display"] = f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "—"
    row["memory_display"] = f"{mem:.1f}%" if isinstance(mem, (int, float)) else "—"
    row["network_display"] = (metrics.get("network") or {}).get("summary") or "—"
    row["error"] = metrics.get("error")
    return row


def format_memory_line(memory: dict[str, Any] | None) -> str:
    memory = memory or {}
    used = memory.get("used")
    total = memory.get("total")
    percent = memory.get("percent")
    if used is None or total is None:
        return "— / — (— %)"
    pct = f"{percent:.1f}" if isinstance(percent, (int, float)) else "—"
    return f"{format_bytes(used)} / {format_bytes(total)} ({pct} %)"


def safe_empty() -> dict[str, Any]:
    return empty_metrics(reachable=False, error="Unknown server")
