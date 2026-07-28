"""Typed, read-only parent workspace queries."""

from __future__ import annotations

from statistics import mean

from backend.core.access.context import ActorContext
from backend.core.access.domain_types import Capability
from backend.core.api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.communications.contracts import list_parent_announcements
from backend.modules.domains.finance.contracts import (
    PaymentRecord,
    get_account_billing_access,
    list_payment_records,
    parent_invoice_checkout_data,
)
from backend.modules.domains.parent_relationships.contracts import (
    get_parent_preference,
    list_parent_client_children,
)
from backend.modules.domains.support_cases.tickets.contracts import (
    get_parent_ticket,
    list_parent_tickets,
)
from backend.modules.people.parent.policies import (
    ParentRecordNotFoundError,
    require_parent_capability,
)
from backend.modules.people.parent.schemas import (
    ParentAcademicIndicatorResponse,
    ParentAnnouncementResponse,
    ParentBillingStatusResponse,
    ParentChildrenResponse,
    ParentChildResponse,
    ParentLessonResponse,
    ParentOverviewResponse,
    ParentPaymentRecordResponse,
    ParentPaymentsResponse,
    ParentPaymentSummaryResponse,
    ParentPreferenceResponse,
    ParentTicketResponse,
    ParentTicketsResponse,
    ParentUpdatesResponse,
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _number(value: object) -> float:
    try:
        return float(str(value or 0))
    except (TypeError, ValueError):
        return 0


def _integer(value: object) -> int:
    try:
        return int(str(value or 0))
    except (TypeError, ValueError):
        return 0


def _child(raw: dict) -> ParentChildResponse:
    indicators = [
        ParentAcademicIndicatorResponse(
            enrollment_id=_integer(item.get("enrollment_id")),
            subject_name=_text(item.get("subject_name")),
            subject_display_name=_text(item.get("subject_display_name")),
            subject_short=_text(item.get("subject_short")),
            group_name=_text(item.get("group_name")),
            aap=_number(item.get("aap")),
            attendance_rate=_integer(item.get("ar")),
            exam_performance=_integer(item.get("ep")),
            total_coins=_integer(item.get("total_coins")),
            completed_lessons=_integer(item.get("program_completed_lessons")),
            total_lessons=_integer(item.get("program_total_lessons")),
            completion_rate=_integer(item.get("program_completion_rate")),
            updated_at=_text(item.get("updated_at")),
        )
        for item in raw.get("academic_indicators", [])
        if isinstance(item, dict)
    ]
    lessons = [
        ParentLessonResponse(
            date=_text(item.get("date")),
            subject_name=_text(item.get("subject_name")),
            subject_display_name=_text(item.get("subject_display_name")),
            group_name=_text(item.get("group_name")),
            lesson_number=_text(item.get("lesson_number")),
            topic=_text(item.get("topic")),
            attendance_status=_text(item.get("attendance_status")),
        )
        for item in raw.get("recent_lessons", [])
        if isinstance(item, dict)
    ]
    summary = raw.get("payment_summary")
    summary = summary if isinstance(summary, dict) else {}
    student_row_id = _integer(raw.get("student_row_id") or raw.get("id"))
    subjects = _text(raw.get("subjects"))
    return ParentChildResponse(
        student_row_id=student_row_id,
        student_code=_text(raw.get("student_code") or raw.get("student_id")),
        full_name=_text(raw.get("full_name") or raw.get("student_full_name")) or "Student",
        school_name=_text(raw.get("school_name")) or "MSI School",
        class_name=_text(raw.get("class_name")),
        photo_url=_text(raw.get("photo_url")),
        subjects=[part.strip() for part in subjects.split(",") if part.strip()],
        academic_indicators=indicators,
        recent_lessons=lessons,
        payment_summary=ParentPaymentSummaryResponse(
            currency=_text(summary.get("currency")) or "UZS",
            debt_total=_number(summary.get("debt_total")),
            due_total=_number(summary.get("due_total")),
            upcoming_total=_number(summary.get("upcoming_total")),
            paid_total=_number(summary.get("paid_total")),
        ),
        dashboard_url=f"/parent/dashboard/{student_row_id}",
    )


class ParentQueries:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def list_children(self, actor: ActorContext) -> ParentChildrenResponse:
        parent_id = require_parent_capability(actor, Capability.VIEW_DASHBOARD)
        raw_children = list_parent_client_children(parent_id)
        return ParentChildrenResponse(
            items=[_child(item) for item in raw_children if isinstance(item, dict)]
        )

    def get_preference(self, actor: ActorContext) -> ParentPreferenceResponse:
        parent_id = require_parent_capability(actor, Capability.VIEW_DASHBOARD)
        with self._unit_of_work_factory.read() as unit_of_work:
            preference = get_parent_preference(
                unit_of_work.conn,
                parent_id=parent_id,
            )
        if preference is None:
            raise ParentRecordNotFoundError("Parent account was not found.")
        return ParentPreferenceResponse(**preference.__dict__)

    def get_billing_status(self, actor: ActorContext) -> ParentBillingStatusResponse:
        require_parent_capability(actor, Capability.VIEW_PAYMENTS)
        if actor.account_id is None:
            raise ParentRecordNotFoundError("Parent account was not found.")
        with self._unit_of_work_factory.read() as unit_of_work:
            status = get_account_billing_access(
                unit_of_work.conn,
                account_id=actor.account_id,
            )
        return ParentBillingStatusResponse.model_validate(status.model_dump())

    def get_child(
        self,
        actor: ActorContext,
        student_row_id: int,
    ) -> ParentChildResponse:
        for child in self.list_children(actor).items:
            if child.student_row_id == student_row_id:
                return child
        raise ParentRecordNotFoundError("Linked child was not found.")

    def list_updates(
        self,
        actor: ActorContext,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> ParentUpdatesResponse:
        require_parent_capability(actor, Capability.VIEW_DASHBOARD)
        with self._unit_of_work_factory.read() as unit_of_work:
            items = list_parent_announcements(unit_of_work.conn, limit=limit)
        return ParentUpdatesResponse(
            items=[
                ParentAnnouncementResponse(
                    announcement_id=item.announcement_id,
                    title=item.title,
                    body=item.body,
                    priority=item.priority,
                    is_pinned=item.is_pinned,
                    published_at=item.published_at,
                )
                for item in items
            ]
        )

    def list_payments(
        self,
        actor: ActorContext,
        *,
        student_row_id: int | None = None,
    ) -> ParentPaymentsResponse:
        require_parent_capability(actor, Capability.VIEW_PAYMENTS)
        children = self.list_children(actor).items
        if student_row_id is not None:
            children = [
                child for child in children if child.student_row_id == student_row_id
            ]
            if not children:
                raise ParentRecordNotFoundError("Linked child was not found.")
        records: list[PaymentRecord] = []
        with self._unit_of_work_factory.read() as unit_of_work:
            for child in children:
                records.extend(
                    list_payment_records(
                        unit_of_work.conn,
                        student_row_id=child.student_row_id,
                    )
                )
        currency = next((record.currency for record in records if record.currency), "UZS")
        summary = ParentPaymentSummaryResponse(
            currency=currency,
            debt_total=sum(record.amount for record in records if record.state == "debt"),
            due_total=sum(record.amount for record in records if record.state == "due"),
            upcoming_total=sum(
                record.amount for record in records if record.state == "upcoming"
            ),
            paid_total=sum(record.amount for record in records if record.state == "paid"),
        )
        return ParentPaymentsResponse(
            items=[ParentPaymentRecordResponse.from_record(record) for record in records],
            summary=summary,
        )

    def get_invoice_checkout(
        self,
        actor: ActorContext,
        *,
        invoice_id: int,
    ) -> tuple[int, str]:
        parent_id = require_parent_capability(actor, Capability.VIEW_PAYMENTS)
        with self._unit_of_work_factory.read() as unit_of_work:
            return parent_invoice_checkout_data(
                unit_of_work.conn,
                parent_id=parent_id,
                invoice_id=invoice_id,
            )

    def list_tickets(
        self,
        actor: ActorContext,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> ParentTicketsResponse:
        parent_id = require_parent_capability(actor, Capability.CONTACT_SUPPORT)
        with self._unit_of_work_factory.read() as unit_of_work:
            tickets = list_parent_tickets(
                unit_of_work.conn,
                parent_id=parent_id,
                limit=limit,
            )
        return ParentTicketsResponse(
            items=[ParentTicketResponse.from_data(ticket) for ticket in tickets]
        )

    def get_ticket(self, actor: ActorContext, ticket_id: int) -> ParentTicketResponse:
        parent_id = require_parent_capability(actor, Capability.CONTACT_SUPPORT)
        with self._unit_of_work_factory.read() as unit_of_work:
            ticket = get_parent_ticket(
                unit_of_work.conn,
                parent_id=parent_id,
                ticket_id=ticket_id,
            )
        return ParentTicketResponse.from_data(ticket)

    def overview(self, actor: ActorContext) -> ParentOverviewResponse:
        children = self.list_children(actor).items
        updates = self.list_updates(actor, limit=3).items
        payments = self.list_payments(actor)
        tickets = self.list_tickets(actor, limit=MAX_PAGE_SIZE).items
        attendance = [
            indicator.attendance_rate
            for child in children
            for indicator in child.academic_indicators
        ]
        completion = [
            indicator.completion_rate
            for child in children
            for indicator in child.academic_indicators
        ]
        return ParentOverviewResponse(
            children=children,
            latest_updates=updates,
            payment_summary=payments.summary,
            open_ticket_count=sum(ticket.status.value != "resolved" for ticket in tickets),
            average_attendance_rate=round(mean(attendance)) if attendance else None,
            average_completion_rate=round(mean(completion)) if completion else None,
            preference=self.get_preference(actor),
        )


__all__ = ["ParentQueries"]
