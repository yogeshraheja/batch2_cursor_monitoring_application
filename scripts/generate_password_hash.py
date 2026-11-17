#!/usr/bin/env python3
"""Generate a Werkzeug password hash for ADMIN_PASSWORD_HASH.

Usage:
  python scripts/generate_password_hash.py
  python scripts/generate_password_hash.py 'your-demo-password'

The plaintext is read from the argument or a prompt; it is never printed back.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Allow running from project root without installing a package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import hash_password  # noqa: E402


def main() -> int:
    if len(sys.argv) > 1:
        plaintext = sys.argv[1]
    else:
        plaintext = getpass.getpass("Demo password: ")
        confirm = getpass.getpass("Confirm password: ")
        if plaintext != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1

    if not plaintext:
        print("Password must not be empty.", file=sys.stderr)
        return 1

    print(hash_password(plaintext))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
