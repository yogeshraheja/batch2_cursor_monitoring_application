"""Unit tests for local + SSH collectors (mocked)."""

import socket
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psutil

from collectors.local import collect_local, filter_listening_ports
from collectors.metrics import mask_secret_in_text
from collectors.ssh import (
    ALLOWLISTED_COMMANDS,
    CMD_PROC_STAT,
    collect_remote,
    parse_cpu_percent,
    parse_meminfo,
    parse_net_dev,
    parse_ss_listening,
)
from servers import AUTH_PASSWORD, Server


def test_filter_listening_ports_only():
    listen = SimpleNamespace(
        status=psutil.CONN_LISTEN,
        laddr=SimpleNamespace(ip="0.0.0.0", port=5100),
        type=socket.SOCK_STREAM,
        pid=None,
    )
    established = SimpleNamespace(
        status=psutil.CONN_ESTABLISHED,
        laddr=SimpleNamespace(ip="10.0.0.1", port=443),
        type=socket.SOCK_STREAM,
        pid=None,
    )
    result = filter_listening_ports([listen, established])
    assert len(result) == 1
    assert result[0]["port"] == 5100


def test_collect_local_smoke():
    metrics = collect_local()
    assert metrics["reachable"] is True
    assert metrics["cpu_percent"] is not None
    assert metrics["memory"]["total"] is not None
    assert "summary" in metrics["network"]
    assert isinstance(metrics["listening_ports"], list)


def test_parse_cpu_mem_net_ss():
    cpu = parse_cpu_percent(
        "cpu  100 0 50 850 0 0 0 0 0 0\ncpu0 50 0 25 425 0 0 0 0 0 0\n"
    )
    assert cpu == 15.0

    mem = parse_meminfo(
        "MemTotal:       1000000 kB\nMemAvailable:    400000 kB\nMemFree: 100000 kB\n"
    )
    assert mem["total"] == 1000000 * 1024
    assert mem["used"] == 600000 * 1024
    assert mem["percent"] == 60.0

    recv, sent = parse_net_dev(
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets\n"
        "    lo: 100 0 0 0 0 0 0 0 100 0 0 0 0 0 0 0\n"
        "  eth0: 2000 0 0 0 0 0 0 0 3000 0 0 0 0 0 0 0\n"
    )
    assert recv == 2000
    assert sent == 3000

    ports = parse_ss_listening(
        "Netid State  Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
        "tcp   LISTEN 0      128          0.0.0.0:22        0.0.0.0:*\n"
        "tcp   ESTAB  0      0        10.0.0.1:22      10.0.0.2:4000\n"
        "udp   UNCONN 0      0        0.0.0.0:68        0.0.0.0:*\n"
    )
    assert {(p["port"], p["protocol"]) for p in ports} == {(22, "tcp"), (68, "udp")}


def test_ssh_allowlist_fixed():
    assert CMD_PROC_STAT in ALLOWLISTED_COMMANDS
    for cmd in ALLOWLISTED_COMMANDS:
        assert "{" not in cmd
        assert "%" not in cmd


def test_collect_remote_mocked_success():
    server = Server(
        id="abc",
        name="r",
        host="lab.example",
        port=22,
        ssh_user="ops",
        auth_type=AUTH_PASSWORD,
        password="pw-secret",
    )

    fake_client = MagicMock()

    def fake_exec(command, timeout=None):
        stdout = MagicMock()
        stderr = MagicMock()
        outputs = {
            "cat /proc/stat": "cpu  10 0 10 80 0 0 0 0 0 0\n",
            "cat /proc/meminfo": "MemTotal: 2000000 kB\nMemAvailable: 1000000 kB\n",
            "cat /proc/net/dev": (
                "Inter-| Receive | Transmit\n"
                " face |bytes packets|bytes packets\n"
                " eth0: 100 0 0 0 0 0 0 0 200 0 0 0 0 0 0 0\n"
            ),
            "ss -lntu": (
                "Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port\n"
                "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
            ),
        }
        stdout.read.return_value = outputs[command].encode()
        stderr.read.return_value = b""
        stdout.channel.recv_exit_status.return_value = 0
        return MagicMock(), stdout, stderr

    fake_client.exec_command.side_effect = fake_exec

    with patch("collectors.ssh._connect", return_value=fake_client):
        metrics = collect_remote(server)

    assert metrics["reachable"] is True
    assert metrics["cpu_percent"] is not None
    assert metrics["memory"]["percent"] == 50.0
    assert metrics["listening_ports"][0]["port"] == 22
    fake_client.close.assert_called_once()


def test_collect_remote_masks_password_in_errors():
    server = Server(
        id="abc",
        name="r",
        host="lab.example",
        port=22,
        ssh_user="ops",
        auth_type=AUTH_PASSWORD,
        password="unique-secret-xyz",
    )
    with patch(
        "collectors.ssh._connect",
        side_effect=RuntimeError("auth failed unique-secret-xyz"),
    ):
        metrics = collect_remote(server)
    assert metrics["reachable"] is False
    assert "unique-secret-xyz" not in (metrics["error"] or "")


def test_mask_secret_helper():
    assert "***" in mask_secret_in_text("boom secret99 here", "secret99")
