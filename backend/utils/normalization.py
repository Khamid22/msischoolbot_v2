"""Compatibility shim — the canonical normalization rules live in ``database.academics.canonical``.

This module re-exports the canonical helpers so existing
``backend.utils.normalization`` imports keep working. New code should import
from ``database.academics.canonical`` directly.

The one wrinkle: this layer historically defaulted ``normalize_school_code`` to
``default=""`` (empty input stays empty), whereas canonical defaults to the active
school code. We preserve the empty-stays-empty default here to avoid changing the
behavior of existing callers.
"""

from database.academics import canonical
from database.academics.canonical import *  # noqa: F401,F403  (re-export the canonical surface)


def normalize_school_code(value, default=""):
    return canonical.normalize_school_code(value, default=default)


__all__ = list(canonical.__all__)
