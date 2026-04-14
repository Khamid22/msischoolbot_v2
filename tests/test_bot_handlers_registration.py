import unittest

from bot.handlers.account_link import router as account_link_router
from bot.handlers.contact_us import router as contact_router
from bot.handlers.quick_summary import router as quick_summary_router
from bot.handlers.start import router as start_router
from bot.keyboards.inline_keyboard import student_menu_keyboard


class BotHandlersRegistrationTests(unittest.TestCase):
    def test_start_router_exposes_start_and_menu_handlers(self):
        handler_names = {handler.callback.__name__ for handler in start_router.message.handlers}
        self.assertIn("start_handler", handler_names)
        self.assertIn("menu_handler", handler_names)

    def test_account_router_has_command_handlers(self):
        handler_names = {
            handler.callback.__name__ for handler in account_link_router.message.handlers
        }
        self.assertIn("whoami_handler", handler_names)
        self.assertIn("unlink_me_handler", handler_names)

    def test_student_menu_callbacks_have_matching_handlers(self):
        keyboard = student_menu_keyboard()
        callback_data = {
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data
        }
        quick_handlers = {
            handler.callback.__name__
            for handler in quick_summary_router.callback_query.handlers
        }
        contact_handlers = {
            handler.callback.__name__ for handler in contact_router.callback_query.handlers
        }
        self.assertIn("student_quick_summary", callback_data)
        self.assertIn("student_contact_us", callback_data)
        self.assertIn("quick_summary_callback", quick_handlers)
        self.assertIn("contact_us_callback", contact_handlers)


if __name__ == "__main__":
    unittest.main()
