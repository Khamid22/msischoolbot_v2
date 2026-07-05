#!/usr/bin/env python3
"""Create or reset the bootstrap Academic Director account.

The command is intentionally small and idempotent. It writes hashed passwords
to ``msi_v2.msi_staff`` and ``msi_v2.accounts`` and prints only the temporary
credential the operator needs for first login.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.roles.academic_director.staff_registration import create_academic_director_account  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the bootstrap Academic Director account.")
    parser.add_argument("--login", default="AD0001", help="Academic Director login, default AD0001.")
    parser.add_argument("--display-name", default="Academic Director", help="Display name to store.")
    parser.add_argument(
        "--temporary-password",
        default="",
        help="Temporary password. Defaults to the login. Never pass a real long-term password here.",
    )
    args = parser.parse_args()

    created, error_message, credentials = create_academic_director_account(
        login=args.login,
        display_name=args.display_name,
        temporary_password=args.temporary_password,
    )
    if not created:
        print(f"Academic Director bootstrap failed: {error_message}", file=sys.stderr)
        return 1

    print("Academic Director account ready.")
    print(f"Login: {credentials['login']}")
    print(f"Temporary password: {credentials['temporary_password']}")
    print("Password hash stored in PostgreSQL; no hash was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
