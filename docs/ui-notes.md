# UI notes

Local Flask UI. Monitoring pages require login (Phase 1).

| Route | Page | Purpose | Access |
|-------|------|---------|--------|
| `/` | Home | Redirects to overview (signed in) or login | — |
| `/login` | Sign in | Username + password; CSRF-protected | Public |
| `/logout` | Logout | Clears session | Public |
| `/overview` | Overview | Servers table/cards skeleton | Login |
| `/servers/<server_id>` | Server detail | CPU / memory / network / ports placeholders | Login |
| `/servers/add` | Add server | Field layout only; no submit / no secret fields yet | Login |

## Navigation

Signed out: Sign in.  
Signed in: Overview · Server detail · Add server · Logout.

## Notes

- Bind: `0.0.0.0:5100` (reachable from any host).
- Credential secrets are not collected on the Add server form yet.
- Styling: `static/css/style.css` — dark infra shell, IBM Plex fonts.
