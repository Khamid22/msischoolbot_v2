"""HTTP cache policy kept separate from application composition."""

from __future__ import annotations

import os
import re

_NO_STORE = "no-store, max-age=0"
_NO_CACHE_REVALIDATE = "no-cache, no-store, must-revalidate"
_LONG_IMMUTABLE = "public, max-age=31536000, immutable"
_STATIC_DEFAULT = "public, max-age=2592000, immutable"

_HASHED_REACT_ASSET_FILE_RE = re.compile(r"-[A-Za-z0-9_-]{8,}\.(js|css)$")
_VERSIONED_REACT_ENTRY_RE = re.compile(r"^/static/react/app\.(js|css)$")
_VERSIONED_BUNDLE_RE = re.compile(r"^/static/js/bundles/[^/]+\.js$")

_ROLE_PAGE_PREFIXES = (
    "/academic-director",
    "/academic_director",
    "/ceo",
    "/support",
    "/customer-support",
    "/parent",
    "/student",
    "/head-of-department",
    "/head-of-departments",
    "/hr-manager",
    "/account",
)


def resolve_cache_control_header(
    request_path: str,
    query_version: str = "",
) -> str | None:
    if request_path == "/" or request_path.startswith("/dashboard/"):
        return _NO_STORE

    if request_path in _ROLE_PAGE_PREFIXES or request_path.startswith(
        tuple(f"{prefix}/" for prefix in _ROLE_PAGE_PREFIXES)
    ):
        return _NO_STORE

    if request_path.startswith("/api/"):
        return _NO_STORE

    if request_path.startswith("/static/react/"):
        file_name = os.path.basename(request_path)
        if file_name in {"manifest.json", "index.html"}:
            return _NO_CACHE_REVALIDATE
        if _HASHED_REACT_ASSET_FILE_RE.search(file_name):
            return _LONG_IMMUTABLE
        if query_version and _VERSIONED_REACT_ENTRY_RE.match(request_path):
            return _LONG_IMMUTABLE
        return _NO_STORE

    if request_path.startswith("/static/js/bundles/"):
        if query_version and _VERSIONED_BUNDLE_RE.match(request_path):
            return _LONG_IMMUTABLE
        return _NO_STORE

    if request_path.startswith("/static/"):
        return _STATIC_DEFAULT

    return None


__all__ = ["resolve_cache_control_header"]
