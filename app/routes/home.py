import os
import re
from datetime import datetime

from flask import render_template, request, session, url_for

try:
    from ..services.auth_service import (
        assign_teacher_to_group,
        change_student_password,
        delete_teacher_by_id,
        detect_login_role,
        get_admin_student_profile,
        get_bot_users_count,
        get_student_by_telegram_user_id,
        link_admin_telegram_user,
        get_teacher_by_id,
        link_student_telegram_user,
        list_students_for_admin,
        list_teachers,
        unlink_student_telegram_user,
        sync_students_if_needed,
        update_teacher_by_id,
        update_student_admin_profile,
        upsert_teacher,
        verify_admin_credentials,
        verify_student_credentials,
    )
except ImportError:
    from services.auth_service import (
        assign_teacher_to_group,
        change_student_password,
        delete_teacher_by_id,
        detect_login_role,
        get_admin_student_profile,
        get_bot_users_count,
        get_student_by_telegram_user_id,
        link_admin_telegram_user,
        get_teacher_by_id,
        link_student_telegram_user,
        list_students_for_admin,
        list_teachers,
        unlink_student_telegram_user,
        sync_students_if_needed,
        update_teacher_by_id,
        update_student_admin_profile,
        upsert_teacher,
        verify_admin_credentials,
        verify_student_credentials,
    )

try:
    from .admin.admins import register_admin_routes
    from .students.students import register_student_routes
except ImportError:
    from admin.admins import register_admin_routes
    from students.students import register_student_routes

try:
    from ..config.schools import get_configured_school_spreadsheets
except ImportError:
    from app.config.schools import get_configured_school_spreadsheets

try:
    from ..services.subject_summary_service import (
        list_subject_summaries,
        sync_subject_summaries_if_needed,
    )
except ImportError:
    from services.subject_summary_service import (
        list_subject_summaries,
        sync_subject_summaries_if_needed,
    )

try:
    from ..services.resources_service import (
        create_resource,
        create_resource_type,
        delete_resource,
        delete_resource_type,
        is_resource_upload_enabled,
        list_resource_subject_names,
        list_resource_types,
        list_resources,
        normalize_subject_name,
    )
except ImportError:
    from services.resources_service import (
        create_resource,
        create_resource_type,
        delete_resource,
        delete_resource_type,
        is_resource_upload_enabled,
        list_resource_subject_names,
        list_resource_types,
        list_resources,
        normalize_subject_name,
    )

try:
    from ..services.r2_storage_service import upload_resource_file
except ImportError:
    from services.r2_storage_service import upload_resource_file


def register_home_routes(
    app,
    *,
    load_dataset,
    seed_group_cache_from_dataset,
    build_students_by_subject_group,
    empty_form_data,
    is_full_form,
    get_group_cache_entry,
    search_student,
):
    configured_school_codes = set(get_configured_school_spreadsheets().keys())
    school_option_catalog = {
        "school5": "School 5",
        "sehriyo": "Sehriyo",
    }
    ordered_school_codes = [
        code
        for code in ("school5", "sehriyo")
        if code in configured_school_codes
    ]
    if not ordered_school_codes:
        ordered_school_codes = ["school5"]

    admin_school_options = [{"code": "all", "label": "All Schools"}] + [
        {"code": code, "label": school_option_catalog.get(code, code.title())}
        for code in ordered_school_codes
    ]
    available_school_codes = [
        option["code"]
        for option in admin_school_options
        if option["code"] != "all"
    ]

    def _current_auth_role():
        role = str(session.get("auth_role", "")).strip().lower()
        if role in {"admin", "student"}:
            return role
        return ""

    def _current_auth_login():
        return str(session.get("auth_login", "")).strip()

    def _normalize_admin_school_filter(value):
        normalized = str(value or "all").strip().casefold()
        allowed_codes = {option["code"] for option in admin_school_options}
        if normalized in allowed_codes:
            return normalized
        return "all"

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

    def _parse_telegram_user_id(raw_value):
        try:
            parsed = int(str(raw_value).strip())
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        return parsed

    def _set_admin_session(admin):
        session.clear()
        session["auth_role"] = "admin"
        session["auth_login"] = str(admin.get("login", "")).strip()
        session["admin_id"] = int(admin["id"])
        session["admin_is_owner"] = bool(admin.get("is_owner"))
        session["admin_last_panel"] = "overview"
        session["admin_last_school"] = "all"
        session.permanent = True

    def _set_student_session(student, telegram_user_id):
        if not isinstance(student, dict):
            return False
        try:
            student_db_id = int(student["id"])
            sheet_student_id = int(student["sheet_student_id"])
        except (KeyError, TypeError, ValueError):
            return False

        if student_db_id <= 0 or sheet_student_id <= 0:
            return False

        session.clear()
        session["auth_role"] = "student"
        session["auth_login"] = str(student.get("student_id", "")).strip()
        session["student_db_id"] = student_db_id
        session["student_id"] = str(student.get("student_id", "")).strip()
        session["student_sheet_id"] = sheet_student_id
        session["student_full_name"] = str(student.get("full_name", "")).strip()
        student_school_code = str(student.get("school_code", "")).strip().casefold()
        if student_school_code:
            session["student_school_code"] = student_school_code
        session["telegram_user_id"] = telegram_user_id
        session.permanent = True
        return True

    def _try_auto_login_student_by_telegram(telegram_user_id):
        if not isinstance(telegram_user_id, int) or telegram_user_id <= 0:
            return False

        student = get_student_by_telegram_user_id(telegram_user_id)
        if not student:
            return False
        return _set_student_session(student, telegram_user_id)

    def _build_dashboard_url(student_sheet_id, subject="", group="", **extra_params):
        route_params = {
            "student_id": int(student_sheet_id),
        }
        normalized_subject = str(subject or "").strip()
        normalized_group = str(group or "").strip()
        normalized_school = str(extra_params.pop("school", "")).strip().casefold()
        if not normalized_school:
            normalized_school = str(session.get("student_school_code", "")).strip().casefold()
        if normalized_subject:
            route_params["subject"] = normalized_subject
        if normalized_group:
            route_params["group"] = normalized_group
        if normalized_school:
            route_params["school"] = normalized_school
        for key, value in extra_params.items():
            if str(value or "").strip():
                route_params[key] = str(value).strip()
        return url_for("dashboard", **route_params)

    def _delete_uploaded_student_photo(photo_url):
        raw_url = str(photo_url or "").strip()
        if not raw_url:
            return
        expected_prefix = "/static/uploads/student_photos/"
        if not raw_url.startswith(expected_prefix):
            return
        file_name = os.path.basename(raw_url)
        if not file_name:
            return
        static_root = app.static_folder or os.path.join(app.root_path, "web", "static")
        uploads_dir = os.path.join(static_root, "uploads", "student_photos")
        candidate_path = os.path.join(uploads_dir, file_name)
        if os.path.isfile(candidate_path):
            try:
                os.remove(candidate_path)
            except OSError:
                return

    def _normalize_text(value):
        return " ".join(str(value or "").strip().casefold().split())

    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _should_force_refresh():
        return False

    def _merge_admin_datasets(datasets):
        merged_students = []
        merged_dashboards_by_id = {}
        groups_set = set()
        subjects_set = set()
        groups_by_subject_sets = {}

        for dataset in datasets:
            if not isinstance(dataset, dict):
                continue

            dataset_students = dataset.get("students", [])
            if isinstance(dataset_students, list):
                merged_students.extend(
                    student for student in dataset_students if isinstance(student, dict)
                )

            dataset_dashboards = dataset.get("dashboards_by_id", {})
            if isinstance(dataset_dashboards, dict):
                merged_dashboards_by_id.update(dataset_dashboards)

            dataset_groups = dataset.get("groups", [])
            if isinstance(dataset_groups, list):
                for group_name in dataset_groups:
                    normalized_group = str(group_name or "").strip()
                    if normalized_group:
                        groups_set.add(normalized_group)

            dataset_subjects = dataset.get("subjects", [])
            if isinstance(dataset_subjects, list):
                for subject_name in dataset_subjects:
                    normalized_subject = str(subject_name or "").strip()
                    if normalized_subject:
                        subjects_set.add(normalized_subject)

            dataset_groups_by_subject = dataset.get("groups_by_subject", {})
            if isinstance(dataset_groups_by_subject, dict):
                for subject_name, groups in dataset_groups_by_subject.items():
                    normalized_subject = str(subject_name or "").strip()
                    if not normalized_subject:
                        continue
                    target_groups = groups_by_subject_sets.setdefault(
                        normalized_subject, set()
                    )
                    if isinstance(groups, list):
                        for group_name in groups:
                            normalized_group = str(group_name or "").strip()
                            if normalized_group:
                                target_groups.add(normalized_group)

        return {
            "students": merged_students,
            "dashboards_by_id": merged_dashboards_by_id,
            "groups": sorted(groups_set, key=lambda value: value.casefold()),
            "subjects": sorted(subjects_set, key=lambda value: value.casefold()),
            "groups_by_subject": {
                subject_name: sorted(group_set, key=lambda value: value.casefold())
                for subject_name, group_set in sorted(
                    groups_by_subject_sets.items(),
                    key=lambda item: str(item[0]).casefold(),
                )
            },
        }

    def _load_admin_dataset_for_filter(school_filter, force_refresh = False):
        selected_school_codes = (
            available_school_codes
            if school_filter == "all"
            else [school_filter]
        )
        loaded_datasets = []
        first_load_error = ""

        for school_code in selected_school_codes:
            try:
                dataset, load_error = load_dataset(
                    school_code=school_code,
                    force_refresh=force_refresh,
                )
            except TypeError:
                dataset, load_error = load_dataset()

            normalized_load_error = str(load_error or "").strip()
            if normalized_load_error and not first_load_error:
                first_load_error = normalized_load_error

            if dataset:
                loaded_datasets.append(dataset)

        if not loaded_datasets:
            return None, first_load_error or "Unable to load Google Sheets data."

        if len(loaded_datasets) == 1:
            return loaded_datasets[0], first_load_error

        return _merge_admin_datasets(loaded_datasets), first_load_error

    def _average_or_none(values):
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    def _extract_overview_student_metrics(summary_rows):
        metrics = []
        if not isinstance(summary_rows, list):
            return metrics

        for row in summary_rows:
            if not isinstance(row, dict):
                continue

            school_key = str(row.get("school_key", "")).strip().casefold()
            school_name = str(row.get("school_name", "")).strip()
            if not school_name:
                school_name = school_option_catalog.get(school_key, "School")

            average_aap = _safe_float(row.get("aap"))
            if average_aap is not None and average_aap < 0:
                average_aap = None
            attendance_rate = _safe_float(row.get("ar"))
            if attendance_rate is not None and attendance_rate < 0:
                attendance_rate = None

            metrics.append(
                {
                    "school_key": school_key,
                    "school_name": school_name,
                    "full_name": str(row.get("full_name", "")).strip(),
                    "subject": str(row.get("subject_name", "")).strip(),
                    "group": str(row.get("group_name", "")).strip(),
                    "aap": average_aap,
                    "ar": attendance_rate,
                }
            )

        return metrics

    def _build_admin_school_info(metrics):
        buckets = {}
        for item in metrics:
            school_name = str(item.get("school_name", "")).strip() or "School"
            bucket = buckets.setdefault(
                school_name,
                {
                    "students": set(),
                    "subjects": set(),
                    "groups": set(),
                    "aap_values": [],
                    "ar_values": [],
                },
            )
            full_name = str(item.get("full_name", "")).strip()
            subject_name = str(item.get("subject", "")).strip()
            group_name = str(item.get("group", "")).strip()
            if full_name:
                bucket["students"].add(full_name)
            if subject_name:
                bucket["subjects"].add(subject_name)
            if group_name:
                bucket["groups"].add(group_name)

            aap = item.get("aap")
            if aap is not None and aap > 0:
                bucket["aap_values"].append(float(aap))
            ar = item.get("ar")
            if ar is not None:
                bucket["ar_values"].append(float(ar))

        info_rows = []
        for school_name, bucket in buckets.items():
            info_rows.append(
                {
                    "school_name": school_name,
                    "total_students": len(bucket["students"]),
                    "total_subjects": len(bucket["subjects"]),
                    "total_groups": len(bucket["groups"]),
                    "avg_aap": _average_or_none(bucket["aap_values"]),
                    "avg_ar": _average_or_none(bucket["ar_values"]),
                }
            )

        info_rows.sort(key=lambda row: str(row.get("school_name", "")).casefold())
        return info_rows

    def _build_admin_group_highlights(metrics):
        group_buckets = {}
        for item in metrics:
            school_name = str(item.get("school_name", "")).strip() or "School"
            group_name = str(item.get("group", "")).strip()
            if not group_name:
                continue

            key = (school_name, group_name)
            bucket = group_buckets.setdefault(
                key,
                {
                    "school_name": school_name,
                    "group_name": group_name,
                    "students": set(),
                    "aap_values": [],
                    "ar_values": [],
                },
            )
            full_name = str(item.get("full_name", "")).strip()
            if full_name:
                bucket["students"].add(full_name)

            aap = item.get("aap")
            if aap is not None and aap > 0:
                bucket["aap_values"].append(float(aap))
            ar = item.get("ar")
            if ar is not None:
                bucket["ar_values"].append(float(ar))

        summary_rows = []
        for bucket in group_buckets.values():
            summary_rows.append(
                {
                    "school_name": bucket["school_name"],
                    "group_name": bucket["group_name"],
                    "students_count": len(bucket["students"]),
                    "avg_aap": _average_or_none(bucket["aap_values"]),
                    "avg_ar": _average_or_none(bucket["ar_values"]),
                }
            )

        top_aap = [
            row
            for row in summary_rows
            if row.get("avg_aap") is not None
        ]
        top_aap.sort(
            key=lambda row: (
                -float(row.get("avg_aap", 0)),
                -float(row.get("avg_ar") or 0),
                _normalize_text(row.get("group_name", "")),
            )
        )

        top_ar = [
            row
            for row in summary_rows
            if row.get("avg_ar") is not None
        ]
        top_ar.sort(
            key=lambda row: (
                -float(row.get("avg_ar", 0)),
                -float(row.get("avg_aap") or 0),
                _normalize_text(row.get("group_name", "")),
            )
        )

        return {
            "top_aap": top_aap[:8],
            "top_ar": top_ar[:8],
        }

    def _build_admin_group_zones(metrics):
        grouped_rows = {}
        for item in metrics:
            school_name = str(item.get("school_name", "")).strip() or "School"
            subject_name = str(item.get("subject", "")).strip()
            group_name = str(item.get("group", "")).strip()
            if not subject_name or not group_name:
                continue

            key = (school_name, subject_name, group_name)
            bucket = grouped_rows.setdefault(
                key,
                {
                    "school_name": school_name,
                    "subject_name": subject_name,
                    "group_name": group_name,
                    "aap_values": [],
                    "ar_values": [],
                },
            )

            aap_value = item.get("aap")
            if aap_value is not None:
                bucket["aap_values"].append(float(aap_value))

            ar_value = item.get("ar")
            if ar_value is not None:
                bucket["ar_values"].append(float(ar_value))

        zone_rows = []
        for bucket in grouped_rows.values():
            avg_aap = _average_or_none(bucket["aap_values"])
            if avg_aap is None:
                continue

            zone_rows.append(
                {
                    "school_name": bucket["school_name"],
                    "subject_name": bucket["subject_name"],
                    "group_name": bucket["group_name"],
                    "aap": avg_aap,
                    "ar": _average_or_none(bucket["ar_values"]),
                }
            )

        zones = {
            "green": [],
            "yellow": [],
            "red": [],
        }
        for row in zone_rows:
            aap_value = float(row.get("aap") or 0)
            if aap_value > 7:
                zones["green"].append(row)
            elif aap_value < 5:
                zones["red"].append(row)
            else:
                zones["yellow"].append(row)

        zones["green"].sort(
            key=lambda row: (
                -float(row.get("aap") or 0),
                -float(row.get("ar") or 0),
                _normalize_text(row.get("school_name", "")),
                _normalize_text(row.get("subject_name", "")),
                _normalize_text(row.get("group_name", "")),
            )
        )
        zones["yellow"].sort(
            key=lambda row: (
                -float(row.get("aap") or 0),
                -float(row.get("ar") or 0),
                _normalize_text(row.get("school_name", "")),
                _normalize_text(row.get("subject_name", "")),
                _normalize_text(row.get("group_name", "")),
            )
        )
        zones["red"].sort(
            key=lambda row: (
                float(row.get("aap") or 0),
                float(row.get("ar") or 0),
                _normalize_text(row.get("school_name", "")),
                _normalize_text(row.get("subject_name", "")),
                _normalize_text(row.get("group_name", "")),
            )
        )
        return zones

    def _build_admin_subject_info(metrics, dataset = None):
        def _normalize_school_key(raw_value, school_name = ""):
            normalized = _normalize_text(raw_value)
            if normalized in {"school_5", "school-5", "school 5", "school5"}:
                return "school5"
            if normalized in {"sehriyo", "sehriyo school"}:
                return "sehriyo"

            normalized_school_name = _normalize_text(school_name)
            if normalized_school_name in {"school 5", "school5"}:
                return "school5"
            if normalized_school_name in {"sehriyo", "sehriyo school"}:
                return "sehriyo"

            return normalized or "school5"

        def _format_group_label(_school_name, group_name):
            return str(group_name or "").strip()

        def _parse_month_key(raw_value):
            normalized = str(raw_value or "").strip()
            if not normalized:
                return ""

            candidates = [normalized]
            if "T" in normalized:
                candidates.append(normalized.split("T", 1)[0])
            if " " in normalized:
                candidates.append(normalized.split(" ", 1)[0])
            if len(normalized) >= 10:
                candidates.append(normalized[:10])

            for candidate in candidates:
                text = str(candidate or "").strip()
                if not text:
                    continue

                for fmt in (
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%d.%m.%Y",
                    "%d/%m/%Y",
                    "%m/%d/%Y",
                    "%d-%m-%Y",
                    "%m-%d-%Y",
                    "%d/%m/%y",
                    "%m/%d/%y",
                    "%d.%m.%y",
                    "%m.%d.%y",
                    "%d-%m-%y",
                    "%m-%d-%y",
                    "%Y-%m",
                    "%Y/%m",
                    "%m.%Y",
                ):
                    try:
                        parsed = datetime.strptime(text, fmt)
                    except ValueError:
                        continue
                    if parsed.year < 2020 or parsed.year > datetime.utcnow().year + 1:
                        continue
                    return f"{parsed.year:04d}-{parsed.month:02d}"

                parts = text.replace("/", "-").split("-")
                if (
                    len(parts) >= 2
                    and parts[0].isdigit()
                    and parts[1].isdigit()
                    and len(parts[0]) == 4
                ):
                    year = int(parts[0])
                    month = int(parts[1])
                    if 1 <= month <= 12 and 2020 <= year <= datetime.utcnow().year + 1:
                        return f"{year:04d}-{month:02d}"

                short_parts = re.split(r"[./-]", text)
                if (
                    len(short_parts) == 2
                    and short_parts[0].isdigit()
                    and short_parts[1].isdigit()
                ):
                    first = int(short_parts[0])
                    second = int(short_parts[1])
                    inferred_month = None

                    # Most sheets store dates as day/month without year (e.g. 11/2).
                    if 1 <= first <= 31 and 1 <= second <= 12:
                        inferred_month = second
                    elif 1 <= first <= 12 and 1 <= second <= 31:
                        inferred_month = first

                    if inferred_month is not None:
                        now_utc = datetime.utcnow()
                        inferred_year = int(now_utc.year)
                        # If month is far ahead of current month, treat it as previous school year.
                        if inferred_month > now_utc.month + 1:
                            inferred_year -= 1
                        return f"{inferred_year:04d}-{inferred_month:02d}"

            return ""

        def _month_range(start_key, end_key):
            if not start_key or not end_key:
                return []

            try:
                start_year, start_month = [int(part) for part in start_key.split("-", 1)]
                end_year, end_month = [int(part) for part in end_key.split("-", 1)]
            except (TypeError, ValueError):
                return []

            if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
                return []

            if (start_year, start_month) > (end_year, end_month):
                return [start_key]

            months = []
            year = start_year
            month = start_month
            while (year, month) <= (end_year, end_month):
                months.append(f"{year:04d}-{month:02d}")
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            return months

        subject_monthly_scores = {}
        if isinstance(dataset, dict):
            dashboards = dataset.get("dashboards_by_id", {})
            if isinstance(dashboards, dict):
                for payload in dashboards.values():
                    if not isinstance(payload, dict):
                        continue

                    student = payload.get("student", {})
                    if not isinstance(student, dict):
                        continue

                    subject_name = str(student.get("subject", "")).strip()
                    group_name = str(student.get("group", "")).strip()
                    if not subject_name or not group_name:
                        continue

                    school_name = str(student.get("schoolName", "")).strip()
                    school_key = _normalize_school_key(student.get("schoolCode", ""), school_name)
                    if not school_name:
                        school_name = school_option_catalog.get(school_key, "School")

                    subject_key = (school_key, subject_name)
                    group_key = str(group_name).strip()
                    homework_grades = payload.get("homeworkGrades", [])
                    if not isinstance(homework_grades, list):
                        continue

                    for lesson in homework_grades:
                        if not isinstance(lesson, dict):
                            continue

                        score = _safe_float(lesson.get("score"))
                        if score is None or score <= 0:
                            continue

                        month_key = _parse_month_key(lesson.get("date"))
                        if not month_key:
                            continue

                        subject_bucket = subject_monthly_scores.setdefault(subject_key, {})
                        group_bucket = subject_bucket.setdefault(group_key, {})
                        group_bucket.setdefault(month_key, []).append(float(score))

        current_utc = datetime.utcnow()
        current_month_key = f"{current_utc.year:04d}-{current_utc.month:02d}"

        subject_buckets = {}
        for item in metrics:
            subject_name = str(item.get("subject", "")).strip()
            if not subject_name:
                continue

            school_name = str(item.get("school_name", "")).strip()
            school_key = _normalize_school_key(item.get("school_key", ""), school_name)
            if not school_name:
                school_name = school_option_catalog.get(school_key, "School")

            group_name = str(item.get("group", "")).strip()
            full_name = str(item.get("full_name", "")).strip()

            bucket_key = (school_key, school_name, subject_name)
            bucket = subject_buckets.setdefault(
                bucket_key,
                {
                    "students": set(),
                    "groups": {},
                    "aap_values": [],
                    "ar_values": [],
                },
            )
            if full_name:
                bucket["students"].add(full_name)

            aap = item.get("aap")
            if aap is not None and aap > 0:
                bucket["aap_values"].append(float(aap))

            ar = item.get("ar")
            if ar is not None:
                bucket["ar_values"].append(float(ar))

            if not group_name:
                continue

            group_bucket = bucket["groups"].setdefault(
                group_name,
                {
                    "group_name": group_name,
                    "students": set(),
                    "aap_values": [],
                    "ar_values": [],
                },
            )
            if full_name:
                group_bucket["students"].add(full_name)

            if aap is not None and aap > 0:
                group_bucket["aap_values"].append(float(aap))

            if ar is not None:
                group_bucket["ar_values"].append(float(ar))

        rows = []
        for bucket_key, bucket in subject_buckets.items():
            school_key, school_name, subject_name = bucket_key
            group_rows = []
            for group_bucket in bucket["groups"].values():
                group_name = str(group_bucket.get("group_name", "")).strip()
                label = _format_group_label(school_name, group_name)
                if not label:
                    continue
                group_rows.append(
                    {
                        "label": label,
                        "students_count": len(group_bucket["students"]),
                        "avg_aap": _average_or_none(group_bucket["aap_values"]),
                        "avg_ar": _average_or_none(group_bucket["ar_values"]),
                    }
                )

            group_rows.sort(key=lambda row: _normalize_text(row.get("label", "")))
            monthly_subject_bucket = subject_monthly_scores.get((school_key, subject_name), {})
            month_keys = sorted(
                {
                    month_key
                    for group_scores in monthly_subject_bucket.values()
                    for month_key in group_scores.keys()
                }
            )
            month_range = _month_range(month_keys[0], current_month_key) if month_keys else []
            monthly_series = []
            for group_name, month_scores in monthly_subject_bucket.items():
                label = _format_group_label(school_name, group_name)
                if not label:
                    continue

                values = []
                has_value = False
                for month_key in month_range:
                    month_values = month_scores.get(month_key, [])
                    if month_values:
                        values.append(round(sum(month_values) / len(month_values), 1))
                        has_value = True
                    else:
                        values.append(None)

                if has_value:
                    monthly_series.append(
                        {
                            "label": label,
                            "values": values,
                        }
                    )

            monthly_series.sort(key=lambda row: _normalize_text(row.get("label", "")))

            # Fallback for sheets where lesson-level dates are missing or not parseable:
            # render a current-month snapshot using group average AAP so chart is never empty.
            if (not month_range or not monthly_series) and group_rows:
                snapshot_series = []
                for group_row in group_rows:
                    label = str(group_row.get("label", "")).strip()
                    if not label:
                        continue
                    avg_aap_value = _safe_float(group_row.get("avg_aap"))
                    if avg_aap_value is None or avg_aap_value <= 0:
                        continue
                    snapshot_series.append(
                        {
                            "label": label,
                            "values": [round(float(avg_aap_value), 1)],
                        }
                    )

                if snapshot_series:
                    month_range = [current_month_key]
                    monthly_series = sorted(
                        snapshot_series,
                        key=lambda row: _normalize_text(row.get("label", "")),
                    )

            rows.append(
                {
                    "school_key": school_key,
                    "school_name": school_name,
                    "subject_name": subject_name,
                    "students_count": len(bucket["students"]),
                    "groups_count": len(group_rows),
                    "avg_aap": _average_or_none(bucket["aap_values"]),
                    "avg_ar": _average_or_none(bucket["ar_values"]),
                    "groups": group_rows,
                    "monthly_months": month_range,
                    "monthly_series": monthly_series,
                }
            )

        rows.sort(
            key=lambda row: (
                _normalize_text(row.get("school_name", "")),
                _normalize_text(row.get("subject_name", "")),
            )
        )
        return rows

    def _build_admin_student_ratings(metrics):
        student_buckets = {}
        for item in metrics:
            school_name = str(item.get("school_name", "")).strip() or "School"
            full_name = str(item.get("full_name", "")).strip()
            if not full_name:
                continue

            key = (school_name, full_name)
            bucket = student_buckets.setdefault(
                key,
                {
                    "school_name": school_name,
                    "full_name": full_name,
                    "groups": set(),
                    "subjects": set(),
                    "aap_values": [],
                    "ar_values": [],
                },
            )

            group_name = str(item.get("group", "")).strip()
            subject_name = str(item.get("subject", "")).strip()
            if group_name:
                bucket["groups"].add(group_name)
            if subject_name:
                bucket["subjects"].add(subject_name)

            aap = item.get("aap")
            if aap is not None and aap > 0:
                bucket["aap_values"].append(float(aap))
            ar = item.get("ar")
            if ar is not None:
                bucket["ar_values"].append(float(ar))

        aggregated = []
        for bucket in student_buckets.values():
            avg_aap = _average_or_none(bucket["aap_values"])
            avg_ar = _average_or_none(bucket["ar_values"])
            if avg_aap is None and avg_ar is None:
                continue
            groups = sorted(bucket["groups"], key=lambda value: value.casefold())
            aggregated.append(
                {
                    "school_name": bucket["school_name"],
                    "full_name": bucket["full_name"],
                    "groups": groups,
                    "groups_label": ", ".join(groups[:2]),
                    "avg_aap": avg_aap,
                    "avg_ar": avg_ar,
                }
            )

        aggregated.sort(
            key=lambda row: (
                -float(row.get("avg_aap") or 0),
                -float(row.get("avg_ar") or 0),
                _normalize_text(row.get("full_name", "")),
            )
        )

        global_rating = []
        for index, row in enumerate(aggregated[:10], start=1):
            global_rating.append(
                {
                    "rank": index,
                    "school_name": row["school_name"],
                    "full_name": row["full_name"],
                    "groups_label": row["groups_label"],
                    "avg_aap": row.get("avg_aap"),
                    "avg_ar": row.get("avg_ar"),
                }
            )

        local_rating = []
        rows_by_school = {}
        for row in aggregated:
            rows_by_school.setdefault(row["school_name"], []).append(row)

        for school_name in sorted(rows_by_school.keys(), key=lambda value: value.casefold()):
            school_rows = rows_by_school[school_name]
            top_rows = []
            for local_rank, row in enumerate(school_rows[:5], start=1):
                top_rows.append(
                    {
                        "local_rank": local_rank,
                        "full_name": row["full_name"],
                        "groups_label": row["groups_label"],
                        "avg_aap": row.get("avg_aap"),
                        "avg_ar": row.get("avg_ar"),
                    }
                )
            local_rating.append(
                {
                    "school_name": school_name,
                    "students": top_rows,
                }
            )

        return {
            "global": global_rating,
            "local": local_rating,
            "aggregated": aggregated,
        }

    def _build_admin_attention(student_ratings, dataset, admin_teachers):
        low_aap = []
        low_ar = []
        groups_without_teacher = []
        aap_threshold = 5.0
        ar_threshold = 70.0

        aggregated_rows = (
            student_ratings.get("aggregated", [])
            if isinstance(student_ratings, dict)
            else []
        )
        for row in aggregated_rows:
            if not isinstance(row, dict):
                continue

            avg_aap = row.get("avg_aap")
            avg_ar = row.get("avg_ar")
            entry_base = {
                "school_name": row.get("school_name", ""),
                "full_name": row.get("full_name", ""),
                "groups_label": row.get("groups_label", ""),
            }
            if avg_aap is not None and 0 < float(avg_aap) < aap_threshold:
                low_aap.append(
                    {
                        **entry_base,
                        "value": round(float(avg_aap), 1),
                    }
                )
            if avg_ar is not None and float(avg_ar) < ar_threshold:
                low_ar.append(
                    {
                        **entry_base,
                        "value": round(float(avg_ar), 1),
                    }
                )

        low_aap.sort(
            key=lambda row: (
                float(row.get("value", 0)),
                _normalize_text(row.get("full_name", "")),
            )
        )
        low_ar.sort(
            key=lambda row: (
                float(row.get("value", 0)),
                _normalize_text(row.get("full_name", "")),
            )
        )

        teacher_groups = {
            _normalize_text(row.get("assigned_group", ""))
            for row in admin_teachers
            if isinstance(row, dict) and str(row.get("assigned_group", "")).strip()
        }
        group_pairs = set()
        dataset_students = dataset.get("students", []) if isinstance(dataset, dict) else []
        if isinstance(dataset_students, list):
            for student_row in dataset_students:
                if not isinstance(student_row, dict):
                    continue
                group_name = str(student_row.get("group", "")).strip()
                if not group_name:
                    continue
                school_name = str(
                    student_row.get("schoolName")
                    or student_row.get("school_name")
                    or "School"
                ).strip() or "School"
                group_pairs.add((school_name, group_name))

        if not group_pairs:
            for row in aggregated_rows:
                if not isinstance(row, dict):
                    continue
                school_name = str(row.get("school_name", "")).strip() or "School"
                for group_name in row.get("groups", []):
                    normalized_group = str(group_name or "").strip()
                    if normalized_group:
                        group_pairs.add((school_name, normalized_group))

        for school_name, group_name in sorted(
            group_pairs,
            key=lambda item: (
                str(item[0]).casefold(),
                str(item[1]).casefold(),
            ),
        ):
            if _normalize_text(group_name) in teacher_groups:
                continue
            groups_without_teacher.append(f"{group_name} ({school_name})")

        return {
            "low_aap": low_aap[:8],
            "low_ar": low_ar[:8],
            "groups_without_teacher": groups_without_teacher[:8],
        }

    def _build_admin_quick_stats(admin_school_info, admin_teachers, total_subjects):
        total_students = sum(int(row.get("total_students", 0)) for row in admin_school_info)
        school_counts = [
            {
                "school_name": row.get("school_name", ""),
                "count": int(row.get("total_students", 0)),
            }
            for row in admin_school_info
        ]
        return {
            "total_students": int(total_students),
            "total_schools": len(admin_school_info),
            "total_teachers": len(admin_teachers),
            "total_subjects": int(total_subjects),
            "school_counts": school_counts,
        }

    def _build_admin_resource_subject_options(summary_rows, resource_rows):
        subject_priority = {
            "math": 0,
            "english": 1,
            "chemistry": 2,
            "biology": 3,
            "physics": 4,
        }

        subject_map = {}
        if isinstance(summary_rows, list):
            for row in summary_rows:
                if not isinstance(row, dict):
                    continue
                subject_name = normalize_subject_name(row.get("subject_name", ""))
                subject_key = _normalize_text(subject_name)
                if subject_name and subject_key and subject_key not in subject_map:
                    subject_map[subject_key] = subject_name

        if isinstance(resource_rows, list):
            for row in resource_rows:
                if not isinstance(row, dict):
                    continue
                subject_name = normalize_subject_name(row.get("subject_name", ""))
                subject_key = _normalize_text(subject_name)
                if subject_name and subject_key and subject_key not in subject_map:
                    subject_map[subject_key] = subject_name

        for subject_name in list_resource_subject_names():
            normalized_name = normalize_subject_name(subject_name)
            subject_key = _normalize_text(normalized_name)
            if normalized_name and subject_key and subject_key not in subject_map:
                subject_map[subject_key] = normalized_name

        return sorted(
            subject_map.values(),
            key=lambda value: (
                subject_priority.get(_normalize_text(value), 999),
                _normalize_text(value),
            ),
        )

    def _render_login_page(auth_error="", auth_login_input=""):
        return render_template(
            "home.html",
            groups=[],
            groups_by_subject={},
            subjects=[],
            students_by_subject_group={},
            error="",
            form_data=empty_form_data(),
            auth_role="",
            auth_login="",
            auth_error=auth_error,
            auth_login_input=auth_login_input,
            bot_users_count=0,
            admin_students=[],
            admin_panel="overview",
            admin_teachers=[],
            admin_teacher_options=[],
            admin_group_options=[],
            admin_groups=[],
            admin_selected_student=None,
            admin_teacher_edit=None,
            admin_teacher_edit_school="",
            admin_school="all",
            admin_school_options=admin_school_options,
            admin_notice="",
            admin_quick_stats={
                "total_students": 0,
                "total_schools": 0,
                "total_teachers": 0,
                "total_subjects": 0,
                "school_counts": [],
            },
            admin_school_info=[],
            admin_subject_info=[],
            admin_group_highlights={
                "top_aap": [],
                "top_ar": [],
            },
            admin_group_zones={
                "green": [],
                "yellow": [],
                "red": [],
            },
            admin_student_ratings={
                "global": [],
                "local": [],
            },
            admin_attention={
                "low_aap": [],
                "low_ar": [],
                "groups_without_teacher": [],
            },
            admin_sync_statuses=[],
            admin_resource_types=[],
            admin_resource_active_types=[],
            admin_resources=[],
            admin_resource_subject_options=[],
            admin_resource_upload_enabled=False,
        )

    def _render_admin_page(
        auth_error="",
        admin_notice="",
        admin_panel="overview",
        admin_selected_student=None,
        admin_teacher_edit=None,
        admin_school="all",
    ):
        panel = str(admin_panel or "overview").strip().lower()
        if panel not in {"overview", "students", "teachers", "resources"}:
            panel = "overview"

        school_filter = _normalize_admin_school_filter(admin_school)
        if _current_auth_role() == "admin":
            session["admin_last_panel"] = panel
            session["admin_last_school"] = school_filter
        dataset_scope = "all" if panel in {"overview", "teachers"} else school_filter
        force_refresh = _should_force_refresh()
        sync_errors = []
        sync_results_by_code = {}
        should_sync_students = False
        if should_sync_students:
            school_codes_to_sync = (
                available_school_codes
                if dataset_scope == "all"
                else [dataset_scope]
            )
            for school_code in school_codes_to_sync:
                sync_result = sync_students_if_needed(
                    load_dataset,
                    school_code=school_code,
                    force_refresh=force_refresh,
                )
                sync_results_by_code[school_code] = sync_result
                sync_error = str(sync_result.get("error", "")).strip()
                if sync_error:
                    sync_errors.append(sync_error)

        dataset = None
        load_error = ""
        groups = []
        if panel in {"overview", "teachers"}:
            dataset, load_error = _load_admin_dataset_for_filter(
                dataset_scope,
                force_refresh=force_refresh,
            )
            groups = dataset["groups"] if dataset else []

        admin_teachers = list_teachers()
        admin_students = list_students_for_admin(
            school_filter=school_filter if panel == "students" else "all"
        )
        group_school_sets = {}
        dataset_students = dataset.get("students", []) if isinstance(dataset, dict) else []
        if isinstance(dataset_students, list):
            for student_row in dataset_students:
                if not isinstance(student_row, dict):
                    continue
                group_name = str(student_row.get("group", "")).strip()
                if not group_name:
                    continue
                school_code = str(
                    student_row.get("schoolCode")
                    or student_row.get("school_code")
                    or student_row.get("schoolKey")
                    or student_row.get("school_key")
                    or ""
                ).strip().casefold()
                if school_code not in available_school_codes:
                    continue
                group_school_sets.setdefault(group_name, set()).add(school_code)

        if not group_school_sets:
            fallback_school_code = (
                school_filter
                if school_filter in available_school_codes
                else (available_school_codes[0] if len(available_school_codes) == 1 else "")
            )
            if fallback_school_code:
                for group_name in groups:
                    normalized_group = str(group_name or "").strip()
                    if normalized_group:
                        group_school_sets.setdefault(normalized_group, set()).add(
                            fallback_school_code
                        )

        admin_group_options = []
        for group_name in groups:
            normalized_group = str(group_name or "").strip()
            if not normalized_group:
                continue
            school_codes = sorted(
                group_school_sets.get(normalized_group, set()),
                key=lambda value: value.casefold(),
            )
            if not school_codes and school_filter in available_school_codes:
                school_codes = [school_filter]
            elif not school_codes and len(available_school_codes) == 1:
                school_codes = [available_school_codes[0]]
            admin_group_options.append(
                {
                    "name": normalized_group,
                    "school_codes": school_codes,
                }
            )

        teacher_name_to_schools = {}
        for teacher_row in admin_teachers:
            teacher_name = str(teacher_row.get("full_name", "")).strip()
            if not teacher_name:
                continue
            teacher_group = str(teacher_row.get("assigned_group", "")).strip()
            teacher_school_codes = group_school_sets.get(teacher_group, set())
            school_set = teacher_name_to_schools.setdefault(teacher_name, set())
            school_set.update(teacher_school_codes)

        admin_teacher_options = []
        for teacher_name in sorted(teacher_name_to_schools, key=lambda value: value.casefold()):
            school_codes = sorted(
                teacher_name_to_schools.get(teacher_name, set()),
                key=lambda value: value.casefold(),
            )
            if not school_codes and school_filter in available_school_codes:
                school_codes = [school_filter]
            elif not school_codes and len(available_school_codes) == 1:
                school_codes = [available_school_codes[0]]
            admin_teacher_options.append(
                {
                    "name": teacher_name,
                    "school_codes": school_codes,
                }
            )

        admin_teacher_edit_school = ""
        if isinstance(admin_teacher_edit, dict):
            edit_group_name = str(admin_teacher_edit.get("assigned_group", "")).strip()
            edit_group_schools = sorted(
                group_school_sets.get(edit_group_name, set()),
                key=lambda value: value.casefold(),
            )
            if edit_group_schools:
                admin_teacher_edit_school = edit_group_schools[0]
            elif school_filter in available_school_codes:
                admin_teacher_edit_school = school_filter
            elif available_school_codes:
                admin_teacher_edit_school = available_school_codes[0]

        admin_quick_stats = {
            "total_students": 0,
            "total_schools": 0,
            "total_teachers": 0,
            "total_subjects": 0,
            "school_counts": [],
        }
        admin_school_info = []
        admin_subject_info = []
        admin_group_highlights = {
            "top_aap": [],
            "top_ar": [],
        }
        admin_group_zones = {
            "green": [],
            "yellow": [],
            "red": [],
        }
        admin_student_ratings = {
            "global": [],
            "local": [],
        }
        admin_attention = {
            "low_aap": [],
            "low_ar": [],
            "groups_without_teacher": [],
        }
        admin_resource_types = []
        admin_resource_active_types = []
        admin_resources = []
        admin_resource_subject_options = []
        admin_resource_upload_enabled = False
        if panel == "overview":
            def _load_all_schools_dataset(force_refresh = False):
                loaded_dataset, loaded_error = _load_admin_dataset_for_filter(
                    "all",
                    force_refresh=force_refresh,
                )
                if loaded_dataset:
                    return loaded_dataset, ""
                return None, loaded_error

            summary_sync_result = sync_subject_summaries_if_needed(
                _load_all_schools_dataset,
                force_refresh=force_refresh,
            )
            summary_sync_error = str(summary_sync_result.get("error", "")).strip()
            if summary_sync_error:
                sync_errors.append(summary_sync_error)

            summary_rows = list_subject_summaries("all")
            overview_metrics = _extract_overview_student_metrics(summary_rows)
            admin_school_info = _build_admin_school_info(overview_metrics)
            admin_subject_info = _build_admin_subject_info(overview_metrics, dataset)
            admin_group_highlights = _build_admin_group_highlights(overview_metrics)
            admin_group_zones = _build_admin_group_zones(overview_metrics)
            admin_student_ratings = _build_admin_student_ratings(overview_metrics)
            admin_attention = _build_admin_attention(
                admin_student_ratings,
                dataset,
                admin_teachers,
            )
            total_subjects = len(
                {
                    str(item.get("subject", "")).strip().casefold()
                    for item in overview_metrics
                    if str(item.get("subject", "")).strip()
                }
            )
            admin_quick_stats = _build_admin_quick_stats(
                admin_school_info,
                admin_teachers,
                total_subjects,
            )
        elif panel == "resources":
            summary_rows = list_subject_summaries("all")
            admin_resource_types = list_resource_types(include_inactive=True)
            admin_resource_active_types = [
                row for row in admin_resource_types if bool(row.get("is_active"))
            ]
            admin_resources = list_resources(include_inactive=True)
            admin_resource_subject_options = _build_admin_resource_subject_options(
                summary_rows,
                admin_resources,
            )
            admin_resource_upload_enabled = is_resource_upload_enabled()
        admin_sync_statuses = []
        for school_code in available_school_codes:
            school_label = school_option_catalog.get(school_code, school_code.title())
            sync_result = sync_results_by_code.get(school_code)
            if not sync_result:
                admin_sync_statuses.append(
                    {
                        "school_code": school_code,
                        "school_label": school_label,
                        "status_text": "Not refreshed in this view",
                        "is_error": False,
                    }
                )
                continue

            sync_error = str(sync_result.get("error", "")).strip()
            if sync_error:
                admin_sync_statuses.append(
                    {
                        "school_code": school_code,
                        "school_label": school_label,
                        "status_text": sync_error,
                        "is_error": True,
                    }
                )
                continue

            if sync_result.get("synced"):
                status_text = "Synced now"
            else:
                status_text = "Already up to date"
            added = int(sync_result.get("added", 0))
            updated = int(sync_result.get("updated", 0))
            status_text = f"{status_text}: +{added} new, {updated} updated"
            admin_sync_statuses.append(
                {
                    "school_code": school_code,
                    "school_label": school_label,
                    "status_text": status_text,
                    "is_error": False,
                }
            )

        return render_template(
            "home.html",
            groups=[],
            groups_by_subject={},
            subjects=[],
            students_by_subject_group={},
            error="",
            form_data=empty_form_data(),
            auth_role="admin",
            auth_login=_current_auth_login(),
            auth_error=auth_error or (sync_errors[0] if sync_errors else ""),
            auth_login_input="",
            bot_users_count=get_bot_users_count(),
            admin_students=admin_students,
            admin_panel=panel,
            admin_teachers=admin_teachers,
            admin_teacher_options=admin_teacher_options,
            admin_group_options=admin_group_options,
            admin_groups=groups,
            admin_selected_student=admin_selected_student,
            admin_teacher_edit=admin_teacher_edit,
            admin_teacher_edit_school=admin_teacher_edit_school,
            admin_school=school_filter,
            admin_school_options=admin_school_options,
            admin_notice=admin_notice or load_error or "",
            admin_quick_stats=admin_quick_stats,
            admin_school_info=admin_school_info,
            admin_subject_info=admin_subject_info,
            admin_group_highlights=admin_group_highlights,
            admin_group_zones=admin_group_zones,
            admin_student_ratings=admin_student_ratings,
            admin_attention=admin_attention,
            admin_sync_statuses=admin_sync_statuses,
            admin_resource_types=admin_resource_types,
            admin_resource_active_types=admin_resource_active_types,
            admin_resources=admin_resources,
            admin_resource_subject_options=admin_resource_subject_options,
            admin_resource_upload_enabled=admin_resource_upload_enabled,
        )

    def _render_edit_student_page(student_row_id, auth_error="", admin_notice=""):
        selected_student = get_admin_student_profile(student_row_id, load_dataset)
        if not selected_student:
            return None

        teacher_rows = list_teachers()
        teacher_name_options = sorted(
            {
                str(row.get("full_name", "")).strip()
                for row in teacher_rows
                if str(row.get("full_name", "")).strip()
            },
            key=lambda value: value.casefold(),
        )

        return render_template(
            "admin/edit_student_profile.html",
            auth_login=_current_auth_login(),
            auth_error=auth_error,
            admin_notice=admin_notice,
            student=selected_student,
            teacher_name_options=teacher_name_options,
        )

    def _render_student_panel(form_data, panel_error=""):
        force_refresh = _should_force_refresh()
        student_school_code = str(session.get("student_school_code", "")).strip().casefold()
        if student_school_code in {"school_5", "school-5", "school 5", "school5"}:
            student_school_code = "school5"
        elif student_school_code in {"sehriyo", "sehriyo school"}:
            student_school_code = "sehriyo"
        else:
            student_school_code = ""
        try:
            if student_school_code:
                dataset, load_error = load_dataset(
                    school_code=student_school_code,
                    force_refresh=force_refresh,
                )
            else:
                dataset, load_error = load_dataset(force_refresh=force_refresh)
        except TypeError:
            if student_school_code:
                dataset, load_error = load_dataset(school_code=student_school_code)
            else:
                dataset, load_error = load_dataset()
        groups = dataset["groups"] if dataset else []
        groups_by_subject = dataset["groups_by_subject"] if dataset else {}
        subjects = dataset["subjects"] if dataset else []

        if dataset:
            seed_group_cache_from_dataset(dataset)

        students_by_subject_group = (
            build_students_by_subject_group(dataset["students"]) if dataset else {}
        )

        return render_template(
            "home.html",
            groups=groups,
            groups_by_subject=groups_by_subject,
            subjects=subjects,
            students_by_subject_group=students_by_subject_group,
            error=panel_error or load_error or "",
            form_data=form_data,
            auth_role="student",
            auth_login=_current_auth_login(),
            auth_error="",
            auth_login_input="",
            bot_users_count=0,
            admin_students=[],
            admin_panel="overview",
            admin_teachers=[],
            admin_teacher_options=[],
            admin_group_options=[],
            admin_groups=[],
            admin_selected_student=None,
            admin_teacher_edit=None,
            admin_teacher_edit_school="",
            admin_school="all",
            admin_school_options=admin_school_options,
            admin_notice="",
            admin_quick_stats={
                "total_students": 0,
                "total_schools": 0,
                "total_teachers": 0,
                "total_subjects": 0,
                "school_counts": [],
            },
            admin_school_info=[],
            admin_subject_info=[],
            admin_group_highlights={
                "top_aap": [],
                "top_ar": [],
            },
            admin_group_zones={
                "green": [],
                "yellow": [],
                "red": [],
            },
            admin_student_ratings={
                "global": [],
                "local": [],
            },
            admin_attention={
                "low_aap": [],
                "low_ar": [],
                "groups_without_teacher": [],
            },
            admin_sync_statuses=[],
            admin_resource_types=[],
            admin_resource_active_types=[],
            admin_resources=[],
            admin_resource_subject_options=[],
            admin_resource_upload_enabled=False,
        )

    register_admin_routes(
        app,
        current_auth_role=_current_auth_role,
        render_admin_page=_render_admin_page,
        render_edit_student_page=_render_edit_student_page,
        delete_uploaded_student_photo=_delete_uploaded_student_photo,
        load_dataset=load_dataset,
        get_admin_student_profile=get_admin_student_profile,
        assign_teacher_to_group=assign_teacher_to_group,
        update_student_admin_profile=update_student_admin_profile,
        list_teachers=list_teachers,
        get_teacher_by_id=get_teacher_by_id,
        update_teacher_by_id=update_teacher_by_id,
        upsert_teacher=upsert_teacher,
        delete_teacher_by_id=delete_teacher_by_id,
        create_resource_type=create_resource_type,
        delete_resource_type=delete_resource_type,
        create_resource=create_resource,
        delete_resource=delete_resource,
        upload_resource_file=upload_resource_file,
    )

    register_student_routes(
        app,
        current_auth_role=_current_auth_role,
        current_student_sheet_id=_current_student_sheet_id,
        current_student_db_id=_current_student_db_id,
        parse_telegram_user_id=_parse_telegram_user_id,
        set_admin_session=_set_admin_session,
        set_student_session=_set_student_session,
        try_auto_login_student_by_telegram=_try_auto_login_student_by_telegram,
        build_dashboard_url=_build_dashboard_url,
        render_login_page=_render_login_page,
        render_admin_page=_render_admin_page,
        get_teacher_by_id=get_teacher_by_id,
        detect_login_role=detect_login_role,
        verify_admin_credentials=verify_admin_credentials,
        verify_student_credentials=verify_student_credentials,
        sync_students_if_needed=sync_students_if_needed,
        load_dataset=load_dataset,
        link_student_telegram_user=link_student_telegram_user,
        link_admin_telegram_user=link_admin_telegram_user,
        change_student_password=change_student_password,
        unlink_student_telegram_user=unlink_student_telegram_user,
        is_full_form=is_full_form,
        render_student_panel=_render_student_panel,
        get_group_cache_entry=get_group_cache_entry,
        build_students_by_subject_group=build_students_by_subject_group,
        search_student=search_student,
    )
