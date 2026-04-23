import unittest
from unittest.mock import patch

from flask import Blueprint, Flask

from app.routes.students.services.dashboard_service import build_ar_lessons_page_context


class DashboardArCancellationRowsTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"

        student_bp = Blueprint("student", __name__)

        @student_bp.get("/dashboard/<int:student_id>")
        def dashboard(student_id):
            _ = student_id
            return "ok"

        app.register_blueprint(student_bp)
        self.app = app

    def test_non_chemistry_ar_keeps_duplicate_cancelled_rows_with_dates(self):
        payload = {
            "student": {
                "fullName": "Амир",
                "subject": "IGCSE Mathematics A",
                "group": "Online",
                "schoolCode": "school5",
            },
            "attendanceLessons": [
                {
                    "lesson": "Lesson 1",
                    "topic": "Rounding Numbers",
                    "date": "7/11",
                    "status": "present",
                },
                {
                    "lesson": "Cancelled",
                    "topic": "Student Health Problems",
                    "date": "21/11",
                    "status": "absent",
                },
                {
                    "lesson": "Cancelled",
                    "topic": "Family Emergency",
                    "date": "22/11",
                    "status": "absent",
                },
            ],
        }

        lesson_catalog = [
            {
                "lesson_number": "Lesson 1",
                "lesson_topic": "Rounding Numbers",
                "lesson_date": "7/11",
                "lesson_order": 1,
            }
        ]

        with self.app.app_context():
            with self.app.test_request_context("/"):
                with patch(
                    "app.routes.students.services.dashboard_service.get_lessons_for_subject",
                    return_value=(lesson_catalog, ""),
                ):
                    context, error_message, status_code = build_ar_lessons_page_context(
                        student_id=3553052387,
                        payload=payload,
                        requested_subject="IGCSE Mathematics A",
                        requested_group="Online",
                        requested_school="school5",
                        load_dataset=lambda **_kwargs: ({}, ""),
                        force_refresh=False,
                    )

        self.assertEqual(error_message, "")
        self.assertEqual(status_code, 200)
        self.assertIsInstance(context, dict)

        lesson_rows = context["lesson_rows"]
        cancelled_rows = [
            row for row in lesson_rows if str(row.get("lesson_number", "")) == "Cancelled"
        ]
        self.assertEqual(len(cancelled_rows), 2)

        cancelled_dates = sorted(str(row.get("lesson_date_display", "")) for row in cancelled_rows)
        self.assertEqual(cancelled_dates, ["21/11", "22/11"])
        cancelled_topics = {str(row.get("lesson_topic", "")) for row in cancelled_rows}
        self.assertIn("Student Health Problems", cancelled_topics)
        self.assertIn("Family Emergency", cancelled_topics)
        for row in cancelled_rows:
            self.assertEqual(str(row.get("attendance_status", "")), "absent")
            self.assertEqual(str(row.get("attendance_display", "")), "Absent")

    def test_amir_online_ar_uses_raw_attendance_rows_only(self):
        payload = {
            "student": {
                "fullName": "Амир",
                "subject": "IGCSE Mathematics A",
                "group": "Online",
                "schoolCode": "school5",
            },
            "attendanceLessons": [
                {
                    "lesson": "Lesson 1",
                    "topic": "Rounding Numbers",
                    "date": "7/11",
                    "status": "present",
                },
                {
                    "lesson": "Cancelled",
                    "topic": "Student Health Problems",
                    "date": "21/11",
                    "status": "absent",
                },
                {
                    "lesson": "Cancelled",
                    "topic": "Family Emergency",
                    "date": "22/11",
                    "status": "absent",
                },
            ],
        }

        with self.app.app_context():
            with self.app.test_request_context("/"):
                with patch(
                    "app.routes.students.services.dashboard_service.get_lessons_for_subject",
                    side_effect=AssertionError(
                        "Catalog lookup should not run for Amir Online AR view."
                    ),
                ):
                    context, error_message, status_code = build_ar_lessons_page_context(
                        student_id=3553052387,
                        payload=payload,
                        requested_subject="IGCSE Mathematics A",
                        requested_group="Online",
                        requested_school="school5",
                        load_dataset=lambda **_kwargs: ({}, ""),
                        force_refresh=False,
                    )

        self.assertEqual(error_message, "")
        self.assertEqual(status_code, 200)
        lesson_rows = context["lesson_rows"]
        self.assertEqual(len(lesson_rows), 3)
        self.assertEqual(
            [str(row.get("lesson_number", "")) for row in lesson_rows],
            ["Lesson 1", "Cancelled", "Cancelled"],
        )


if __name__ == "__main__":
    unittest.main()
