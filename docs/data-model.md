# Data model (in-memory)

Server inventory lives only in the Flask process. **Restarting the app clears all servers.**

## Server fields

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | Short hex id assigned on create |
| `name` | string | Optional display name |
| `host` | string | Hostname or IP (`127.0.0.1` for localhost mode) |
| `port` | int | SSH port `1–65535` (ignored for localhost) |
| `ssh_user` | string | SSH username (empty for localhost) |
| `auth_type` | enum | `password` · `key` · `localhost` |
| `password` | string \| null | In memory only; never rendered in HTML |
| `private_key` | string \| null | Pasted PEM content in memory; never re-rendered |

Public UI views expose `has_password` / `has_key` booleans instead of secrets.

## Sessions

Flask signed session cookie holds the logged-in admin username. No server-side session DB.
