import math

from flask import jsonify, render_template, request, session, url_for

try:
    from ..lesson_catalog_store import get_lessons_for_subject
except ImportError:
    from lesson_catalog_store import get_lessons_for_subject

try:
    from ..auth_store import (
        get_dashboard_student_profile,
        get_student_db_id_by_sheet_student_id,
    )
except ImportError:
    from auth_store import (
        get_dashboard_student_profile,
        get_student_db_id_by_sheet_student_id,
    )


def register_dashboard_routes(
    app,
    *,
    load_dashboard_payload,
    load_dataset,
    extract_attendance_rate,
    extract_exam_average_score,
    round_grade_half_up,
    compute_subject_rating,
):
    def _normalize_text(value):
        return " ".join(str(value or "").strip().casefold().split())

    def _subject_short_name(subject_name):
        normalized = _normalize_text(subject_name)
        short_names = {
            "igcse mathematics a": "Math",
            "mathematics": "Math",
            "math": "Math",
            "general english": "Eng",
            "english": "Eng",
            "chemistry": "Chem",
            "biology": "Bio",
            "physics": "Phys",
        }
        if normalized in short_names:
            return short_names[normalized]

        words = [part for part in str(subject_name or "").strip().split() if part]
        if not words:
            return "Subject"
        if len(words) == 1:
            return words[0][:4]
        return words[0][:4]

    def _current_auth_role():
        return str(session.get("auth_role", "")).strip().lower()

    def _current_student_sheet_id():
        raw_value = session.get("student_sheet_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _current_student_db_id():
        raw_value = session.get("student_db_id")
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _current_student_full_name():
        return str(session.get("student_full_name", "")).strip()

    def _is_student_owner_of_payload(student_id, payload):
        # Allow student access only to dashboards that belong to the same full name.
        own_full_name = _normalize_text(_current_student_full_name())
        if own_full_name:
            payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
            payload_full_name = _normalize_text(payload_student.get("fullName", ""))
            return bool(payload_full_name) and payload_full_name == own_full_name

        # Backward-compatible fallback for old sessions without student_full_name.
        own_sheet_student_id = _current_student_sheet_id()
        return own_sheet_student_id is not None and int(student_id) == own_sheet_student_id

    def _extract_aap_remark(score):
        if score is None:
            return "Not Graded", "remark-muted"
        if score <= 4:
            return "Fail", "remark-fail"
        if score <= 7:
            return "Satisfactory", "remark-satisfactory"
        return "Excellent", "remark-excellent"

    def _build_subject_switch_options(dataset, current_full_name):
        students = dataset.get("students", []) if isinstance(dataset, dict) else []
        if not isinstance(students, list):
            return []

        current_name_norm = _normalize_text(current_full_name)
        if not current_name_norm:
            return []

        options = []
        seen = set()
        for student in students:
            if not isinstance(student, dict):
                continue

            if _normalize_text(student.get("fullName", "")) != current_name_norm:
                continue

            option_student_id = student.get("id")
            if not isinstance(option_student_id, int):
                continue

            subject_name = str(student.get("subject", "")).strip()
            group_name = str(student.get("group", "")).strip()
            unique_key = (option_student_id, subject_name, group_name)
            if unique_key in seen:
                continue
            seen.add(unique_key)

            options.append(
                {
                    "student_id": option_student_id,
                    "subject": subject_name,
                    "subject_short": _subject_short_name(subject_name),
                    "group": group_name,
                }
            )

        options.sort(
            key=lambda item: (
                _normalize_text(item.get("subject", "")),
                _normalize_text(item.get("group", "")),
                int(item.get("student_id", 0)),
            )
        )
        return options

    # Student dashboard page with summary metrics.
    @app.get("/dashboard/<int:student_id>")
    def dashboard(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()

        payload, dataset, payload_error = load_dashboard_payload(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
        )
        if payload_error:
            return (
                render_template(
                    "not_found.html",
                    message=payload_error,
                ),
                503,
            )

        if not payload:
            return (
                render_template(
                    "not_found.html",
                    message="We could not retrieve data for this student. Please search again.",
                ),
                404,
            )

        if _current_auth_role() == "student" and not _is_student_owner_of_payload(
            student_id, payload
        ):
            if not _current_student_sheet_id() and not _current_student_full_name():
                return (
                    render_template(
                        "not_found.html",
                        message="Student session is invalid. Please login again.",
                    ),
                    401,
                )
            return (
                render_template(
                    "not_found.html",
                    message="Access denied: you can open only your own dashboard.",
                ),
                403,
            )

        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        current_subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
        current_group_name = str(payload_student.get("group", "")).strip()
        current_full_name = str(payload_student.get("fullName", "")).strip()
        resolved_student_db_id = _current_student_db_id()
        if not resolved_student_db_id:
            resolved_student_db_id = get_student_db_id_by_sheet_student_id(student_id)
            if resolved_student_db_id:
                session["student_db_id"] = resolved_student_db_id

        student_profile = get_dashboard_student_profile(
            student_db_id=resolved_student_db_id,
            full_name=current_full_name,
            group_name=current_group_name,
            subject_name=current_subject_name,
            load_dataset=load_dataset,
        )

        dataset_for_subject_switch = dataset
        if not dataset_for_subject_switch:
            refreshed_dataset, load_error = load_dataset()
            if not load_error and refreshed_dataset:
                dataset_for_subject_switch = refreshed_dataset

        subject_switch_options = _build_subject_switch_options(
            dataset_for_subject_switch,
            current_full_name,
        )
        if not subject_switch_options:
            subject_switch_options = [
                {
                    "student_id": int(student_id),
                    "subject": current_subject_name,
                    "subject_short": _subject_short_name(current_subject_name),
                    "group": current_group_name,
                }
            ]

        for option in subject_switch_options:
            option_student_id = int(option.get("student_id", student_id))
            option_subject = str(option.get("subject", "")).strip()
            option_group = str(option.get("group", "")).strip()

            route_params = {"student_id": option_student_id}
            if option_subject:
                route_params["subject"] = option_subject
            if option_group:
                route_params["group"] = option_group

            option["is_current"] = option_student_id == int(student_id)
            option["url"] = url_for("dashboard", **route_params)

        current_subject_short_name = _subject_short_name(current_subject_name)

        attendance_rate = extract_attendance_rate(payload)
        exam_average_score = extract_exam_average_score(payload)
        exam_performance = (
            round_grade_half_up(exam_average_score)
            if exam_average_score is not None and exam_average_score > 0
            else 0
        )
        program_total_lessons = 180
        completed_lessons = min(
            len(payload.get("homeworkGrades", [])),
            program_total_lessons,
        )
        program_completed_rate = round((completed_lessons / program_total_lessons) * 100)
        subject_rating = compute_subject_rating(
            student_id=student_id,
            payload=payload,
            dataset=dataset,
        )
        rating_board_url = url_for(
            "rating_board",
            student_id=student_id,
            subject=requested_subject or current_subject_name,
            group=requested_group or current_group_name,
        )
        aap_lessons_url = url_for(
            "aap_lessons",
            student_id=student_id,
            subject=requested_subject or current_subject_name,
            group=requested_group or current_group_name,
        )

        return render_template(
            "dashboard.html",
            payload=payload,
            attendance_rate=attendance_rate,
            exam_performance=exam_performance,
            program_completed_lessons=completed_lessons,
            program_completed_rate=program_completed_rate,
            subject_rating=subject_rating,
            rating_board_url=rating_board_url,
            aap_lessons_url=aap_lessons_url,
            current_subject_name=current_subject_name,
            current_subject_short_name=current_subject_short_name,
            subject_switch_options=subject_switch_options,
            student_profile=student_profile,
        )

    @app.get("/dashboard/<int:student_id>/aap-lessons")
    def aap_lessons(student_id):
        requested_subject = request.args.get("subject", "").strip()
        requested_group = request.args.get("group", "").strip()

        payload, _dataset, payload_error = load_dashboard_payload(
            student_id=student_id,
            requested_subject=requested_subject,
            requested_group=requested_group,
        )
        if payload_error:
            return (
                render_template(
                    "not_found.html",
                    message=payload_error,
                ),
                503,
            )

        if not payload:
            return (
                render_template(
                    "not_found.html",
                    message="We could not retrieve data for this student. Please search again.",
                ),
                404,
            )

        if _current_auth_role() == "student" and not _is_student_owner_of_payload(
            student_id, payload
        ):
            if not _current_student_sheet_id() and not _current_student_full_name():
                return (
                    render_template(
                        "not_found.html",
                        message="Student session is invalid. Please login again.",
                    ),
                    401,
                )
            return (
                render_template(
                    "not_found.html",
                    message="Access denied: you can open only your own AAP table.",
                ),
                403,
            )

        payload_student = payload.get("student", {}) if isinstance(payload, dict) else {}
        subject_name = str(payload_student.get("subject", "")).strip() or "Unknown"
        group_name = str(payload_student.get("group", "")).strip()
        full_name = str(payload_student.get("fullName", "")).strip()

        lesson_catalog, lesson_error = get_lessons_for_subject(
            subject_name,
            group_name,
            load_dataset,
        )
        if lesson_error:
            return (
                render_template(
                    "not_found.html",
                    message=lesson_error,
                ),
                503,
            )

        homework_grades = payload.get("homeworkGrades", [])
        if not isinstance(homework_grades, list):
            homework_grades = []

        grade_by_lesson = {}
        topic_by_lesson = {}
        date_by_lesson = {}
        for item in homework_grades:
            if not isinstance(item, dict):
                continue

            lesson_number = str(item.get("lesson", "")).strip()
            if not lesson_number:
                continue

            raw_score = item.get("score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(score):
                continue

            grade_by_lesson[lesson_number] = max(0, min(9, round_grade_half_up(score)))

            lesson_topic = str(item.get("topic", "")).strip()
            if lesson_topic:
                topic_by_lesson[lesson_number] = lesson_topic

            lesson_date = str(item.get("date", "")).strip()
            if lesson_date:
                date_by_lesson[lesson_number] = lesson_date

        if not lesson_catalog:
            lesson_catalog = []
            seen = set()
            for index, lesson_number in enumerate(grade_by_lesson.keys(), start=1):
                dedupe_key = lesson_number.casefold()
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                lesson_catalog.append(
                    {
                        "lesson_number": lesson_number,
                        "lesson_topic": topic_by_lesson.get(lesson_number, ""),
                        "lesson_date": date_by_lesson.get(lesson_number, ""),
                        "lesson_order": index,
                    }
                )

        lesson_rows = []
        for lesson in lesson_catalog:
            lesson_number = str(lesson.get("lesson_number", "")).strip()
            lesson_topic = str(lesson.get("lesson_topic", "")).strip()
            lesson_date = str(lesson.get("lesson_date", "")).strip()
            if not lesson_number:
                continue
            if not lesson_date:
                lesson_date = str(date_by_lesson.get(lesson_number, "")).strip()

            lesson_score = grade_by_lesson.get(lesson_number)
            remark, remark_class = _extract_aap_remark(lesson_score)
            progress_width = (
                int(round((int(lesson_score) / 9) * 100))
                if lesson_score is not None
                else 0
            )
            lesson_rows.append(
                {
                    "lesson_number": lesson_number,
                    "lesson_topic": lesson_topic or "Topic unavailable",
                    "lesson_date_display": lesson_date or "Not conducted",
                    "aap_score": lesson_score,
                    "aap_display": (
                        f"{int(lesson_score)}/9"
                        if lesson_score is not None
                        else "N/A"
                    ),
                    "progress_width": max(0, min(progress_width, 100)),
                    "remark": remark,
                    "remark_class": remark_class,
                }
            )

        back_url = url_for(
            "dashboard",
            student_id=student_id,
            subject=requested_subject or subject_name,
            group=requested_group or group_name,
        )

        return render_template(
            "aap_lessons.html",
            student_id=student_id,
            student_full_name=full_name,
            subject_name=subject_name,
            lesson_rows=lesson_rows,
            back_url=back_url,
        )

    @app.get("/api/students/<int:student_id>/dashboard")
    def api_student_dashboard(student_id):
        # Raw dashboard payload for API consumers.
        dataset, load_error = load_dataset()
        if load_error or not dataset:
            return jsonify(
                {"message": load_error or "Unable to load Google Sheets data."}
            ), 503

        payload = dataset["dashboards_by_id"].get(student_id)
        if not payload:
            return jsonify({"message": "Student not found"}), 404

        if _current_auth_role() == "student" and not _is_student_owner_of_payload(
            student_id, payload
        ):
            if not _current_student_sheet_id() and not _current_student_full_name():
                return jsonify({"message": "Student session is invalid."}), 401
            return jsonify({"message": "Access denied."}), 403

        return jsonify(payload)
