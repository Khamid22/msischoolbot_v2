import math
from datetime import date, datetime

from database.academics import canonical
from database import queries


VALID_PAYMENT_STATUSES = {"paid", "due", "debt", "upcoming"}


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_status(value):
    normalized = str(value or "").strip().casefold()
    aliases = {
        "overdue": "debt",
        "late": "debt",
        "unpaid": "due",
        "pending": "due",
        "scheduled": "upcoming",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in VALID_PAYMENT_STATUSES else "due"


def _safe_float(value, default=0.0):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _normalize_amount(value):
    return max(0.0, _safe_float(value))


def _date_sort_value(value):
    # Unparseable dates sort last. Canonical date parsing lives in database.academics.canonical.
    return canonical.parse_date(value) or date.max


def _payment_record_from_row(row):
    record = {
        "id": int(row["id"]),
        "student_row_id": int(row["student_row_id"]),
        "subject": str(row["subject"] or "").strip(),
        "month": str(row["month_label"] or "").strip(),
        "amount": _normalize_amount(row["amount"]),
        "currency": str(row["currency"] or "UZS").strip() or "UZS",
        "status": _normalize_status(row["status"]),
        "due_date": str(row["due_date"] or "").strip(),
        "paid_at": str(row["paid_at"] or "").strip(),
        "notes": str(row["notes"] or "").strip(),
        "created_by_admin_id": (
            int(row["created_by_admin_id"])
            if row["created_by_admin_id"] is not None
            else None
        ),
        "created_at": str(row["created_at"] or "").strip(),
        "updated_at": str(row["updated_at"] or "").strip(),
    }
    # `state` is the live, time-derived bucket the parent/admin views render.
    # It is recomputed on every read, so an unpaid charge rolls from
    # upcoming -> due -> debt on its own without anyone re-editing the row.
    record["paid"] = _is_paid(record)
    record["state"] = _BUCKET_TO_STATE.get(_payment_bucket(record), "due")
    return record


def payment_row_to_record(row):
    return _payment_record_from_row(row)


_BUCKET_TO_STATE = {
    "monthly_history": "paid",
    "debts": "debt",
    "due_payments": "due",
    "upcoming_payments": "upcoming",
}


def _is_paid(record):
    """A charge is settled once it carries a paid timestamp.

    `status == 'paid'` is honored too for records created/marked paid without
    an explicit date, but `paid_at` is the canonical signal.
    """
    if str(record.get("paid_at") or "").strip():
        return True
    return _normalize_status(record.get("status")) == "paid"


def _payment_bucket(record):
    # Paid charges are history; everything unpaid is bucketed purely by how its
    # due date compares to today. The stored status is intentionally NOT used to
    # freeze a charge as debt/upcoming, so buckets never go stale.
    if _is_paid(record):
        return "monthly_history"

    due_date = canonical.parse_date(record.get("due_date"))
    today = date.today()
    if due_date is None:
        return "due_payments"
    if due_date < today:
        return "debts"
    if due_date > today:
        return "upcoming_payments"
    return "due_payments"


def summarize_payment_records(records, progress=None):
    progress = progress if isinstance(progress, dict) else {}
    currency = "UZS"
    buckets = {
        "monthly_history": [],
        "debts": [],
        "due_payments": [],
        "upcoming_payments": [],
    }

    for record in records:
        if str(record.get("currency") or "").strip():
            currency = str(record.get("currency")).strip()
        bucket = _payment_bucket(record)
        buckets[bucket].append(record)

    buckets["monthly_history"].sort(
        key=lambda row: (_date_sort_value(row.get("paid_at") or row.get("due_date")), int(row.get("id") or 0)),
        reverse=True,
    )
    for key in ("debts", "due_payments", "upcoming_payments"):
        buckets[key].sort(
            key=lambda row: (_date_sort_value(row.get("due_date")), int(row.get("id") or 0))
        )

    paid_total = sum(_normalize_amount(row.get("amount")) for row in buckets["monthly_history"])
    debt_total = sum(_normalize_amount(row.get("amount")) for row in buckets["debts"])
    due_total = sum(_normalize_amount(row.get("amount")) for row in buckets["due_payments"])
    upcoming_total = sum(_normalize_amount(row.get("amount")) for row in buckets["upcoming_payments"])

    return {
        "currency": currency,
        "monthly_history": buckets["monthly_history"],
        "debts": buckets["debts"],
        "due_payments": buckets["due_payments"],
        "upcoming_payments": buckets["upcoming_payments"],
        "paid_total": paid_total,
        "debt_total": debt_total,
        "due_total": due_total,
        "upcoming_total": upcoming_total,
        "program_completion_rate": int(progress.get("program_completion_rate") or 0),
        "program_completed_lessons": int(progress.get("program_completed_lessons") or 0),
        "program_total_lessons": int(progress.get("program_total_lessons") or 0),
    }


def list_student_payments(student_row_id):
    with _connect() as conn:
        queries.ensure_payments_schema(conn)
        rows = queries.list_student_payment_rows(conn, int(student_row_id))
    return [_payment_record_from_row(row) for row in rows]


def payment_summary_for_student(student_row_id, progress=None):
    return summarize_payment_records(list_student_payments(student_row_id), progress=progress)


def create_student_payment(student_row_id, payload, created_by_admin_id=0):
    student_id = int(student_row_id or 0)
    if student_id <= 0:
        raise ValueError("Student is required.")

    amount = _normalize_amount(payload.get("amount"))
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    subject = str(payload.get("subject") or "").strip()
    if not subject:
        raise ValueError("Subject is required.")

    month_label = str(payload.get("month") or payload.get("month_label") or "").strip()
    status = _normalize_status(payload.get("status"))
    due_date = str(payload.get("due_date") or "").strip()
    paid_at = str(payload.get("paid_at") or "").strip()
    currency = str(payload.get("currency") or "UZS").strip().upper() or "UZS"
    notes = str(payload.get("notes") or "").strip()
    now = _utc_now_iso()

    with _connect() as conn:
        queries.ensure_students_schema(conn)
        queries.ensure_payments_schema(conn)
        student_row = queries.get_student_admin_row(conn, student_id)
        if not student_row:
            raise ValueError("Student was not found.")
        row = queries.insert_student_payment_row(
            conn,
            student_row_id=student_id,
            subject=subject,
            month_label=month_label,
            amount=amount,
            currency=currency,
            status=status,
            due_date=due_date,
            paid_at=paid_at,
            notes=notes,
            created_by_admin_id=int(created_by_admin_id or 0),
            created_at=now,
            updated_at=now,
        )
        conn.commit()
        rows = queries.list_student_payment_rows(conn, student_id)

    return {
        "payment": _payment_record_from_row(row),
        "payments": [_payment_record_from_row(payment_row) for payment_row in rows],
    }


def set_student_payment_paid(payment_id, paid=True, paid_at=None):
    """Mark a charge paid (stamping paid_at) or revert it to unpaid.

    Reverting clears paid_at so the live bucket logic resumes deriving
    due/debt/upcoming from the due date.
    """
    payment_id = int(payment_id or 0)
    if payment_id <= 0:
        raise ValueError("Payment record is required.")

    if paid:
        stamp = str(paid_at or "").strip() or date.today().strftime("%Y-%m-%d")
        new_status = "paid"
    else:
        stamp = ""
        new_status = "due"
    now = _utc_now_iso()

    with _connect() as conn:
        queries.ensure_payments_schema(conn)
        row = queries.get_student_payment_row(conn, payment_id)
        if not row:
            return None
        student_id = int(row["student_row_id"])
        queries.update_student_payment_paid_row(
            conn,
            payment_id,
            paid_at=stamp,
            status=new_status,
            updated_at=now,
        )
        conn.commit()
        rows = queries.list_student_payment_rows(conn, student_id)

    return {
        "student_row_id": student_id,
        "payments": [_payment_record_from_row(payment_row) for payment_row in rows],
    }


def delete_student_payment(payment_id):
    payment_id = int(payment_id or 0)
    if payment_id <= 0:
        raise ValueError("Payment record is required.")

    with _connect() as conn:
        queries.ensure_payments_schema(conn)
        row = queries.get_student_payment_row(conn, payment_id)
        if not row:
            return None
        student_id = int(row["student_row_id"])
        removed = queries.delete_student_payment_row(conn, payment_id)
        conn.commit()
        rows = queries.list_student_payment_rows(conn, student_id) if removed else []

    return {
        "student_row_id": student_id,
        "payments": [_payment_record_from_row(payment_row) for payment_row in rows],
    }


__all__ = [
    "create_student_payment",
    "delete_student_payment",
    "set_student_payment_paid",
    "list_student_payments",
    "payment_summary_for_student",
    "payment_row_to_record",
    "summarize_payment_records",
]
