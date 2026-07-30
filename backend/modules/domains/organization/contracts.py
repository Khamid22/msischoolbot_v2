"""Transaction-aware public contracts for organization data.

Academic use cases may participate in an existing transaction through these
functions without importing the Organization repository directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.organization import repository
from backend.modules.domains.organization.dates import parse_date
from backend.modules.domains.organization.operations import (
    create_class_from_payload,
    create_school_from_payload,
)
from backend.modules.domains.organization.schools import (
    is_public_school_code,
    normalize_school_code,
    student_code_prefix,
)
from backend.modules.domains.organization.subjects import (
    canonical_subject_name,
    subject_short_name,
)
from backend.modules.domains.organization.text import normalize_text


@dataclass(frozen=True)
class SchoolReference:
    school_id: int
    code: str
    name: str


def list_school_references(conn: Connection) -> tuple[SchoolReference, ...]:
    return tuple(
        SchoolReference(
            school_id=int(row["id"]),
            code=str(row["code"] or "").strip(),
            name=str(row["name"] or "").strip(),
        )
        for row in repository.list_school_rows(conn)
    )


def list_public_school_references(conn: Connection) -> tuple[SchoolReference, ...]:
    """List schools classified as public by the Organization domain."""
    return tuple(
        school for school in list_school_references(conn) if is_public_school_code(school.code)
    )


def list_school_rows(conn):
    return repository.list_school_rows(conn)


def list_class_rows(conn):
    return repository.list_class_rows(conn)


def list_subject_rows(conn):
    return repository.list_subject_rows(conn)


def get_school_by_key(conn, school_key):
    return repository.get_school_by_key(conn, school_key)


def get_class(conn, class_id):
    return repository.get_class(conn, class_id)


def get_class_by_school_and_name(conn, school_id, class_name):
    return repository.get_class_by_school_and_name(conn, school_id, class_name)


def insert_class(conn, school_id, class_name, class_code):
    return repository.insert_class(conn, school_id, class_name, class_code)


def upsert_class_student(conn, class_id, student_id):
    return repository.upsert_class_student(conn, class_id, student_id)


__all__ = [
    "SchoolReference",
    "get_class",
    "get_class_by_school_and_name",
    "get_school_by_key",
    "insert_class",
    "is_public_school_code",
    "list_class_rows",
    "list_public_school_references",
    "list_school_rows",
    "list_school_references",
    "list_subject_rows",
    "normalize_school_code",
    "normalize_text",
    "parse_date",
    "canonical_subject_name",
    "create_class_from_payload",
    "create_school_from_payload",
    "subject_short_name",
    "student_code_prefix",
    "upsert_class_student",
]
