"""Gradebook window operations."""

from datetime import date, datetime

from backend.modules.organization import canonical

def _gradebook_lesson_sort_key(item):
    raw = str(item.get("date") or "")
    try:
        parsed = datetime.strptime(raw, "%d/%m/%Y").date()
    except ValueError:
        parsed = datetime.max.date()
    return (
        parsed,
        str(item.get("startTime") or ""),
        0 if _is_gradebook_cancellation(item) else 1,
        int(item.get("order") or 0),
    )


def _is_gradebook_cancellation(item):
    return (
        bool(item.get("isCancellation"))
        or str(item.get("status") or "").strip().casefold() in {"cancelled", "canceled"}
        or str(item.get("sourceKind") or "").strip().casefold() in {"cancelled", "canceled", "cancellation"}
    )


def _gradebook_lesson_payload(lesson_rows, exception_rows):
    items = [
        {
            "id": int(row["id"]),
            "lessonNumber": str(row["lesson_number"]),
            "topic": str(row["topic"] or ""),
            "date": str(row["lesson_date"] or ""),
            "startTime": str(row["start_time"] or ""),
            "endTime": str(row["end_time"] or ""),
            "room": str(row["room"] or ""),
            "order": int(row["lesson_order"] or 0),
            "status": str(row["status"] or "scheduled"),
            "sourceKind": str(row["source_kind"] or ""),
            "hasHomework": bool(row["has_homework"]),
            "hasAcademicRecords": bool(row.get("has_academic_records")),
            "isCancellation": False,
            "cancellationReason": "",
            "exceptionId": None,
            "canRecover": False,
        }
        for row in lesson_rows
    ]
    items.extend(
        {
            "id": -int(row["id"]),
            "lessonSessionId": int(row["lesson_session_id"]),
            "lessonNumber": f"{str(row['lesson_number'])} (Cancelled)",
            "topic": str(row["reason"] or ""),
            "date": str(row["lesson_date"] or ""),
            "startTime": str(row["start_time"] or ""),
            "endTime": str(row["end_time"] or ""),
            "room": str(row["room"] or ""),
            "order": int(row["lesson_order"] or 0),
            "status": "cancelled",
            "sourceKind": "cancellation",
            "hasHomework": False,
            "hasAcademicRecords": False,
            "isCancellation": True,
            "cancellationReason": str(row["reason"] or ""),
            "exceptionId": int(row["id"]),
            "canRecover": True,
        }
        for row in exception_rows
    )

    items.sort(key=_gradebook_lesson_sort_key)
    return items


def _gradebook_lesson_window(
    items, *, limit=0, cursor="", direction="", anchor_date="", month="", closures=()
):
    def is_cancellation(item):
        return (
            bool(item.get("isCancellation"))
            or str(item.get("status") or "").strip().casefold() in {"cancelled", "canceled"}
            or str(item.get("sourceKind") or "").strip().casefold() in {"cancelled", "canceled", "cancellation"}
        )

    def sort_key(item):
        return (
            canonical.parse_date(item.get("date")) or date.max,
            str(item.get("startTime") or ""),
            0 if is_cancellation(item) else 1,
            int(item.get("order") or 0),
        )

    lessons = [item for item in items if not is_cancellation(item)]
    cancellations = [item for item in items if is_cancellation(item)]
    total = len(lessons)

    month_text = str(month or "").strip()
    if month_text:
        def month_parts(value):
            parts = str(value or "").split("-")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                return None
            year, month_number = (int(part) for part in parts)
            try:
                date(year, month_number, 1)
            except ValueError:
                return None
            return year, month_number

        requested_parts = month_parts(month_text)
        if requested_parts is None:
            raise ValueError("month must use YYYY-MM format.")

        dated_items = []
        available_months = set()
        for item in items:
            parsed = canonical.parse_date(item.get("date"))
            if not parsed:
                continue
            key = f"{parsed.year:04d}-{parsed.month:02d}"
            available_months.add(key)
            dated_items.append((item, key))

        # Keep the requested month selected even when it contains no dated
        # lessons. Silently substituting the nearest populated month made the
        # Gradebook toolbar and chart appear to ignore the administrator's
        # selection (especially for "This month").
        closure_months = set()
        for closure in closures:
            cursor_month = date(closure["start_date"].year, closure["start_date"].month, 1)
            final_month = date(closure["end_date"].year, closure["end_date"].month, 1)
            while cursor_month <= final_month:
                closure_months.add(cursor_month.strftime("%Y-%m"))
                absolute = cursor_month.year * 12 + cursor_month.month
                next_year, next_month_zero = divmod(absolute, 12)
                cursor_month = date(next_year, next_month_zero + 1, 1)
        month_keys = sorted(available_months | closure_months)
        option_month_keys = sorted({*month_keys, month_text})
        month_options = []
        for key in option_month_keys:
            year, month_number = month_parts(key)
            month_start = date(year, month_number, 1)
            absolute = year * 12 + month_number
            next_year, next_month_zero = divmod(absolute, 12)
            next_month = date(next_year, next_month_zero + 1, 1)
            month_end = date.fromordinal(next_month.toordinal() - 1)
            month_closures = [
                row for row in closures
                if row["start_date"] <= month_end and month_start <= row["end_date"]
            ]
            month_option = {
                "value": key,
                "label": date(year, month_number, 1).strftime("%B %Y"),
                "lessonCount": sum(
                    1
                    for item, item_month in dated_items
                    if item_month == key and not is_cancellation(item)
                ),
            }
            if month_closures:
                month_option.update({
                    "hasClosure": True,
                    "isLocked": any(
                        row["start_date"] <= month_start and row["end_date"] >= month_end
                        for row in month_closures
                    ),
                    "closureTitles": list(dict.fromkeys(str(row["title"]) for row in month_closures)),
                    "closureScopes": list(dict.fromkeys(
                        "group" if row.get("group_id") else "school" for row in month_closures
                    )),
                    "protectedRecordCount": sum(
                        1
                        for item, item_month in dated_items
                        if item_month == key
                        and not is_cancellation(item)
                        and bool(item.get("hasAcademicRecords"))
                    ),
                })
            month_options.append(month_option)

        if not month_keys:
            return [], {
                "totalLessons": total,
                "startIndex": 0,
                "endIndex": 0,
                "previousCursor": None,
                "nextCursor": None,
                "hasPrevious": False,
                "hasNext": False,
                "selectedMonth": month_text,
                "previousMonth": None,
                "nextMonth": None,
                "monthOptions": month_options,
            }

        selected_month = month_text
        selected_items = [item for item, key in dated_items if key == selected_month]
        selected_items.sort(key=sort_key)
        selected_lesson_ids = {
            int(item.get("id") or 0)
            for item in selected_items
            if not is_cancellation(item)
        }
        selected_indexes = [
            index
            for index, item in enumerate(lessons)
            if int(item.get("id") or 0) in selected_lesson_ids
        ]
        start = selected_indexes[0] if selected_indexes else 0
        end = selected_indexes[-1] + 1 if selected_indexes else start
        selected_month_index = option_month_keys.index(selected_month)
        previous_month = option_month_keys[selected_month_index - 1] if selected_month_index > 0 else None
        next_month = (
            option_month_keys[selected_month_index + 1]
            if selected_month_index + 1 < len(option_month_keys)
            else None
        )
        return selected_items, {
            "totalLessons": total,
            "startIndex": start,
            "endIndex": end,
            "previousCursor": None,
            "nextCursor": None,
            "hasPrevious": previous_month is not None,
            "hasNext": next_month is not None,
            "selectedMonth": selected_month,
            "previousMonth": previous_month,
            "nextMonth": next_month,
            "monthOptions": month_options,
        }

    limit = max(0, min(int(limit or 0), 40))
    if limit <= 0 or total <= limit:
        return items, {
            "totalLessons": total,
            "startIndex": 0,
            "endIndex": total,
            "previousCursor": None,
            "nextCursor": None,
            "hasPrevious": False,
            "hasNext": False,
        }
    start = None
    cursor_text = str(cursor or "").strip().lower()
    if cursor_text:
        raw_offset = cursor_text[1:] if cursor_text.startswith("o") else cursor_text
        try:
            start = max(0, min(int(raw_offset), max(0, total - limit)))
        except ValueError:
            raise ValueError("Invalid Gradebook lesson cursor.")
        normalized_direction = str(direction or "").strip().casefold()
        if normalized_direction == "previous":
            start = max(0, start - limit)
        elif normalized_direction == "next":
            start = min(max(0, total - limit), start + limit)
        elif normalized_direction not in {"", "current"}:
            raise ValueError("Invalid Gradebook lesson direction.")
    if start is None:
        anchor = canonical.parse_date(anchor_date) if str(anchor_date or "").strip() else date.today()
        if not anchor:
            raise ValueError("anchor_date must be a valid date.")
        anchor_index = 0
        for index, item in enumerate(lessons):
            parsed = canonical.parse_date(item.get("date"))
            if parsed and parsed >= anchor:
                anchor_index = index
                break
        start = max(0, min(anchor_index - (limit // 2), max(0, total - limit)))
    end = min(total, start + limit)
    selected_lessons = lessons[start:end]
    selected_dates = [canonical.parse_date(item.get("date")) for item in selected_lessons]
    selected_dates = [value for value in selected_dates if value]
    visible_cancellations = []
    if selected_dates:
        last_date = max(selected_dates)
        previous_date = canonical.parse_date(lessons[start - 1].get("date")) if start > 0 else None
        for item in cancellations:
            cancellation_date = canonical.parse_date(item.get("date"))
            if cancellation_date is None:
                if end == total:
                    visible_cancellations.append(item)
            elif (previous_date is None or cancellation_date > previous_date) and (end == total or cancellation_date <= last_date):
                visible_cancellations.append(item)
    elif end == total:
        visible_cancellations = cancellations
    visible_items = [*selected_lessons, *visible_cancellations]
    visible_items.sort(key=sort_key)
    previous_start = max(0, start - limit)
    next_start = min(max(0, total - limit), start + limit)
    return visible_items, {
        "totalLessons": total,
        "startIndex": start,
        "endIndex": end,
        "previousCursor": f"o{previous_start}" if start > 0 else None,
        "nextCursor": f"o{next_start}" if end < total else None,
        "hasPrevious": start > 0,
        "hasNext": end < total,
    }
