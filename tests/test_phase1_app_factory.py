import os
import unittest


os.environ.setdefault("DISABLE_BACKGROUND_REFRESH", "1")

from app.server import create_app


class AppFactoryPhase1Tests(unittest.TestCase):
    def test_create_app_is_idempotent(self):
        first = create_app()
        second = create_app()
        self.assertIs(first, second)

    def test_core_routes_are_registered(self):
        flask_app = create_app()
        rules = {rule.rule for rule in flask_app.url_map.iter_rules()}
        self.assertIn("/", rules)
        self.assertIn("/login", rules)
        self.assertIn("/dashboard/<int:student_id>", rules)
        self.assertIn("/webhooks/google-sheets", rules)


if __name__ == "__main__":
    unittest.main()
