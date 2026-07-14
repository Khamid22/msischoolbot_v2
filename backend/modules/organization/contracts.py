"""Transaction-aware public contracts for organization data.

Academic use cases may participate in an existing transaction through these
functions without importing the Organization repository directly.
"""

from backend.modules.organization import repository


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
    "get_class",
    "get_class_by_school_and_name",
    "get_school_by_key",
    "insert_class",
    "list_class_rows",
    "list_school_rows",
    "list_subject_rows",
    "upsert_class_student",
]
