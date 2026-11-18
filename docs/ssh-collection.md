# SSH metric collection

Remote hosts are polled with **Paramiko** using a fixed command allowlist. User input is never interpolated into shell strings.

## Allowlisted commands

| Command | Purpose |
|---------|---------|
| `cat /proc/stat` | CPU busy/idle estimate |
| `cat /proc/meminfo` | Memory used / total / % |
| `cat /proc/net/dev` | RX/TX byte counters (skips `lo`) |
| `ss -lntu` | Listening TCP/UDP sockets only |

## Auth

- **Password:** Paramiko password auth
- **Private key:** pasted PEM/OpenSSH key content held in memory (no arbitrary filesystem path reads)

## Security notes (demo)

- **Host keys:** the demo uses `AutoAddPolicy` (accept unknown host keys on first connect). That is convenient for a lab demo and **unsafe on untrusted networks**. Prefer a `known_hosts` file for anything beyond demo use.
- Connect timeout: 5s · command timeout: 8s
- SSH clients are always closed in a `finally` block
- Credential substrings are masked in UI error messages
- One collect per HTTP request (no background worker pool)

## Smoke checklist (manual)

1. Add a lab host with password or pasted key
2. Open Overview — status should become `reachable` with CPU/memory
3. Open Detail — listening ports listed; no established connections
4. Stop `sshd` or use a bad password — status `unreachable` with a safe error string
