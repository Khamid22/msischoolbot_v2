#!/usr/bin/env python3

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.web.css_bundle import build_css_bundle


def main():
    css_root = REPO_ROOT / "app" / "web" / "static" / "css"
    entry_path = css_root / "main.source.css"
    output_path = css_root / "main.css"
    source_files = build_css_bundle(entry_path, output_path)
    print(f"Bundled {len(source_files)} CSS files into {output_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
