"""Compatibility shim.

This module moved to app.web.js_bundles. Keep this re-export so existing imports
outside the web layer do not break during rollout.
"""

from app.web.js_bundles import JS_BUNDLES, ensure_js_bundles

__all__ = ["JS_BUNDLES", "ensure_js_bundles"]
