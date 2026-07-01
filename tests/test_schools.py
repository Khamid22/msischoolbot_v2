"""School code canonicalization — shared/academics/schools.py."""

from database.academics.schools import (
    normalize_admin_school_filter,
    normalize_school_code,
    school_display_name,
    student_code_prefix,
)


def test_normalize_school_code_aliases():
    assert normalize_school_code("School 5") == "school5"
    assert normalize_school_code("school-5") == "school5"
    assert normalize_school_code("Sehriyo School") == "sehriyo"


def test_normalize_school_code_default_and_passthrough():
    assert normalize_school_code("") == "school5"  # default
    # Unknown codes pass through, casefolded.
    assert normalize_school_code("Branch9") == "branch9"


def test_display_name():
    assert school_display_name("school5") == "School 5"
    assert school_display_name("sehriyo") == "Sehriyo"
    assert school_display_name("unknown") == "School 5"  # default name


def test_student_code_prefix():
    assert student_code_prefix("school5") == "MSI"
    assert student_code_prefix("sehriyo") == "MSIS"


def test_admin_school_filter():
    assert normalize_admin_school_filter("") == "all"
    assert normalize_admin_school_filter("school5") == "school5"
    # A value that is not a known canonical code collapses to "all".
    assert normalize_admin_school_filter("School 5") == "all"
