"""Read-only role workspace count cards."""

from backend.services.staff import workspace as workspace_counts
from backend.repositories import staff as staff_repository


class _Result:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return {"total": self.value}


class _Connection:
    def __init__(self, values, failing_markers=None):
        self.values = values
        self.failing_markers = failing_markers or set()
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, sql):
        normalized = " ".join(str(sql).casefold().split())
        for marker in self.failing_markers:
            if marker in normalized:
                raise RuntimeError("table unavailable")
        for marker, value in self.values.items():
            if marker in normalized:
                return _Result(value)
        raise AssertionError(f"Unhandled query: {normalized}")

    def rollback(self):
        self.rollbacks += 1


def _patch_counts_connection(monkeypatch, values, failing_markers=None):
    connection = _Connection(values, failing_markers=failing_markers)
    monkeypatch.setattr(staff_repository, "connect", lambda: connection)
    return connection


def test_ceo_workspace_cards_show_core_counts(monkeypatch):
    _patch_counts_connection(
        monkeypatch,
        {
            "from msi_v2.schools": 2,
            "from msi_v2.students": 177,
            "from msi_v2.teachers": 3,
            "from msi_v2.subjects": 6,
        },
    )

    assert workspace_counts.ceo_workspace_cards() == [
        {"label": "Schools", "value": "2"},
        {"label": "Students", "value": "177"},
        {"label": "Teachers", "value": "3"},
        {"label": "Subjects", "value": "6"},
    ]


def test_academic_director_workspace_cards_show_academic_counts(monkeypatch):
    _patch_counts_connection(
        monkeypatch,
        {
            "from msi_v2.groups": 8,
            "from msi_v2.teachers": 3,
            "from msi_v2.subjects": 6,
            "from msi_v2.students": 177,
        },
    )

    assert workspace_counts.academic_director_workspace_cards() == [
        {"label": "Groups", "value": "8"},
        {"label": "Teachers", "value": "3"},
        {"label": "Subjects", "value": "6"},
        {"label": "Students", "value": "177"},
    ]


def test_customer_support_workspace_cards_show_parent_and_invite_counts(monkeypatch):
    _patch_counts_connection(
        monkeypatch,
        {
            "from msi_v2.parents": 4,
            "from msi_v2.students": 177,
            "from msi_v2.accounts": 3,
            "from msi_v2.account_invites": 5,
        },
    )

    assert workspace_counts.customer_support_workspace_cards() == [
        {"label": "Parents", "value": "4"},
        {"label": "Students", "value": "177"},
        {"label": "Pending Parents/Invites", "value": "3 / 5"},
        {"label": "Support/Payments", "value": "Placeholder"},
    ]


def test_hr_manager_workspace_cards_keep_candidate_placeholder_when_table_missing(monkeypatch):
    connection = _patch_counts_connection(
        monkeypatch,
        {
            "from msi_v2.teachers": 3,
        },
        failing_markers={"from msi_v2.teacher_candidates"},
    )

    assert workspace_counts.hr_manager_workspace_cards() == [
        {"label": "Teachers", "value": "3"},
        {"label": "Candidates", "value": "Placeholder"},
        {"label": "Teacher Academy", "value": "Placeholder"},
    ]
    assert connection.rollbacks == 1
