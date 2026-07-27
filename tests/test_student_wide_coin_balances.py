from pathlib import Path


def test_coin_balances_are_aggregated_once_per_student_across_subjects():
    paths = [
        Path("backend/modules/domains/reporting/academic_repository.py"),
        Path("backend/modules/domains/reporting/summary_repository.py"),
        Path("backend/modules/domains/parent_relationships/repository.py"),
    ]

    for path in paths:
        source = path.read_text()
        assert "coins.group_id" not in source, path
        assert "GROUP BY student_id" in source, path
