# PRD: Demo Linux Server Monitoring Infrastructure

## 1. Overview

Local demo web application that shows real-time Linux server metrics (CPU, memory, network, listening ports) without requiring operators to SSH into each host for a quick check.

**Audience:** Internal L1 / L2 / L3 infrastructure and application teams  
**Nature:** Demo only — run on the same machine as Cursor  
**Stack:** Python, Flask, HTML/CSS/JS UI

---

## 2. Problem

Today, teams log into each Linux server to inspect live CPU, memory, network, and port usage. That is slow for triage and inconsistent across teams.

---

## 3. Goals

- Provide a read-only, browser-based view of live server metrics
- Allow adding/editing Linux servers (and localhost) from the UI
- Authenticate with a single admin account using a hashed password
- Keep setup and run steps minimal for a local demo

---

## 4. Non-Goals (Out of Scope)

- Alerting / thresholds / notifications
- Historical charts or metric retention
- Windows or cloud-managed hosts
- Multi-user accounts or RBAC
- Production hardening (HTTPS, HA, rate limits)
- Persistent database (all runtime data is in memory)

---

## 5. Users & Access

| Role | Access |
|------|--------|
| Admin (only user) | Sign in, view metrics, add/edit servers |

- Default username: `admin`
- Password stored as a hash (e.g. Werkzeug / bcrypt-style hash)
- No other users; no self-registration
- Session-based login with logout available

---

## 6. Features

### 6.1 Sign-in (read-gated UI)

- Login page with username + password
- Successful login grants access to dashboard
- Unauthenticated users are redirected to login
- Monitoring views are **read-only** (no remote commands beyond metric collection)

### 6.2 Server inventory

- Add Linux servers with:
  - Display name (optional)
  - IP address or hostname
  - SSH credentials: username + **password** *or* **private key** path/content
  - Port (default `22`)
- **Localhost** entry: collect metrics directly on the app host (no SSH)
- Edit existing server entries (credentials, host, name)
- Remove server from the in-memory list
- Server list is held **in memory** only (lost on process restart)

### 6.3 Overview dashboard

- Table/cards of all configured servers
- Per server: name/host, connection status (reachable / unreachable), latest CPU %, memory %, short network summary
- Auto-refresh (suggested interval: **5–10 seconds**)
- Click through to server detail

### 6.4 Server detail page

- Live CPU usage
- Live memory usage (used / total / %)
- Network usage (e.g. RX/TX rates or interface counters — keep simple)
- **Listening ports only** (no established-connection listing)
- Auto-refresh on the same interval as overview
- Read-only presentation

### 6.5 Metric collection

| Target | Method |
|--------|--------|
| Remote Linux host | SSH from the Flask app; run lightweight read-only commands (e.g. `/proc`, `ss`/`ss -lntu`, or equivalent) |
| Localhost | Collect directly on the machine running the app (no SSH) |

Collection failures must show a clear error state on the UI (e.g. “unreachable” / last error message), without crashing the app.

---

## 7. UI Requirements

- Attractive, simple Flask-served front end (templates + CSS; optional minimal JS for refresh)
- Read-only monitoring screens
- Clear navigation: Login → Overview → Detail; Add/Edit server forms
- Usable on desktop browsers; mobile polish not required for demo

---

## 8. Technical Requirements

| Item | Choice |
|------|--------|
| Language | Python 3 |
| Framework | Flask |
| Auth | Single admin user; hashed password |
| Storage | In-memory (servers + sessions as applicable) |
| Remote access | Paramiko (or equivalent) over SSH |
| Local metrics | Direct OS reads / `psutil` (or equivalent) |
| Deployment | Local only |

---

## 9. Local Run (Minimal)

```bash
# from project root
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5100` (or the port printed by the app).  
Sign in with `admin` and the configured demo password.

---

## 10. Acceptance Criteria

1. Unauthenticated user cannot see monitoring pages.
2. `admin` can sign in with the hashed-password credential.
3. Admin can add a remote Linux server (password or key) and edit/remove it.
4. Admin can monitor localhost without SSH.
5. Overview lists all servers with live CPU/memory (and status).
6. Detail page shows CPU, memory, network, and **listening ports** only.
7. Pages auto-refresh without full manual reload being required.
8. Restarting the app clears the in-memory server list (expected for demo).
9. No alerting, history, or multi-user features are present.

---

## 11. Demo Assumptions

- Target hosts are reachable from the Cursor machine over SSH when remote monitoring is used.
- Demo credentials and keys are for lab/demo hosts only.
- Data loss on restart is acceptable.
