import re
import threading
from datetime import datetime

try:
    from ..storage import queries
except ImportError:
    from app.storage import queries

try:
    from .r2_storage_service import (
        build_resource_file_url,
        delete_resource_file,
        infer_resource_mime_type,
        is_r2_configured,
    )
except ImportError:
    from app.services.r2_storage_service import (
        build_resource_file_url,
        delete_resource_file,
        infer_resource_mime_type,
        is_r2_configured,
    )

_DB_LOCK = threading.Lock()

_SUBJECT_ALIASES = {
    "igcse mathematics a": ("math", "Math"),
    "mathematics": ("math", "Math"),
    "math": ("math", "Math"),
    "general english": ("english", "English"),
    "english": ("english", "English"),
    "chemistry": ("chemistry", "Chemistry"),
    "biology": ("biology", "Biology"),
    "physics": ("physics", "Physics"),
}


def _connect():
    return queries.connect_auth_db()


def _utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


def _slugify(value):
    text = _normalize(value)
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def _canonical_subject(subject_name):
    raw_text = str(subject_name or "").strip()
    normalized = _normalize(raw_text)
    if not normalized:
        return "", ""

    alias_value = _SUBJECT_ALIASES.get(normalized)
    if alias_value:
        return alias_value

    subject_key = _slugify(normalized)
    if not subject_key:
        return "", ""
    subject_label = " ".join(part.capitalize() for part in normalized.split())
    return subject_key, subject_label


def _ensure_storage(conn):
    queries.create_tables(conn)
    queries.ensure_resources_schema(conn)
    queries.ensure_default_resource_types(conn, _utc_now_iso())


def _to_resource_type(row):
    return {
        "id": int(row["id"]),
        "name": str(row["name"]).strip(),
        "slug": str(row["slug"]).strip(),
        "is_active": bool(row["is_active"]),
        "is_system": bool(row["is_system"]),
        "display_order": int(row["display_order"] or 0),
        "created_at": str(row["created_at"] or "").strip(),
        "updated_at": str(row["updated_at"] or "").strip(),
    }


def _row_field(row, key, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def _to_resource(row):
    resource_file_path = str(_row_field(row, "resource_file_path", "") or "").strip()
    resource_file_mime = infer_resource_mime_type(resource_file_path)
    resource_file_kind = "file"
    if resource_file_mime.startswith("video/"):
        resource_file_kind = "video"
    elif resource_file_mime.startswith("audio/"):
        resource_file_kind = "audio"
    elif resource_file_mime == "application/pdf":
        resource_file_kind = "pdf"
    return {
        "id": int(_row_field(row, "id", 0) or 0),
        "subject_name": str(_row_field(row, "subject_name", "") or "").strip(),
        "subject_key": str(_row_field(row, "subject_key", "") or "").strip(),
        "resource_type_id": int(_row_field(row, "resource_type_id", 0) or 0),
        "resource_type_name": str(_row_field(row, "resource_type_name", "") or "").strip(),
        "resource_type_slug": str(_row_field(row, "resource_type_slug", "") or "").strip(),
        "resource_type_display_order": int(
            _row_field(row, "resource_type_display_order", 0) or 0
        ),
        "title": str(_row_field(row, "title", "") or "").strip(),
        "description": str(_row_field(row, "description", "") or "").strip(),
        "resource_url": str(_row_field(row, "resource_url", "") or "").strip(),
        "resource_file_path": resource_file_path,
        "resource_file_mime": resource_file_mime,
        "resource_file_kind": resource_file_kind,
        "resource_file_url": build_resource_file_url(resource_file_path),
        "is_active": bool(_row_field(row, "is_active", 0)),
        "created_by_admin_id": (
            int(_row_field(row, "created_by_admin_id"))
            if _row_field(row, "created_by_admin_id") is not None
            else None
        ),
        "created_at": str(_row_field(row, "created_at", "") or "").strip(),
        "updated_at": str(_row_field(row, "updated_at", "") or "").strip(),
    }


def normalize_subject_name(subject_name):
    _subject_key, subject_label = _canonical_subject(subject_name)
    return subject_label


def is_resource_upload_enabled():
    return bool(is_r2_configured())


def list_resource_types(include_inactive=False):
    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_resource_type_rows(
            conn,
            include_inactive=bool(include_inactive),
        )
    return [_to_resource_type(row) for row in rows]


def create_resource_type(name):
    normalized_name = str(name or "").strip()
    if not normalized_name:
        return False, "Resource type name is required."
    if len(normalized_name) > 80:
        return False, "Resource type name is too long."

    slug_base = _slugify(normalized_name)
    if not slug_base:
        return False, "Resource type name is invalid."

    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            existing_by_name = queries.get_resource_type_by_name_row(conn, normalized_name)
            if existing_by_name:
                if bool(existing_by_name["is_active"]):
                    return False, "Resource type already exists."

                queries.update_resource_type_active(
                    conn,
                    int(existing_by_name["id"]),
                    True,
                    now,
                )
                conn.commit()
                return True, ""

            slug = slug_base
            suffix = 2
            while queries.get_resource_type_by_slug_row(conn, slug):
                slug = f"{slug_base}-{suffix}"
                suffix += 1

            display_order = queries.get_next_resource_type_display_order(conn)
            queries.insert_resource_type_row(
                conn,
                name=normalized_name,
                slug=slug,
                is_system=False,
                display_order=display_order,
                created_at=now,
                updated_at=now,
            )
            conn.commit()
    return True, ""


def set_resource_type_active(resource_type_id, is_active):
    try:
        type_id = int(resource_type_id)
    except (TypeError, ValueError):
        return False, "Invalid resource type."
    if type_id <= 0:
        return False, "Invalid resource type."

    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            existing = queries.get_resource_type_by_id_row(conn, type_id)
            if not existing:
                return False, "Resource type was not found."

            queries.update_resource_type_active(
                conn,
                type_id,
                bool(is_active),
                now,
            )
            conn.commit()
    return True, ""


def delete_resource_type(resource_type_id):
    try:
        type_id = int(resource_type_id)
    except (TypeError, ValueError):
        return False, "Invalid resource type."
    if type_id <= 0:
        return False, "Invalid resource type."

    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            existing = queries.get_resource_type_by_id_row(conn, type_id)
            if not existing:
                return False, "Resource type was not found."
            if bool(existing["is_system"]):
                return False, "Default resource types cannot be deleted."

            usage_count = queries.count_resources_by_type(conn, type_id)
            if usage_count > 0:
                return (
                    False,
                    "Delete resources that use this type first.",
                )

            queries.delete_resource_type_row_by_id(conn, type_id)
            conn.commit()
    return True, ""


def list_resource_subject_names():
    with _connect() as conn:
        _ensure_storage(conn)
        raw_names = queries.list_resource_subject_names(conn)

    deduped = {}
    for subject_name in raw_names:
        subject_key, subject_label = _canonical_subject(subject_name)
        if subject_key and subject_label and subject_key not in deduped:
            deduped[subject_key] = subject_label

    return [
        deduped[key]
        for key in sorted(deduped, key=lambda value: value.casefold())
    ]


def create_resource(
    *,
    subject_name,
    resource_type_id,
    title,
    description="",
    resource_url="",
    resource_file_path="",
    created_by_admin_id=None,
):
    subject_key, subject_label = _canonical_subject(subject_name)
    if not subject_key or not subject_label:
        return False, "Subject is required."

    normalized_title = str(title or "").strip()
    if not normalized_title:
        return False, "Resource title is required."
    if len(normalized_title) > 180:
        return False, "Resource title is too long."

    normalized_description = str(description or "").strip()
    if len(normalized_description) > 2000:
        return False, "Description is too long."

    normalized_url = str(resource_url or "").strip()
    normalized_file_path = str(resource_file_path or "").strip()
    if not normalized_url and not normalized_file_path:
        return False, "Provide either a resource link or an uploaded file."

    try:
        type_id = int(resource_type_id)
    except (TypeError, ValueError):
        return False, "Please select a valid resource type."
    if type_id <= 0:
        return False, "Please select a valid resource type."

    admin_id = None
    if created_by_admin_id is not None:
        try:
            parsed_admin_id = int(created_by_admin_id)
        except (TypeError, ValueError):
            parsed_admin_id = 0
        if parsed_admin_id > 0:
            admin_id = parsed_admin_id

    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            resource_type = queries.get_resource_type_by_id_row(conn, type_id)
            if not resource_type:
                return False, "Resource type was not found."
            if not bool(resource_type["is_active"]):
                return False, "Selected resource type is inactive."

            queries.insert_resource_row(
                conn,
                subject_name=subject_label,
                subject_key=subject_key,
                resource_type_id=type_id,
                title=normalized_title,
                description=normalized_description,
                resource_url=normalized_url,
                resource_file_path=normalized_file_path,
                created_by_admin_id=admin_id,
                created_at=now,
                updated_at=now,
            )
            conn.commit()
    return True, ""


def set_resource_active(resource_id, is_active):
    try:
        parsed_resource_id = int(resource_id)
    except (TypeError, ValueError):
        return False, "Invalid resource."
    if parsed_resource_id <= 0:
        return False, "Invalid resource."

    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            existing = queries.get_resource_row_by_id(conn, parsed_resource_id)
            if not existing:
                return False, "Resource was not found."

            queries.update_resource_active(
                conn,
                parsed_resource_id,
                bool(is_active),
                now,
            )
            conn.commit()
    return True, ""


def delete_resource(resource_id):
    try:
        parsed_resource_id = int(resource_id)
    except (TypeError, ValueError):
        return False, "Invalid resource."
    if parsed_resource_id <= 0:
        return False, "Invalid resource."

    resource_file_path = ""
    with _DB_LOCK:
        with _connect() as conn:
            _ensure_storage(conn)
            existing = queries.get_resource_row_by_id(conn, parsed_resource_id)
            if not existing:
                return False, "Resource was not found."

            resource_file_path = str(existing["resource_file_path"] or "").strip()
            queries.delete_resource_row_by_id(conn, parsed_resource_id)
            conn.commit()

    if resource_file_path:
        delete_resource_file(resource_file_path)
    return True, ""


def list_resources(*, include_inactive=False, subject_name=""):
    subject_key, _subject_label = _canonical_subject(subject_name)
    with _connect() as conn:
        _ensure_storage(conn)
        rows = queries.list_resource_rows(
            conn,
            include_inactive=bool(include_inactive),
            subject_key=subject_key,
        )

    return [_to_resource(row) for row in rows]


def list_resources_grouped_by_type(subject_name):
    resources = list_resources(
        include_inactive=False,
        subject_name=subject_name,
    )
    grouped = []
    by_type = {}
    for row in resources:
        type_key = int(row["resource_type_id"])
        bucket = by_type.get(type_key)
        if bucket is None:
            bucket = {
                "resource_type_id": type_key,
                "resource_type_name": row["resource_type_name"],
                "resource_type_slug": row["resource_type_slug"],
                "resource_type_display_order": int(
                    row.get("resource_type_display_order", 0)
                ),
                "resources": [],
            }
            by_type[type_key] = bucket
            grouped.append(bucket)
        bucket["resources"].append(row)

    grouped.sort(
        key=lambda row: (
            int(row.get("resource_type_display_order", 0)),
            str(row.get("resource_type_name", "")).casefold(),
        )
    )
    for bucket in grouped:
        bucket["resources"].sort(
            key=lambda row: (
                str(row.get("title", "")).casefold(),
                int(row.get("id", 0)),
            )
        )
    return grouped


__all__ = [
    "normalize_subject_name",
    "is_resource_upload_enabled",
    "list_resource_types",
    "create_resource_type",
    "set_resource_type_active",
    "delete_resource_type",
    "list_resource_subject_names",
    "create_resource",
    "set_resource_active",
    "delete_resource",
    "list_resources",
    "list_resources_grouped_by_type",
]
