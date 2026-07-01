"""Parent invite helpers shared by web and bot."""

import os
import secrets
from datetime import datetime, timedelta

from itsdangerous import BadSignature, URLSafeTimedSerializer

from shared.db import queries
from shared.identity.common import connect, utc_now_iso

PARENT_INVITE_SALT = "msi-parent-invite-v1"
PARENT_INVITE_MAX_AGE_SECONDS = 60 * 60 * 24 * 14


def _serializer():
    secret = os.environ.get("APP_SECRET_KEY", os.environ.get("FLASK_SECRET_KEY", "")).strip()
    if not secret:
        raise RuntimeError("APP_SECRET_KEY is required to use parent invite links.")
    return URLSafeTimedSerializer(secret_key=secret, salt=PARENT_INVITE_SALT)


def _ensure(conn):
    queries.ensure_account_invites_schema(conn)


def _expires_at(days=14):
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_parent_invite_token(payload):
    return _serializer().dumps(payload)


def load_parent_invite_payload(token):
    try:
        payload = _serializer().loads(
            str(token or ""),
            max_age=PARENT_INVITE_MAX_AGE_SECONDS,
        )
    except BadSignature:
        return None
    return payload if isinstance(payload, dict) else None


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
                    INSERT INTO msi_v2.account_invites (
                        invite_type,
                        token_hash,
                        token,
                        student_id,
                        issued_by_staff_id,
                        created_at,
                        expires_at
                    )
                    VALUES ('parent', %s, %s, %s, %s, %s::timestamptz, %s::timestamptz)
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
            FROM msi_v2.account_invites
            WHERE invite_type = 'parent'
              AND token_hash = %s
              AND status = 'pending'
            LIMIT 1
            """,
            (code,),
        ).fetchone()
    return str(row["token"] or "").strip() if row else ""


def load_parent_invite_code_payload(code):
    token = get_parent_invite_token(code)
    if not token:
        return None
    return load_parent_invite_payload(token)


__all__ = [
    "PARENT_INVITE_MAX_AGE_SECONDS",
    "PARENT_INVITE_SALT",
    "create_parent_invite_code",
    "create_parent_invite_token",
    "get_parent_invite_token",
    "load_parent_invite_code_payload",
    "load_parent_invite_payload",
]
