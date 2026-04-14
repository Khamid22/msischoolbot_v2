import os
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


class WebRuntimeFlagsTests(unittest.TestCase):
    def test_pwa_registers_sw_with_update_via_cache_none(self):
        pwa_path = os.path.join(ROOT_DIR, "app", "web", "static", "js", "pwa.js")
        with open(pwa_path, "r", encoding="utf-8") as pwa_file:
            source = pwa_file.read()
        self.assertIn('.register("/sw.js", { updateViaCache: "none" })', source)

    def test_telegram_bundle_manifest_order_contains_modular_init(self):
        bundles_builder = os.path.join(ROOT_DIR, "app", "web", "js_bundles.py")
        with open(bundles_builder, "r", encoding="utf-8") as source_file:
            source = source_file.read()
        self.assertIn('"js/telegram/sdk-init.js"', source)
        self.assertIn('"js/telegram/safe-area.js"', source)
        self.assertIn('"js/telegram/fullscreen.js"', source)
        self.assertIn('"js/telegram/swipe.js"', source)
        self.assertIn('"js/telegram/back-button.js"', source)

    def test_admin_resources_api_uses_same_visibility_scope_as_panel(self):
        resource_routes_path = os.path.join(
            ROOT_DIR, "app", "routes", "admin", "resource_routes.py"
        )
        with open(resource_routes_path, "r", encoding="utf-8") as source_file:
            source = source_file.read()
        self.assertIn("svc_list_resources(include_inactive=True)", source)


if __name__ == "__main__":
    unittest.main()
