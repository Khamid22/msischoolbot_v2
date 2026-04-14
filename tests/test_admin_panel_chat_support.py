import unittest
from unittest.mock import patch

from app.routes.admin.services.page_service import build_admin_page_context


class AdminPanelChatSupportTests(unittest.TestCase):
    @patch("app.routes.admin.services.page_service.list_teachers", return_value=[])
    @patch("app.routes.admin.services.page_service.list_students_for_admin", return_value=[])
    def test_chat_panel_is_accepted(
        self,
        _mock_list_students,
        _mock_list_teachers,
    ):
        context = build_admin_page_context(
            admin_panel="chat",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({}, ""),
            force_refresh=True,
        )
        self.assertEqual(context["panel"], "chat")

    @patch("app.routes.admin.services.page_service.list_teachers", return_value=[])
    @patch("app.routes.admin.services.page_service.list_students_for_admin", return_value=[])
    def test_invalid_panel_falls_back_to_overview(
        self,
        _mock_list_students,
        _mock_list_teachers,
    ):
        context = build_admin_page_context(
            admin_panel="unknown-panel",
            admin_school="all",
            admin_teacher_edit=None,
            load_dataset=lambda **_kwargs: ({}, ""),
            force_refresh=True,
        )
        self.assertEqual(context["panel"], "overview")


if __name__ == "__main__":
    unittest.main()
