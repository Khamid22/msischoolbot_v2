"""Read-only PostgreSQL projection for Customer Support billing accounts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from backend.core.unit_of_work import Connection


def list_billing_account_rows(
    conn: Connection,
    *,
    school_ids: Iterable[int],
    all_schools: bool,
    query: str,
    school_id: int | None,
    account_type: str,
    account_id: int | None,
    schedule_status: str,
    attention: str,
    access: str,
) -> list[Any]:
    search = f"%{query.strip()}%"
    return conn.execute(
        """
        WITH student_accounts AS (
            SELECT
                'student'::text AS account_type,
                student.id AS account_id,
                student.id AS student_id,
                NULL::bigint AS admission_id,
                student.full_name AS student_name,
                student.student_code,
                COALESCE(parent.display_name, '') AS parent_name,
                student.school_id,
                school.school_name,
                student.status AS lifecycle_status,
                COALESCE(profile.status, 'missing') AS schedule_status,
                profile.billing_day,
                profile.starts_on AS effective_date,
                COALESCE(profile.currency, 'UZS') AS currency,
                CASE
                    WHEN profile.pricing_mode = 'total'
                    THEN COALESCE(profile.total_amount_minor, 0)
                    ELSE COALESCE(
                        prices.monthly_amount_minor,
                        legacy_items.monthly_amount_minor,
                        0
                    )
                END::bigint AS monthly_amount_minor,
                COALESCE(enrollments.subject_count, 0)::integer AS billable_item_count,
                profile.version AS schedule_version,
                COALESCE(profile.pricing_mode, 'per_subject') AS pricing_mode,
                profile.total_amount_minor,
                latest.id AS latest_invoice_id,
                latest.invoice_number AS latest_invoice_number,
                latest.billing_period AS latest_billing_period,
                latest.status AS latest_invoice_status,
                latest.due_date AS latest_invoice_due_date,
                COALESCE(invoice_totals.open_count, 0)::integer AS open_invoice_count,
                COALESCE(invoice_totals.overdue_count, 0)::integer AS overdue_invoice_count,
                COALESCE(invoice_totals.balances, '[]'::jsonb) AS outstanding_balances,
                enforcement.state AS enforcement_state,
                EXISTS (
                    SELECT 1
                    FROM msi_v2.billing_access_holds hold
                    JOIN msi_v2.invoice_enforcement_schedules hold_schedule
                      ON hold_schedule.id = hold.schedule_id
                    WHERE hold_schedule.student_id = student.id
                      AND hold.status = 'active'
                ) AS is_payment_only,
                (
                    profile.id IS NOT NULL
                    AND profile.status = 'active'
                    AND profile.starts_on <= CURRENT_DATE
                    AND (profile.ends_on IS NULL OR profile.ends_on >= CURRENT_DATE)
                    AND CURRENT_DATE >= make_date(
                        EXTRACT(YEAR FROM CURRENT_DATE)::integer,
                        EXTRACT(MONTH FROM CURRENT_DATE)::integer,
                        profile.billing_day
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM msi_v2.invoices due_invoice
                        WHERE due_invoice.student_id = student.id
                          AND due_invoice.invoice_kind = 'monthly'
                          AND due_invoice.billing_period = date_trunc('month', CURRENT_DATE)::date
                          AND due_invoice.status <> 'voided'
                    )
                ) AS is_due_without_invoice,
                (
                    COALESCE(invoice_totals.open_count, 0) > 0
                    AND enforcement.id IS NULL
                ) AS is_enforcement_missing
                ,
                (
                    profile.status = 'active'
                    AND profile.pricing_mode = 'per_subject'
                    AND EXISTS (
                        SELECT 1
                        FROM msi_v2.group_students missing_enrollment
                        JOIN msi_v2.groups missing_group
                          ON missing_group.id = missing_enrollment.group_id
                        JOIN msi_v2.subject_programs missing_program
                          ON missing_program.id = missing_group.program_id
                        WHERE missing_enrollment.student_id = student.id
                          AND missing_enrollment.enrollment_status = 'active'
                          AND missing_group.status = 'active'
                          AND NOT EXISTS (
                              SELECT 1
                              FROM msi_v2.student_billing_subject_prices price
                              WHERE price.profile_id = profile.id
                                AND price.subject_id = missing_program.subject_id
                                AND price.status = 'active'
                                AND price.active_from <= CURRENT_DATE
                                AND (
                                    price.active_until IS NULL
                                    OR price.active_until >= CURRENT_DATE
                                )
                          )
                          AND NOT EXISTS (
                              SELECT 1
                              FROM msi_v2.student_billing_items legacy_item
                              WHERE legacy_item.profile_id = profile.id
                                AND legacy_item.subject_id = missing_program.subject_id
                                AND legacy_item.status = 'active'
                                AND legacy_item.active_from <= CURRENT_DATE
                                AND (
                                    legacy_item.active_until IS NULL
                                    OR legacy_item.active_until >= CURRENT_DATE
                                )
                          )
                    )
                ) AS is_pricing_required
            FROM msi_v2.students student
            JOIN msi_v2.schools school ON school.id = student.school_id
            LEFT JOIN msi_v2.student_billing_profiles profile
              ON profile.student_id = student.id
            LEFT JOIN LATERAL (
                SELECT sum(price.amount_minor)::bigint AS monthly_amount_minor
                FROM msi_v2.student_billing_subject_prices price
                WHERE price.profile_id = profile.id
                  AND price.status = 'active'
                  AND price.active_from <= CURRENT_DATE
                  AND (price.active_until IS NULL OR price.active_until >= CURRENT_DATE)
            ) prices ON true
            LEFT JOIN LATERAL (
                SELECT sum(item.amount_minor)::bigint AS monthly_amount_minor
                FROM msi_v2.student_billing_items item
                WHERE item.profile_id = profile.id
                  AND item.status = 'active'
                  AND item.active_from <= CURRENT_DATE
                  AND (item.active_until IS NULL OR item.active_until >= CURRENT_DATE)
            ) legacy_items ON true
            LEFT JOIN LATERAL (
                SELECT count(DISTINCT program.subject_id)::integer AS subject_count
                FROM msi_v2.group_students enrollment
                JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
                JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
                WHERE enrollment.student_id = student.id
                  AND enrollment.enrollment_status = 'active'
                  AND group_row.status = 'active'
            ) enrollments ON true
            LEFT JOIN LATERAL (
                SELECT invoice.id, invoice.invoice_number, invoice.billing_period,
                       invoice.status, invoice.due_date
                FROM msi_v2.invoices invoice
                WHERE invoice.student_id = student.id
                ORDER BY invoice.billing_period DESC, invoice.id DESC
                LIMIT 1
            ) latest ON true
            LEFT JOIN LATERAL (
                SELECT
                    (
                        SELECT count(*)::integer
                        FROM msi_v2.invoices invoice
                        WHERE invoice.student_id = student.id
                          AND invoice.status IN ('issued', 'partially_paid', 'overdue')
                    ) AS open_count,
                    (
                        SELECT count(*)::integer
                        FROM msi_v2.invoices invoice
                        WHERE invoice.student_id = student.id
                          AND (
                              invoice.status = 'overdue'
                              OR (
                                  invoice.status IN ('issued', 'partially_paid')
                                  AND invoice.due_date < CURRENT_DATE
                              )
                          )
                    ) AS overdue_count,
                    COALESCE(
                        (
                            SELECT jsonb_agg(
                                jsonb_build_object(
                                    'currency', balance.currency,
                                    'balance_minor', balance.balance_minor
                                )
                                ORDER BY balance.currency
                            )
                            FROM (
                                SELECT invoice.currency,
                                       sum(
                                           invoice.total_minor - invoice.paid_minor
                                       )::bigint AS balance_minor
                                FROM msi_v2.invoices invoice
                                WHERE invoice.student_id = student.id
                                  AND invoice.status IN (
                                      'issued', 'partially_paid', 'overdue'
                                  )
                                GROUP BY invoice.currency
                                HAVING sum(
                                    invoice.total_minor - invoice.paid_minor
                                ) > 0
                            ) balance
                        ),
                        '[]'::jsonb
                    ) AS balances
            ) invoice_totals ON true
            LEFT JOIN LATERAL (
                SELECT schedule.id, schedule.state
                FROM msi_v2.invoice_enforcement_schedules schedule
                JOIN msi_v2.invoices invoice ON invoice.id = schedule.invoice_id
                WHERE invoice.student_id = student.id
                  AND invoice.status IN ('issued', 'partially_paid', 'overdue')
                ORDER BY
                    CASE schedule.state
                        WHEN 'held' THEN 0 WHEN 'countdown' THEN 1 ELSE 2
                    END,
                    schedule.deadline_at,
                    schedule.id
                LIMIT 1
            ) enforcement ON true
            LEFT JOIN LATERAL (
                SELECT linked_parent.display_name
                FROM msi_v2.parent_student_links link
                JOIN msi_v2.parents linked_parent ON linked_parent.id = link.parent_id
                WHERE link.student_id = student.id AND link.status = 'active'
                ORDER BY
                    CASE WHEN linked_parent.id = profile.billing_parent_id THEN 0 ELSE 1 END,
                    linked_parent.id
                LIMIT 1
            ) parent ON true
            WHERE student.status = 'active'
               OR EXISTS (
                    SELECT 1 FROM msi_v2.invoices open_invoice
                    WHERE open_invoice.student_id = student.id
                      AND open_invoice.status IN ('issued', 'partially_paid', 'overdue')
               )
               OR EXISTS (
                    SELECT 1
                    FROM msi_v2.billing_access_holds active_hold
                    JOIN msi_v2.invoice_enforcement_schedules active_schedule
                      ON active_schedule.id = active_hold.schedule_id
                    WHERE active_schedule.student_id = student.id
                      AND active_hold.status = 'active'
               )
        ),
        admission_accounts AS (
            SELECT
                'admission'::text AS account_type,
                admission.id AS account_id,
                NULL::bigint AS student_id,
                admission.id AS admission_id,
                admission.student_full_name AS student_name,
                ''::text AS student_code,
                admission.parent_full_name AS parent_name,
                admission.school_id,
                school.school_name,
                admission.status AS lifecycle_status,
                CASE
                    WHEN admission.status IN ('cancelled', 'expired') THEN 'ended'
                    ELSE 'active'
                END AS schedule_status,
                admission.billing_day,
                COALESCE(admission.service_start_date, admission.first_due_date)
                    AS effective_date,
                admission.currency,
                COALESCE(items.monthly_amount_minor, 0)::bigint AS monthly_amount_minor,
                COALESCE(items.item_count, 0)::integer AS billable_item_count,
                admission.version AS schedule_version,
                'per_subject'::text AS pricing_mode,
                NULL::bigint AS total_amount_minor,
                latest.id AS latest_invoice_id,
                latest.invoice_number AS latest_invoice_number,
                latest.billing_period AS latest_billing_period,
                latest.status AS latest_invoice_status,
                latest.due_date AS latest_invoice_due_date,
                COALESCE(invoice_totals.open_count, 0)::integer AS open_invoice_count,
                COALESCE(invoice_totals.overdue_count, 0)::integer AS overdue_invoice_count,
                COALESCE(invoice_totals.balances, '[]'::jsonb) AS outstanding_balances,
                NULL::text AS enforcement_state,
                false AS is_payment_only,
                false AS is_due_without_invoice,
                false AS is_enforcement_missing
                ,
                false AS is_pricing_required
            FROM msi_v2.admissions admission
            JOIN msi_v2.schools school ON school.id = admission.school_id
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(sum(selection.monthly_amount_minor), 0)::bigint
                        AS monthly_amount_minor,
                    count(*)::integer AS item_count
                FROM msi_v2.admission_group_selections selection
                WHERE selection.admission_id = admission.id
            ) items ON true
            LEFT JOIN LATERAL (
                SELECT invoice.id, invoice.invoice_number, invoice.billing_period,
                       invoice.status, invoice.due_date
                FROM msi_v2.invoices invoice
                WHERE invoice.admission_id = admission.id
                ORDER BY invoice.billing_period DESC, invoice.id DESC
                LIMIT 1
            ) latest ON true
            LEFT JOIN LATERAL (
                SELECT
                    (
                        SELECT count(*)::integer
                        FROM msi_v2.invoices invoice
                        WHERE invoice.admission_id = admission.id
                          AND invoice.status IN ('issued', 'partially_paid', 'overdue')
                    ) AS open_count,
                    (
                        SELECT count(*)::integer
                        FROM msi_v2.invoices invoice
                        WHERE invoice.admission_id = admission.id
                          AND invoice.status IN ('issued', 'partially_paid', 'overdue')
                          AND (
                              invoice.status = 'overdue'
                              OR invoice.due_date < CURRENT_DATE
                          )
                    ) AS overdue_count,
                    COALESCE(
                        (
                            SELECT jsonb_agg(
                                jsonb_build_object(
                                    'currency', balance.currency,
                                    'balance_minor', balance.balance_minor
                                )
                                ORDER BY balance.currency
                            )
                            FROM (
                                SELECT invoice.currency,
                                       sum(
                                           invoice.total_minor - invoice.paid_minor
                                       )::bigint AS balance_minor
                                FROM msi_v2.invoices invoice
                                WHERE invoice.admission_id = admission.id
                                  AND invoice.status IN (
                                      'issued', 'partially_paid', 'overdue'
                                  )
                                GROUP BY invoice.currency
                                HAVING sum(
                                    invoice.total_minor - invoice.paid_minor
                                ) > 0
                            ) balance
                        ),
                        '[]'::jsonb
                    ) AS balances
            ) invoice_totals ON true
            WHERE admission.activated_student_id IS NULL
              AND (
                  admission.status NOT IN ('active', 'cancelled', 'expired')
                  OR EXISTS (
                      SELECT 1
                      FROM msi_v2.invoices open_invoice
                      WHERE open_invoice.admission_id = admission.id
                        AND open_invoice.status IN (
                            'issued', 'partially_paid', 'overdue'
                        )
                  )
              )
        ),
        accounts AS (
            SELECT * FROM student_accounts
            UNION ALL
            SELECT * FROM admission_accounts
        )
        SELECT account.*,
               CASE
                   WHEN account.is_payment_only THEN 0
                   WHEN account.overdue_invoice_count > 0 THEN 1
                   WHEN account.is_pricing_required THEN 2
                   WHEN account.is_due_without_invoice THEN 3
                   WHEN account.schedule_status = 'missing' THEN 4
                   WHEN account.is_enforcement_missing THEN 5
                   ELSE 6
               END AS attention_rank
        FROM accounts account
        WHERE (%s OR account.school_id = ANY(%s::bigint[]))
          AND (%s::bigint IS NULL OR account.school_id = %s)
          AND (%s = 'all' OR account.account_type = %s)
          AND (%s::bigint IS NULL OR account.account_id = %s)
          AND (%s = 'all' OR account.schedule_status = %s)
          AND (
              %s = 'all'
              OR (%s = 'payment_only' AND account.is_payment_only)
              OR (%s = 'overdue' AND account.overdue_invoice_count > 0)
              OR (%s = 'due_without_invoice' AND account.is_due_without_invoice)
              OR (%s = 'missing_schedule' AND account.schedule_status = 'missing')
              OR (%s = 'enforcement_missing' AND account.is_enforcement_missing)
              OR (%s = 'pricing_required' AND account.is_pricing_required)
          )
          AND (
              %s = 'all'
              OR (%s = 'normal' AND NOT account.is_payment_only
                    AND account.enforcement_state IS DISTINCT FROM 'countdown')
              OR (%s = 'countdown' AND account.enforcement_state = 'countdown')
              OR (%s = 'payment_only' AND account.is_payment_only)
          )
          AND (
              %s = ''
              OR account.student_name ILIKE %s
              OR account.parent_name ILIKE %s
              OR account.student_code ILIKE %s
              OR account.school_name ILIKE %s
          )
        ORDER BY attention_rank, lower(account.student_name),
                 account.account_type, account.account_id
        """,
        (
            bool(all_schools),
            list(school_ids),
            school_id,
            school_id,
            account_type,
            account_type,
            account_id,
            account_id,
            schedule_status,
            schedule_status,
            attention,
            attention,
            attention,
            attention,
            attention,
            attention,
            attention,
            access,
            access,
            access,
            access,
            query.strip(),
            search,
            search,
            search,
            search,
        ),
    ).fetchall()


def list_student_schedule_item_rows(conn: Connection, student_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT item.group_id, group_row.group_name, item.subject_id,
               subject.subject_name, item.description, item.amount_minor
        FROM msi_v2.student_billing_profiles profile
        JOIN msi_v2.student_billing_items item ON item.profile_id = profile.id
        JOIN msi_v2.groups group_row ON group_row.id = item.group_id
        JOIN msi_v2.subjects subject ON subject.id = item.subject_id
        WHERE profile.student_id = %s
          AND item.status = 'active'
          AND item.active_from <= CURRENT_DATE
          AND (item.active_until IS NULL OR item.active_until >= CURRENT_DATE)
        ORDER BY subject.subject_name, group_row.group_name, item.id
        """,
        (int(student_id),),
    ).fetchall()


def list_student_subject_price_rows(conn: Connection, student_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT price.*, subject.subject_name
        FROM msi_v2.student_billing_profiles profile
        JOIN msi_v2.student_billing_subject_prices price
          ON price.profile_id = profile.id
        JOIN msi_v2.subjects subject ON subject.id = price.subject_id
        WHERE profile.student_id = %s
          AND price.status = 'active'
          AND price.active_until IS NULL
        ORDER BY subject.subject_name, subject.id
        """,
        (int(student_id),),
    ).fetchall()


def list_admission_schedule_item_rows(conn: Connection, admission_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT selection.group_id, group_row.group_name, selection.subject_id,
               subject.subject_name, subject.subject_name AS description,
               selection.monthly_amount_minor AS amount_minor
        FROM msi_v2.admission_group_selections selection
        JOIN msi_v2.groups group_row ON group_row.id = selection.group_id
        JOIN msi_v2.subjects subject ON subject.id = selection.subject_id
        WHERE selection.admission_id = %s
        ORDER BY subject.subject_name, group_row.group_name
        """,
        (int(admission_id),),
    ).fetchall()


def list_student_enrollment_option_rows(conn: Connection, student_id: int) -> list[Any]:
    return conn.execute(
        """
        SELECT enrollment.group_id, group_row.group_name, subject.id AS subject_id,
               subject.subject_name
        FROM msi_v2.group_students enrollment
        JOIN msi_v2.groups group_row ON group_row.id = enrollment.group_id
        JOIN msi_v2.subject_programs program ON program.id = group_row.program_id
        JOIN msi_v2.subjects subject ON subject.id = program.subject_id
        WHERE enrollment.student_id = %s
          AND enrollment.enrollment_status = 'active'
          AND group_row.status = 'active'
        ORDER BY subject.subject_name, group_row.group_name, group_row.id
        """,
        (int(student_id),),
    ).fetchall()


def list_account_invoice_rows(
    conn: Connection,
    *,
    account_type: str,
    account_id: int,
) -> list[Any]:
    owner_column = "student_id" if account_type == "student" else "admission_id"
    return conn.execute(
        f"""
        SELECT invoice.*,
               enforcement.state AS enforcement_state,
               enforcement.countdown_started_at,
               enforcement.deadline_at AS payment_deadline_at,
               student.legacy_student_row_id,
               COALESCE(student.full_name, admission.student_full_name, '') AS student_name,
               COALESCE(student.student_code, '') AS student_code,
               COALESCE(parent.display_name, admission.parent_full_name, '') AS parent_name,
               COALESCE(student.school_id, admission.school_id) AS school_id,
               school.school_name
        FROM msi_v2.invoices invoice
        LEFT JOIN msi_v2.admissions admission ON admission.id = invoice.admission_id
        LEFT JOIN msi_v2.students student ON student.id = invoice.student_id
        LEFT JOIN msi_v2.parents parent ON parent.id = invoice.parent_id
        LEFT JOIN msi_v2.invoice_enforcement_schedules enforcement
          ON enforcement.invoice_id = invoice.id
        JOIN msi_v2.schools school
          ON school.id = COALESCE(student.school_id, admission.school_id)
        WHERE invoice.{owner_column} = %s
        ORDER BY invoice.billing_period DESC, invoice.id DESC
        LIMIT 100
        """,
        (int(account_id),),
    ).fetchall()
