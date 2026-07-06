from __future__ import annotations
import re
from datetime import datetime
from typing import Any

from backend.domains.academics.exam_filters import is_exam_performance_row
from database.academics import canonical

_EXAM_NAME_ALIASES = {
    "half term test 1": "HFT1",
    "half-term test 1": "HFT1",
    "hft1": "HFT1",
    "end of term test 1": "ET1",
    "end-of-term test 1": "ET1",
    "et1": "ET1",
    "half term test 2": "HFT2",
    "half-term test 2": "HFT2",
    "hft2": "HFT2",
    "end of term test 2": "ET2",
    "end-of-term test 2": "ET2",
    "et2": "ET2",
    "half term test 3": "HFT3",
    "half-term test 3": "HFT3",
    "hft3": "HFT3",
    "end of term test 3": "ET3",
    "end-of-term test 3": "ET3",
    "et3": "ET3",
    "half term test 4": "HFT4",
    "half-term test 4": "HFT4",
    "hft4": "HFT4",
}
_EXAM_ORDER = ["HFT1", "ET1", "HFT2", "ET2", "HFT3", "ET3", "HFT4"]


def normalize_text(value):
    return " ".join(str(value or "").strip().casefold().split())


def normalize_exam_name(value):
    label = str(value or "").strip()
    if not label:
        return ""
    compact = re.sub(r"[\s_-]+", "", label).upper()
    if re.fullmatch(r"(HFT|ET)\d+", compact):
        return compact
    return _EXAM_NAME_ALIASES.get(normalize_text(label), label)


def subject_priority_key(subject_name):
    return canonical.subject_sort_key(subject_name)


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def average_or_none(values):
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def extract_overview_student_metrics(summary_rows, school_option_catalog):
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

        average_aap = safe_float(row.get("aap"))
        if average_aap is not None and average_aap < 0:
            average_aap = None
        attendance_rate = safe_float(row.get("ar"))
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


def build_admin_school_info(metrics):
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
                "avg_aap": average_or_none(bucket["aap_values"]),
                "avg_ar": average_or_none(bucket["ar_values"]),
            }
        )

    info_rows.sort(key=lambda row: str(row.get("school_name", "")).casefold())
    return info_rows


def build_admin_group_highlights(metrics):
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
                "avg_aap": average_or_none(bucket["aap_values"]),
                "avg_ar": average_or_none(bucket["ar_values"]),
            }
        )

    top_aap = [row for row in summary_rows if row.get("avg_aap") is not None]
    top_aap.sort(
        key=lambda row: (
            -float(row.get("avg_aap", 0)),
            -float(row.get("avg_ar") or 0),
            normalize_text(row.get("group_name", "")),
        )
    )

    top_ar = [row for row in summary_rows if row.get("avg_ar") is not None]
    top_ar.sort(
        key=lambda row: (
            -float(row.get("avg_ar", 0)),
            -float(row.get("avg_aap") or 0),
            normalize_text(row.get("group_name", "")),
        )
    )

    return {
        "top_aap": top_aap[:8],
        "top_ar": top_ar[:8],
    }


def build_admin_group_zones(metrics):
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
        avg_aap = average_or_none(bucket["aap_values"])
        if avg_aap is None:
            continue

        zone_rows.append(
            {
                "school_name": bucket["school_name"],
                "subject_name": bucket["subject_name"],
                "group_name": bucket["group_name"],
                "aap": avg_aap,
                "ar": average_or_none(bucket["ar_values"]),
            }
        )

    zones = {
        "green": [],
        "yellow": [],
        "red": [],
    }
    for row in zone_rows:
        aap_value = float(row.get("aap") or 0)
        if aap_value >= 7:
            zones["green"].append(row)
        elif aap_value >= 5:
            zones["yellow"].append(row)
        else:
            zones["red"].append(row)

    zones["green"].sort(
        key=lambda row: (
            -float(row.get("aap") or 0),
            -float(row.get("ar") or 0),
            normalize_text(row.get("school_name", "")),
            normalize_text(row.get("subject_name", "")),
            normalize_text(row.get("group_name", "")),
        )
    )
    zones["yellow"].sort(
        key=lambda row: (
            -float(row.get("aap") or 0),
            -float(row.get("ar") or 0),
            normalize_text(row.get("school_name", "")),
            normalize_text(row.get("subject_name", "")),
            normalize_text(row.get("group_name", "")),
        )
    )
    zones["red"].sort(
        key=lambda row: (
            float(row.get("aap") or 0),
            float(row.get("ar") or 0),
            normalize_text(row.get("school_name", "")),
            normalize_text(row.get("subject_name", "")),
            normalize_text(row.get("group_name", "")),
        )
    )
    return zones


def build_admin_subject_info(metrics, dataset = None, school_option_catalog = None):
    school_option_catalog = school_option_catalog or {}

    def normalize_school_key(raw_value, school_name = ""):
        normalized = normalize_text(raw_value)
        if normalized in {"school_5", "school-5", "school 5", "school5"}:
            return "school5"
        if normalized in {"sehriyo", "sehriyo school"}:
            return "sehriyo"

        normalized_school_name = normalize_text(school_name)
        if normalized_school_name in {"school 5", "school5"}:
            return "school5"
        if normalized_school_name in {"sehriyo", "sehriyo school"}:
            return "sehriyo"

        return normalized or "school5"

    def format_group_label(_school_name, group_name):
        return str(group_name or "").strip()

    def parse_month_key(raw_value):
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

                if 1 <= first <= 31 and 1 <= second <= 12:
                    inferred_month = second
                elif 1 <= first <= 12 and 1 <= second <= 31:
                    inferred_month = first

                if inferred_month is not None:
                    now_utc = datetime.utcnow()
                    inferred_year = int(now_utc.year)
                    if inferred_month > now_utc.month + 1:
                        inferred_year -= 1
                    return f"{inferred_year:04d}-{inferred_month:02d}"

        return ""

    def month_range(start_key, end_key):
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

    subject_monthly_scores: dict[tuple[str, str], dict[str, dict[str, list[float]]]] = {}
    subject_exam_scores: dict[tuple[str, str], dict[str, dict[str, list[float]]]] = {}
    # {(school_key, subject_name): {group_name: {month_key: {"present": int, "total": int}}}}
    subject_monthly_ar: dict[tuple[str, str], dict[str, dict[str, dict[str, int]]]] = {}
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
                school_key = normalize_school_key(student.get("schoolCode", ""), school_name)
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

                    score = safe_float(lesson.get("score"))
                    if score is None or score <= 0:
                        continue

                    month_key = parse_month_key(lesson.get("date"))
                    if not month_key:
                        continue

                    subject_bucket = subject_monthly_scores.setdefault(subject_key, {})
                    group_bucket = subject_bucket.setdefault(group_key, {})
                    group_bucket.setdefault(month_key, []).append(float(score))

                exam_results = payload.get("examResults", [])
                if not isinstance(exam_results, list):
                    continue

                student_exam_bests: dict[str, float] = {}
                for exam in exam_results:
                    if not isinstance(exam, dict):
                        continue
                    if not is_exam_performance_row(
                        item_type=exam.get("itemType") or exam.get("item_type") or exam.get("type"),
                        exam_name=exam.get("examName"),
                        label=exam.get("label"),
                        title=exam.get("title") or exam.get("topic") or exam.get("assessment"),
                        attempt=exam.get("attempt"),
                    ):
                        continue
                    score = safe_float(exam.get("score"))
                    if score is None or score <= 0:
                        continue
                    exam_name = normalize_exam_name(exam.get("examName") or exam.get("label"))
                    if not exam_name:
                        continue
                    if exam_name not in student_exam_bests or score > student_exam_bests[exam_name]:
                        student_exam_bests[exam_name] = score

                if student_exam_bests:
                    subject_bucket = subject_exam_scores.setdefault(subject_key, {})
                    group_bucket = subject_bucket.setdefault(group_key, {})
                    for exam_name, best_score in student_exam_bests.items():
                        group_bucket.setdefault(exam_name, []).append(best_score)

                attendance_lessons = payload.get("attendanceLessons", [])
                if isinstance(attendance_lessons, list):
                    for lesson in attendance_lessons:
                        if not isinstance(lesson, dict):
                            continue
                        status = str(lesson.get("status") or "").strip().casefold()
                        if not status:
                            continue
                        month_key = parse_month_key(lesson.get("date"))
                        if not month_key:
                            continue
                        ar_subject_bucket = subject_monthly_ar.setdefault(subject_key, {})
                        ar_group_bucket = ar_subject_bucket.setdefault(group_key, {})
                        month_ar = ar_group_bucket.setdefault(month_key, {"present": 0, "total": 0})
                        month_ar["total"] += 1
                        if status in ("present", "justified"):
                            month_ar["present"] += 1

    current_utc = datetime.utcnow()
    current_month_key = f"{current_utc.year:04d}-{current_utc.month:02d}"

    subject_buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in metrics:
        subject_name = str(item.get("subject", "")).strip()
        if not subject_name:
            continue

        school_name = str(item.get("school_name", "")).strip()
        school_key = normalize_school_key(item.get("school_key", ""), school_name)
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
            label = format_group_label(school_name, group_name)
            if not label:
                continue
            group_rows.append(
                {
                    "label": label,
                    "students_count": len(group_bucket["students"]),
                    "avg_aap": average_or_none(group_bucket["aap_values"]),
                    "avg_ar": average_or_none(group_bucket["ar_values"]),
                }
            )

        group_rows.sort(key=lambda row: normalize_text(row.get("label", "")))
        monthly_subject_bucket = subject_monthly_scores.get((school_key, subject_name), {})
        month_keys = sorted(
            {
                month_key
                for group_scores in monthly_subject_bucket.values()
                for month_key in group_scores.keys()
            }
        )
        # Fill the full range from the first lesson month to the current month
        # so the chart always shows a continuous timeline (no skipped months).
        if month_keys:
            month_range_values = month_range(month_keys[0], current_month_key)
        else:
            month_range_values = []
        monthly_series = []
        for group_name, month_scores in monthly_subject_bucket.items():
            label = format_group_label(school_name, group_name)
            if not label:
                continue

            values = []
            has_value = False
            for month_key in month_range_values:
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

        monthly_series.sort(key=lambda row: normalize_text(row.get("label", "")))

        ar_subject_bucket = subject_monthly_ar.get((school_key, subject_name), {})
        monthly_ar_series = []
        for group_name, month_ar_data in ar_subject_bucket.items():
            label = format_group_label(school_name, group_name)
            if not label:
                continue
            values = []
            has_value = False
            for month_key in month_range_values:
                counts = month_ar_data.get(month_key)
                if counts and counts["total"] > 0:
                    ar = round(counts["present"] / counts["total"] * 100, 1)
                    values.append(ar)
                    has_value = True
                else:
                    values.append(None)
            if has_value:
                monthly_ar_series.append({"label": label, "values": values})
        monthly_ar_series.sort(key=lambda row: normalize_text(row.get("label", "")))

        def _exam_sort_key(label: str) -> tuple:
            try:
                return (0, _EXAM_ORDER.index(normalize_exam_name(label)))
            except ValueError:
                return (1, label)

        exam_subject_bucket = subject_exam_scores.get((school_key, subject_name), {})
        exam_labels = sorted(
            {
                exam_label
                for group_scores in exam_subject_bucket.values()
                for exam_label in group_scores.keys()
            },
            key=_exam_sort_key,
        )
        exam_series = []
        for group_name, exam_scores in exam_subject_bucket.items():
            label = format_group_label(school_name, group_name)
            if not label:
                continue
            values = []
            has_value = False
            for exam_label in exam_labels:
                label_scores = exam_scores.get(exam_label, [])
                if label_scores:
                    values.append(round(sum(label_scores) / len(label_scores), 1))
                    has_value = True
                else:
                    values.append(None)
            if has_value:
                exam_series.append({"label": label, "values": values})

        exam_series.sort(key=lambda row: normalize_text(row.get("label", "")))

        # Fallback for sheets where lesson-level dates are missing or not parseable:
        # render a current-month snapshot using group average AAP so chart is never empty.
        if (not month_range_values or not monthly_series) and group_rows:
            snapshot_series = []
            for group_row in group_rows:
                label = str(group_row.get("label", "")).strip()
                if not label:
                    continue
                avg_aap_value = safe_float(group_row.get("avg_aap"))
                if avg_aap_value is None or avg_aap_value <= 0:
                    continue
                snapshot_series.append(
                    {
                        "label": label,
                        "values": [round(float(avg_aap_value), 1)],
                    }
                )

            if snapshot_series:
                month_range_values = [current_month_key]
                monthly_series = sorted(
                    snapshot_series,
                    key=lambda row: normalize_text(row.get("label", "")),
                )

        rows.append(
            {
                "school_key": school_key,
                "school_name": school_name,
                "subject_name": subject_name,
                "students_count": len(bucket["students"]),
                "groups_count": len(group_rows),
                "avg_aap": average_or_none(bucket["aap_values"]),
                "avg_ar": average_or_none(bucket["ar_values"]),
                "groups": group_rows,
                "monthly_months": month_range_values,
                "monthly_series": monthly_series,
                "monthly_ar_series": monthly_ar_series,
                "exam_labels": exam_labels,
                "exam_series": exam_series,
            }
        )

    rows.sort(
        key=lambda row: (
            normalize_text(row.get("school_name", "")),
            subject_priority_key(row.get("subject_name", "")),
        )
    )
    return rows


def build_admin_student_ratings(metrics):
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
        avg_aap = average_or_none(bucket["aap_values"])
        avg_ar = average_or_none(bucket["ar_values"])
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
            normalize_text(row.get("full_name", "")),
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


def build_admin_attention(student_ratings, dataset, admin_teachers):
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
            normalize_text(row.get("full_name", "")),
        )
    )
    low_ar.sort(
        key=lambda row: (
            float(row.get("value", 0)),
            normalize_text(row.get("full_name", "")),
        )
    )

    teacher_groups = {
        normalize_text(row.get("assigned_group", ""))
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
        if normalize_text(group_name) in teacher_groups:
            continue
        groups_without_teacher.append(f"{group_name} ({school_name})")

    return {
        "low_aap": low_aap[:8],
        "low_ar": low_ar[:8],
        "groups_without_teacher": groups_without_teacher[:8],
    }


def build_admin_quick_stats(admin_school_info, admin_teachers, total_subjects):
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


__all__ = [
    "extract_overview_student_metrics",
    "build_admin_school_info",
    "build_admin_group_highlights",
    "build_admin_group_zones",
    "build_admin_subject_info",
    "is_exam_performance_row",
    "build_admin_student_ratings",
    "build_admin_attention",
    "build_admin_quick_stats",
]
