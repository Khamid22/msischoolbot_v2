import re
import threading
from datetime import datetime, timezone

from backend.modules.organization import canonical
from backend.core.database import connect_auth_db
from backend.modules.academics.resources import repository

from backend.platform.storage.r2 import (
    build_resource_file_url,
    delete_resource_file,
    infer_resource_mime_type,
    is_r2_configured,
    upload_resource_file,
    upload_thumbnail_file,
)

_DB_LOCK = threading.Lock()

def _connect():
    return connect_auth_db()


def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize(value):
    return canonical.normalize_text(value)


def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", _normalize(value)).strip("-")


def _canonical_subject(subject_name):
    subject_label = canonical.canonical_subject_name(subject_name)
    if not subject_label:
        return "", ""
    return canonical.subject_key(subject_label), subject_label


def _canonical_folder_path(folder_path):
    raw_value = str(folder_path or "").strip()
    if not raw_value:
        return ""

    segments = []
    for part in re.split(r"[\\/]+", raw_value):
        cleaned = " ".join(str(part or "").strip().split())
        if cleaned:
            segments.append(cleaned)

    if not segments:
        return ""
    return "/".join(segments)


def _resource_sort_key(row):
    return (
        str(row.get("title", "")).casefold(),
        int(row.get("id", 0)),
    )


def _resource_old_to_new_sort_key(row):
    created_at = str(row.get("created_at", "") or "").strip()
    # Keep rows without timestamp at the end; stable fallback by id.
    normalized_created_at = created_at or "9999-12-31T23:59:59Z"
    return (
        normalized_created_at,
        int(row.get("id", 0)),
    )


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
    folder_path = _canonical_folder_path(_row_field(row, "folder_path", "") or "")
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
        "folder_path": folder_path,
        "title": str(_row_field(row, "title", "") or "").strip(),
        "description": str(_row_field(row, "description", "") or "").strip(),
        "resource_url": str(_row_field(row, "resource_url", "") or "").strip(),
        "resource_file_path": resource_file_path,
        "resource_file_mime": resource_file_mime,
        "resource_file_kind": resource_file_kind,
        "resource_file_url": build_resource_file_url(resource_file_path),
        "thumbnail_file_path": str(_row_field(row, "thumbnail_file_path", "") or "").strip(),
        "thumbnail_url": build_resource_file_url(str(_row_field(row, "thumbnail_file_path", "") or "").strip()),
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
        rows = repository.list_resource_type_rows(
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
            existing_by_name = repository.get_resource_type_by_name_row(conn, normalized_name)
            if existing_by_name:
                if bool(existing_by_name["is_active"]):
                    return False, "Resource type already exists."

                repository.update_resource_type_active(
                    conn,
                    int(existing_by_name["id"]),
                    True,
                    now,
                )
                conn.commit()
                return True, ""

            slug = slug_base
            suffix = 2
            while repository.get_resource_type_by_slug_row(conn, slug):
                slug = f"{slug_base}-{suffix}"
                suffix += 1

            display_order = repository.get_next_resource_type_display_order(conn)
            repository.insert_resource_type_row(
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
            existing = repository.get_resource_type_by_id_row(conn, type_id)
            if not existing:
                return False, "Resource type was not found."

            repository.update_resource_type_active(
                conn,
                type_id,
                bool(is_active),
                now,
            )
            conn.commit()
    return True, ""


def rename_resource_type(resource_type_id, name):
    try:
        type_id = int(resource_type_id)
    except (TypeError, ValueError):
        return False, "Invalid resource type."
    if type_id <= 0:
        return False, "Invalid resource type."

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
            existing = repository.get_resource_type_by_id_row(conn, type_id)
            if not existing:
                return False, "Resource type was not found."

            existing_by_name = repository.get_resource_type_by_name_row(conn, normalized_name)
            if existing_by_name and int(existing_by_name["id"]) != type_id:
                return False, "Resource type already exists."

            slug = str(existing["slug"] or "").strip()
            if not slug or not bool(existing["is_system"]):
                slug = slug_base
                suffix = 2
                slug_conflict = repository.get_resource_type_by_slug_row(conn, slug)
                while slug_conflict and int(slug_conflict["id"]) != type_id:
                    slug = f"{slug_base}-{suffix}"
                    suffix += 1
                    slug_conflict = repository.get_resource_type_by_slug_row(conn, slug)

            repository.update_resource_type_row(
                conn,
                type_id,
                normalized_name,
                slug,
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
            existing = repository.get_resource_type_by_id_row(conn, type_id)
            if not existing:
                return False, "Resource type was not found."

            repository.update_resource_type_active(
                conn,
                type_id,
                False,
                _utc_now_iso(),
            )
            conn.commit()
    return True, ""


def list_resource_subject_names():
    with _connect() as conn:
        raw_names = repository.list_resource_subject_names(conn)

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
    folder_path="",
    description="",
    resource_url="",
    resource_file_path="",
    thumbnail_file_path="",
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

    normalized_folder_path = _canonical_folder_path(folder_path)
    if len(normalized_folder_path) > 240:
        return False, "Folder path is too long."

    normalized_url = str(resource_url or "").strip()
    normalized_file_path = str(resource_file_path or "").strip()
    normalized_thumbnail_path = str(thumbnail_file_path or "").strip()
    if not normalized_file_path and not normalized_url:
        return False, "Please upload a resource file or add an external URL."

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
            resource_type = repository.get_resource_type_by_id_row(conn, type_id)
            if not resource_type:
                return False, "Resource type was not found."
            if not bool(resource_type["is_active"]):
                return False, "Selected resource type is inactive."
            if not normalized_folder_path:
                normalized_folder_path = str(resource_type["name"] or "").strip() or "General"

            repository.insert_resource_row(
                conn,
                subject_name=subject_label,
                subject_key=subject_key,
                resource_type_id=type_id,
                folder_path=normalized_folder_path,
                title=normalized_title,
                description=normalized_description,
                resource_url=normalized_url,
                resource_file_path=normalized_file_path,
                thumbnail_file_path=normalized_thumbnail_path,
                created_by_admin_id=admin_id,
                created_at=now,
                updated_at=now,
            )
            conn.commit()
    return True, ""


def update_resource(resource_id, *, title, description="", resource_type_id=None, new_resource_file=None, new_thumbnail_file=None):
    try:
        parsed_resource_id = int(resource_id)
    except (TypeError, ValueError):
        return False, "Invalid resource."
    if parsed_resource_id <= 0:
        return False, "Invalid resource."

    normalized_title = str(title or "").strip()
    if not normalized_title:
        return False, "Resource title is required."
    if len(normalized_title) > 180:
        return False, "Resource title is too long."

    normalized_description = str(description or "").strip()
    if len(normalized_description) > 2000:
        return False, "Description is too long."

    # Validate resource_type_id if provided
    final_resource_type_id = None
    if resource_type_id is not None:
        try:
            parsed_type_id = int(resource_type_id)
        except (TypeError, ValueError):
            return False, "Invalid resource type."
        if parsed_type_id <= 0:
            return False, "Invalid resource type."
        final_resource_type_id = parsed_type_id

    # Read existing record to get current file paths and subject
    with _connect() as conn:
        existing = repository.get_resource_row_by_id(conn, parsed_resource_id)
    if not existing:
        return False, "Resource was not found."

    existing_subject_name = str(existing["subject_name"] or "").strip()
    existing_resource_file_path = str(existing["resource_file_path"] or "").strip()
    existing_thumbnail_file_path = str(existing["thumbnail_file_path"] or "").strip()

    # Upload replacement resource file if provided
    new_resource_file_path = ""
    if new_resource_file and str(new_resource_file.filename or "").strip():
        new_resource_file_path, upload_error = upload_resource_file(
            new_resource_file,
            subject_name=existing_subject_name,
        )
        if upload_error:
            return False, upload_error

    # Upload replacement thumbnail if provided
    new_thumbnail_file_path = ""
    if new_thumbnail_file and str(new_thumbnail_file.filename or "").strip():
        new_thumbnail_file_path, thumb_error = upload_thumbnail_file(
            new_thumbnail_file,
            subject_name=existing_subject_name,
        )
        if thumb_error:
            if new_resource_file_path:
                delete_resource_file(new_resource_file_path)
            return False, thumb_error

    final_resource_file_path = new_resource_file_path or existing_resource_file_path
    final_thumbnail_file_path = new_thumbnail_file_path or existing_thumbnail_file_path

    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            if final_resource_type_id is not None:
                resource_type = repository.get_resource_type_by_id_row(conn, final_resource_type_id)
                if not resource_type:
                    if new_resource_file_path:
                        delete_resource_file(new_resource_file_path)
                    if new_thumbnail_file_path:
                        delete_resource_file(new_thumbnail_file_path)
                    return False, "Resource type was not found."
                if not bool(resource_type["is_active"]):
                    if new_resource_file_path:
                        delete_resource_file(new_resource_file_path)
                    if new_thumbnail_file_path:
                        delete_resource_file(new_thumbnail_file_path)
                    return False, "Selected resource type is inactive."
            repository.update_resource_full_row(
                conn,
                parsed_resource_id,
                normalized_title,
                normalized_description,
                final_resource_file_path,
                final_thumbnail_file_path,
                now,
                resource_type_id=final_resource_type_id,
            )
            conn.commit()

    # Delete old R2 files that were replaced
    if new_resource_file_path and existing_resource_file_path and new_resource_file_path != existing_resource_file_path:
        delete_resource_file(existing_resource_file_path)
    if new_thumbnail_file_path and existing_thumbnail_file_path and new_thumbnail_file_path != existing_thumbnail_file_path:
        delete_resource_file(existing_thumbnail_file_path)

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
            existing = repository.get_resource_row_by_id(conn, parsed_resource_id)
            if not existing:
                return False, "Resource was not found."

            repository.update_resource_active(
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

    with _DB_LOCK:
        with _connect() as conn:
            existing = repository.get_resource_row_by_id(conn, parsed_resource_id)
            if not existing:
                return False, "Resource was not found."

            repository.update_resource_active(
                conn,
                parsed_resource_id,
                False,
                _utc_now_iso(),
            )
            conn.commit()
    return True, ""


def list_resources(*, include_inactive=False, subject_name=""):
    subject_key, _subject_label = _canonical_subject(subject_name)
    with _connect() as conn:
        rows = repository.list_resource_rows(
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
        bucket["resources"].sort(key=_resource_sort_key)
    return grouped


def list_resources_grouped_by_type_old_to_new(subject_name):
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
        bucket["resources"].sort(key=_resource_old_to_new_sort_key)
    return grouped


def list_resources_grouped_for_library(subject_name):
    resources = list_resources(
        include_inactive=False,
        subject_name=subject_name,
    )
    grouped = []
    root_by_key = {}

    for row in resources:
        folder_path = _canonical_folder_path(row.get("folder_path", ""))
        if not folder_path:
            folder_path = str(row.get("resource_type_name", "") or "").strip() or "General"
        folder_segments = [part for part in folder_path.split("/") if part]
        if not folder_segments:
            folder_segments = ["General"]

        root_folder_name = folder_segments[0]
        root_folder_key = _normalize(root_folder_name) or root_folder_name.casefold()
        root_bucket = root_by_key.get(root_folder_key)
        if root_bucket is None:
            root_bucket = {
                "folder_name": root_folder_name,
                "folder_slug": _slugify(root_folder_name) or "general",
                "total_resources": 0,
                "resources": [],
                "subfolders": [],
                "_subfolder_by_key": {},
            }
            root_by_key[root_folder_key] = root_bucket
            grouped.append(root_bucket)

        root_bucket["total_resources"] += 1
        subfolder_path = "/".join(folder_segments[1:])
        if not subfolder_path:
            root_bucket["resources"].append(row)
            continue

        subfolder_key = _normalize(subfolder_path) or subfolder_path.casefold()
        subfolder_bucket = root_bucket["_subfolder_by_key"].get(subfolder_key)
        if subfolder_bucket is None:
            subfolder_bucket = {
                "folder_name": folder_segments[-1],
                "folder_path": subfolder_path,
                "full_path": folder_path,
                "resources": [],
            }
            root_bucket["_subfolder_by_key"][subfolder_key] = subfolder_bucket
            root_bucket["subfolders"].append(subfolder_bucket)

        subfolder_bucket["resources"].append(row)

    grouped.sort(key=lambda row: str(row.get("folder_name", "")).casefold())
    for root_bucket in grouped:
        root_bucket["resources"].sort(key=_resource_sort_key)
        root_bucket["subfolders"].sort(
            key=lambda row: str(row.get("full_path", "")).casefold()
        )
        for subfolder_bucket in root_bucket["subfolders"]:
            subfolder_bucket["resources"].sort(key=_resource_sort_key)
        root_bucket.pop("_subfolder_by_key", None)

    return grouped


__all__ = [
    "normalize_subject_name",
    "is_resource_upload_enabled",
    "list_resource_types",
    "create_resource_type",
    "set_resource_type_active",
    "rename_resource_type",
    "delete_resource_type",
    "list_resource_subject_names",
    "create_resource",
    "update_resource",
    "set_resource_active",
    "delete_resource",
    "list_resources",
    "list_resources_grouped_by_type",
    "list_resources_grouped_by_type_old_to_new",
    "list_resources_grouped_for_library",
]
