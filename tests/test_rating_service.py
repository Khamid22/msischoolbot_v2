"""Unit tests for the academic rating/leaderboard math (no database)."""

from backend.modules.domains.academics.gradebook.rating import (
    attendance_rate_to_score,
    build_subject_leaderboard,
    extract_attendance_rate,
    extract_best_exam_scores,
    extract_exam_average_score,
    extract_homework_scores,
    is_full_form,
    round_grade_half_up,
    search_student,
)


def make_dashboard(
    student_id,
    *,
    subject="Math",
    group="7A",
    homework=(),
    exams=(),
    present=0,
    absent=0,
    justified=0,
):
    return {
        "student": {
            "id": student_id,
            "fullName": f"Student {student_id}",
            "surname": f"Student",
            "name": str(student_id),
            "subject": subject,
            "group": group,
        },
        "averageGrade": 0.0,
        "homeworkGrades": [{"score": s} for s in homework],
        "examResults": [
            {"examName": name, "attempt": attempt, "score": score}
            for name, attempt, score in exams
        ],
        "attendanceRecord": {
            "presentCount": present,
            "absentCount": absent,
            "justifiedAbsentCount": justified,
        },
    }


def test_round_grade_half_up():
    assert round_grade_half_up(2.4) == 2
    assert round_grade_half_up(2.5) == 3
    assert round_grade_half_up(3.51) == 4


def test_attendance_rate_to_score():
    assert attendance_rate_to_score(100) == 9
    assert attendance_rate_to_score(0) == 0
    assert attendance_rate_to_score(50) == 4.5


def test_extract_attendance_rate_counts_justified_as_attended():
    payload = make_dashboard(1, present=8, absent=2, justified=0)
    assert extract_attendance_rate(payload) == 80
    payload = make_dashboard(1, present=8, absent=0, justified=2)
    assert extract_attendance_rate(payload) == 100


def test_extract_homework_scores_bounds_and_filters():
    payload = make_dashboard(1, homework=(5, 12, -3, "bad"))
    # 12 clamps to 9, -3 clamps to 0, "bad" is dropped
    assert extract_homework_scores(payload) == [5.0, 9.0, 0.0]


def test_best_exam_score_takes_best_attempt():
    payload = make_dashboard(
        1,
        exams=(("Midterm", "1st", 4.0), ("Midterm", "2nd", 7.5), ("Final", "1st", 6.0)),
    )
    best = extract_best_exam_scores(payload)
    assert best["midterm"] == 7.5
    assert best["final"] == 6.0
    assert extract_exam_average_score(payload) == 6.8


def test_leaderboard_ranks_official_before_provisional():
    # Official: >=2 exams, >=10 homework scores, >=10 attendance entries.
    strong = make_dashboard(
        1,
        homework=(8,) * 12,
        exams=(("Midterm", "1st", 8.0), ("Final", "1st", 9.0)),
        present=12,
    )
    weaker = make_dashboard(
        2,
        homework=(6,) * 12,
        exams=(("Midterm", "1st", 5.0), ("Final", "1st", 6.0)),
        present=10,
        absent=2,
    )
    sparse = make_dashboard(3, homework=(9.0,), exams=(("Midterm", "1st", 9.0),), present=2)

    leaderboard = build_subject_leaderboard([sparse, weaker, strong])

    assert [row["studentId"] for row in leaderboard] == [1, 2, 3]
    assert leaderboard[0]["rank"] == 1 and not leaderboard[0]["isProvisional"]
    assert leaderboard[1]["rank"] == 2 and not leaderboard[1]["isProvisional"]
    assert leaderboard[2]["rank"] == 0 and leaderboard[2]["isProvisional"]
    # composite = exam*0.70 + homework*0.15 + attendance_score*0.15
    assert leaderboard[0]["averageComposite"] == round(8.5 * 0.7 + 8.0 * 0.15 + 9 * 0.15, 1)


def test_is_full_form():
    assert is_full_form({"a": "1", "b": "2"})
    assert not is_full_form({"a": "1", "b": ""})


def test_search_student_matches_name_group_subject():
    students = [
        {"fullName": "Aliyev Vali", "group": "7A", "subject": "Math"},
        {"fullName": "Karimov Olim", "group": "7A", "subject": "Math"},
    ]
    found = search_student(students, surname="Karimov", name="Olim", group="7a", subject="math")
    assert found is students[1]
    assert search_student(students, surname="Karimov", name="Olim", group="8B", subject="math") is None
