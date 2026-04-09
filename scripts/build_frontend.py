import os
import subprocess
import sys


_ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)


from app.js_bundles import ensure_js_bundles


def _remove_unused_vite_shell():
    react_root = os.path.join(_ROOT_DIR, "app", "web", "static", "react")
    react_index_path = os.path.join(react_root, "index.html")
    if os.path.isfile(react_index_path):
        os.remove(react_index_path)


def main():
    ensure_js_bundles("app/web/static")
    frontend_dir = os.path.join(_ROOT_DIR, "app", "web", "frontend")
    if os.path.isdir(frontend_dir):
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        _remove_unused_vite_shell()


if __name__ == "__main__":
    main()
