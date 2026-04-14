import unittest
from unittest.mock import patch

from app.routes.admin.services import page_service


class AdminPageContextCacheTests(unittest.TestCase):
    def setUp(self):
        page_service.invalidate_admin_page_context_cache()

    def tearDown(self):
        page_service.invalidate_admin_page_context_cache()

    @patch("app.routes.admin.services.page_service.list_teachers", return_value=[])
    @patch("app.routes.admin.services.page_service.list_students_for_admin", return_value=[])
    @patch("app.routes.admin.services.page_service.build_admin_quick_stats", return_value={})
    @patch(
        "app.routes.admin.services.page_service.build_admin_group_zones",
        return_value={"green": [], "yellow": [], "red": []},
    )
    @patch("app.routes.admin.services.page_service.build_admin_subject_info", return_value=[])
    @patch("app.routes.admin.services.page_service.build_admin_school_info", return_value=[])
    @patch(
        "app.routes.admin.services.page_service.extract_overview_student_metrics",
        return_value=[],
    )
    @patch("app.routes.admin.services.page_service.list_subject_summaries", return_value=[])
    def test_overview_load_error_context_is_not_cached(
        self,
        _mock_subject_summaries,
        _mock_metrics,
        _mock_school_info,
        _mock_subject_info,
        _mock_group_zones,
        _mock_quick_stats,
        _mock_students,
        _mock_teachers,
    ):
        first_context = page_service.build_admin_page_context(
            admin_panel="overview",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: (None, "temporary data source error"),
            force_refresh=False,
        )
        self.assertIn("temporary data source error", first_context["load_error"])

        second_context = page_service.build_admin_page_context(
            admin_panel="overview",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({"groups": [], "students": []}, ""),
            force_refresh=False,
        )
        self.assertEqual(second_context["load_error"], "")

    @patch("app.routes.admin.services.page_service.list_teachers", return_value=[])
    @patch("app.routes.admin.services.page_service.list_students_for_admin", return_value=[])
    @patch("app.routes.admin.services.page_service.list_resource_types", return_value=[])
    @patch("app.routes.admin.services.page_service.list_subject_summaries", return_value=[])
    @patch(
        "app.routes.admin.services.page_service.build_admin_resource_subject_options",
        return_value=[],
    )
    @patch("app.routes.admin.services.page_service.is_resource_upload_enabled", return_value=True)
    @patch(
        "app.routes.admin.services.page_service.list_resources",
        side_effect=[[{"id": 1}], [{"id": 2}]],
    )
    def test_cache_invalidation_refreshes_resources_panel(
        self,
        mock_list_resources,
        _mock_upload_enabled,
        _mock_resource_subject_options,
        _mock_subject_summaries,
        _mock_resource_types,
        _mock_students,
        _mock_teachers,
    ):
        first_context = page_service.build_admin_page_context(
            admin_panel="resources",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({}, ""),
            force_refresh=False,
        )
        self.assertEqual(first_context["admin_resources"], [{"id": 1}])
        self.assertEqual(mock_list_resources.call_count, 1)

        second_context = page_service.build_admin_page_context(
            admin_panel="resources",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({}, ""),
            force_refresh=False,
        )
        self.assertEqual(second_context["admin_resources"], [{"id": 1}])
        self.assertEqual(mock_list_resources.call_count, 1)

        page_service.invalidate_admin_page_context_cache()
        third_context = page_service.build_admin_page_context(
            admin_panel="resources",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({}, ""),
            force_refresh=False,
        )
        self.assertEqual(third_context["admin_resources"], [{"id": 2}])
        self.assertEqual(mock_list_resources.call_count, 2)


if __name__ == "__main__":
    unittest.main()
