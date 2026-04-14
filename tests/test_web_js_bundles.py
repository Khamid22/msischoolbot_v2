import os
import tempfile
import time
import unittest

from app.web.js_bundles import JS_BUNDLES, ensure_js_bundles


class JsBundlesTests(unittest.TestCase):
    def _write_source_tree(self, static_root: str):
        for relative_path in JS_BUNDLES["telegram-base.js"]:
            full_path = os.path.join(static_root, *relative_path.split("/"))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as source_file:
                source_file.write(f"console.log('{relative_path}');\n")

    def test_ensure_js_bundles_creates_bundle_and_prunes_stale_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            static_root = os.path.join(tmp_dir, "static")
            bundles_root = os.path.join(static_root, "js", "bundles")
            os.makedirs(bundles_root, exist_ok=True)
            stale_path = os.path.join(bundles_root, "stale.js")
            with open(stale_path, "w", encoding="utf-8") as stale_file:
                stale_file.write("stale")

            self._write_source_tree(static_root)
            created = ensure_js_bundles(static_root)
            bundle_path = created["telegram-base.js"]

            self.assertTrue(os.path.isfile(bundle_path))
            self.assertFalse(os.path.exists(stale_path))
            with open(bundle_path, "r", encoding="utf-8") as bundle_file:
                content = bundle_file.read()
            for relative_path in JS_BUNDLES["telegram-base.js"]:
                self.assertIn(f"/* Source: {relative_path} */", content)

    def test_ensure_js_bundles_idempotent_and_fast(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            static_root = os.path.join(tmp_dir, "static")
            self._write_source_tree(static_root)
            ensure_js_bundles(static_root)

            runs = 30
            started = time.perf_counter()
            for _ in range(runs):
                ensure_js_bundles(static_root)
            elapsed = time.perf_counter() - started
            avg_ms = (elapsed / runs) * 1000

            # Keep threshold generous for CI variability.
            self.assertLess(avg_ms, 50.0, f"Bundle regeneration too slow: {avg_ms:.2f}ms avg")


if __name__ == "__main__":
    unittest.main()
