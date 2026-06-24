"""Complaint/ticket status + category normalization.

These guard the support-ticket workflow: the backend stores only
new / in_progress / escalated / resolved, and the React helpdesk relies on
aliases (open -> in_progress, closed/done -> resolved) resolving consistently.
"""

from web.backend.domains.complaints.service import (
    _normalize_category,
    _normalize_status,
)


def test_status_aliases():
    assert _normalize_status("open") == "in_progress"
    assert _normalize_status("progress") == "in_progress"
    assert _normalize_status("done") == "resolved"
    assert _normalize_status("closed") == "resolved"


def test_status_passthrough_for_valid_values():
    for value in ("new", "in_progress", "escalated", "resolved"):
        assert _normalize_status(value) == value
    assert _normalize_status("  RESOLVED  ") == "resolved"


def test_status_unknown_defaults_to_new():
    assert _normalize_status("garbage") == "new"
    assert _normalize_status("") == "new"
    assert _normalize_status(None) == "new"


def test_category_normalization():
    assert _normalize_category("lesson quality") == "lesson_quality"
    assert _normalize_category("direct-contact") == "direct_contact"
    assert _normalize_category("payment") == "payment"
    # Unknown categories collapse to "other".
    assert _normalize_category("nonsense") == "other"
    assert _normalize_category("") == "other"
