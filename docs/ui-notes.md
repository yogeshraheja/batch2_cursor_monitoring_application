# UI notes

Local Flask UI. All monitoring pages require login.

| Route | Page | Purpose | Access |
|-------|------|---------|--------|
| `/` | Home | Redirects to overview or login | — |
| `/login` | Sign in | Username + password; CSRF | Public |
| `/logout` | Logout | Clears session | Public |
| `/overview` | Overview | Server table + live metrics (8s refresh) | Login |
| `/servers/add` | Add server | Password / key / localhost | Login |
| `/servers/<id>/edit` | Edit server | Prefill without secrets | Login |
| `/servers/<id>/delete` | Delete | POST + confirm only | Login |
| `/servers/<id>` | Detail | CPU, memory, network, listening ports | Login |

## Navigation

Signed out: Sign in.  
Signed in: Overview · Add server · Logout.

## Notes

- Bind: `0.0.0.0:5100`
- Overview / detail auto-refresh every **8 seconds** (meta refresh + session cookie; no tokens in query string)
- Styling: `static/css/style.css` — dark infra shell, IBM Plex fonts
