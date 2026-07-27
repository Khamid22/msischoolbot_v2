"""Groups academic operations."""

import json

from backend.core.database import connect_auth_db
from backend.modules.domains.academics.groups import repository as academic_repository
from backend.modules.domains.academics.common import (
    _now, _get_v2_enrollment,
)
from backend.modules.domains.academics.groups.service import (
    create_group_from_program,
    create_student_with_enrollment,
    list_academic_management_rows,
)

def list_academic_management_context(*, include_heavy=True, include_groups=True):
    return list_academic_management_rows(
        include_heavy=include_heavy, include_groups=include_groups
    )


def create_group_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    program_subject_key = str(payload.get("program_subject_key", "") or "").strip()
    raw_program_keys = payload.get("program_subject_keys", [])
    if isinstance(raw_program_keys, str):
        raw_program_keys = [raw_program_keys]
    program_subject_keys = [
        str(key or "").strip() for key in raw_program_keys if str(key or "").strip()
    ]
    if program_subject_key and program_subject_key not in program_subject_keys:
        program_subject_keys.append(program_subject_key)
    group_name = str(payload.get("group_name", "") or "").strip()
    group_code = str(payload.get("group_code", "") or "").strip()
    class_id = int(payload.get("class_id", 0) or 0)
    set_name = str(payload.get("set_name", "Set 1") or "Set 1").strip()
    if not school_code or not program_subject_keys or not group_name:
        raise ValueError("Client school, at least one subject program, and group name are required.")
    for subject_key in dict.fromkeys(program_subject_keys):
        create_group_from_program(
            school_code, subject_key, group_name, group_code,
            class_id=class_id, set_name=set_name,
        )
    return {"school_code": school_code}


def archive_group(group_id, *, actor_staff_id=None, actor_account_id=None):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required.")

    with connect_auth_db() as conn:
        group_row = academic_repository.get_group_archive_candidate(conn, group_id)
        if not group_row:
            return None

        group_name = str(group_row["group_name"] or "").strip()
        if group_name.casefold() == "online":
            raise ValueError("The Online group cannot be archived.")

        if str(group_row["status"] or "").strip().lower() == "archived":
            raise ValueError("This group is already archived.")

        v2_group_id = int(group_row["id"])
        counts = academic_repository.count_group_dependencies(conn, v2_group_id)
        archived = academic_repository.archive_group(conn, v2_group_id)
        if not archived:
            raise ValueError("This group could not be archived.")
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.group_archived",
            entity_type="group",
            entity_id=v2_group_id,
            detail_json=json.dumps(
                {
                    "public_id": int(group_row["public_id"]),
                    "group_name": group_name,
                    "preserved_records": counts,
                },
                ensure_ascii=False,
            ),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        conn.commit()

    return {
        "id": int(group_row["public_id"]),
        "name": group_name,
        "code": str(group_row["group_code"] or "").strip(),
        "school_code": str(group_row["school_key"] or "").strip(),
        "subject_name": str(group_row["subject_name"] or "").strip(),
        "status": "archived",
        "preserved": counts,
    }


# The public DELETE endpoint archives groups; retain its established callable name.
delete_group = archive_group


def preview_group_purge(group_id):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required.")
    with connect_auth_db() as conn:
        group = academic_repository.get_group_archive_candidate(conn, group_id)
        if not group:
            return None
        if str(group["status"] or "").strip().casefold() != "archived":
            raise ValueError("Archive this group before permanently purging it.")
        counts = academic_repository.count_group_dependencies(conn, int(group["id"]))
    name = str(group["group_name"] or "").strip()
    return {
        "id": int(group["public_id"]),
        "name": name,
        "dependencies": counts,
        "required_confirmation": f"PURGE {name}",
    }


def permanently_purge_group(
    group_id, confirmation, *, actor_staff_id=None, actor_account_id=None
):
    group_id = int(group_id or 0)
    if group_id <= 0:
        raise ValueError("group_id is required.")
    with connect_auth_db() as conn:
        group = academic_repository.get_group_archive_candidate(conn, group_id)
        if not group:
            return None
        if str(group["status"] or "").strip().casefold() != "archived":
            raise ValueError("Archive this group before permanently purging it.")
        name = str(group["group_name"] or "").strip()
        required = f"PURGE {name}"
        if str(confirmation or "").strip() != required:
            raise ValueError(f'Type "{required}" to confirm permanent deletion.')
        v2_group_id = int(group["id"])
        counts = academic_repository.count_group_dependencies(conn, v2_group_id)
        academic_repository.insert_audit_event(
            conn,
            event_type="academic.group_purged",
            entity_type="group",
            entity_id=v2_group_id,
            detail_json=json.dumps(
                {
                    "public_id": int(group["public_id"]),
                    "group_name": name,
                    "deleted_dependencies": counts,
                },
                ensure_ascii=False,
            ),
            actor_staff_id=actor_staff_id,
            actor_account_id=actor_account_id,
        )
        deleted = academic_repository.purge_group(conn, v2_group_id)
        if not deleted:
            raise ValueError("The archived group could not be purged.")
        conn.commit()
    return {"id": int(group["public_id"]), "name": name, "deleted": counts}


def create_student_with_enrollment_from_payload(payload):
    full_name = str(payload.get("full_name", "") or "").strip()
    group_id = int(payload.get("group_id", 0) or 0)
    if not full_name or group_id <= 0:
        raise ValueError("Student name and group are required.")
    return create_student_with_enrollment(full_name, group_id)


def update_enrollment_status(enrollment_id, status, reason=""):
    enrollment_id = int(enrollment_id or 0)
    if enrollment_id <= 0:
        raise ValueError("Enrollment id is required.")
    normalized_status = str(status or "").strip().casefold()
    if normalized_status not in {"active", "disqualified", "banned"}:
        raise ValueError("Unsupported enrollment status.")

    active = 1 if normalized_status == "active" else 0
    disqualification_reason = "" if normalized_status == "active" else str(reason or "").strip()
    if normalized_status == "banned" and not disqualification_reason:
        disqualification_reason = "Disqualified by Academic Director"

    now = _now()
    disqualified_at = "" if normalized_status == "active" else now.strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect_auth_db() as conn:
        row = _get_v2_enrollment(conn, enrollment_id)
        if not row:
            raise ValueError("Enrollment not found.")
        academic_repository.update_enrollment_status_row(
            conn,
            group_id=row["group_id"],
            student_id=row["student_id"],
            status=normalized_status,
            reason=disqualification_reason,
            changed_at=now,
        )
        conn.commit()

    return {
        "id": enrollment_id,
        "active": bool(active),
        "status": normalized_status,
        "disqualificationReason": disqualification_reason,
        "disqualifiedAt": disqualified_at,
    }


def move_enrollment_group(enrollment_id, group_id):
    enrollment_id = int(enrollment_id or 0)
    group_id = int(group_id or 0)
    if enrollment_id <= 0:
        raise ValueError("Enrollment id is required.")
    if group_id <= 0:
        raise ValueError("Target group is required.")

    with connect_auth_db() as conn:
        row = _get_v2_enrollment(conn, enrollment_id)
        if not row:
            raise ValueError("Enrollment not found.")
        target = academic_repository.get_active_group_by_legacy_or_id(conn, group_id)
        if not target:
            raise ValueError("Target group not found.")
        if int(target["school_id"]) != int(row["school_id"]):
            raise ValueError("Students can only move between groups in the same school.")
        if int(target["program_id"]) != int(row["program_id"]):
            raise ValueError("Students can only move between groups using the same subject program.")
        academic_repository.move_enrollment_row(
            conn,
            source_group_id=row["group_id"],
            target_group_id=target["id"],
            student_id=row["student_id"],
            enrollment_status=row["enrollment_status"],
            joined_at=_now(),
            legacy_enrollment_id=enrollment_id,
        )
        conn.commit()

    return {"id": enrollment_id, "groupId": group_id}


def update_enrollment_status_from_payload(enrollment_id, payload):
    return update_enrollment_status(
        enrollment_id,
        payload.get("status", ""),
        reason=payload.get("reason", ""),
    )


def move_enrollment_group_from_payload(enrollment_id, payload):
    return move_enrollment_group(enrollment_id, payload.get("group_id", 0))
