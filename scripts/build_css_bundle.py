import os
import sys


_ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)


from app.css_bundles import ensure_css_bundles


def main():
    ensure_css_bundles("app/web/static")


if __name__ == "__main__":
    main()
