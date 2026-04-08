from __future__ import annotations

import os
from typing import Dict, Iterable


JS_BUNDLES: Dict[str, tuple[str, ...]] = {
    "telegram-base.js": (
        "js/telegram-init.js",
        "js/pwa.js",
    ),
}


def _read_sources(static_root: str, relative_paths: Iterable[str]) -> str:
    sections = []
    for relative_path in relative_paths:
        source_path = os.path.join(static_root, *relative_path.split("/"))
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Missing JS source file: {source_path}")

        with open(source_path, "r", encoding="utf-8") as source_file:
            source_text = source_file.read().rstrip()

        sections.append(f"/* Source: {relative_path} */\n{source_text}\n")

    return ";\n\n".join(section.rstrip() for section in sections).rstrip() + "\n"


def ensure_js_bundles(static_root: str) -> dict[str, str]:
    bundles_root = os.path.join(static_root, "js", "bundles")
    os.makedirs(bundles_root, exist_ok=True)

    expected_names = set(JS_BUNDLES)
    for file_name in os.listdir(bundles_root):
        if not file_name.endswith(".js") or file_name in expected_names:
            continue
        stale_path = os.path.join(bundles_root, file_name)
        if os.path.isfile(stale_path):
            os.remove(stale_path)

    created_paths = {}
    for bundle_name, relative_paths in JS_BUNDLES.items():
        bundle_path = os.path.join(bundles_root, bundle_name)
        bundle_text = _read_sources(static_root, relative_paths)

        existing_text = None
        if os.path.isfile(bundle_path):
            with open(bundle_path, "r", encoding="utf-8") as bundle_file:
                existing_text = bundle_file.read()

        if existing_text != bundle_text:
            with open(bundle_path, "w", encoding="utf-8") as bundle_file:
                bundle_file.write(bundle_text)

        created_paths[bundle_name] = bundle_path

    return created_paths


__all__ = ["JS_BUNDLES", "ensure_js_bundles"]
