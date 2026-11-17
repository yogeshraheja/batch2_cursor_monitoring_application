# TODO: Demo Linux Server Monitoring (AI-friendly increments)

Work top to bottom. Each step is small, demo-scoped, and meant to be completable in one focused pass.  
**PRD:** [requirements.md](./requirements.md)

Legend: ✅ done · ⬜ not started  
Every step includes **Security** and **Docs** checkboxes — complete those before moving on.

---

## Phase 0 — Project initialization & basic UI

### Step 0.1 — Scaffold the project
- [x] Create package layout: `app/` (or flat `app.py`), `templates/`, `static/css/`, `tests/`, `docs/`
- [x] Add `requirements.txt` with Flask (+ pin versions for demo)
- [x] Add `.gitignore` (venv, `__pycache__`, `.env`, IDE files, secrets)
- [x] Add minimal `README.md`: what it is, local run only, link to PRD/TODO
- **Security**
  - [x] Ensure `.env` / secrets / private keys are in `.gitignore`
  - [x] Do not commit demo passwords in plaintext in tracked files
- **Docs**
  - [x] Document folder layout in `README.md` (3–5 lines)

### Step 0.2 — Flask app boots with a basic shell UI
- [x] Create Flask entrypoint (`app.py` or `app/__init__.py`) binding to `0.0.0.0` (all interfaces)
- [x] Add base template (nav placeholder, content block) + simple attractive CSS
- [x] Add home/placeholder page: app title + short “demo monitoring” blurb
- [x] Verify: `python app.py` opens UI in browser
- **Security**
  - [x] Bind to `0.0.0.0` so the demo is reachable from any host
  - [x] Set a non-default `SECRET_KEY` via env var (document fallback for demo)
- **Docs**
  - [x] Update `README.md` with the 4-line local run block from the PRD

### Step 0.3 — Static pages wired (no auth yet)
- [x] Add empty Overview template (servers table/cards skeleton, no live data)
- [x] Add empty Server Detail template (CPU/memory/network/ports placeholders)
- [x] Add empty Add Server form template (fields only, no submit logic)
- [x] Link pages in nav for local visual check
- **Security**
  - [x] Mark pages as temporary/public; note they will be auth-gated next
  - [x] No forms that accept secrets yet without HTTPS note (local-only OK)
- **Docs**
  - [x] Add `docs/ui-notes.md` (or README section): page list + purpose

---

## Phase 1 — Sign-in & unit tests

### Step 1.1 — Config for single admin user (hashed password)
- [x] Load admin username (`admin`) and password hash from env/config
- [x] Helper to generate hash for local setup (script or documented one-liner)
- [x] Reject empty password / missing hash at startup with a clear error
- **Security**
  - [x] Store only hashed password (Werkzeug `generate_password_hash` / `check_password_hash`)
  - [x] Never log the plaintext password
  - [x] Document how to set `ADMIN_PASSWORD_HASH` (or generate from env once at first run for demo — prefer hash-in-env)
- **Docs**
  - [x] README: how to set admin hash for local demo

### Step 1.2 — Login / logout routes & session
- [x] Login page (username + password)
- [x] POST login: verify hash; set session; redirect to overview
- [x] Logout clears session
- [x] Flash clear errors on bad credentials (no user enumeration detail beyond “invalid”)
- **Security**
  - [x] Use Flask session cookie; `HttpOnly` (default); document `SESSION` settings
  - [x] CSRF: enable Flask-WTF CSRF or equivalent on login form (demo-minimal)
  - [x] Constant-time password check via library helper
- **Docs**
  - [x] README: default username `admin`; logout location

### Step 1.3 — Protect routes (read-gated UI)
- [x] `@login_required` decorator (or before_request) on overview, detail, server forms
- [x] Redirect unauthenticated users to login
- [x] Leave only login (+ static assets) public
- **Security**
  - [x] Confirm no monitoring/API route is public
  - [x] Ensure logout invalidates access to protected pages
- **Docs**
  - [x] Note in README: all monitoring views require login

### Step 1.4 — Unit tests for auth
- [x] Add `pytest` (+ Flask test client) to requirements / requirements-dev
- [x] Tests: login success, login failure, logout, protected route redirects
- [x] Tests: password hash verify helper
- [x] Make tests runnable with: `pytest -q`
- **Security**
  - [x] Tests use fixture hashes only — no real production secrets
  - [x] Assert session not set on failed login
- **Docs**
  - [x] README: how to run unit tests locally

---

## Phase 2 — CI/CD (GitHub Actions) & quality gates

### Step 2.1 — GitHub Actions CI workflow
- [ ] Add `.github/workflows/ci.yml`
- [ ] On push/PR: checkout, set up Python, install deps, run `pytest`
- [ ] Optional lint job (ruff/flake8) — keep minimal if used
- **Security**
  - [ ] No secrets required in CI for unit tests
  - [ ] Do not echo env secrets in workflow logs
- **Docs**
  - [ ] README badge or short “CI” section: what CI runs

### Step 2.2 — Dependency & safety hygiene (demo-light)
- [ ] Pin dependencies in `requirements.txt`
- [ ] Add a CI step or documented command for basic audit (optional `pip-audit` — skip if too heavy)
- **Security**
  - [ ] Prefer pinned versions to avoid surprise supply-chain drift in demo
- **Docs**
  - [ ] Document how to update pins when needed

---

## Phase 3 — In-memory server inventory (CRUD UI)

### Step 3.1 — In-memory server model
- [ ] Define server dict/dataclass: id, name, host, port, ssh_user, auth_type (password|key|localhost), credential fields
- [ ] In-memory store: list/dict with add / get / update / delete
- [ ] Unit tests for store CRUD
- **Security**
  - [ ] Never return raw passwords/keys in HTML listings (mask in UI)
  - [ ] Do not log SSH passwords or private key material
- **Docs**
  - [ ] `docs/data-model.md` (or README): fields + “lost on restart”

### Step 3.2 — Add server form (password auth)
- [ ] Wire Add Server POST → store
- [ ] Validate host, port, username, password present for password mode
- [ ] Redirect to overview after add
- [ ] Unit/integration tests for add validation
- **Security**
  - [ ] CSRF on form
  - [ ] Basic input validation (host length, port range 1–65535)
  - [ ] Reject path traversal-like junk in host field
- **Docs**
  - [ ] Short help text under form: demo credentials only

### Step 3.3 — Add server: key-based + localhost modes
- [ ] UI toggle/option: password | private key | localhost
- [ ] Localhost: skip SSH fields; mark `auth_type=localhost`
- [ ] Key mode: accept key path or key content (demo-simple); validate non-empty
- [ ] Tests for each mode’s validation rules
- **Security**
  - [ ] If key path: only allow reading paths intended for demo; document risk of path abuse
  - [ ] Prefer pasting key into memory for demo over reading arbitrary filesystem paths if simpler/safer
  - [ ] Never render private key back to the browser after save (show “key set” only)
- **Docs**
  - [ ] README: three server types explained in 3 bullets

### Step 3.4 — Edit & remove servers
- [ ] Edit form pre-filled (without revealing secrets; blank = keep existing)
- [ ] Delete with confirm (simple confirm dialog or POST confirm)
- [ ] Tests: update, delete, 404 for unknown id
- **Security**
  - [ ] Only authenticated admin can mutate inventory
  - [ ] Use POST/DELETE for mutations (no state-changing GET)
- **Docs**
  - [ ] Note: edits are in-memory only

---

## Phase 4 — Localhost metrics (direct collection)

### Step 4.1 — Local collector module
- [ ] Implement `collect_local()` using `psutil` (or `/proc`): CPU %, memory used/total/%, simple network counters
- [ ] Unit tests with mocks for psutil where needed
- **Security**
  - [ ] Read-only APIs only; no shell=`True` with user input
  - [ ] Handle permission errors without crashing
- **Docs**
  - [ ] Comment or docs: which metrics are collected locally

### Step 4.2 — Listening ports (local)
- [ ] List listening ports only (filter established)
- [ ] Show bind address + port + optional process name if cheap
- [ ] Tests: filter logic for listening vs non-listening
- **Security**
  - [ ] Do not expose command execution; use psutil/net_connections carefully
  - [ ] Fail soft if permissions block process names
- **Docs**
  - [ ] UI label: “Listening ports only”

### Step 4.3 — Wire localhost into Overview + Detail
- [ ] Overview row for localhost server shows live CPU/memory (+ status)
- [ ] Detail page renders full local metrics + listening ports
- [ ] Auto-refresh via meta refresh or small JS `fetch`/reload (5–10s)
- **Security**
  - [ ] Metrics JSON/HTML endpoints still require login
  - [ ] No arbitrary query params that change collection commands
- **Docs**
  - [ ] README: add localhost server and open detail

---

## Phase 5 — Remote metrics via SSH

### Step 5.1 — SSH client wrapper
- [ ] Connect with Paramiko (password or key) with short timeout
- [ ] Run fixed, allowlisted read-only commands only (e.g. read `/proc/stat`, `/proc/meminfo`, `ss -lntu`)
- [ ] Parse output into same metric shape as local collector
- [ ] Unit tests with mocked SSH client
- **Security**
  - [ ] **Allowlist commands** — never interpolate user input into shell strings
  - [ ] Disable unknown host-key policy that silently trusts everything *or* document demo `AutoAddPolicy` risk clearly
  - [ ] Timeouts + connection error handling; no hang forever
  - [ ] Close SSH sessions in `finally`
- **Docs**
  - [ ] `docs/ssh-collection.md`: commands used + security notes

### Step 5.2 — Remote Overview + Detail integration
- [ ] Overview: status reachable/unreachable, CPU %, memory %, short network summary
- [ ] Detail: CPU, memory, network, listening ports from SSH parse
- [ ] Show last error message when unreachable
- [ ] Manual smoke test checklist (local SSH to a lab host if available)
- **Security**
  - [ ] Mask credentials in any error messages
  - [ ] Rate/limit concurrency simply (one collect per request is fine for demo)
- **Docs**
  - [ ] README: how to add a remote host for demo

### Step 5.3 — Auto-refresh polish
- [ ] Shared refresh interval (5–10s) on overview and detail
- [ ] Avoid full layout flash if using JS (optional nicety)
- [ ] Ensure refresh does not re-POST forms
- **Security**
  - [ ] Refresh requests use session cookie only; no tokens in query string
- **Docs**
  - [ ] Document refresh interval in UI or README

---

## Phase 6 — Hardening, docs wrap-up, demo readiness

### Step 6.1 — Final security pass (demo-appropriate)
- [ ] Confirm bind address is localhost
- [ ] Confirm all mutating routes require login + CSRF
- [ ] Confirm secrets not in git / logs / HTML
- [ ] Confirm SSH command allowlist
- [ ] Confirm listening-ports-only filter
- **Docs**
  - [ ] Add `docs/security.md`: threat model for local demo (short)

### Step 6.2 — Final documentation pass
- [ ] README: run, login, add localhost, add remote, run tests, CI
- [ ] Ensure PRD ↔ TODO ↔ README agree on scope (no alerting/history/RBAC)
- [ ] Mark completed TODO items as you go
- **Security**
  - [ ] README warns: demo only; not for production; lab credentials only
- **Docs**
  - [ ] Keep instructions minimal (match PRD §9)

### Step 6.3 — Demo acceptance checklist
- [ ] Unauthenticated users redirected
- [ ] Admin login with hashed password works
- [ ] Add / edit / remove server works (in memory)
- [ ] Localhost metrics work without SSH
- [ ] Remote SSH metrics work (if lab host available)
- [ ] Overview + detail auto-refresh
- [ ] Listening ports only
- [ ] Restart clears inventory (expected)
- [ ] `pytest` green locally and in GitHub Actions
- **Security**
  - [ ] Re-check no plaintext password in repo
- **Docs**
  - [ ] Tick PRD acceptance criteria against this checklist

---

## Suggested implementation order (summary)

1. Phase 0 — init + basic UI  
2. Phase 1 — sign-in + unit tests  
3. Phase 2 — GitHub Actions CI  
4. Phase 3 — in-memory server CRUD  
5. Phase 4 — localhost metrics  
6. Phase 5 — SSH remote metrics  
7. Phase 6 — security/docs/demo checklist  

---

## Out of scope (do not add TODO work)

- Alerting, historical graphs, Windows hosts, multi-user RBAC, HTTPS/HA, persistent DB, Docker (unless explicitly requested later)
