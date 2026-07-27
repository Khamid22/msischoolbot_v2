"""Application composition for Customer Support use cases."""

from backend.application.container import AppContainer
from backend.modules.domains.teacher_records.support_queries import (
    PostgresTeacherSupportReader,
)
from backend.modules.people.customer_support.scope import CustomerSupportScopeResolver
from backend.modules.people.customer_support.teachers.queries import (
    CustomerSupportTeacherQueries,
)


def build_customer_support_teacher_queries(
    container: AppContainer,
) -> CustomerSupportTeacherQueries:
    return CustomerSupportTeacherQueries(
        reader=PostgresTeacherSupportReader(container.unit_of_work_factory),
        scope_resolver=CustomerSupportScopeResolver(container.unit_of_work_factory),
    )


__all__ = ["build_customer_support_teacher_queries"]
