"""PostgreSQL persistence for Recruitment tasks."""

from __future__ import annotations

from typing import Any, Iterable


def list_task_rows(
    conn: Any,
    *,
    candidate_id: int | None = None,
    visible_account_id: int | None = None,
    visible_subject_ids: set[int] | None = None,
    include_decision_queue: bool = False,
) -> list[Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if candidate_id:
        clauses.append("task.candidate_id = %s")
        params.append(candidate_id)
    else:
        clauses.append("candidate.status <> 'trash_bin'")
    if visible_account_id:
        if visible_subject_ids is not None and not visible_subject_ids:
            clauses.append("FALSE")
        else:
            subject_clause = ""
            if visible_subject_ids is not None:
                subject_clause = "AND visibility.subject_id = ANY(%s::bigint[])"
            queue_clause = ""
            if include_decision_queue:
                queue_clause = """
                    OR EXISTS (
                        SELECT 1
                        FROM msi_v2.teacher_candidate_hire_approvals queue_approval
                        WHERE queue_approval.candidate_id = task.candidate_id
                          AND queue_approval.status IN ('requested', 'approved')
                    )
                """
            clauses.append(
                f"""(EXISTS (
                    SELECT 1 FROM msi_v2.teacher_candidate_assignments visibility
                    WHERE visibility.candidate_id = task.candidate_id
                      AND visibility.assignee_account_id = %s
                      AND visibility.status = 'active'
                      {subject_clause}
                ){queue_clause})"""
            )
            params.append(visible_account_id)
            if visible_subject_ids is not None:
                params.append(sorted(visible_subject_ids))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return conn.execute(
        f"""
        SELECT task.id, task.candidate_id, task.title, task.due_at::text AS due_at,
               task.responsible_account_id, task.status, task.note,
               task.task_key, task.task_origin, task.stage_history_id,
               task.completed_at::text AS completed_at,
               task.cancelled_at::text AS cancelled_at,
               task.created_at::text AS created_at,
               task.updated_at::text AS updated_at,
               candidate.full_name AS candidate_name,
               COALESCE(account.login, account.full_name, '') AS responsible_name
        FROM msi_v2.teacher_candidate_tasks task
        JOIN msi_v2.teacher_candidates candidate ON candidate.id = task.candidate_id
        LEFT JOIN msi_v2.accounts account ON account.id = task.responsible_account_id
        {where_sql}
        ORDER BY
            CASE task.status WHEN 'pending' THEN 0 WHEN 'completed' THEN 1 ELSE 2 END,
            task.due_at ASC NULLS LAST, task.id DESC
        """,
        tuple(params) if params else None,
    ).fetchall()


def insert_task(
    conn: Any,
    *,
    candidate_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> int:
    status = values.get("status", "pending")
    row = conn.execute(
        """
        INSERT INTO msi_v2.teacher_candidate_tasks (
            candidate_id, title, due_at, responsible_account_id, status, note,
            completed_at, cancelled_at, created_by_account_id,
            updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s, %s, %s,
            CASE WHEN %s = 'completed' THEN %s::timestamptz END,
            CASE WHEN %s = 'cancelled' THEN %s::timestamptz END,
            %s, %s, %s::timestamptz, %s::timestamptz
        ) RETURNING id
        """,
        (
            candidate_id,
            values["title"],
            values.get("due_at", ""),
            values.get("responsible_account_id"),
            status,
            values.get("note", ""),
            status,
            now,
            status,
            now,
            actor_account_id,
            actor_account_id,
            now,
            now,
        ),
    ).fetchone()
    return int(row["id"]) if row else 0


def update_task(
    conn: Any,
    *,
    candidate_id: int,
    task_id: int,
    values: dict[str, Any],
    actor_account_id: int | None,
    now: str,
) -> bool:
    status = values.get("status", "pending")
    cursor = conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_tasks
        SET title = %s, due_at = NULLIF(%s, '')::timestamptz,
            responsible_account_id = %s, status = %s, note = %s,
            completed_at = CASE WHEN %s = 'completed' THEN COALESCE(completed_at, %s::timestamptz) ELSE NULL END,
            cancelled_at = CASE WHEN %s = 'cancelled' THEN COALESCE(cancelled_at, %s::timestamptz) ELSE NULL END,
            updated_by_account_id = %s, updated_at = %s::timestamptz
        WHERE id = %s AND candidate_id = %s
        """,
        (
            values["title"],
            values.get("due_at", ""),
            values.get("responsible_account_id"),
            status,
            values.get("note", ""),
            status,
            now,
            status,
            now,
            actor_account_id,
            now,
            task_id,
            candidate_id,
        ),
    )
    return int(getattr(cursor, "rowcount", 0) or 0) > 0


def candidate_automation_state_row(conn: Any, candidate_id: int) -> Any:
    return conn.execute(
        """
        SELECT candidate.id, candidate.status, candidate.updated_by_account_id,
               history.id AS stage_history_id,
               history.sla_due_at::text AS sla_due_at,
               history.responsible_account_id AS stage_responsible_account_id,
               interview.result AS interview_result,
               subject_test.result AS subject_test_result,
               demo.result AS demo_result,
               interview_appointment.id AS interview_appointment_id,
               interview_appointment.ends_at::text AS interview_appointment_ends_at,
               demo_appointment.id AS demo_appointment_id,
               demo_appointment.ends_at::text AS demo_appointment_ends_at,
               COALESCE(documents.required_count, 0) AS required_document_count,
               approval.id AS actionable_approval_id
        FROM msi_v2.teacher_candidates candidate
        LEFT JOIN LATERAL (
            SELECT item.id, item.sla_due_at, item.responsible_account_id
            FROM msi_v2.teacher_candidate_stage_history item
            WHERE item.candidate_id = candidate.id AND item.exited_at IS NULL
            ORDER BY item.entered_at DESC, item.id DESC
            LIMIT 1
        ) history ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_interviews item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) interview ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_subject_tests item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) subject_test ON true
        LEFT JOIN LATERAL (
            SELECT item.result
            FROM msi_v2.teacher_candidate_demo_lessons item
            WHERE item.candidate_id = candidate.id AND item.voided_at IS NULL
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) demo ON true
        LEFT JOIN LATERAL (
            SELECT item.id, item.ends_at
            FROM msi_v2.teacher_candidate_appointments item
            WHERE item.candidate_id = candidate.id
              AND item.appointment_type = 'job_interview'
              AND item.status = 'scheduled'
            ORDER BY item.starts_at, item.id
            LIMIT 1
        ) interview_appointment ON true
        LEFT JOIN LATERAL (
            SELECT item.id, item.ends_at
            FROM msi_v2.teacher_candidate_appointments item
            WHERE item.candidate_id = candidate.id
              AND item.appointment_type = 'demo_lesson'
              AND item.status = 'scheduled'
            ORDER BY item.starts_at, item.id
            LIMIT 1
        ) demo_appointment ON true
        LEFT JOIN LATERAL (
            SELECT count(DISTINCT item.document_type) AS required_count
            FROM msi_v2.teacher_candidate_documents item
            WHERE item.candidate_id = candidate.id
              AND item.removed_at IS NULL
              AND item.document_type IN ('cv', 'id_passport', 'diploma')
        ) documents ON true
        LEFT JOIN LATERAL (
            SELECT item.id
            FROM msi_v2.teacher_candidate_hire_approvals item
            WHERE item.candidate_id = candidate.id
              AND item.status IN ('requested', 'approved')
            ORDER BY item.created_at DESC, item.id DESC
            LIMIT 1
        ) approval ON true
        WHERE candidate.id = %s
        LIMIT 1
        """,
        (int(candidate_id),),
    ).fetchone()


def replace_system_tasks(
    conn: Any,
    *,
    candidate_id: int,
    stage: str,
    stage_history_id: int,
    desired_tasks: list[dict[str, Any]],
    actor_account_id: int | None,
    now: str,
) -> None:
    desired_keys = [str(item["task_key"]) for item in desired_tasks]
    terminal = stage in {
        "teacher_academy",
        "active_teacher",
        "rejected",
        "candidate_withdrew",
        "trash_bin",
    }
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_tasks
        SET status = CASE WHEN %s THEN 'cancelled' ELSE 'completed' END,
            completed_at = CASE WHEN %s THEN NULL ELSE %s::timestamptz END,
            cancelled_at = CASE WHEN %s THEN %s::timestamptz ELSE NULL END,
            updated_by_account_id = %s,
            updated_at = %s::timestamptz
        WHERE candidate_id = %s
          AND task_origin = 'system'
          AND status = 'pending'
          AND NOT (task_key = ANY(%s::text[]) AND stage_history_id = %s)
        """,
        (
            terminal,
            terminal,
            now,
            terminal,
            now,
            actor_account_id,
            now,
            int(candidate_id),
            desired_keys,
            int(stage_history_id),
        ),
    )
    if not desired_tasks:
        return
    conn.executemany(
        """
        INSERT INTO msi_v2.teacher_candidate_tasks (
            candidate_id, title, due_at, responsible_account_id,
            status, note, task_key, task_origin, stage_history_id,
            created_by_account_id, updated_by_account_id, created_at, updated_at
        ) VALUES (
            %s, %s, NULLIF(%s, '')::timestamptz, %s,
            'pending', '', %s, 'system', %s,
            %s, %s, %s::timestamptz, %s::timestamptz
        )
        ON CONFLICT (candidate_id, task_key, stage_history_id)
            WHERE task_origin = 'system' AND status = 'pending'
        DO UPDATE SET
            title = excluded.title,
            due_at = excluded.due_at,
            responsible_account_id = excluded.responsible_account_id,
            updated_by_account_id = excluded.updated_by_account_id,
            updated_at = excluded.updated_at
        """,
        [
            (
                int(candidate_id),
                item["title"],
                item.get("due_at", ""),
                item.get("responsible_account_id"),
                item["task_key"],
                int(stage_history_id),
                actor_account_id,
                actor_account_id,
                now,
                now,
            )
            for item in desired_tasks
        ],
    )


def replace_assignments(
    conn: Any,
    *,
    candidate_id: int,
    assignee_account_ids: Iterable[int],
    subject_id: int | None,
    actor_account_id: int | None,
    now: str,
) -> None:
    wanted = {int(value) for value in assignee_account_ids if int(value) > 0}
    conn.execute(
        """
        UPDATE msi_v2.teacher_candidate_assignments
        SET status = 'removed', updated_at = %s::timestamptz
        WHERE candidate_id = %s AND assignment_type = 'academic_evaluator'
          AND status = 'active' AND NOT (assignee_account_id = ANY(%s::bigint[]))
        """,
        (now, candidate_id, list(wanted) or [0]),
    )
    for assignee_id in sorted(wanted):
        conn.execute(
            """
            INSERT INTO msi_v2.teacher_candidate_assignments (
                candidate_id, assignee_account_id, assignment_type, subject_id,
                status, assigned_by_account_id, created_at, updated_at
            ) VALUES (%s, %s, 'academic_evaluator', %s, 'active', %s, %s::timestamptz, %s::timestamptz)
            ON CONFLICT (candidate_id, assignee_account_id, assignment_type)
                WHERE status = 'active'
            DO UPDATE SET subject_id = excluded.subject_id,
                          assigned_by_account_id = excluded.assigned_by_account_id,
                          updated_at = excluded.updated_at
            """,
            (candidate_id, assignee_id, subject_id, actor_account_id, now, now),
        )


__all__ = [
    "candidate_automation_state_row",
    "insert_task",
    "list_task_rows",
    "replace_assignments",
    "replace_system_tasks",
    "update_task",
]
