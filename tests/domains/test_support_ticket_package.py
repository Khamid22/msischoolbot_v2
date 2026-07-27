"""Focused checks for the Support Cases ticket package boundary."""

import pytest

from backend.modules.domains.support_cases import repository as legacy_repository
from backend.modules.domains.support_cases import service as legacy_service
from backend.modules.domains.support_cases.tickets import (
    contracts,
    repository,
    service,
    transactional,
)
from backend.modules.domains.support_cases.tickets.domain_types import (
    VALID_TICKET_CATEGORIES,
    VALID_TICKET_STATUSES,
    TicketCategory,
    TicketStatus,
    normalize_ticket_category,
    normalize_ticket_status,
)


def test_ticket_domain_vocabulary_matches_persisted_values():
    assert {
        "new",
        "in_progress",
        "escalated",
        "resolved",
    } == VALID_TICKET_STATUSES
    assert {
        "complaint",
        "direct_contact",
        "payment",
        "teacher",
        "lesson_quality",
        "schedule",
        "attendance",
        "technical",
        "account",
        "other",
    } == VALID_TICKET_CATEGORIES
    assert TicketStatus.IN_PROGRESS.value == "in_progress"
    assert TicketCategory.LESSON_QUALITY.value == "lesson_quality"


def test_ticket_vocabulary_normalization_preserves_legacy_behavior():
    assert normalize_ticket_status(" Open ") == "in_progress"
    assert normalize_ticket_status("done") == "resolved"
    assert normalize_ticket_status("unknown") == "new"
    assert normalize_ticket_category("Lesson Quality") == "lesson_quality"
    assert normalize_ticket_category("not-a-category") == "other"


def test_legacy_modules_are_thin_compatibility_facades():
    assert legacy_service.create_complaint is service.create_complaint
    assert legacy_service.add_complaint_reply is service.add_complaint_reply
    assert legacy_repository.get_parent_complaint_row is repository.get_parent_complaint_row
    assert (
        legacy_repository.insert_complaint_message_row
        is repository.insert_complaint_message_row
    )


def test_ticket_contract_exposes_business_names_without_changing_payload(monkeypatch):
    expected = {"id": 41, "status": "new"}
    monkeypatch.setattr(service, "get_complaint", lambda ticket_id: expected)

    assert contracts.get_ticket(41) is expected
    assert contracts.get_complaint(41) is expected


def test_parent_ticket_requires_a_linked_child_before_insert(monkeypatch):
    monkeypatch.setattr(
        transactional,
        "parent_can_access_student_on_connection",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        repository,
        "insert_parent_complaint_row",
        lambda *args, **kwargs: pytest.fail("An unlinked child must never be inserted."),
    )

    with pytest.raises(ValueError, match="not linked"):
        transactional.create_parent_ticket(
            object(),
            parent_id=9,
            student_row_id=71,
            category=TicketCategory.ATTENDANCE,
            topic="Attendance question",
            message="Please check the attendance record.",
        )


def test_parent_reply_locks_ticket_and_rejects_resolved_conversation(monkeypatch):
    captured = {}

    def locked_row(conn, *, ticket_id, parent_id, for_update):
        captured.update(
            ticket_id=ticket_id,
            parent_id=parent_id,
            for_update=for_update,
        )
        return {"status": TicketStatus.RESOLVED.value}

    monkeypatch.setattr(repository, "get_parent_ticket_row", locked_row)

    with pytest.raises(transactional.TicketLifecycleError, match="read-only"):
        transactional.reply_to_parent_ticket(
            object(),
            parent_id=9,
            ticket_id=51,
            body="One more question",
        )

    assert captured == {"ticket_id": 51, "parent_id": 9, "for_update": True}
