"""PostgreSQL persistence for Recruitment hiring decisions."""

from __future__ import annotations

from typing import Any


def void_latest_closed_decision(
    conn: Any,
    *,
    candidate_id: int,
    actor_account_id: int | None,
    reason: str,
    now: str,
) -> int | None:
    row = conn.execute(
        """
        WITH latest AS (
            SELECT id
            FROM msi_v2.teacher_candidate_final_decisions
            WHERE candidate_id = %s
              AND decision IN ('rejected', 'candidate_withdrew')
              AND voided_at IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
        )
        UPDATE msi_v2.teacher_candidate_final_decisions decision
        SET voided_at = %s::timestamptz,
            voided_by_account_id = %s,
            void_reason = %s
        FROM latest
        WHERE decision.id = latest.id
        RETURNING decision.id
        """,
        (int(candidate_id), now, actor_account_id, reason),
    ).fetchone()
    return int(row["id"]) if row else None


def lock_candidate_decision_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT candidate.id, candidate.full_name, candidate.phone,
               candidate.email, candidate.telegram_username, candidate.subject_id,
               candidate.applied_position, candidate.status, candidate.version,
               candidate.profile_origin, candidate.is_application_received,
               candidate.linked_account_id,
               academy.id AS academy_teacher_id,
               teacher.id AS active_teacher_id
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN msi_v2.academy_teachers academy
          ON academy.recruitment_candidate_id = candidate.id
        LEFT JOIN msi_v2.teachers teacher
          ON teacher.recruitment_candidate_id = candidate.id
        WHERE candidate.id = %s
        LIMIT 1
        FOR UPDATE OF candidate
        """,
        (int(candidate_id),),
    ).fetchone()


def candidate_actionable_approval_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, requested_outcome, status, created_at
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE candidate_id = %s AND status IN ('requested', 'approved')
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (int(candidate_id),),
    ).fetchone()


def list_approval_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT approval.id, approval.candidate_id, approval.requested_outcome,
               approval.status, approval.request_note, approval.review_comment,
               approval.requested_by_account_id, approval.reviewed_by_account_id,
               approval.reviewed_at::text AS reviewed_at,
               approval.consumed_at::text AS consumed_at,
               approval.created_at::text AS created_at,
               approval.updated_at::text AS updated_at,
               COALESCE(requester.login, '') AS requested_by,
               COALESCE(reviewer.login, '') AS reviewed_by
        FROM msi_v2.teacher_candidate_hire_approvals approval
        LEFT JOIN msi_v2.accounts requester ON requester.id = approval.requested_by_account_id
        LEFT JOIN msi_v2.accounts reviewer ON reviewer.id = approval.reviewed_by_account_id
        WHERE approval.candidate_id = %s
        ORDER BY approval.created_at DESC, approval.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_decision_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT decision.id, decision.candidate_id, decision.decision,
               decision.rejection_reason, decision.reason_detail,
               decision.origin_stage,
               decision.is_system_generated, decision.source_evaluation_type,
               decision.source_evaluation_id,
               decision.voided_at::text AS voided_at,
               decision.follow_up_at::text AS follow_up_at,
               decision.approval_id, decision.decided_by_account_id,
               COALESCE(account.full_name, account.login, decision.decided_by_login, '') AS decided_by,
               decision.created_at::text AS created_at
        FROM msi_v2.teacher_candidate_final_decisions decision
        LEFT JOIN msi_v2.accounts account ON account.id = decision.decided_by_account_id
        WHERE decision.candidate_id = %s
        ORDER BY decision.created_at DESC, decision.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def insert_approval_request(
    conn: Any,
    *,
    candidate_id: int,
    outcome: str,
    note: str,
    actor_account_id: int | None,
    now: str,
) -> int:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'revoked', updated_at = %s::timestamptz
        WHERE candidate_id = %s AND requested_outcome = %s
          AND status IN ('requested', 'approved')
        """,
        (now, candidate_id, outcome),
    )
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_hire_approvals (
            candidate_id, requested_outcome, status, request_note,
            requested_by_account_id, created_at, updated_at
        ) VALUES (%s, %s, 'requested', %s, %s, %s::timestamptz, %s::timestamptz)
        RETURNING id
        """,
        (candidate_id, outcome, note, actor_account_id, now, now),
    ).fetchone()
    return int(row["id"]) if row else 0


def get_approval_row(
    conn: Any, *, candidate_id: int, approval_id: int, for_update: bool = False
) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, requested_outcome, status,
               requested_by_account_id, reviewed_by_account_id
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE id = %s AND candidate_id = %s
        LIMIT 1 {lock}
        """,
        (approval_id, candidate_id),
    ).fetchone()


def get_approval_by_id(conn: Any, *, approval_id: int, for_update: bool = False) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, requested_outcome, status,
               requested_by_account_id, reviewed_by_account_id
        FROM msi_v2.teacher_candidate_hire_approvals
        WHERE id = %s
        LIMIT 1 {lock}
        """,
        (int(approval_id),),
    ).fetchone()


def review_approval(
    conn: Any,
    *,
    candidate_id: int,
    approval_id: int,
    status: str,
    comment: str,
    actor_account_id: int | None,
    now: str,
) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = %s, review_comment = %s, reviewed_by_account_id = %s,
            reviewed_at = %s::timestamptz, updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s AND status = 'requested'
        """,
        (status, comment, actor_account_id, now, now, approval_id, candidate_id),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def final_decision_for_approval(
    conn: Any, *, candidate_id: int, approval_id: int
) -> Any:
    return conn.execute(
        """
        SELECT id, decision
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s AND approval_id = %s AND voided_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(candidate_id), int(approval_id)),
    ).fetchone()


def revoke_open_approvals(
    conn: Any,
    *,
    candidate_id: int,
    comment: str,
    actor_account_id: int | None,
    now: str,
) -> list[int]:
    rows = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'revoked',
            review_comment = %s,
            reviewed_by_account_id = %s,
            reviewed_at = %s::timestamptz,
            updated_at = %s::timestamptz
        WHERE candidate_id = %s AND status IN ('requested', 'approved')
        RETURNING id
        """,
        (comment, actor_account_id, now, now, int(candidate_id)),
    ).fetchall()
    return [int(row["id"]) for row in rows]


def consume_approval(conn: Any, *, approval_id: int, now: str) -> None:
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_hire_approvals
        SET status = 'consumed', consumed_at = %s::timestamptz, updated_at = %s::timestamptz
        WHERE id = %s
        """,
        (now, now, approval_id),
    )


def insert_final_decision(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    actor_login: str,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_final_decisions (
            candidate_id, decision, rejection_reason, reason_detail,
            origin_stage, follow_up_at, approval_id, decided_by_account_id,
            decided_by_login, created_at, is_system_generated,
            source_evaluation_type, source_evaluation_id
        ) VALUES (
            %s, %s, %s, %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s::timestamptz, %s, %s, %s
        )
        RETURNING id
        """,
        (
            candidate_id,
            values["decision"],
            values.get("rejection_reason", ""),
            values.get("reason_detail", ""),
            values.get("origin_stage", ""),
            values.get("follow_up_at", ""),
            values.get("approval_id"),
            actor_account_id,
            actor_login,
            now,
            bool(values.get("is_system_generated")),
            values.get("source_evaluation_type", ""),
            values.get("source_evaluation_id"),
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


__all__ = [
    "candidate_actionable_approval_row",
    "consume_approval",
    "final_decision_for_approval",
    "get_approval_by_id",
    "get_approval_row",
    "insert_approval_request",
    "insert_final_decision",
    "list_approval_rows",
    "list_decision_rows",
    "lock_candidate_decision_row",
    "review_approval",
    "revoke_open_approvals",
    "void_latest_closed_decision",
]
