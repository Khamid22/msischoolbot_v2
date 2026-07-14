from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_class_summary_groups_every_ordered_school_column():
    source = (ROOT / "backend/modules/organization/repository.py").read_text(encoding="utf-8")
    query = source.split("def list_class_rows(conn):", 1)[1].split("def get_class(", 1)[0]

    assert "GROUP BY c.id, s.school_key, s.school_name" in query
    assert "ORDER BY s.school_name, c.class_name" in query
