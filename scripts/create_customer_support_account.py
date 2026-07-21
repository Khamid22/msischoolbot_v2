from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.modules.people.staff.service import create_customer_support_account  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reset the fixed cs0001 Customer Support account."
    )
    parser.add_argument(
        "--display-name",
        default="Customer Support",
        help="Display name to store for cs0001.",
    )
    args = parser.parse_args()

    created, error_message, credentials = create_customer_support_account(
        display_name=args.display_name,
    )
    if not created:
        print(f"Customer Support provisioning failed: {error_message}", file=sys.stderr)
        return 1

    print("Customer Support account ready.")
    print(f"Login: {credentials['login']}")
    print(f"Password: {credentials['temporary_password']}")
    print("The password is stored as a hash and can be changed later from Account security.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
