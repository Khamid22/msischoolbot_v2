"""Organization domain services."""


from backend.modules.organization import repository as academic_repository
from backend.modules.academics.foundation import (
    _connect, _canonical_subject_name, _canonical_subject_key, _canonical_subject_short,
)

def create_school(name, code=""):
    import re

    name = str(name or "").strip()
    if not name:
        raise ValueError("School name is required.")
    code_value = str(code or "").strip().casefold()
    if not code_value:
        code_value = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "school"
    with _connect() as conn:
        existing = academic_repository.get_school_by_key(conn, code_value)
        if existing:
            raise ValueError(f"A client school with code '{code_value}' already exists.")
        academic_repository.insert_school(conn, code_value, name)
        conn.commit()


def create_subject(school_code, name, code=""):
    # Subjects are universal in msi_v2; the school_code is accepted for backward
    # compatibility with the old per-school form but no longer scopes the row.
    name = _canonical_subject_name(name)
    key = _canonical_subject_key(name)
    short_name = _canonical_subject_short(name)
    with _connect() as conn:
        academic_repository.upsert_subject(conn, key, name, short_name)
        conn.commit()


def create_class(school_code, class_name, class_code=""):
    class_name = str(class_name or "").strip()
    class_code = str(class_code or "").strip()
    if not class_name:
        raise ValueError("Class name is required.")
    with _connect() as conn:
        school = academic_repository.get_school_by_key(conn, school_code)
        if not school:
            raise ValueError("Client school was not found.")
        existing = academic_repository.get_class_by_school_and_name(
            conn, int(school["id"]), class_name
        )
        if existing:
            raise ValueError("A class with this name already exists in the selected school.")
        row = academic_repository.insert_class(
            conn, int(school["id"]), class_name, class_code
        )
        conn.commit()
        return dict(row)
