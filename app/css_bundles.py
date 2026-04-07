from __future__ import annotations

import os
from typing import Dict, Iterable


_CORE_SOURCES = (
    "css/settings/tokens.css",
    "css/generic/reset.css",
    "css/elements/typography.css",
    "css/layouts/app-shell.css",
    "css/components/alerts.css",
    "css/components/forms.css",
    "css/components/buttons.css",
    "css/components/avatar-badges.css",
    "css/platform/telegram.css",
    "css/utilities/motion.css",
)


CSS_BUNDLES: Dict[str, tuple[str, ...]] = {
    "core.css": _CORE_SOURCES,
    "portal.css": _CORE_SOURCES + (
        "css/pages/portal-shell.css",
    ),
    "admin-overview.css": (
        "css/components/tables.css",
        "css/pages/admin-core.css",
        "css/pages/portal-admin.css",
        "css/pages/admin-overview.css",
    ),
    "admin-management.css": (
        "css/components/tables.css",
        "css/pages/admin-core.css",
        "css/pages/portal-admin.css",
        "css/pages/admin-management.css",
    ),
    "admin-profile.css": _CORE_SOURCES + (
        "css/pages/portal-shell.css",
        "css/pages/admin-core.css",
        "css/pages/admin-profile.css",
    ),
    "student-dashboard.css": _CORE_SOURCES + (
        "css/components/overlays.css",
        "css/pages/student-shell.css",
        "css/pages/student-dashboard.css",
    ),
    "student-resources.css": _CORE_SOURCES + (
        "css/components/overlays.css",
        "css/pages/student-shell.css",
        "css/pages/student-resources.css",
    ),
    "student-rating.css": _CORE_SOURCES + (
        "css/components/tables.css",
        "css/pages/student-shell.css",
        "css/pages/student-rating.css",
    ),
    "student-aap.css": _CORE_SOURCES + (
        "css/components/tables.css",
        "css/pages/student-shell.css",
        "css/pages/student-aap.css",
    ),
}


def _read_sources(static_root: str, relative_paths: Iterable[str]) -> str:
    sections = []
    for relative_path in relative_paths:
        source_path = os.path.join(static_root, *relative_path.split("/"))
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Missing CSS source file: {source_path}")

        with open(source_path, "r", encoding="utf-8") as source_file:
            source_text = source_file.read().rstrip()

        sections.append(f"/* Source: {relative_path} */\n{source_text}\n")

    return "\n".join(sections).rstrip() + "\n"


def ensure_css_bundles(static_root: str) -> dict[str, str]:
    bundles_root = os.path.join(static_root, "css", "bundles")
    os.makedirs(bundles_root, exist_ok=True)

    expected_names = set(CSS_BUNDLES)
    for file_name in os.listdir(bundles_root):
        if not file_name.endswith(".css") or file_name in expected_names:
            continue
        stale_path = os.path.join(bundles_root, file_name)
        if os.path.isfile(stale_path):
            os.remove(stale_path)

    created_paths = {}
    for bundle_name, relative_paths in CSS_BUNDLES.items():
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


__all__ = ["CSS_BUNDLES", "ensure_css_bundles"]
