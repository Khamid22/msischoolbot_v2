import json
import os
import tempfile
import time
import unittest

from flask import Flask

from app.web.render import render_react_page


class RenderAssetsTests(unittest.TestCase):
    def _create_app(self, static_root: str, version: str = "42") -> Flask:
        app = Flask(__name__, static_folder=static_root, static_url_path="/static")
        app.config["ASSET_VERSION"] = version

        @app.get("/manifest.webmanifest", endpoint="system.manifest")
        def manifest():
            return "{}", 200, {"Content-Type": "application/manifest+json"}

        return app

    def test_render_uses_manifest_hashed_assets_and_script_order(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            static_root = os.path.join(tmp_dir, "static")
            react_root = os.path.join(static_root, "react")
            os.makedirs(react_root, exist_ok=True)
            manifest_path = os.path.join(react_root, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as manifest_file:
                json.dump(
                    {
                        "index.html": {
                            "file": "assets/index-abc123def456.js",
                            "css": ["assets/index-abc123def456.css"],
                        }
                    },
                    manifest_file,
                )

            app = self._create_app(static_root, version="999")
            with app.app_context():
                with app.test_request_context("/"):
                    html = render_react_page("login", {}, telegram=True)

            self.assertIn('/static/react/assets/index-abc123def456.css"', html)
            self.assertIn('/static/react/assets/index-abc123def456.js"', html)
            self.assertIn('dns-prefetch" href="//telegram.org"', html)
            self.assertIn('preconnect" href="https://telegram.org"', html)

            tg_sdk_pos = html.find("telegram-web-app.js")
            tg_base_pos = html.find("js/bundles/telegram-base.js")
            app_js_pos = html.find("assets/index-abc123def456.js")
            self.assertTrue(tg_sdk_pos != -1 and tg_base_pos != -1 and app_js_pos != -1)
            self.assertLess(tg_sdk_pos, tg_base_pos)
            self.assertLess(tg_base_pos, app_js_pos)

    def test_render_falls_back_to_versioned_static_assets_when_manifest_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            static_root = os.path.join(tmp_dir, "static")
            os.makedirs(os.path.join(static_root, "react"), exist_ok=True)

            app = self._create_app(static_root, version="77")
            with app.app_context():
                with app.test_request_context("/"):
                    html = render_react_page("login", {}, telegram=False)

            self.assertIn('/static/react/app.css?v=77"', html)
            self.assertIn('/static/react/app.js?v=77"', html)

    def test_render_speed(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            static_root = os.path.join(tmp_dir, "static")
            os.makedirs(os.path.join(static_root, "react"), exist_ok=True)
            app = self._create_app(static_root, version="1")

            with app.app_context():
                with app.test_request_context("/"):
                    runs = 200
                    started = time.perf_counter()
                    for _ in range(runs):
                        render_react_page("login", {"x": 1}, telegram=True)
                    elapsed = time.perf_counter() - started
                    avg_ms = (elapsed / runs) * 1000

            self.assertLess(avg_ms, 5.0, f"render_react_page too slow: {avg_ms:.2f}ms avg")


if __name__ == "__main__":
    unittest.main()
