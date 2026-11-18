"""
Localhost metric collection via psutil (read-only APIs).

Collected: CPU %, memory used/total/%, network RX/TX counters,
and listening ports only (no established connections).
"""

from __future__ import annotations

import logging
import socket
from typing import Any

import psutil

from collectors.metrics import empty_metrics, network_summary

logger = logging.getLogger(__name__)


def filter_listening_ports(connections: list[Any]) -> list[dict[str, Any]]:
    """Keep LISTEN sockets only; drop established / other states."""
    ports: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    for conn in connections:
        status = getattr(conn, "status", None)
        if status != psutil.CONN_LISTEN and status != "LISTEN":
            continue
        laddr = getattr(conn, "laddr", None)
        if not laddr:
            continue
        address = getattr(laddr, "ip", None) or (laddr[0] if len(laddr) > 0 else "")
        port = getattr(laddr, "port", None) or (laddr[1] if len(laddr) > 1 else None)
        if port is None:
            continue
        sock_type = getattr(conn, "type", None)
        if sock_type == socket.SOCK_DGRAM:
            protocol = "udp"
        else:
            protocol = "tcp"
        key = (str(address), int(port), protocol)
        if key in seen:
            continue
        seen.add(key)

        process_name = None
        pid = getattr(conn, "pid", None)
        if pid:
            try:
                process_name = psutil.Process(pid).name()
            except (psutil.Error, PermissionError, ProcessLookupError):
                process_name = None

        ports.append(
            {
                "address": str(address),
                "port": int(port),
                "protocol": protocol,
                "process": process_name,
            }
        )

    ports.sort(key=lambda p: (p["port"], p["protocol"], p["address"]))
    return ports


def collect_local() -> dict[str, Any]:
    """Collect live metrics from the machine running this app (no SSH)."""
    result = empty_metrics(reachable=True)

    try:
        # interval=None uses a non-blocking snapshot relative to last call;
        # a short interval gives a more meaningful first reading.
        result["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
    except (psutil.Error, PermissionError, OSError) as exc:
        logger.warning("CPU collection failed: %s", exc)
        result["error"] = "CPU metrics unavailable"
        result["reachable"] = False
        return result

    try:
        mem = psutil.virtual_memory()
        result["memory"] = {
            "used": int(mem.used),
            "total": int(mem.total),
            "percent": float(mem.percent),
        }
    except (psutil.Error, PermissionError, OSError) as exc:
        logger.warning("Memory collection failed: %s", exc)
        result["error"] = "Memory metrics unavailable"

    try:
        net = psutil.net_io_counters()
        recv = int(net.bytes_recv)
        sent = int(net.bytes_sent)
        result["network"] = {
            "bytes_recv": recv,
            "bytes_sent": sent,
            "summary": network_summary(recv, sent),
        }
    except (psutil.Error, PermissionError, OSError) as exc:
        logger.warning("Network collection failed: %s", exc)
        result["network"]["summary"] = "unavailable"

    try:
        # kind='inet' avoids unix sockets; permissions may hide PIDs — fail soft.
        conns = psutil.net_connections(kind="inet")
        result["listening_ports"] = filter_listening_ports(conns)
    except (psutil.Error, PermissionError, OSError) as exc:
        logger.warning("Listening-port collection failed: %s", exc)
        result["listening_ports"] = []
        if not result["error"]:
            result["error"] = "Listening ports unavailable (permissions?)"

    return result
