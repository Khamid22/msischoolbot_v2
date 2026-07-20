"""Provision accounts for eligible pending Teacher Academy records.

Dry-run is the default. Use ``--apply`` only after reviewing the exact rows and
proposed logins printed by this command.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.database import connect_auth_db  # noqa: E402
from backend.modules.teacher_academy.account_provisioning import (  # noqa: E402
    AcademyAccountProvisioningError,
    provision_recruitment_academy_account,
)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actor_account_id(conn: Any, login: str) -> int:
    row = conn.execute(
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE lower(btrim(login)) = lower(btrim(%s))
          AND role IN ('hr_manager', 'academic_director', 'ceo')
          AND status = 'active'
        LIMIT 1
        """,
        (login,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"Active operator account {login!r} was not found.")
    return int(row["id"])


def _review_rows(conn: Any) -> list[Any]:
    return conn.execute(
        """
        SELECT
            academy.id AS academy_teacher_id,
            academy.full_name,
            academy.academy_status,
            academy.recruitment_candidate_id,
            candidate.id AS candidate_id,
            candidate.status AS candidate_status,
            candidate.linked_account_id,
            candidate_account.role AS candidate_account_role,
            candidate_account.legacy_source_table AS candidate_account_source,
            candidate_account_staff.id AS candidate_account_staff_id,
            candidate_account_staff.role AS candidate_account_staff_role,
            candidate_account_staff.login AS candidate_account_staff_login,
            candidate_account_teacher.id AS candidate_account_teacher_id,
            candidate_account_teacher.recruitment_candidate_id
                AS candidate_account_teacher_candidate_id,
            linked_identity.teacher_id AS linked_teacher_id,
            linked_identity.teacher_status AS linked_teacher_status,
            linked_identity.staff_login AS linked_staff_login,
            EXISTS (
                SELECT 1
                FROM msi_v2.teachers promoted
                WHERE promoted.recruitment_candidate_id = candidate.id
                  AND promoted.status = 'active'
            ) AS has_active_teacher
        FROM msi_v2.academy_teachers academy
        LEFT JOIN msi_v2.teacher_candidates candidate
          ON candidate.id = academy.recruitment_candidate_id
        LEFT JOIN msi_v2.accounts candidate_account
          ON candidate_account.id = candidate.linked_account_id
        LEFT JOIN msi_v2.msi_staff candidate_account_staff
          ON candidate_account.legacy_source_table = 'msi_staff'
         AND candidate_account_staff.id = candidate_account.legacy_source_id
        LEFT JOIN msi_v2.teachers candidate_account_teacher
          ON candidate_account_teacher.id = candidate_account_staff.teacher_id
        LEFT JOIN LATERAL (
            SELECT
                teacher.id AS teacher_id,
                teacher.status AS teacher_status,
                staff.login AS staff_login
            FROM msi_v2.teachers teacher
            LEFT JOIN msi_v2.msi_staff staff
              ON staff.teacher_id = teacher.id
            WHERE teacher.recruitment_candidate_id = candidate.id
            ORDER BY teacher.id ASC, staff.id ASC
            LIMIT 1
        ) linked_identity ON TRUE
        WHERE academy.account_onboarding_status = 'pending'
          AND academy.user_id IS NULL
        ORDER BY academy.id ASC
        """
    ).fetchall()


def _eligibility_issue(row: Any) -> str:
    academy_status = str(row["academy_status"] or "").strip().lower()
    if academy_status in {"rejected", "removed"}:
        return f"Academy status is {academy_status}"
    candidate_id = int(row["candidate_id"] or 0)
    if not candidate_id:
        return "Academy record is not linked to a lifecycle profile"
    candidate_status = str(row["candidate_status"] or "").strip().lower()
    if candidate_status != "teacher_academy":
        return f"Lifecycle profile status is {candidate_status or 'missing'}"
    if bool(row["has_active_teacher"]):
        return "Teacher has already been promoted to Active Teacher"

    linked_account_id = int(row["linked_account_id"] or 0)
    if not linked_account_id:
        return ""
    if str(row["candidate_account_role"] or "").strip().lower() != "teacher":
        return "Lifecycle profile is linked to a non-teacher account"
    if str(row["candidate_account_source"] or "").strip().lower() != "msi_staff":
        return "Teacher account does not use the canonical staff identity"
    if not int(row["candidate_account_staff_id"] or 0):
        return "Linked teacher account has no staff identity"
    if str(row["candidate_account_staff_role"] or "").strip().lower() != "teacher":
        return "Linked staff identity belongs to another role"
    if not int(row["candidate_account_teacher_id"] or 0):
        return "Linked staff identity has no teacher profile"
    teacher_candidate_id = int(row["candidate_account_teacher_candidate_id"] or 0)
    if teacher_candidate_id not in {0, candidate_id}:
        return "Linked teacher identity belongs to another lifecycle profile"
    return ""


def _next_login_number(conn: Any) -> int:
    rows = conn.execute(
        """
        SELECT upper(login) AS login
        FROM msi_v2.msi_staff
        WHERE upper(login) ~ '^TCH[0-9]+$'
        """
    ).fetchall()
    values = []
    for row in rows:
        match = re.fullmatch(r"TCH(\d+)", str(row["login"] or "").upper())
        if match:
            values.append(int(match.group(1)))
    return max(values, default=0) + 1


def run(*, apply: bool, actor_login: str) -> int:
    with connect_auth_db() as conn:
        review_rows = _review_rows(conn)
        rows = [row for row in review_rows if not _eligibility_issue(row)]
        skipped = [
            (row, _eligibility_issue(row))
            for row in review_rows
            if _eligibility_issue(row)
        ]
        start_number = _next_login_number(conn)
        if skipped:
            print(f"Skipped pending Academy accounts: {len(skipped)}")
            for row, issue in skipped:
                candidate_label = (
                    f"Candidate #{int(row['candidate_id'])}"
                    if int(row["candidate_id"] or 0)
                    else "Candidate not linked"
                )
                print(
                    "  "
                    f"Academy #{int(row['academy_teacher_id'])} | "
                    f"{candidate_label} | "
                    f"{str(row['full_name'] or '').strip()} | "
                    f"{issue}"
                )
        if not rows:
            conn.rollback()
            print("Eligible pending Academy accounts: 0")
            return 0

        print(f"Eligible pending Academy accounts: {len(rows)}")
        new_login_offset = 0
        for row in rows:
            proposed_login = str(
                row["candidate_account_staff_login"]
                or row["linked_staff_login"]
                or ""
            ).strip()
            if not proposed_login:
                proposed_login = f"TCH{start_number + new_login_offset:04d}"
                new_login_offset += 1
            print(
                "  "
                f"Academy #{int(row['academy_teacher_id'])} | "
                f"Candidate #{int(row['candidate_id'])} | "
                f"{str(row['full_name'] or '').strip()} | "
                f"proposed login {proposed_login}"
            )
        if not apply:
            conn.rollback()
            print("Dry-run only. Re-run with --apply to provision these accounts.")
            return 0

        actor_account_id = _actor_account_id(conn, actor_login)
        now = _now()
        created = 0
        try:
            for row in rows:
                result = provision_recruitment_academy_account(
                    conn,
                    academy_teacher_id=int(row["academy_teacher_id"]),
                    actor_account_id=actor_account_id,
                    actor_login=actor_login,
                    now=now,
                )
                created += int(result.created)
        except AcademyAccountProvisioningError:
            conn.rollback()
            raise
        conn.commit()
        print(f"Provisioned Academy accounts: {created}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision eligible pending Teacher Academy accounts."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the changes. Without this flag the command is read-only.",
    )
    parser.add_argument(
        "--actor-login",
        default="HR0001",
        help="Active HR/Academic Director/CEO account attributed in audit events.",
    )
    args = parser.parse_args()
    try:
        return run(apply=bool(args.apply), actor_login=str(args.actor_login or "").strip())
    except (AcademyAccountProvisioningError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
