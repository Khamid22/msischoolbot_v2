from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.db import queries  # noqa: E402
from web.backend.domains.academics.postgres_service import (  # noqa: E402
    consolidate_postgres_values,
    ensure_academic_schema,
)


def main():
    parser = argparse.ArgumentParser(
        description="Normalize existing PostgreSQL data into canonical MSI School values."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the changes. Without this flag the script rolls back after counting.",
    )
    args = parser.parse_args()

    with queries.connect_auth_db() as conn:
        queries.create_tables(conn)
        ensure_academic_schema(conn)
        result = consolidate_postgres_values(conn)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    mode = "applied" if args.apply else "dry run rolled back"
    print(f"PostgreSQL consolidation {mode}:")
    for key in sorted(result):
        print(f"- {key}: {result[key]}")


if __name__ == "__main__":
    main()
