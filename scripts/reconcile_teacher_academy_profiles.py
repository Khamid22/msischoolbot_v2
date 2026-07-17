"""Idempotently reconcile production Teacher Academy records with lifecycle profiles.

The command is dry-run by default. Pass ``--apply`` only after reviewing the
printed actions. It never creates hiring decisions or application history.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.database import connect_auth_db  # noqa: E402
from backend.modules.hr.recruitment import repository  # noqa: E402


APPLICATION_LINKS = (
    (164, 8, "Qodirov Ibrohim"),
    (111, 9, "Niaz Ahmed"),
    (301, 11, "Ziyodullayeva Nigora"),
)
APPLICATION_INTAKES = (
    (146, "Zikriyoev Javokhir"),
    (190, "Mamadiyev Asilbek"),
    (288, "Murotboyeva Sabrina"),
)
ACADEMY_DIRECT_EXISTING = (
    (14, "Bunyodjon Xaydaraliyev"),
    (12, "Shakhzod"),
)
ACADEMY_DIRECT_NEW = ("Azizbek Quldashev",)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(conn: Any, sql: str, params: tuple[Any, ...]) -> Any:
    return conn.execute(sql, params).fetchone()


def _actor(conn: Any, login: str) -> tuple[int | None, int | None]:
    row = _row(
        conn,
        """
        SELECT id, legacy_source_id
        FROM msi_v2.accounts
        WHERE lower(login) = lower(%s) AND role = 'hr_manager'
        LIMIT 1
        """,
        (login,),
    )
    if not row:
        raise RuntimeError(f"HR actor account {login!r} was not found.")
    return int(row["id"]), int(row["legacy_source_id"] or 0) or None


def _account_for_academy(conn: Any, academy: Any) -> int | None:
    staff_id = int(academy["user_id"] or 0)
    if not staff_id:
        return None
    account = _row(
        conn,
        """
        SELECT id
        FROM msi_v2.accounts
        WHERE legacy_source_table = 'msi_staff' AND legacy_source_id = %s
        ORDER BY id
        LIMIT 1
        """,
        (staff_id,),
    )
    return int(account["id"]) if account else None


def _academy(conn: Any, academy_id: int) -> Any:
    row = _row(
        conn,
        """
        SELECT id, user_id, full_name, subject_id, position, phone, email,
               telegram_username, recruitment_candidate_id,
               academy_start_date::text AS academy_start_date,
               account_onboarding_status
        FROM msi_v2.academy_teachers
        WHERE id = %s
        FOR UPDATE
        """,
        (int(academy_id),),
    )
    if not row:
        raise RuntimeError(f"Teacher Academy record #{academy_id} was not found.")
    return row


def _candidate(conn: Any, candidate_id: int) -> Any:
    row = repository.lock_candidate_decision_row(conn, int(candidate_id))
    if not row:
        raise RuntimeError(f"Lifecycle profile #{candidate_id} was not found.")
    return row


def _audit(
    conn: Any,
    *,
    candidate_id: int,
    event_type: str,
    detail: dict[str, Any],
    actor_account_id: int,
    actor_staff_id: int | None,
    now: str,
) -> None:
    repository.insert_audit(
        conn,
        candidate_id=candidate_id,
        event_type=event_type,
        detail=detail,
        actor_account_id=actor_account_id,
        actor_staff_id=actor_staff_id,
        now=now,
    )


def _move_application_to_academy(
    conn: Any,
    *,
    candidate_id: int,
    actor_account_id: int,
    actor_staff_id: int | None,
    now: str,
    actions: list[str],
) -> None:
    candidate = _candidate(conn, candidate_id)
    if candidate["profile_origin"] != "application" or not candidate["is_application_received"]:
        raise RuntimeError(f"Profile #{candidate_id} is not an application-origin profile.")
    if candidate["status"] == "teacher_academy":
        return
    moved = repository.update_candidate_stage(
        conn,
        candidate_id=candidate_id,
        stage="teacher_academy",
        expected_version=int(candidate["version"]),
        actor_account_id=actor_account_id,
        now=now,
        comment="Reconciled with the existing Teacher Academy lifecycle block.",
        transition_source="academy_reconciliation",
    )
    if not moved:
        raise RuntimeError(f"Profile #{candidate_id} changed during reconciliation.")
    _audit(
        conn,
        candidate_id=candidate_id,
        event_type="candidate.stage_reconciled",
        detail={
            "from_stage": candidate["status"],
            "to_stage": "teacher_academy",
            "source": "academy_reconciliation",
            "historical_decision_created": False,
        },
        actor_account_id=actor_account_id,
        actor_staff_id=actor_staff_id,
        now=now,
    )
    actions.append(f"move application profile #{candidate_id} to Teacher Academy")


def _link_existing(
    conn: Any,
    *,
    candidate_id: int,
    academy_id: int,
    canonical_name: str,
    actor_account_id: int,
    actor_staff_id: int | None,
    now: str,
    actions: list[str],
) -> None:
    candidate = _candidate(conn, candidate_id)
    academy = _academy(conn, academy_id)
    linked_candidate_id = int(academy["recruitment_candidate_id"] or 0)
    if linked_candidate_id and linked_candidate_id != candidate_id:
        raise RuntimeError(
            f"Academy #{academy_id} is already linked to profile #{linked_candidate_id}."
        )
    candidate_subject_id = int(candidate["subject_id"] or 0)
    academy_subject_id = int(academy["subject_id"] or 0)
    if candidate_subject_id and academy_subject_id and candidate_subject_id != academy_subject_id:
        raise RuntimeError(
            f"Academy #{academy_id} and profile #{candidate_id} have different subjects."
        )
    linked_account_id = _account_for_academy(conn, academy)
    if not repository.link_academy_profile(
        conn,
        academy_teacher_id=academy_id,
        candidate_id=candidate_id,
        full_name=canonical_name,
        linked_account_id=linked_account_id,
        now=now,
    ):
        raise RuntimeError(f"Could not uniquely link Academy #{academy_id} to profile #{candidate_id}.")
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidates
        SET full_name = %s,
            phone = COALESCE(NULLIF(phone, ''), %s),
            email = COALESCE(NULLIF(email, ''), %s),
            telegram_username = COALESCE(NULLIF(telegram_username, ''), %s),
            updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (
            canonical_name,
            academy["phone"] or "",
            academy["email"] or "",
            academy["telegram_username"] or "",
            now,
            candidate_id,
        ),
    )
    if linked_candidate_id != candidate_id:
        _audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.academy_profile_linked",
            detail={
                "academy_teacher_id": academy_id,
                "profile_origin": candidate["profile_origin"],
                "academy_start_date_preserved": academy["academy_start_date"],
                "account_preserved": bool(academy["user_id"]),
            },
            actor_account_id=actor_account_id,
            actor_staff_id=actor_staff_id,
            now=now,
        )
        actions.append(f"link profile #{candidate_id} to Academy #{academy_id}")


def _direct_profile_for_existing_academy(
    conn: Any,
    *,
    academy_id: int,
    canonical_name: str,
    actor_account_id: int,
    actor_staff_id: int | None,
    now: str,
    actions: list[str],
) -> int:
    academy = _academy(conn, academy_id)
    candidate_id = int(academy["recruitment_candidate_id"] or 0)
    if candidate_id:
        candidate = _candidate(conn, candidate_id)
        if candidate["profile_origin"] != "academy_direct":
            raise RuntimeError(
                f"Academy #{academy_id} is linked to non-direct profile #{candidate_id}."
            )
    else:
        linked_account_id = _account_for_academy(conn, academy)
        candidate_id = repository.insert_academy_direct_profile(
            conn,
            full_name=canonical_name,
            subject_id=academy["subject_id"],
            applied_position=academy["position"] or "Trainee Teacher",
            phone=academy["phone"] or "",
            email=academy["email"] or "",
            telegram_username=academy["telegram_username"] or "",
            linked_account_id=linked_account_id,
            now=now,
            actor_account_id=actor_account_id,
        )
        _audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.profile_created_from_academy",
            detail={
                "academy_teacher_id": academy_id,
                "profile_origin": "academy_direct",
                "application_created": False,
            },
            actor_account_id=actor_account_id,
            actor_staff_id=actor_staff_id,
            now=now,
        )
        actions.append(f"create Academy-direct profile #{candidate_id} for Academy #{academy_id}")
    _link_existing(
        conn,
        candidate_id=candidate_id,
        academy_id=academy_id,
        canonical_name=canonical_name,
        actor_account_id=actor_account_id,
        actor_staff_id=actor_staff_id,
        now=now,
        actions=actions,
    )
    return candidate_id


def _create_new_academy_record(
    conn: Any,
    *,
    candidate_id: int,
    actor_login: str,
    actor_account_id: int,
    actor_staff_id: int | None,
    now: str,
    actions: list[str],
) -> int:
    candidate = _candidate(conn, candidate_id)
    academy_id = repository.ensure_academy_intake(
        conn,
        candidate=candidate,
        actor_login=actor_login,
        now=now,
    )
    if not academy_id:
        raise RuntimeError(f"Could not create the Academy block for profile #{candidate_id}.")
    if not candidate["academy_teacher_id"]:
        _audit(
            conn,
            candidate_id=candidate_id,
            event_type="candidate.academy_profile_linked",
            detail={
                "academy_teacher_id": academy_id,
                "profile_origin": candidate["profile_origin"],
                "account_onboarding_status": "pending",
            },
            actor_account_id=actor_account_id,
            actor_staff_id=actor_staff_id,
            now=now,
        )
        actions.append(f"create pending Academy #{academy_id} for profile #{candidate_id}")
    return academy_id


def reconcile(*, apply: bool, actor_login: str) -> list[str]:
    now = _now()
    actions: list[str] = []
    with connect_auth_db() as conn:
        actor_account_id, actor_staff_id = _actor(conn, actor_login)

        for candidate_id, academy_id, canonical_name in APPLICATION_LINKS:
            _link_existing(
                conn,
                candidate_id=candidate_id,
                academy_id=academy_id,
                canonical_name=canonical_name,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )
            _move_application_to_academy(
                conn,
                candidate_id=candidate_id,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )

        for academy_id, canonical_name in ACADEMY_DIRECT_EXISTING:
            _direct_profile_for_existing_academy(
                conn,
                academy_id=academy_id,
                canonical_name=canonical_name,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )

        for candidate_id, canonical_name in APPLICATION_INTAKES:
            candidate = _candidate(conn, candidate_id)
            if candidate["full_name"] != canonical_name:
                raise RuntimeError(
                    f"Profile #{candidate_id} is {candidate['full_name']!r}, expected {canonical_name!r}."
                )
            _create_new_academy_record(
                conn,
                candidate_id=candidate_id,
                actor_login=actor_login,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )
            _move_application_to_academy(
                conn,
                candidate_id=candidate_id,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )

        esl_reference = _candidate(conn, 146)
        for canonical_name in ACADEMY_DIRECT_NEW:
            direct = _row(
                conn,
                """
                SELECT id
                FROM msi_v2.teacher_candidates
                WHERE profile_origin = 'academy_direct'
                  AND lower(full_name) = lower(%s)
                ORDER BY id
                LIMIT 1
                FOR UPDATE
                """,
                (canonical_name,),
            )
            if direct:
                candidate_id = int(direct["id"])
            else:
                candidate_id = repository.insert_academy_direct_profile(
                    conn,
                    full_name=canonical_name,
                    subject_id=esl_reference["subject_id"],
                    applied_position="IGCSE ESL Teacher",
                    phone="",
                    email="",
                    telegram_username="",
                    linked_account_id=None,
                    now=now,
                    actor_account_id=actor_account_id,
                )
                _audit(
                    conn,
                    candidate_id=candidate_id,
                    event_type="candidate.profile_created_from_academy",
                    detail={"profile_origin": "academy_direct", "application_created": False},
                    actor_account_id=actor_account_id,
                    actor_staff_id=actor_staff_id,
                    now=now,
                )
                actions.append(f"create Academy-direct profile #{candidate_id} for {canonical_name}")
            _create_new_academy_record(
                conn,
                candidate_id=candidate_id,
                actor_login=actor_login,
                actor_account_id=actor_account_id,
                actor_staff_id=actor_staff_id,
                now=now,
                actions=actions,
            )

        if apply:
            conn.commit()
        else:
            conn.rollback()
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile named Teacher Academy records with unified lifecycle profiles."
    )
    parser.add_argument("--apply", action="store_true", help="Commit changes. Default is dry-run.")
    parser.add_argument("--actor-login", default="HR0001")
    args = parser.parse_args()
    try:
        actions = reconcile(apply=args.apply, actor_login=args.actor_login)
    except Exception as exc:
        print(f"Reconciliation failed: {exc}", file=sys.stderr)
        return 1
    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: {len(actions)} change(s)")
    for action in actions:
        print(f"- {action}")
    if not args.apply:
        print("No data was committed. Re-run with --apply after reviewing this output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
