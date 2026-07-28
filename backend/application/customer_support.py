"""Application composition for Customer Support use cases."""

from backend.application.container import AppContainer
from backend.modules.domains.admissions.public_service import PublicAdmissions
from backend.modules.domains.reporting.customer_support.postgres_repository import (
    PostgresCustomerSupportDashboardRepository,
)
from backend.modules.domains.reporting.customer_support.queries import (
    CustomerSupportDashboardQueries,
)
from backend.modules.domains.teacher_records.support_queries import (
    PostgresTeacherSupportReader,
)
from backend.modules.people.customer_support.admissions.use_cases import (
    CustomerSupportAdmissions,
)
from backend.modules.people.customer_support.dashboard.queries import (
    GetCustomerSupportDashboard,
)
from backend.modules.people.customer_support.payments.use_cases import (
    CustomerSupportPayments,
)
from backend.modules.people.customer_support.scope import CustomerSupportScopeResolver
from backend.modules.people.customer_support.teachers.queries import (
    CustomerSupportTeacherQueries,
)
from backend.modules.people.customer_support.tickets.use_cases import (
    CustomerSupportTickets,
)


def build_customer_support_teacher_queries(
    container: AppContainer,
) -> CustomerSupportTeacherQueries:
    return CustomerSupportTeacherQueries(
        reader=PostgresTeacherSupportReader(container.unit_of_work_factory),
        scope_resolver=CustomerSupportScopeResolver(container.unit_of_work_factory),
    )


def build_customer_support_tickets(
    container: AppContainer,
) -> CustomerSupportTickets:
    return CustomerSupportTickets(
        unit_of_work_factory=container.unit_of_work_factory,
        scope_resolver=CustomerSupportScopeResolver(container.unit_of_work_factory),
    )


def build_customer_support_dashboard(
    container: AppContainer,
) -> GetCustomerSupportDashboard:
    scope_resolver = CustomerSupportScopeResolver(container.unit_of_work_factory)
    return GetCustomerSupportDashboard(
        reader=CustomerSupportDashboardQueries(
            unit_of_work_factory=container.unit_of_work_factory,
            repository=PostgresCustomerSupportDashboardRepository(),
            clock=container.clock,
        ),
        scope_resolver=scope_resolver,
    )


def build_customer_support_admissions(
    container: AppContainer,
) -> CustomerSupportAdmissions:
    return CustomerSupportAdmissions(
        unit_of_work_factory=container.unit_of_work_factory,
        scope_resolver=CustomerSupportScopeResolver(container.unit_of_work_factory),
        storage_settings=container.settings.storage,
        public_base_url=container.settings.payme.callback_base_url,
    )


def build_customer_support_payments(
    container: AppContainer,
) -> CustomerSupportPayments:
    return CustomerSupportPayments(
        unit_of_work_factory=container.unit_of_work_factory,
        scope_resolver=CustomerSupportScopeResolver(container.unit_of_work_factory),
    )


def build_public_admissions(container: AppContainer) -> PublicAdmissions:
    return PublicAdmissions(
        unit_of_work_factory=container.unit_of_work_factory,
        payme_settings=container.settings.payme,
        storage_settings=container.settings.storage,
    )


__all__ = [
    "build_customer_support_admissions",
    "build_customer_support_dashboard",
    "build_customer_support_payments",
    "build_customer_support_teacher_queries",
    "build_customer_support_tickets",
    "build_public_admissions",
]
