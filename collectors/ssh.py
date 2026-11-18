"""
Remote Linux metrics via Paramiko SSH.

Security:
  - Commands are a fixed allowlist — never interpolate user input into shells.
  - Demo uses AutoAddPolicy (accepts unknown host keys). Lab hosts only —
    see docs/ssh-collection.md.
  - Sessions always closed in finally; short connect/command timeouts.
  - Credential material is masked in error strings returned to the UI.
"""

from __future__ import annotations

import logging
import re
from io import StringIO
from typing import Any

import paramiko

from collectors.metrics import empty_metrics, mask_secret_in_text, network_summary
from servers import AUTH_KEY, AUTH_PASSWORD, Server

logger = logging.getLogger(__name__)

# Fixed allowlist — do not build these from user input.
CMD_PROC_STAT = "cat /proc/stat"
CMD_PROC_MEMINFO = "cat /proc/meminfo"
CMD_PROC_NET_DEV = "cat /proc/net/dev"
CMD_SS_LISTEN = "ss -lntu"

ALLOWLISTED_COMMANDS = frozenset(
    {
        CMD_PROC_STAT,
        CMD_PROC_MEMINFO,
        CMD_PROC_NET_DEV,
        CMD_SS_LISTEN,
    }
)

SSH_CONNECT_TIMEOUT = 5
SSH_COMMAND_TIMEOUT = 8


def _assert_allowlisted(command: str) -> None:
    if command not in ALLOWLISTED_COMMANDS:
        raise ValueError(f"Command not allowlisted: {command!r}")


def _run_command(client: paramiko.SSHClient, command: str) -> str:
    _assert_allowlisted(command)
    _stdin, stdout, stderr = client.exec_command(command, timeout=SSH_COMMAND_TIMEOUT)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0 and not out:
        raise RuntimeError(err.strip() or f"Command failed ({exit_status}): {command}")
    return out


def parse_cpu_percent(proc_stat: str) -> float | None:
    """Estimate idle-based CPU usage from a single /proc/stat snapshot."""
    for line in proc_stat.splitlines():
        if not line.startswith("cpu "):
            continue
        parts = line.split()
        if len(parts) < 5:
            return None
        values = [int(x) for x in parts[1:]]
        total = sum(values)
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        if total <= 0:
            return None
        busy = total - idle
        return round(100.0 * busy / total, 1)
    return None


def parse_meminfo(proc_meminfo: str) -> dict[str, int | float | None]:
    data: dict[str, int] = {}
    for line in proc_meminfo.splitlines():
        match = re.match(r"^(\w+):\s+(\d+)", line)
        if match:
            data[match.group(1)] = int(match.group(2)) * 1024  # kB → bytes

    total = data.get("MemTotal")
    available = data.get("MemAvailable")
    if total is None:
        return {"used": None, "total": None, "percent": None}
    if available is not None:
        used = total - available
    else:
        free = data.get("MemFree", 0)
        buffers = data.get("Buffers", 0)
        cached = data.get("Cached", 0)
        used = total - free - buffers - cached
    percent = round(100.0 * used / total, 1) if total else None
    return {"used": used, "total": total, "percent": percent}


def parse_net_dev(proc_net_dev: str) -> tuple[int | None, int | None]:
    recv_total = 0
    sent_total = 0
    found = False
    for line in proc_net_dev.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        iface = name.strip()
        if iface == "lo":
            continue
        cols = rest.split()
        if len(cols) < 9:
            continue
        recv_total += int(cols[0])
        sent_total += int(cols[8])
        found = True
    if not found:
        return None, None
    return recv_total, sent_total


def parse_ss_listening(ss_output: str) -> list[dict[str, Any]]:
    """Parse ``ss -lntu`` into listening-port rows (LISTEN / UNCONN only)."""
    ports: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()

    for line in ss_output.splitlines():
        line = line.strip()
        if not line or line.startswith("Netid") or line.startswith("State"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        state = parts[1]
        # ss -lntu: tcp LISTEN, udp UNCONN (listening)
        if state not in {"LISTEN", "UNCONN"}:
            continue
        protocol = parts[0].lower()
        local = parts[4]
        # Handle IPv6 [::]:22 and IPv4 0.0.0.0:22 / *:22
        if local.startswith("["):
            match = re.match(r"^\[([^\]]+)\]:(\d+)$", local)
            if not match:
                continue
            address, port_s = match.group(1), match.group(2)
        else:
            if ":" not in local:
                continue
            address, port_s = local.rsplit(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            continue
        key = (address, port, protocol)
        if key in seen:
            continue
        seen.add(key)
        ports.append(
            {
                "address": address,
                "port": port,
                "protocol": protocol,
                "process": None,
            }
        )

    ports.sort(key=lambda p: (p["port"], p["protocol"], p["address"]))
    return ports


def _connect(server: Server) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    # DEMO ONLY: AutoAddPolicy trusts unknown host keys on first connect.
    # Do not use this policy against untrusted networks. Prefer known_hosts
    # verification for anything beyond a lab demo.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        "hostname": server.host,
        "port": server.port,
        "username": server.ssh_user,
        "timeout": SSH_CONNECT_TIMEOUT,
        "allow_agent": False,
        "look_for_keys": False,
    }

    if server.auth_type == AUTH_PASSWORD:
        connect_kwargs["password"] = server.password or ""
    elif server.auth_type == AUTH_KEY:
        key_file = StringIO(server.private_key or "")
        pkey = None
        last_err: Exception | None = None
        for key_cls in (
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        ):
            try:
                key_file.seek(0)
                pkey = key_cls.from_private_key(key_file)
                break
            except paramiko.SSHException as exc:
                last_err = exc
                continue
        if pkey is None:
            raise RuntimeError(
                f"Unable to load private key: {last_err or 'unsupported format'}"
            )
        connect_kwargs["pkey"] = pkey
    else:
        raise RuntimeError(f"Unsupported SSH auth_type: {server.auth_type}")

    client.connect(**connect_kwargs)
    return client


def collect_remote(server: Server) -> dict[str, Any]:
    """Collect metrics from a remote Linux host over SSH (allowlisted commands)."""
    if server.auth_type not in {AUTH_PASSWORD, AUTH_KEY}:
        return empty_metrics(reachable=False, error="Not an SSH server entry")

    secrets = (server.password, server.private_key)
    client: paramiko.SSHClient | None = None
    try:
        client = _connect(server)
        cpu_raw = _run_command(client, CMD_PROC_STAT)
        mem_raw = _run_command(client, CMD_PROC_MEMINFO)
        net_raw = _run_command(client, CMD_PROC_NET_DEV)
        ss_raw = _run_command(client, CMD_SS_LISTEN)

        recv, sent = parse_net_dev(net_raw)
        result = empty_metrics(reachable=True)
        result["cpu_percent"] = parse_cpu_percent(cpu_raw)
        result["memory"] = parse_meminfo(mem_raw)
        result["network"] = {
            "bytes_recv": recv,
            "bytes_sent": sent,
            "summary": network_summary(recv, sent),
        }
        result["listening_ports"] = parse_ss_listening(ss_raw)
        return result
    except Exception as exc:  # noqa: BLE001 — surface any SSH/parse failure to UI
        msg = mask_secret_in_text(str(exc), *secrets)
        logger.info("SSH collection failed for %s: %s", server.host, msg)
        return empty_metrics(reachable=False, error=msg or "SSH connection failed")
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass
