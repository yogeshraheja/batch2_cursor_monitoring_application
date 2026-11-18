# Demo Linux Server Monitoring

Local demo web app for viewing live Linux server metrics (CPU, memory, network, listening ports) without SSHing into each host for a quick check.

**Audience:** Internal L1 / L2 / L3 infrastructure teams  
**Nature:** Demo only — **not for production**; lab credentials only  
**Stack:** Python, Flask, HTML/CSS, Paramiko, psutil

See [docs/requirements.md](docs/requirements.md) (PRD), [docs/TODO.md](docs/TODO.md), and [docs/security.md](docs/security.md).

Out of scope (intentionally): alerting, historical graphs, Windows hosts, multi-user RBAC, HTTPS/HA, persistent DB.

## Folder layout

```
app.py              Flask entrypoint / factory
auth.py             Login helpers + login_required
config.py           Admin hash / session config from env
servers.py          In-memory server inventory
collectors/         Local (psutil) + SSH (Paramiko) metrics
scripts/            Password-hash generator
templates/          Jinja HTML templates
static/             CSS + small refresh helper
tests/              Unit / integration tests
docs/               PRD, TODO, security, data model, SSH notes
.github/workflows/  CI (pytest + minimal ruff)
```

## Local run

```bash
# from project root
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# set a demo admin password hash (plaintext is never stored)
export ADMIN_PASSWORD_HASH="$(python scripts/generate_password_hash.py 'your-demo-password')"
# optional: export SECRET_KEY='a-long-random-string'
# optional: export ADMIN_USERNAME=admin

python app.py
```

Open `http://127.0.0.1:5100`. Sign in as **`admin`** with the password you hashed. Use **Logout** to clear the session.

All monitoring views require login. Only `/login` and static assets are public.

### Configuration

| Env var | Purpose | Demo fallback |
|---------|---------|---------------|
| `ADMIN_PASSWORD_HASH` | Werkzeug hash of the admin password | **Required** |
| `ADMIN_USERNAME` | Single admin username | `admin` |
| `SECRET_KEY` | Flask session signing | `dev-only-change-me` |

Session cookies: `HttpOnly=True`, `SameSite=Lax`, `Secure=False` (HTTP demo). Forms use Flask-WTF CSRF.

### Server types (inventory)

- **Localhost** — metrics via `psutil` on the app host (no SSH)
- **Password** — remote Linux host over SSH with username + password
- **Private key** — remote Linux host over SSH; paste PEM/OpenSSH key into the form (held in memory; never shown again after save)

Inventory is **in-memory only** (cleared on restart). Edits never reveal existing secrets; leave password/key blank to keep them.

### Demo walkthrough

1. Sign in as `admin`
2. **Add server** → Auth type **Localhost** → Save → open detail for live CPU/memory/ports
3. (Optional) Add a lab remote host (password or pasted key) — see [docs/ssh-collection.md](docs/ssh-collection.md)
4. Overview and detail auto-refresh every **8 seconds**

## Unit tests

```bash
source .venv/bin/activate
pytest -q
```

Tests use fixture password hashes only — no production secrets.

## CI

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

GitHub Actions (`.github/workflows/ci.yml`) on push/PR:

1. Install pinned `requirements.txt`
2. Run `pytest -q` (no repository secrets required)
3. Minimal `ruff` syntax/undefined-name check

Replace `OWNER/REPO` in the badge URL with your GitHub path, or drop the badge if unused.

## Dependencies

Versions are **pinned** in `requirements.txt` to limit demo supply-chain drift.

To update pins:

```bash
# bump the version in requirements.txt, then:
pip install -r requirements.txt
pytest -q
# optional: pip install pip-audit && pip-audit -r requirements.txt
```

Do not commit real passwords or private keys. Use env vars / local untracked files for secrets.
