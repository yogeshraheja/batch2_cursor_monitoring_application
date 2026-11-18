# Security notes — local demo threat model

This app is a **local / lab demo**, not production monitoring.

## Trust boundary

- Single admin user; hashed password via env (`ADMIN_PASSWORD_HASH`)
- All monitoring and inventory mutations require login
- Mutating forms use Flask-WTF CSRF tokens
- Bind address is `0.0.0.0:5100` so the demo is reachable on the host network (Phase 0 choice). Anyone who can reach that port can attempt login — use only on trusted networks / localhost port-forwarding as appropriate.

## What we protect (demo-appropriate)

| Control | Status |
|---------|--------|
| Password stored hashed (Werkzeug) | Yes |
| Secrets not committed to git | `.gitignore` covers `.env`, keys, PEMs |
| Secrets not rendered in HTML listings | Masked; blank-on-edit keeps existing |
| Secrets not logged | Collectors mask credential substrings in errors |
| SSH commands allowlisted | Fixed `cat /proc/*` + `ss -lntu` only |
| Listening ports filter | LISTEN / UNCONN only |
| Local collector | psutil read-only APIs; no `shell=True` with user input |

## Explicit non-goals

- HTTPS, HA, rate limiting, RBAC, audit log shipping
- Persistent encrypted secret store
- Strict SSH host-key pinning (demo uses `AutoAddPolicy` — see [ssh-collection.md](./ssh-collection.md))

## Operator guidance

- Use **lab credentials only**
- Do not expose the process to the public internet
- Treat pasted private keys as sensitive; they live in process memory until restart
