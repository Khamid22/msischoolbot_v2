"""Public Customer Support orchestration interface."""

from backend.modules.domains.support_cases.customer_records_contracts import (
    CustomerSupportError,
    SchoolScope,
    SupportActor,
    context,
    create_parent_invite,
    create_payment,
    create_student,
    link_parent_child,
    list_student_payments,
    parent_detail,
    reset_student_access,
    search_records,
    set_parent_lifecycle,
    set_student_lifecycle,
    settle_payment,
    student_detail,
    unlink_parent_child,
    update_parent,
    update_payment,
    update_student,
    void_payment,
)
from backend.modules.people.customer_support.commands import create_customer_support_account
from backend.modules.people.customer_support.dashboard.contracts import (
    GetCustomerSupportDashboard,
)
from backend.modules.people.customer_support.module import PERSON_MODULE
from backend.modules.people.customer_support.parents.contracts import (
    CustomerSupportParentCommands,
    CustomerSupportParentQueries,
)
from backend.modules.people.customer_support.teachers.contracts import (
    CustomerSupportTeacherQueries,
)
from backend.modules.people.customer_support.tickets.contracts import (
    CustomerSupportTicketCommands,
    CustomerSupportTicketQueries,
)

__all__ = [
    "PERSON_MODULE",
    "CustomerSupportError",
    "CustomerSupportParentCommands",
    "CustomerSupportParentQueries",
    "CustomerSupportTeacherQueries",
    "CustomerSupportTicketCommands",
    "CustomerSupportTicketQueries",
    "GetCustomerSupportDashboard",
    "SchoolScope",
    "SupportActor",
    "context",
    "create_customer_support_account",
    "create_parent_invite",
    "create_payment",
    "create_student",
    "link_parent_child",
    "list_student_payments",
    "parent_detail",
    "reset_student_access",
    "search_records",
    "set_parent_lifecycle",
    "set_student_lifecycle",
    "settle_payment",
    "student_detail",
    "unlink_parent_child",
    "update_parent",
    "update_payment",
    "update_student",
    "void_payment",
]
