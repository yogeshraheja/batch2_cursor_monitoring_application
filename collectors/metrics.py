"""Shared metric shape for local and SSH collectors."""

from __future__ import annotations

from typing import Any


def empty_metrics(*, reachable: bool = False, error: str | None = None) -> dict[str, Any]:
    return {
        "reachable": reachable,
        "cpu_percent": None,
        "memory": {"used": None, "total": None, "percent": None},
        "network": {"bytes_recv": None, "bytes_sent": None, "summary": "—"},
        "listening_ports": [],
        "error": error,
    }


def format_bytes(n: int | None) -> str:
    if n is None:
        return "—"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def network_summary(bytes_recv: int | None, bytes_sent: int | None) -> str:
    return f"RX {format_bytes(bytes_recv)} · TX {format_bytes(bytes_sent)}"


def mask_secret_in_text(text: str, *secrets: str | None) -> str:
    """Strip known credential material from error strings before UI/logging."""
    result = text or ""
    for secret in secrets:
        if secret and len(secret) >= 4:
            result = result.replace(secret, "***")
    return result
