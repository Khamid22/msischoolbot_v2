from backend.modules.academics.service import _normalize_weekdays


def test_monday_zero_is_preserved_with_other_weekdays():
    assert _normalize_weekdays([0, 2, 4]) == [0, 2, 4]


def test_named_and_numeric_weekdays_are_deduplicated():
    assert _normalize_weekdays(["monday", 0, "2", "friday"]) == [0, 2, 4]
