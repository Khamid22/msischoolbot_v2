"""Parent invite code helpers shared by web and bot."""

import secrets
from datetime import datetime, timedelta

from shared.db import queries
from shared.identity.common import connect, utc_now_iso


def _ensure(conn):
    queries.ensure_parent_invites_schema(conn)


def _expires_at(days=14):
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_parent_invite_code(token, student_row_id, issued_by=0, *, expires_days=14):
    token = str(token or "").strip()
    student_row_id = int(student_row_id or 0)
    issued_by = int(issued_by or 0) or None
    if not token or student_row_id <= 0:
        raise ValueError("token and student_row_id are required")

    with connect() as conn:
        _ensure(conn)
        for _ in range(5):
            code = secrets.token_urlsafe(9).rstrip("=")
            try:
                conn.execute(
                    """
                    INSERT INTO parent_invites (
                        code, token, student_row_id, issued_by, created_at, expires_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        code,
                        token,
                        student_row_id,
                        issued_by,
                        utc_now_iso(),
                        _expires_at(expires_days),
                    ),
                )
                return code
            except Exception:
                conn.rollback()
        raise RuntimeError("Could not generate a unique parent invite code")


def get_parent_invite_token(code):
    code = str(code or "").strip()
    if not code:
        return ""
    with connect() as conn:
        _ensure(conn)
        row = conn.execute(
            """
            SELECT token
            FROM parent_invites
            WHERE code = %s
            LIMIT 1
            """,
            (code,),
        ).fetchone()
    return str(row["token"] or "").strip() if row else ""


__all__ = ["create_parent_invite_code", "get_parent_invite_token"]
