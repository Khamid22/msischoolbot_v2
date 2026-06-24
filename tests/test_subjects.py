"""Canonical subject rules — shared/academics/subjects.py."""

from shared.academics.subjects import (
    canonical_subject_name,
    split_subjects,
    subject_key,
    subject_short_name,
    subject_sort_key,
)


def test_canonical_name_maps_aliases():
    assert canonical_subject_name("math") == "IGCSE Mathematics A"
    assert canonical_subject_name("Chemistry") == "IGCSE Chemistry"
    assert canonical_subject_name("  ENGLISH ") == "English as a Second Language"


def test_canonical_name_passthrough_and_empty():
    assert canonical_subject_name("") == ""
    # Unknown subjects pass through, only outer whitespace trimmed.
    assert canonical_subject_name("  Robotics  ") == "Robotics"


def test_short_name():
    assert subject_short_name("math") == "Math"
    assert subject_short_name("biology") == "Bio"
    assert subject_short_name("") == "Subject"
    # Unknown subject falls back to its first word.
    assert subject_short_name("Creative Writing 101") == "Creative"


def test_subject_key_is_slug():
    assert subject_key("math") == "igcse-mathematics-a"
    assert subject_key("") == "subject"


def test_split_subjects_handles_commas_and_semicolons():
    assert split_subjects("Math, Chemistry; Bio") == ["Math", "Chemistry", "Bio"]
    assert split_subjects("") == []
    assert split_subjects("  Physics  ") == ["Physics"]


def test_sort_key_orders_core_subjects_first():
    subjects = ["physics", "math", "biology", "chemistry", "english"]
    ordered = sorted(subjects, key=subject_sort_key)
    assert ordered == ["math", "english", "chemistry", "biology", "physics"]
    # Unknown subjects sort after the known core ones.
    assert subject_sort_key("Robotics")[0] == 999
