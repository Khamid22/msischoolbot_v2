"""PostgreSQL persistence for Recruitment evaluations."""

from __future__ import annotations

from typing import Any, Iterable


def list_interview_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT interview.*, interview.interview_at::text AS interview_at_text,
               interview.created_at::text AS created_at_text,
               interview.updated_at::text AS updated_at_text,
               COALESCE(interviewer.login, '') AS interviewer_login
        FROM msi_v2.teacher_candidate_interviews interview
        LEFT JOIN msi_v2.accounts interviewer ON interviewer.id = interview.interviewer_account_id
        WHERE interview.candidate_id = %s
        ORDER BY interview.created_at DESC, interview.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_subject_test_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT test.*, test.test_at::text AS test_at_text,
               test.created_at::text AS created_at_text,
               test.updated_at::text AS updated_at_text,
               CASE
                   WHEN test.score IS NOT NULL AND test.maximum_score > 0
                   THEN round((test.score / test.maximum_score) * 100, 1)
                   ELSE NULL
               END AS percentage,
               COALESCE(subject.subject_name, test.subject_label, '') AS subject,
               COALESCE(evaluator.login, '') AS evaluator_login,
               COALESCE(topics.items, '[]'::jsonb) AS topic_scores
        FROM msi_v2.teacher_candidate_subject_tests test
        LEFT JOIN msi_v2.subjects subject ON subject.id = test.subject_id
        LEFT JOIN msi_v2.accounts evaluator ON evaluator.id = test.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id', topic.id,
                    'topic', topic.topic,
                    'score', topic.score,
                    'maximum_score', topic.maximum_score,
                    'percentage', round((topic.score / topic.maximum_score) * 100, 1)
                ) ORDER BY topic.id
            ) AS items
            FROM msi_v2.teacher_candidate_subject_test_topics topic
            WHERE topic.subject_test_id = test.id
        ) topics ON true
        WHERE test.candidate_id = %s
        ORDER BY test.created_at DESC, test.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def list_demo_rows(conn: Any, candidate_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT demo.*, demo.demo_at::text AS demo_at_text,
               demo.created_at::text AS created_at_text,
               demo.updated_at::text AS updated_at_text,
               COALESCE(subject.subject_name, demo.subject_label, '') AS subject,
               COALESCE(evaluator.login, '') AS evaluator_login,
               COALESCE(criteria.items, '[]'::jsonb) AS criteria_scores
        FROM msi_v2.teacher_candidate_demo_lessons demo
        LEFT JOIN msi_v2.subjects subject ON subject.id = demo.subject_id
        LEFT JOIN msi_v2.accounts evaluator ON evaluator.id = demo.evaluator_account_id
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id', criterion.id,
                    'criterion', criterion.criterion,
                    'score', criterion.score,
                    'maximum_score', criterion.maximum_score
                ) ORDER BY criterion.id
            ) AS items
            FROM msi_v2.teacher_candidate_demo_criteria criterion
            WHERE criterion.demo_lesson_id = demo.id
        ) criteria ON true
        WHERE demo.candidate_id = %s
        ORDER BY demo.created_at DESC, demo.id DESC
        """,
        (candidate_id,),
    ).fetchall()


def void_evaluation(
    conn: Any,
    *,
    table: str,
    candidate_id: int,
    attempt_id: int,
    actor_account_id: int | None,
    reason: str,
    now: str,
) -> Any:
    allowed_tables = {
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
    }
    if table not in allowed_tables:
        return None
    return conn.execute(
        f"""
        UPDATE msi_v2.{table}
        SET voided_at = %s::timestamptz,
            voided_by_account_id = %s,
            void_reason = %s,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s AND voided_at IS NULL
        RETURNING id
        """,
        (
            now,
            actor_account_id,
            reason,
            actor_account_id,
            now,
            attempt_id,
            candidate_id,
        ),
    ).fetchone()


def get_evaluation_row(
    conn: Any,
    *,
    table: str,
    candidate_id: int,
    attempt_id: int,
    for_update: bool = False,
) -> Any:
    allowed_tables = {
        "teacher_candidate_interviews",
        "teacher_candidate_subject_tests",
        "teacher_candidate_demo_lessons",
    }
    if table not in allowed_tables:
        return None
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, result, voided_at
        FROM msi_v2.{table}
        WHERE id = %s AND candidate_id = %s
        LIMIT 1 {lock}
        """,
        (int(attempt_id), int(candidate_id)),
    ).fetchone()


def get_system_decision_for_evaluation(
    conn: Any,
    *,
    candidate_id: int,
    evaluation_type: str,
    attempt_id: int,
    for_update: bool = False,
) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, candidate_id, decision, origin_stage, created_at, voided_at
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s
          AND is_system_generated = true
          AND source_evaluation_type = %s
          AND source_evaluation_id = %s
          AND voided_at IS NULL
        LIMIT 1 {lock}
        """,
        (int(candidate_id), evaluation_type, int(attempt_id)),
    ).fetchone()


def latest_active_final_decision(
    conn: Any, candidate_id: int, *, for_update: bool = False
) -> Any:
    lock = "FOR UPDATE" if for_update else ""
    return conn.execute(
        f"""
        SELECT id, decision, created_at
        FROM msi_v2.teacher_candidate_final_decisions
        WHERE candidate_id = %s AND voided_at IS NULL
        ORDER BY created_at DESC, id DESC
        LIMIT 1 {lock}
        """,
        (int(candidate_id),),
    ).fetchone()


def void_system_final_decision(
    conn: Any,
    *,
    decision_id: int,
    actor_account_id: int | None,
    reason: str,
    now: str,
) -> bool:
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_final_decisions
        SET voided_at = %s::timestamptz, voided_by_account_id = %s,
            void_reason = %s
        WHERE id = %s AND is_system_generated = true AND voided_at IS NULL
        """,
        (now, actor_account_id, reason, int(decision_id)),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def responsible_account_row(conn: Any, account_id: int) -> Any:
    return conn.execute(
        """
        SELECT id, role, status, COALESCE(NULLIF(full_name, ''), login) AS name
        FROM msi_v2.accounts WHERE id = %s LIMIT 1
        """,
        (int(account_id),),
    ).fetchone()


def hod_account_has_subject_scope(
    conn: Any, *, account_id: int, subject_id: int
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM msi_v2.staff_subject_scopes
        WHERE account_id = %s AND subject_id = %s
          AND scope_type = 'head_of_department' AND status = 'active'
        LIMIT 1
        """,
        (int(account_id), int(subject_id)),
    ).fetchone()
    return bool(row)


def ensure_candidate_assignment(
    conn: Any,
    *,
    candidate_id: int,
    assignee_account_id: int,
    subject_id: int | None,
    actor_account_id: int | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_assignments (
            candidate_id, assignee_account_id, assignment_type, subject_id,
            status, assigned_by_account_id, created_at, updated_at
        ) VALUES (%s, %s, 'academic_evaluator', %s, 'active', %s, %s::timestamptz, %s::timestamptz)
        ON CONFLICT (candidate_id, assignee_account_id, assignment_type)
            WHERE status = 'active'
        DO UPDATE SET subject_id = COALESCE(excluded.subject_id, teacher_candidate_assignments.subject_id),
                      assigned_by_account_id = excluded.assigned_by_account_id,
                      updated_at = excluded.updated_at
        """,
        (
            int(candidate_id),
            int(assignee_account_id),
            subject_id,
            actor_account_id,
            now,
            now,
        ),
    )


def insert_interview(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_interviews (
            candidate_id, appointment_id, interview_at, interviewer_account_id, interview_format,
            notes, english_level, strengths, concerns, hr_recommendation, result,
            cefr_level, overall_score, communication_score, recommendation_code,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id,
            values.get("appointment_id"),
            values.get("interview_at", ""),
            values.get("interviewer_account_id"),
            values.get("interview_format", ""),
            values.get("notes", ""),
            values.get("english_level", ""),
            values.get("strengths", ""),
            values.get("concerns", ""),
            values.get("hr_recommendation", ""),
            values["result"],
            values.get("cefr_level", ""),
            values.get("overall_score"),
            values.get("communication_score"),
            values.get("recommendation_code", ""),
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def insert_subject_test(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_subject_tests (
            candidate_id, test_at, subject_id, subject_label, evaluator_account_id,
            score, maximum_score, paper, notes, result, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id,
            values.get("test_at", ""),
            values.get("subject_id"),
            values.get("subject_label", ""),
            values.get("evaluator_account_id"),
            values.get("score"),
            values.get("maximum_score"),
            values.get("paper", ""),
            values.get("notes", ""),
            values["result"],
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()
    attempt_id = int(row["id"]) if row else 0
    topic_scores = list(values.get("topic_scores") or [])
    if attempt_id and topic_scores:
        conn.executemany(
            """
            INSERT INTO msi_v2.teacher_candidate_subject_test_topics (
                subject_test_id, topic, score, maximum_score
            ) VALUES (%s, %s, %s, %s)
            """,
            [
                (
                    attempt_id,
                    item.get("topic", ""),
                    item.get("score"),
                    item.get("maximum_score"),
                )
                for item in topic_scores
            ],
        )
    return attempt_id


def insert_demo(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_demo_lessons (
            candidate_id, appointment_id, demo_at, subject_id, subject_label, topic,
            evaluator_account_id, overview, strengths, areas_for_improvement,
            score, result, recommendation, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id,
            values.get("appointment_id"),
            values.get("demo_at", ""),
            values.get("subject_id"),
            values.get("subject_label", ""),
            values.get("topic", ""),
            values.get("evaluator_account_id"),
            values.get("overview", ""),
            values.get("strengths", ""),
            values.get("areas_for_improvement", ""),
            values.get("score"),
            values["result"],
            values.get("recommendation", ""),
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()
    attempt_id = int(row["id"]) if row else 0
    criteria_scores = list(values.get("criteria_scores") or [])
    if attempt_id and criteria_scores:
        conn.executemany(
            """
            INSERT INTO msi_v2.teacher_candidate_demo_criteria (
                demo_lesson_id, criterion, score, maximum_score
            ) VALUES (%s, %s, %s, %s)
            """,
            [
                (
                    attempt_id,
                    item.get("criterion", ""),
                    item.get("score"),
                    item.get("maximum_score", 10),
                )
                for item in criteria_scores
            ],
        )
    return attempt_id


def list_valid_evaluator_accounts(conn: Any, account_ids: Iterable[int]) -> set[int]:
    values = sorted({int(value) for value in account_ids if int(value) > 0})
    if not values:
        return set()
    rows = conn.execute(
        """
        SELECT id FROM msi_v2.accounts
        WHERE id = ANY(%s::bigint[]) AND role IN ('academic_director', 'head_of_department')
          AND status = 'active'
        """,
        (values,),
    ).fetchall()
    return {int(row["id"]) for row in rows}


__all__ = [
    "ensure_candidate_assignment",
    "get_evaluation_row",
    "get_system_decision_for_evaluation",
    "hod_account_has_subject_scope",
    "insert_demo",
    "insert_interview",
    "insert_subject_test",
    "latest_active_final_decision",
    "list_demo_rows",
    "list_interview_rows",
    "list_subject_test_rows",
    "list_valid_evaluator_accounts",
    "responsible_account_row",
    "void_evaluation",
    "void_system_final_decision",
]
