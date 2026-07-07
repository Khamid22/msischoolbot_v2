"""Teacher role page route — workspace scoped to the logged-in teacher."""

from backend.render import generate_csrf, render_react_page
from backend.roles.teacher.services import build_teacher_workspace
from backend.roles.teacher.workspace_cards import build_teacher_workspace_cards
from backend.utils.response_helpers import redirect, jsonify
from fastapi import APIRouter, Depends, Request

from backend.utils.guards import GuardResponse
from backend.utils.context import request
from backend.utils.performance import PagePerformanceTimer, log_page_performance
from backend.utils.session import (
    current_auth_login,
    current_auth_role,
    current_teacher_id,
    current_teacher_staff_id,
)
from backend.roles.admin.routes.request_payload import request_payload
from backend.domains.office_hours import service as oh_service


def register_teacher_page_routes(app):
    def ensure_teacher_role(request_obj: Request):
        if current_auth_role() == "teacher":
            return
        requested_with = str(request_obj.headers.get("X-Requested-With", "")).strip()
        if requested_with == "XMLHttpRequest" or request_obj.url.path.startswith("/teacher/api/"):
            raise GuardResponse(
                jsonify({"ok": False, "message": "Teacher authentication required."}, status_code=401)
            )
        raise GuardResponse(redirect("/"))

    teacher = APIRouter(dependencies=[Depends(ensure_teacher_role)])

    @teacher.get("/teacher")
    def teacher_home():
        timer = PagePerformanceTimer()
        teacher_id = current_teacher_id()
        teacher_staff_id = current_teacher_staff_id()
        try:
            workspace = build_teacher_workspace(teacher_id, teacher_staff_id)
        except Exception:
            workspace = None
        timer.mark("workspace_build")
        if not isinstance(workspace, dict):
            workspace = {
                "teacher": {
                    "id": teacher_id or 0,
                    "full_name": "",
                    "login": current_auth_login(),
                    "assigned_group": "",
                    "category": "",
                    "semester_stage": "",
                    "performance_score": 0,
                },
                "groups": [],
                "academy": None,
                "academy_summary": {},
                "academy_updates": [],
                "journey": [],
                "lesson_reports": [],
                "training_timetable": [],
            }
        workspace_cards = build_teacher_workspace_cards(
            teacher_id=teacher_id,
            teacher_staff_id=teacher_staff_id,
            workspace=workspace,
        )
        timer.mark("card_build")

        # Get teacher's DB details for academic info (subject, etc.)
        from backend.domains.teachers.service import get_teacher_by_id
        try:
            teacher_db = get_teacher_by_id(teacher_id) if teacher_id else None
        except Exception:
            teacher_db = None
        timer.mark("teacher_lookup")

        # Get list of subjects for teacher's options
        from database import connect_auth_db
        subjects_options = []
        try:
            if teacher_id:
                with connect_auth_db() as conn:
                    rows = conn.execute(
                        """
                        SELECT DISTINCT s.id, s.subject_name AS name
                        FROM msi_v2.subjects s
                        LEFT JOIN msi_v2.teacher_subjects ts
                          ON ts.subject_id = s.id
                         AND ts.teacher_id = %s
                         AND ts.status = 'active'
                        WHERE s.status = 'active'
                          AND (
                            EXISTS (
                                SELECT 1
                                FROM msi_v2.teacher_subjects assigned
                                WHERE assigned.teacher_id = %s
                                  AND assigned.status = 'active'
                            ) = false
                            OR ts.teacher_id IS NOT NULL
                          )
                        ORDER BY s.subject_name
                        """,
                        (teacher_id, teacher_id),
                    ).fetchall()
                    subjects_options = [dict(row) for row in rows]
        except Exception:
            subjects_options = []
        timer.mark("subject_options")

        response = render_react_page(
            "teacher-home",
            {
                "authLogin": current_auth_login(),
                "csrfToken": generate_csrf(),
                "teacher": {
                    **workspace["teacher"],
                    "id": teacher_id,
                    "assigned_group": teacher_db.get("assigned_group", "") if teacher_db else "",
                    "category": teacher_db.get("category", "") if teacher_db else "",
                    "semester_stage": teacher_db.get("semester_stage", "") if teacher_db else "",
                    "performance_score": teacher_db.get("performance_score", 7.0) if teacher_db else 7.0,
                },
                "groups": workspace["groups"],
                "academy": workspace.get("academy"),
                "academySummary": workspace.get("academy_summary", {}),
                "academyUpdates": workspace.get("academy_updates", []),
                "journey": workspace.get("journey", []),
                "lessonReports": workspace.get("lesson_reports", []),
                "trainingTimetable": workspace.get("training_timetable", []),
                "subjectsOptions": subjects_options,
                "workspaceCards": workspace_cards,
            },
        )
        timer.mark("render")
        log_page_performance(
            "teacher_home",
            timer,
            response=response,
            rows={
                "groups": workspace["groups"],
                "academy": [workspace.get("academy")] if workspace.get("academy") else [],
                "academy_updates": workspace.get("academy_updates", []),
                "journey": workspace.get("journey", []),
                "lesson_reports": workspace.get("lesson_reports", []),
                "training_timetable": workspace.get("training_timetable", []),
                "subjects_options": subjects_options,
                "workspace_cards": workspace_cards,
            },
        )
        return response

    @teacher.get("/teacher/api/office-hours/availability")
    def teacher_list_availability():
        teacher_id = current_teacher_id()
        subject_id = request.args.get("subject_id")
        status = request.args.get("status")
        starts_at_from = request.args.get("starts_at_from")

        try:
            s_id = int(subject_id) if subject_id else None
        except ValueError:
            return jsonify({"ok": False, "message": "Invalid query parameters."}, status_code=400)

        availabilities = oh_service.list_availabilities(
            teacher_id=teacher_id,
            subject_id=s_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return jsonify({"ok": True, "availabilities": availabilities})

    @teacher.post("/teacher/api/office-hours/availability")
    def teacher_create_availability():
        teacher_id = current_teacher_id()
        payload = request_payload()
        try:
            starts_at = str(payload.get("starts_at"))
            ends_at = str(payload.get("ends_at"))
            slot_minutes = int(payload.get("slot_minutes", 30))
            room = str(payload.get("room", ""))
            capacity = int(payload.get("capacity", 1))
            subject_id = int(payload.get("subject_id")) if payload.get("subject_id") else None
            planned_topic = str(payload.get("planned_topic", "") or "").strip()
        except (TypeError, ValueError, KeyError) as exc:
            return jsonify({"ok": False, "message": "Missing or invalid payload parameters."}, status_code=400)

        try:
            availability_id = oh_service.create_availability(
                teacher_id=teacher_id,
                subject_id=subject_id,
                starts_at=starts_at,
                ends_at=ends_at,
                slot_minutes=slot_minutes,
                room=room,
                capacity=capacity,
                planned_topic=planned_topic,
            )
            return jsonify({"ok": True, "availability_id": availability_id})
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=500)

    @teacher.patch("/teacher/api/office-hours/availability/{availability_id}")
    def teacher_cancel_availability(availability_id: int):
        teacher_id = current_teacher_id()
        payload = request_payload()
        status = payload.get("status")
        if status != "cancelled":
            return jsonify({"ok": False, "message": "Only 'cancelled' state transitions are allowed."}, status_code=400)

        try:
            oh_service.cancel_availability(availability_id, teacher_id=teacher_id)
            return jsonify({"ok": True})
        except PermissionError as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=403)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=500)

    @teacher.get("/teacher/api/office-hours/bookings")
    def teacher_list_bookings():
        teacher_id = current_teacher_id()
        availability_id = request.args.get("availability_id")
        student_row_id = request.args.get("student_row_id")
        subject_id = request.args.get("subject_id")
        status = request.args.get("status")
        starts_at_from = request.args.get("starts_at_from")

        try:
            a_id = int(availability_id) if availability_id else None
            s_row_id = int(student_row_id) if student_row_id else None
            s_id = int(subject_id) if subject_id else None
        except ValueError:
            return jsonify({"ok": False, "message": "Invalid query parameters."}, status_code=400)

        bookings = oh_service.list_bookings(
            availability_id=a_id,
            teacher_id=teacher_id,
            student_row_id=s_row_id,
            subject_id=s_id,
            status=status,
            starts_at_from=starts_at_from
        )
        return jsonify({"ok": True, "bookings": bookings})

    @teacher.patch("/teacher/api/office-hours/bookings/{booking_id}")
    def teacher_update_booking_status(booking_id: int):
        teacher_id = current_teacher_id()
        payload = request_payload()
        status = payload.get("status")
        teacher_note = payload.get("teacher_note")

        if not status:
            return jsonify({"ok": False, "message": "Missing status parameter."}, status_code=400)

        try:
            oh_service.update_booking_status(booking_id, status, teacher_note, teacher_id=teacher_id)
            return jsonify({"ok": True})
        except PermissionError as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=403)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}, status_code=500)

    app.include_router(teacher)
