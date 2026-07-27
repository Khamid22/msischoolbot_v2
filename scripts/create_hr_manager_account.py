from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.modules.people.hr_manager.contracts import create_hr_manager_account  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reset the fixed HR0001 HR Manager account."
    )
    parser.add_argument(
        "--display-name",
        default="HR Manager",
        help="Display name to store for HR0001.",
    )
    args = parser.parse_args()

    created, error_message, credentials = create_hr_manager_account(
        display_name=args.display_name,
    )
    if not created:
        print(f"HR Manager provisioning failed: {error_message}", file=sys.stderr)
        return 1

    print("HR Manager account ready.")
    print(f"Login: {credentials['login']}")
    print(f"Password: {credentials['temporary_password']}")
    print("The password is stored as a hash and can be changed later from Account security.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
