from backend.utils.response_helpers import jsonify, with_status
from backend.utils.context import request

from backend.identity.account_service import (
    delete_teacher_by_id,
    get_teacher_by_id,
    list_teachers,
    update_teacher_by_id,
    upsert_teacher,
)
from backend.utils.normalization import normalize_school_code
from backend.roles.admin.services.page_service import invalidate_admin_page_context_cache
from backend.roles.admin.services.route_service import group_belongs_to_school
from backend.utils.session import current_auth_login
from backend.roles.admin.services.teacher_candidate_service import (
    create_teacher_candidate,
    delete_candidate_event,
    get_teacher_candidate,
    get_teacher_candidate_training_summary,
    list_teacher_candidates,
    update_candidate_event,
    update_teacher_candidate_status,
)
from backend.roles.admin.services.teacher_academy_service import (
    add_assessment,
    create_academy_teacher,
    list_academy_teachers,
    promote_academy_teacher,
    update_academy_status,
    update_assignment,
)


def _wants_json():
    requested_with = str(request.headers.get("X-Requested-With", "")).strip()
    return requested_with == "XMLHttpRequest"


def _resolve_teacher_fields(mode):
    """Parse and validate the common teacher form fields.

    Returns (full_name, pay_rate, assigned_group, assigned_school, progression, error_message).
    error_message is a non-empty string when validation fails.
    """
    assigned_group = request.form.get("teacher_assigned_group", "").strip()
    assigned_school = normalize_school_code(
        request.form.get("teacher_assigned_school", "")
    )

    if not assigned_group:
        return None, None, None, None, None, "Please select a group for teacher assignment."

    progression = {
        "category": request.form.get("teacher_category", "junior"),
        "semester_stage": request.form.get("teacher_semester_stage", "1-2"),
        "performance_score": request.form.get("teacher_performance_score", "7"),
        "supervised_lessons": request.form.get("teacher_supervised_lessons", "0"),
        "igcse_evidence": request.form.get("teacher_igcse_evidence", ""),
        "promotion_notes": request.form.get("teacher_promotion_notes", ""),
    }

    if mode == "add":
        full_name = request.form.get("teacher_full_name", "").strip()
        pay_rate = request.form.get("teacher_pay_rate", "").strip()
    else:
        selected_name = request.form.get("teacher_selected_name", "").strip()
        teacher_rows = list_teachers()
        matched = next(
            (
                row
                for row in teacher_rows
                if str(row.get("full_name", "")).strip().casefold()
                == selected_name.casefold()
            ),
            None,
        )
        if not matched:
            return None, None, None, None, None, "Please select an existing teacher."
        full_name = str(matched.get("full_name", "")).strip()
        pay_rate = float(matched.get("pay_rate", 0))
        progression = {
            "category": matched.get("category", "junior"),
            "semester_stage": matched.get("semester_stage", "1-2"),
            "performance_score": matched.get("performance_score", 7),
            "supervised_lessons": matched.get("supervised_lessons", 0),
            "igcse_evidence": matched.get("igcse_evidence", ""),
            "promotion_notes": matched.get("promotion_notes", ""),
        }

    return full_name, pay_rate, assigned_group, assigned_school, progression, ""


def _form_list(name):
    getter = getattr(request.form, "getlist", None)
    if callable(getter):
        raw_items = getter(name)
    else:
        raw_items = [str(request.form.get(name, "") or "")]
    values = []
    for raw in raw_items:
        values.extend(item.strip() for item in str(raw or "").split(",") if item.strip())
    return values


def _academy_payload(message):
    invalidate_admin_page_context_cache()
    return jsonify(
        {
            "ok": True,
            "message": message,
            "academy": list_academy_teachers(),
            "teachers": list_teachers(),
        }
    )


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


def _assessment_sections_from_form():
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


def _assessment_scores_from_form():
    return {
        "teacher_guidance_compliance_score": request.form.get("teacher_guidance_compliance_score", ""),
        "timing_adherence_score": request.form.get("timing_adherence_score", ""),
        "resource_familiarity_score": request.form.get("resource_familiarity_score", ""),
        "english_fluency_score": request.form.get("english_fluency_score", ""),
        "confidence_delivery_score": request.form.get("confidence_delivery_score", ""),
        "engagement_technique_score": request.form.get("engagement_technique_score", ""),
    }


def register_admin_teacher_routes(
    router,
    *,
    render_admin_page,
):
    def _teacher_error(message, *, teacher_edit=None, status=400):
        if _wants_json():
            return jsonify({"ok": False, "message": message}, status_code=status)
        return with_status(render_admin_page(
                auth_error=message,
                admin_panel="teachers",
                admin_teacher_edit=teacher_edit,
            ), status)

    def _teacher_success(message):
        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {"ok": True, "message": message, "teachers": list_teachers()}
            )
        return render_admin_page(admin_notice=message, admin_panel="teachers")

    def _academy_error(message, status=400):
        if _wants_json():
            return jsonify({"ok": False, "message": message}, status_code=status)
        return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), status)

    @router.post("/admin/teacher-academy")
    def create_teacher_academy_route():
        created, error_message = create_academy_teacher(
            full_name=request.form.get("academy_full_name", ""),
            subject_program_id=request.form.get("academy_subject_program_id", ""),
            position=request.form.get("academy_position", "Trainee Teacher"),
            employment_type=request.form.get("academy_employment_type", "academy"),
            telegram_username=request.form.get("academy_telegram_username", ""),
            phone=request.form.get("academy_phone", ""),
            email=request.form.get("academy_email", ""),
            academy_start_date=request.form.get("academy_start_date", ""),
            mentor_id=request.form.get("academy_mentor_id", "0"),
            department_head_id=request.form.get("academy_department_head_id", "0"),
            notes=request.form.get("academy_notes", ""),
            created_by=current_auth_login() or "Academic Director",
        )
        if not created:
            return _academy_error(error_message or "Unable to create academy teacher.")
        if _wants_json():
            return _academy_payload("Academy teacher created with 12 training lessons.")
        return render_admin_page(admin_notice="Academy teacher created.", admin_panel="teachers")

    @router.post("/admin/teacher-academy/assignments/{assignment_id}")
    def update_teacher_academy_assignment_route(assignment_id: int):
        updated, error_message = update_assignment(
            assignment_id=assignment_id,
            assignment_type=request.form.get("assignment_type", ""),
            deadline_date=request.form.get("deadline_date", ""),
            session_datetime=request.form.get("session_datetime", ""),
            evaluator_id=request.form.get("evaluator_id", "0"),
            focus_areas=_form_list("focus_areas"),
            notes_to_trainee=request.form.get("notes_to_trainee", ""),
            status=request.form.get("assignment_status", "assigned"),
        )
        if not updated:
            return _academy_error(error_message or "Unable to update assignment.")
        if _wants_json():
            return _academy_payload("Training lesson updated.")
        return render_admin_page(admin_notice="Training lesson updated.", admin_panel="teachers")

    @router.post("/admin/teacher-academy/{academy_teacher_id}/assessments")
    def add_teacher_academy_assessment_route(academy_teacher_id: int):
        saved, error_message = add_assessment(
            academy_teacher_id=academy_teacher_id,
            lesson_assignment_id=request.form.get("lesson_assignment_id", ""),
            assessment_type=request.form.get("assessment_type", "academy_practice_lesson"),
            evaluator_id=request.form.get("evaluator_id", "0"),
            assessment_datetime=request.form.get("assessment_datetime", ""),
            session_type=request.form.get("session_type", "training_simulation"),
            class_label=request.form.get("class_label", ""),
            section_feedback=_assessment_sections_from_form(),
            scores=_assessment_scores_from_form(),
            strengths=request.form.get("strengths", ""),
            areas_for_improvement=request.form.get("areas_for_improvement", ""),
            final_recommendation=request.form.get("final_recommendation", ""),
            decision=request.form.get("decision", "needs_improvement"),
            created_by=current_auth_login() or "Academic Director",
        )
        if not saved:
            return _academy_error(error_message or "Unable to save assessment.")
        if _wants_json():
            return _academy_payload("Assessment saved.")
        return render_admin_page(admin_notice="Assessment saved.", admin_panel="teachers")

    @router.post("/admin/teacher-academy/{academy_teacher_id}/status")
    def update_teacher_academy_status_route(academy_teacher_id: int):
        updated, error_message = update_academy_status(
            academy_teacher_id=academy_teacher_id,
            status=request.form.get("academy_status", ""),
        )
        if not updated:
            return _academy_error(error_message or "Unable to update academy status.")
        if _wants_json():
            return _academy_payload("Academy status updated.")
        return render_admin_page(admin_notice="Academy status updated.", admin_panel="teachers")

    @router.post("/admin/teacher-academy/{academy_teacher_id}/promote")
    def promote_teacher_academy_route(academy_teacher_id: int):
        promoted, error_message = promote_academy_teacher(
            academy_teacher_id=academy_teacher_id,
            assigned_group=request.form.get("teacher_assigned_group", ""),
            pay_rate=request.form.get("teacher_pay_rate", "0"),
            category=request.form.get("teacher_category", "junior"),
            semester_stage=request.form.get("teacher_semester_stage", "1-2"),
            promotion_notes=request.form.get("teacher_promotion_notes", ""),
        )
        if not promoted:
            return _academy_error(error_message or "Unable to promote academy teacher.")
        if _wants_json():
            return _academy_payload("Academy teacher promoted to Active Teachers.")
        return render_admin_page(admin_notice="Academy teacher promoted.", admin_panel="teachers")

    @router.post("/admin/teacher-candidates")
    def create_teacher_candidate_route():
        created, error_message = create_teacher_candidate(
            full_name=request.form.get("candidate_full_name", ""),
            phone=request.form.get("candidate_phone", ""),
            telegram_username=request.form.get("candidate_telegram", ""),
            email=request.form.get("candidate_email", ""),
            subject=request.form.get("candidate_subject", ""),
            source=request.form.get("candidate_source", ""),
            notes=request.form.get("candidate_notes", ""),
            created_by=current_auth_login() or "Admin",
        )
        if not created:
            message = error_message or "Unable to add candidate."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {
                    "ok": True,
                    "message": "Candidate added.",
                    "candidates": list_teacher_candidates(),
                }
            )
        return render_admin_page(
            admin_notice="Candidate added.",
            admin_panel="teachers",
        )

    @router.post("/admin/teacher-candidates/{candidate_id}/status")
    def update_teacher_candidate_status_route(candidate_id: int):
        updated, error_message = update_teacher_candidate_status(
            candidate_id=candidate_id,
            status=request.form.get("candidate_status", ""),
            event_type=request.form.get("candidate_event_type", ""),
            result=request.form.get("candidate_result", ""),
            score=request.form.get("candidate_score", ""),
            notes=request.form.get("candidate_event_notes", ""),
            created_by=current_auth_login() or "Admin",
            detail=request.form.get("candidate_event_detail", ""),
        )
        if not updated:
            message = error_message or "Unable to update candidate."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {
                    "ok": True,
                    "message": "Candidate updated.",
                    "candidates": list_teacher_candidates(),
                }
            )
        return render_admin_page(
            admin_notice="Candidate updated.",
            admin_panel="teachers",
        )

    @router.post("/admin/teacher-candidates/{candidate_id}/promote")
    def promote_teacher_candidate_route(candidate_id: int):
        candidate = get_teacher_candidate(candidate_id)
        if not candidate:
            message = "Candidate not found."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=404)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 404)

        assigned_group = request.form.get("teacher_assigned_group", "").strip()
        assigned_school = normalize_school_code(request.form.get("teacher_assigned_school", ""))
        pay_rate = request.form.get("teacher_pay_rate", "").strip()
        category = request.form.get("teacher_category", "junior")
        semester_stage = request.form.get("teacher_semester_stage", "1-2")
        performance_score = request.form.get("teacher_performance_score", "")
        supervised_lessons = request.form.get("teacher_supervised_lessons", "")
        igcse_evidence = request.form.get("teacher_igcse_evidence", "")
        promotion_notes = request.form.get("teacher_promotion_notes", "")
        if not assigned_group:
            message = "Select a group to promote this candidate."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                message = "Selected group does not belong to the selected school."
                if _wants_json():
                    return jsonify({"ok": False, "message": message}, status_code=400)
                return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        training_summary = get_teacher_candidate_training_summary(candidate_id)
        if performance_score == "":
            performance_score = str(training_summary.get("average_score") or 7)
        if supervised_lessons == "":
            supervised_lessons = str(training_summary.get("accepted_lessons") or 0)

        created = upsert_teacher(
            full_name=str(candidate.get("full_name", "")).strip(),
            pay_rate=pay_rate,
            assigned_group=assigned_group,
            category=category,
            semester_stage=semester_stage,
            performance_score=performance_score,
            supervised_lessons=supervised_lessons,
            igcse_evidence=igcse_evidence,
            promotion_notes=promotion_notes,
        )
        if not created:
            message = "Unable to create the teacher record."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        update_teacher_candidate_status(
            candidate_id=candidate_id,
            status="hired",
            event_type="promote",
            result="hired",
            notes=f"Promoted to active teacher in {assigned_group}.",
            created_by=current_auth_login() or "Admin",
        )

        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {
                    "ok": True,
                    "message": "Candidate promoted to active teacher.",
                    "teachers": list_teachers(),
                    "candidates": list_teacher_candidates(),
                }
            )
        return render_admin_page(
            admin_notice="Candidate promoted to active teacher.",
            admin_panel="teachers",
        )

    @router.post("/admin/teacher-candidates/{candidate_id}/events/{event_id}/edit")
    def edit_teacher_candidate_event_route(candidate_id: int, event_id: int):
        updated, error_message = update_candidate_event(
            candidate_id=candidate_id,
            event_id=event_id,
            result=request.form.get("candidate_result", ""),
            score=request.form.get("candidate_score", ""),
            notes=request.form.get("candidate_event_notes", ""),
            detail=request.form.get("candidate_event_detail", ""),
        )
        if not updated:
            message = error_message or "Unable to edit evaluation."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {"ok": True, "message": "Evaluation updated.", "candidates": list_teacher_candidates()}
            )
        return render_admin_page(admin_notice="Evaluation updated.", admin_panel="teachers")

    @router.post("/admin/teacher-candidates/{candidate_id}/events/{event_id}/delete")
    def delete_teacher_candidate_event_route(candidate_id: int, event_id: int):
        deleted, error_message = delete_candidate_event(
            candidate_id=candidate_id,
            event_id=event_id,
        )
        if not deleted:
            message = error_message or "Unable to delete evaluation."
            if _wants_json():
                return jsonify({"ok": False, "message": message}, status_code=400)
            return with_status(render_admin_page(auth_error=message, admin_panel="teachers"), 400)

        invalidate_admin_page_context_cache()
        if _wants_json():
            return jsonify(
                {"ok": True, "message": "Evaluation deleted.", "candidates": list_teacher_candidates()}
            )
        return render_admin_page(admin_notice="Evaluation deleted.", admin_panel="teachers")

    @router.post("/admin/teachers")
    def create_teacher():
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()

        full_name, pay_rate, assigned_group, assigned_school, progression, err = _resolve_teacher_fields(
            mode
        )
        if err:
            return _teacher_error(err)

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return _teacher_error(
                    "Selected group does not belong to the selected school."
                )

        created = upsert_teacher(
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
            **progression,
        )
        if not created:
            return _teacher_error(
                "Unable to save teacher. Check full name, pay rate, and group."
            )

        return _teacher_success("Teacher saved.")

    @router.post("/admin/teachers/{teacher_id}")
    def update_teacher(teacher_id: int):
        mode = str(request.form.get("teacher_mode", "select")).strip().lower()
        teacher_edit = get_teacher_by_id(teacher_id)

        full_name, pay_rate, assigned_group, assigned_school, progression, err = _resolve_teacher_fields(
            mode
        )
        if err:
            return _teacher_error(err, teacher_edit=teacher_edit)

        if assigned_school and assigned_school != "all":
            if not group_belongs_to_school(assigned_group, assigned_school):
                return _teacher_error(
                    "Selected group does not belong to the selected school.",
                    teacher_edit=teacher_edit,
                )

        updated, update_error = update_teacher_by_id(
            teacher_id=teacher_id,
            full_name=full_name,
            pay_rate=pay_rate,
            assigned_group=assigned_group,
            **progression,
        )
        if not updated:
            return _teacher_error(
                update_error or "Unable to update teacher.",
                teacher_edit=get_teacher_by_id(teacher_id),
            )

        return _teacher_success("Teacher updated.")

    @router.post("/admin/teachers/{teacher_id}/delete")
    def delete_teacher(teacher_id: int):
        deleted = delete_teacher_by_id(teacher_id)
        if not deleted:
            return _teacher_error("Unable to delete teacher.")

        return _teacher_success("Teacher deleted.")
