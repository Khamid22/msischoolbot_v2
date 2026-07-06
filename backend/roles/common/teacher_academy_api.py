"""Shared JSON handlers for Teacher Academy role APIs."""

from __future__ import annotations

from backend.domains.teacher_academy.service import (
    add_assessment,
    create_academy_teacher,
    delete_academy_teacher,
    list_academy_teachers,
    promote_academy_teacher,
    update_academy_status,
    update_assignment,
)
from backend.domains.teachers.service import list_teachers
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.utils.context import request
from backend.utils.response_helpers import jsonify
from backend.utils.session import current_auth_login


ACADEMY_SECTIONS = (
    "starter",
    "warmup",
    "teaching_session_1",
    "teaching_session_2",
    "teaching_session_3",
    "end_activity",
    "homework",
)

ACADEMY_CRITERIA_REMARKS = (
    ("tgc", "teacher_guidance_compliance_score", "teacher_guidance_compliance_remarks"),
    ("ta", "timing_adherence_score", "timing_adherence_remarks"),
    ("rf", "resource_familiarity_score", "resource_familiarity_remarks"),
    ("ef", "english_fluency_score", "english_fluency_remarks"),
    ("con", "confidence_delivery_score", "confidence_delivery_remarks"),
    ("se", "engagement_technique_score", "engagement_technique_remarks"),
)


def form_list(name: str) -> list[str]:
    getter = getattr(request.form, "getlist", None)
    if callable(getter):
        raw_items = getter(name)
    else:
        raw_items = [str(request.form.get(name, "") or "")]
    values: list[str] = []
    for raw in raw_items:
        values.extend(item.strip() for item in str(raw or "").split(",") if item.strip())
    return values


def academy_error(message: str, status: int = 400):
    return jsonify({"ok": False, "message": message}, status_code=status)


def safe_credentials(credentials: dict | None) -> dict[str, str]:
    credentials = credentials or {}
    return {
        "role": "teacher",
        "login": credentials.get("login", ""),
        "teacher_code": credentials.get("teacher_code", ""),
        "temporary_password": credentials.get("temporary_password", ""),
        "display_name": credentials.get("display_name", ""),
        "subject_name": credentials.get("subject_name", ""),
    }


def filter_academy_teachers_for_current_scope(rows):
    from backend.roles.head_of_department.academy_scope import (
        filter_academy_teachers_for_current_scope as _filter_academy_teachers_for_current_scope,
    )

    return _filter_academy_teachers_for_current_scope(rows)


def academy_payload(message: str, *, credentials: dict | None = None):
    invalidate_admin_page_context_cache()
    payload = {
        "ok": True,
        "message": message,
        "academy": filter_academy_teachers_for_current_scope(list_academy_teachers()),
        "teachers": list_teachers(),
    }
    if credentials:
        payload["credentials"] = safe_credentials(credentials)
    return jsonify(payload)


def assessment_sections_from_form() -> dict:
    sections = {}
    for key in ACADEMY_SECTIONS:
        sections[key] = {
            "status": request.form.get(f"{key}_status", "not_applicable"),
            "time_used": request.form.get(f"{key}_time_used", ""),
            "remarks": request.form.get(f"{key}_remarks", ""),
        }
    criteria = {}
    for key, score_key, remarks_key in ACADEMY_CRITERIA_REMARKS:
        criteria[key] = {
            "score": request.form.get(score_key, ""),
            "remarks": request.form.get(remarks_key, ""),
        }
    sections["marking_criteria"] = criteria
    return sections


def assessment_scores_from_form() -> dict[str, str]:
    return {
        "teacher_guidance_compliance_score": request.form.get("teacher_guidance_compliance_score", ""),
        "timing_adherence_score": request.form.get("timing_adherence_score", ""),
        "resource_familiarity_score": request.form.get("resource_familiarity_score", ""),
        "english_fluency_score": request.form.get("english_fluency_score", ""),
        "confidence_delivery_score": request.form.get("confidence_delivery_score", ""),
        "engagement_technique_score": request.form.get("engagement_technique_score", ""),
    }


def create_academy_teacher_response(*, created_by_label: str = "Academic Director"):
    create_result = create_academy_teacher(
        full_name=request.form.get("academy_full_name", ""),
        subject_program_id=request.form.get("academy_subject_program_id", ""),
        selected_curriculum_item_ids=form_list("academy_curriculum_item_ids"),
        position=request.form.get("academy_position", "Trainee Teacher"),
        employment_type=request.form.get("academy_employment_type", "academy"),
        telegram_username=request.form.get("academy_telegram_username", ""),
        phone=request.form.get("academy_phone", ""),
        email=request.form.get("academy_email", ""),
        academy_start_date=request.form.get("academy_start_date", ""),
        mentor_id=request.form.get("academy_mentor_id", "0"),
        department_head_id=request.form.get("academy_department_head_id", "0"),
        notes=request.form.get("academy_notes", ""),
        created_by=current_auth_login() or created_by_label,
        return_credentials=True,
    )
    if isinstance(create_result, tuple) and len(create_result) == 3:
        created, error_message, credentials = create_result
    else:
        created, error_message = create_result
        credentials = {}
    if not created:
        return academy_error(error_message or "Unable to create academy teacher.")
    return academy_payload(
        "Academy teacher created with selected Teacher Academy lessons.",
        credentials=credentials,
    )


def update_assignment_response(assignment_id: int):
    updated, error_message = update_assignment(
        assignment_id=assignment_id,
        assignment_type=request.form.get("assignment_type", ""),
        deadline_date=request.form.get("deadline_date", ""),
        session_datetime=request.form.get("session_datetime", ""),
        evaluator_id=request.form.get("evaluator_id", "0"),
        focus_areas=form_list("focus_areas"),
        notes_to_trainee=request.form.get("notes_to_trainee", ""),
        status=request.form.get("assignment_status", "assigned"),
    )
    if not updated:
        return academy_error(error_message or "Unable to update assignment.")
    return academy_payload("Academy lesson updated.")


def add_assessment_response(academy_teacher_id: int, *, created_by_label: str = "Academic Director"):
    saved, error_message = add_assessment(
        academy_teacher_id=academy_teacher_id,
        lesson_assignment_id=request.form.get("lesson_assignment_id", ""),
        assessment_type=request.form.get("assessment_type", "academy_practice_lesson"),
        evaluator_id=request.form.get("evaluator_id", "0"),
        assessment_datetime=request.form.get("assessment_datetime", ""),
        session_type=request.form.get("session_type", "training_simulation"),
        class_label=request.form.get("class_label", ""),
        section_feedback=assessment_sections_from_form(),
        scores=assessment_scores_from_form(),
        strengths=request.form.get("strengths", ""),
        areas_for_improvement=request.form.get("areas_for_improvement", ""),
        final_recommendation=request.form.get("final_recommendation", ""),
        decision=request.form.get("decision", "needs_improvement"),
        created_by=current_auth_login() or created_by_label,
    )
    if not saved:
        return academy_error(error_message or "Unable to save assessment.")
    return academy_payload("Assessment saved.")


def update_status_response(academy_teacher_id: int):
    updated, error_message = update_academy_status(
        academy_teacher_id=academy_teacher_id,
        status=request.form.get("academy_status", ""),
    )
    if not updated:
        return academy_error(error_message or "Unable to update academy status.")
    return academy_payload("Academy status updated.")


def delete_academy_teacher_response(academy_teacher_id: int):
    deleted, error_message = delete_academy_teacher(academy_teacher_id=academy_teacher_id)
    if not deleted:
        return academy_error(error_message or "Unable to delete academy teacher.")
    return academy_payload("Academy teacher deleted.")


def promote_response(academy_teacher_id: int):
    promoted, error_message = promote_academy_teacher(
        academy_teacher_id=academy_teacher_id,
        assigned_group=request.form.get("teacher_assigned_group", ""),
        pay_rate=request.form.get("teacher_pay_rate", "0"),
        category=request.form.get("teacher_category", "junior"),
        semester_stage=request.form.get("teacher_semester_stage", "1-2"),
        promotion_notes=request.form.get("teacher_promotion_notes", ""),
    )
    if not promoted:
        return academy_error(error_message or "Unable to promote academy teacher.")
    return academy_payload("Academy teacher promoted to Active Teachers.")


__all__ = [
    "academy_error",
    "academy_payload",
    "add_assessment_response",
    "create_academy_teacher_response",
    "delete_academy_teacher_response",
    "form_list",
    "promote_response",
    "update_assignment_response",
    "update_status_response",
]
