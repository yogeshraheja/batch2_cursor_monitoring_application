# Demo Linux Server Monitoring

Local-only demo web app for viewing live Linux server metrics (CPU, memory, network, listening ports) without SSHing into each host for a quick check.

**Audience:** Internal L1 / L2 / L3 infrastructure teams  
**Nature:** Demo only — run on the same machine as Cursor  
**Stack:** Python, Flask, HTML/CSS

See [docs/requirements.md](docs/requirements.md) (PRD) and [docs/TODO.md](docs/TODO.md) for scope and build plan.

## Folder layout

```
app.py              Flask entrypoint / factory
auth.py             Login helpers + login_required
config.py           Admin hash / session config from env
scripts/            Password-hash generator
templates/          Jinja HTML templates
static/css/         Stylesheets
tests/              Unit / integration tests
docs/               PRD, TODO, UI notes
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

One-liner (same as the script):

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-demo-password'))"
```

Open `http://127.0.0.1:5100` (or the host/port printed by the app).  
Sign in with username **`admin`** and the password you hashed above.  
Use **Logout** in the nav to clear the session.

All monitoring views (overview, server detail, add server) require login. Only `/login` and static assets are public.

### Configuration

| Env var | Purpose | Demo fallback |
|---------|---------|---------------|
| `ADMIN_PASSWORD_HASH` | Werkzeug hash of the admin password | **Required** — app refuses to start without it |
| `ADMIN_USERNAME` | Single admin username | `admin` |
| `SECRET_KEY` | Flask session signing | `dev-only-change-me` (local demo only) |

Session cookies: `HttpOnly=True`, `SameSite=Lax`, `Secure=False` (HTTP demo). Login form uses Flask-WTF CSRF.

Do not commit real passwords or private keys. Use env vars / local untracked files for secrets. Never put plaintext passwords in tracked files.

## Unit tests

```bash
source .venv/bin/activate
pytest -q
```

Tests use fixture password hashes only — no production secrets.
