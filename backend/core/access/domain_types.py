"""Canonical role and capability vocabulary."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    CEO = "ceo"
    TEACHER = "teacher"
    CUSTOMER_SUPPORT = "customer_support"
    PARENT = "parent"
    STUDENT = "student"
    ACADEMIC_DIRECTOR = "academic_director"
    HEAD_OF_DEPARTMENT = "head_of_department"
    HR_MANAGER = "hr_manager"


class PersonType(StrEnum):
    CEO = "ceo"
    ACADEMIC_DIRECTOR = "academic_director"
    HEAD_OF_DEPARTMENT = "head_of_department"
    HR_MANAGER = "hr_manager"
    CUSTOMER_SUPPORT = "customer_support"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class Domain(StrEnum):
    IDENTITY = "identity"
    ORGANIZATION = "organization"
    STUDENT_RECORDS = "student_records"
    PARENT_RELATIONSHIPS = "parent_relationships"
    TEACHER_RECORDS = "teacher_records"
    ACADEMICS = "academics"
    RECRUITMENT = "recruitment"
    TEACHER_ACADEMY = "teacher_academy"
    FINANCE = "finance"
    SUPPORT_CASES = "support_cases"
    COMMUNICATIONS = "communications"
    REPORTING = "reporting"


class SchoolScopeMode(StrEnum):
    ALL_SCHOOLS = "all_schools"
    ASSIGNED_SCHOOLS = "assigned_schools"


class ObjectScope(StrEnum):
    ORGANIZATION_WIDE = "organization_wide"
    MANAGED_ACADEMIC_RECORDS = "managed_academic_records"
    ASSIGNED_DEPARTMENTS_AND_SUBJECTS = "assigned_departments_and_subjects"
    ASSIGNED_RECRUITMENT_RECORDS = "assigned_recruitment_records"
    SUPPORTED_PEOPLE = "supported_people"
    OWN_AND_ASSIGNED_RECORDS = "own_and_assigned_records"
    OWN_RECORDS = "own_records"
    LINKED_CHILDREN = "linked_children"


class Capability(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_STUDENTS = "manage_students"
    MANAGE_TEACHERS = "manage_teachers"
    MANAGE_PARENTS = "manage_parents"
    MANAGE_ANNOUNCEMENTS = "manage_announcements"
    MANAGE_RESOURCES = "manage_resources"
    MANAGE_COMPLAINTS = "manage_complaints"
    MANAGE_PAYMENTS = "manage_payments"
    MANAGE_ACADEMICS = "manage_academics"
    MANAGE_RECRUITMENT = "manage_recruitment"
    VIEW_GLOBAL_REPORTS = "view_global_reports"
    VIEW_FINANCE_SUMMARY = "view_finance_summary"
    VIEW_SCHOOL_PERFORMANCE = "view_school_performance"
    VIEW_STAFF_SUMMARY = "view_staff_summary"
    VIEW_RECRUITMENT = "view_recruitment"
    FINALIZE_RECRUITMENT = "finalize_recruitment"
    VIEW_TICKETS = "view_tickets"
    REPLY_TICKETS = "reply_tickets"
    ASSIGN_TICKETS = "assign_tickets"
    ESCALATE_TICKETS = "escalate_tickets"
    RESOLVE_TICKETS = "resolve_tickets"
    VIEW_PARENT_CONTACTS = "view_parent_contacts"
    VIEW_STUDENT_BASIC_INFO = "view_student_basic_info"
    VIEW_TEACHER_SUPPORT_INFO = "view_teacher_support_info"
    MANAGE_TEACHER_ACCESS = "manage_teacher_access"
    MANAGE_STUDENT_RECORDS = "manage_student_records"
    MANAGE_PARENT_RECORDS = "manage_parent_records"
    MANAGE_STUDENT_ACCESS = "manage_student_access"
    VIEW_OWN_DASHBOARD = "view_own_dashboard"
    VIEW_OWN_ATTENDANCE = "view_own_attendance"
    VIEW_OWN_GRADES = "view_own_grades"
    VIEW_RESOURCES = "view_resources"
    USE_STUDENT_CHAT = "use_student_chat"
    VIEW_CHILD_PROGRESS = "view_child_progress"
    VIEW_CHILD_ATTENDANCE = "view_child_attendance"
    VIEW_CHILD_GRADES = "view_child_grades"
    VIEW_PAYMENTS = "view_payments"
    CONTACT_SUPPORT = "contact_support"
    VIEW_ACADEMIC_REPORTS = "view_academic_reports"
    VIEW_TEACHER_PERFORMANCE = "view_teacher_performance"
    OBSERVE_LESSONS = "observe_lessons"
    MANAGE_CURRICULUM_PROGRESS = "manage_curriculum_progress"
    REVIEW_DEMO_LESSONS = "review_demo_lessons"
    EVALUATE_RECRUITMENT_CANDIDATES = "evaluate_recruitment_candidates"
    MANAGE_TEACHER_ACADEMY = "manage_teacher_academy"
    VIEW_TEACHER_PROFILES = "view_teacher_profiles"


__all__ = [
    "Capability",
    "Domain",
    "ObjectScope",
    "PersonType",
    "Role",
    "SchoolScopeMode",
]
