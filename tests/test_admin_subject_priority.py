import unittest
from unittest.mock import patch

from flask import Blueprint, Flask

from app.routes.admin.services import insights_service, page_service
from app.routes.admin.student_routes import register_admin_student_routes


class AdminSubjectPriorityTests(unittest.TestCase):
    @patch(
        "app.routes.admin.services.page_service.get_configured_school_spreadsheets",
        return_value={"school5": "id-1", "sehriyo": "id-2"},
    )
    def test_school_configuration_prefers_sehriyo_first(self, _mock_school_sheets):
        config = page_service.build_school_configuration()
        codes = [item["code"] for item in config["admin_school_options"] if item["code"] != "all"]
        self.assertEqual(codes, ["sehriyo", "school5"])

    def test_resource_subject_options_prioritize_math(self):
        summary_rows = [
            {"subject_name": "General English"},
            {"subject_name": "IGCSE Mathematics A"},
            {"subject_name": "Physics"},
        ]
        options = page_service.build_admin_resource_subject_options(
            summary_rows,
            resource_rows=[],
        )
        self.assertEqual(options[0], "Math")
        self.assertIn("English", options)
        self.assertIn("Physics", options)

    def test_admin_subject_info_prioritizes_math(self):
        metrics = [
            {
                "school_key": "sehriyo",
                "school_name": "Sehriyo",
                "full_name": "Student B",
                "subject": "General English",
                "group": "G1",
                "aap": 6.5,
                "ar": 88.0,
            },
            {
                "school_key": "sehriyo",
                "school_name": "Sehriyo",
                "full_name": "Student A",
                "subject": "IGCSE Mathematics A",
                "group": "G1",
                "aap": 7.5,
                "ar": 91.0,
            },
            {
                "school_key": "sehriyo",
                "school_name": "Sehriyo",
                "full_name": "Student C",
                "subject": "Chemistry",
                "group": "G2",
                "aap": 6.0,
                "ar": 84.0,
            },
        ]

        rows = insights_service.build_admin_subject_info(
            metrics,
            dataset=None,
            school_option_catalog={"sehriyo": "Sehriyo"},
        )
        sehriyo_subjects = [
            str(row.get("subject_name", ""))
            for row in rows
            if str(row.get("school_key", "")).strip().casefold() == "sehriyo"
        ]
        self.assertGreaterEqual(len(sehriyo_subjects), 3)
        self.assertEqual(sehriyo_subjects[0], "IGCSE Mathematics A")


class AdminStudentsApiTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "test"
        router = Blueprint("admin", __name__)
        register_admin_student_routes(
            router,
            render_admin_page=lambda **_kwargs: "ok",
            render_edit_student_page=lambda *_args, **_kwargs: "ok",
            delete_uploaded_student_photo=lambda *_args, **_kwargs: None,
            load_dataset=lambda **_kwargs: ({}, ""),
        )
        self.app.register_blueprint(router)
        self.client = self.app.test_client()

    @patch("app.routes.admin.student_routes.list_students_for_admin", return_value=[{"id": 1}])
    def test_students_api_respects_school_filter(self, mock_students):
        response = self.client.get("/admin/api/students?school=sehriyo")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"students": [{"id": 1}]})
        mock_students.assert_called_once_with(school_filter="sehriyo")

    @patch("app.routes.admin.student_routes.list_students_for_admin", return_value=[])
    def test_students_api_normalizes_unknown_filter_to_all(self, mock_students):
        response = self.client.get("/admin/api/students?school=unknown-school")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"students": []})
        mock_students.assert_called_once_with(school_filter="all")


if __name__ == "__main__":
    unittest.main()
