#!/usr/bin/env python3
"""Copy the current PostgreSQL database into an empty Railway PostgreSQL DB.

The script is intentionally conservative:
- It never deletes local data.
- It refuses to restore into a non-empty target database.
- It uses pg_dump + psql so all existing tables/data are preserved in the dump.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def output(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        check=True,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def require_postgres_url(value: str, label: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned.startswith(("postgres://", "postgresql://")):
        raise SystemExit(f"{label} must be a postgresql:// URL.")
    return cleaned


def target_table_count(target_url: str) -> int:
    sql = (
        "SELECT COUNT(*) "
        "FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
    )
    raw_count = output(["psql", target_url, "-Atqc", sql])
    try:
        return int(raw_count or "0")
    except ValueError as exc:
        raise SystemExit(f"Could not read target table count: {raw_count}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=os.environ.get("LOCAL_DATABASE_URL") or os.environ.get("DATABASE_URL") or "")
    parser.add_argument("--target", default=os.environ.get("RAILWAY_DATABASE_URL") or os.environ.get("RAILWAY_DATABASE_PUBLIC_URL") or "")
    parser.add_argument("--dump-path", default="backups/railway-migration.sql")
    args = parser.parse_args()

    source_url = require_postgres_url(args.source, "--source / LOCAL_DATABASE_URL")
    target_url = require_postgres_url(args.target, "--target / RAILWAY_DATABASE_PUBLIC_URL")
    dump_path = Path(args.dump_path)
    dump_path.parent.mkdir(parents=True, exist_ok=True)

    count = target_table_count(target_url)
    if count > 0:
        raise SystemExit(
            "Refusing to restore: target Railway database is not empty "
            f"({count} public tables found). Use a fresh Railway Postgres service "
            "or create an explicit backup/restore plan first."
        )

    print(f"Creating dump: {dump_path}")
    run(
        [
            "pg_dump",
            "--no-owner",
            "--no-privileges",
            "--format=plain",
            "--file",
            str(dump_path),
            source_url,
        ]
    )

    print("Restoring dump into empty Railway database...")
    run(["psql", target_url, "-v", "ON_ERROR_STOP=1", "-f", str(dump_path)])
    print("Done. Local data was not modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
