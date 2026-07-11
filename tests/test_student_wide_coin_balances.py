from pathlib import Path


def test_coin_balances_are_aggregated_once_per_student_across_subjects():
    paths = [
        Path("backend/modules/academics/repository.py"),
        Path("backend/modules/reporting/summary_repository.py"),
        Path("backend/modules/parent_access/repository.py"),
        Path("backend/modules/academics/operations.py"),
    ]

    for path in paths:
        source = path.read_text()
        assert "coins.group_id" not in source, path
        assert "GROUP BY student_id" in source, path
