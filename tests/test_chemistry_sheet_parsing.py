import unittest

from app.integrations.sheets.parsers import GroupInfo, parse_group_rows


def _blank_row(width=40):
    return [""] * width


class ChemistrySheetParsingTests(unittest.TestCase):
    def test_chemistry_layout_uses_v_triplets_and_c_to_t_exams(self):
        rows = [_blank_row() for _ in range(24)]

        # Header rows
        # Row 1 (date), Row 2 (lesson number), Row 3 (lesson name)
        rows[0][21] = "2026-01-10"  # V: lesson date
        rows[0][22] = "2026-01-11"  # W: lab date
        rows[0][23] = "2026-01-12"  # X: homework date
        rows[0][24] = "2026-01-17"  # Y: lesson date
        rows[0][25] = "2026-01-18"  # Z: lab date
        rows[0][26] = "2026-01-19"  # AA: homework date

        rows[1][21] = "L1"
        rows[1][24] = "L2"

        rows[2][21] = "Atomic Structure (Lesson)"
        rows[2][22] = "Atomic Structure (Lab)"
        rows[2][24] = "Chemical Bonding (Lesson)"
        rows[2][25] = "Chemical Bonding (Lab)"

        # Exams C..T (2..19)
        rows[2][2] = "Midterm"
        rows[2][19] = "Final"

        # Student row 4 (included)
        rows[3][1] = "Alice Example"
        rows[3][2] = 8  # Midterm first attempt
        rows[3][3] = 7  # Midterm second attempt
        rows[3][19] = 9  # Final (T)

        # V/W/X -> Lesson/Lab/HW for L1
        rows[3][21] = "P"
        rows[3][22] = "A"
        rows[3][23] = 6

        # Y/Z/AA -> Lesson/Lab/HW for L2
        rows[3][24] = "AI"
        rows[3][25] = "P"
        rows[3][26] = 7

        # Student row 20 (excluded for chemistry)
        rows[19][1] = "Should Be Ignored"
        rows[19][2] = 5
        rows[19][23] = 5

        group = GroupInfo(
            title="CHMMG1",
            normalized_code="CHMMG1",
            subject_code="CHM",
            subject_name="Chemistry",
            group_display_name="MG1",
            school_code="school5",
        )

        parsed_rows, lesson_catalog = parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]

        # AAP: homework only, using lesson name + homework score
        homework_grades = dashboard["homeworkGrades"]
        self.assertEqual(len(homework_grades), 2)
        self.assertEqual(homework_grades[0]["lesson"], "L1")
        self.assertEqual(homework_grades[0]["topic"], "Atomic Structure")
        self.assertEqual(homework_grades[0]["date"], "HOMEWORK")
        self.assertEqual(homework_grades[0]["type"], "Homework")
        self.assertEqual(homework_grades[0]["score"], 6.0)
        self.assertEqual(homework_grades[1]["lesson"], "L2")
        self.assertEqual(homework_grades[1]["topic"], "Chemical Bonding")
        self.assertEqual(homework_grades[1]["date"], "HOMEWORK")
        self.assertEqual(homework_grades[1]["type"], "Homework")
        self.assertEqual(homework_grades[1]["score"], 7.0)

        # AR: plain topics + explicit attendance type.
        attendance_lessons = dashboard["attendanceLessons"]
        attendance_topics = {item["topic"] for item in attendance_lessons}
        self.assertEqual(attendance_topics, {"Atomic Structure", "Chemical Bonding"})
        attendance_types = {item["attendanceType"] for item in attendance_lessons}
        self.assertEqual(attendance_types, {"Lecture", "Lab"})

        # Exam range includes T
        exam_results = dashboard["examResults"]
        self.assertEqual(len(exam_results), 3)
        exam_names = {item["examName"] for item in exam_results}
        self.assertIn("Midterm", exam_names)
        self.assertIn("Final", exam_names)

        # Lesson catalog remains homework-oriented
        self.assertEqual(len(lesson_catalog), 2)
        self.assertEqual(lesson_catalog[0]["lesson_number"], "L1")
        self.assertEqual(lesson_catalog[0]["lesson_topic"], "Atomic Structure")
        self.assertEqual(lesson_catalog[1]["lesson_number"], "L2")
        self.assertEqual(lesson_catalog[1]["lesson_topic"], "Chemical Bonding")

    def test_chemistry_keeps_duplicate_lesson_numbers_as_separate_rows(self):
        rows = [_blank_row() for _ in range(24)]

        # Two triplets with the same lesson number/topic but different dates.
        rows[0][21] = "2026-02-01"
        rows[0][22] = "2026-02-02"
        rows[0][23] = "2026-02-03"
        rows[0][24] = "2026-02-08"
        rows[0][25] = "2026-02-09"
        rows[0][26] = "2026-02-10"

        rows[1][21] = "L3"
        rows[1][24] = "L3"
        rows[2][21] = "Moles (Lesson)"
        rows[2][22] = "Moles (Lab)"
        rows[2][24] = "Moles (Lesson)"
        rows[2][25] = "Moles (Lab)"

        rows[3][1] = "Bob Example"
        rows[3][21] = "P"
        rows[3][22] = "A"
        rows[3][23] = 5
        rows[3][24] = "P"
        rows[3][25] = "P"
        rows[3][26] = 6

        group = GroupInfo(
            title="CHMMG1",
            normalized_code="CHMMG1",
            subject_code="CHM",
            subject_name="Chemistry",
            group_display_name="MG1",
            school_code="sehriyo",
        )

        parsed_rows, lesson_catalog = parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]

        homework_grades = dashboard["homeworkGrades"]
        self.assertEqual(len(homework_grades), 2)
        self.assertEqual([item["lesson"] for item in homework_grades], ["L3", "L3"])
        self.assertEqual(
            [item["date"] for item in homework_grades],
            ["HOMEWORK", "HOMEWORK"],
        )

        attendance_lessons = dashboard["attendanceLessons"]
        self.assertEqual(len(attendance_lessons), 4)
        self.assertEqual(
            [item["attendanceType"] for item in attendance_lessons],
            ["Lecture", "Lab", "Lecture", "Lab"],
        )
        self.assertTrue(all(item["topic"] == "Moles" for item in attendance_lessons))

        self.assertEqual(len(lesson_catalog), 2)
        self.assertEqual([item["lesson_number"] for item in lesson_catalog], ["L3", "L3"])

    def test_chemistry_keeps_homework_when_lecture_and_lab_are_cancelled(self):
        rows = [_blank_row() for _ in range(24)]

        # V/W/X triplet is marked cancelled for lesson/lab, but H/W is present.
        rows[0][21] = "2026-03-01"
        rows[0][22] = "2026-03-02"
        rows[0][23] = "H/W"
        rows[1][21] = "Lesson Cancelled"
        rows[1][22] = "Lab Cancelled"
        rows[1][23] = "H/W"
        rows[2][21] = "Moles (Lesson)"
        rows[2][22] = "Moles (Lab)"

        rows[3][1] = "Carla Example"
        rows[3][23] = 8

        group = GroupInfo(
            title="CHMMG1",
            normalized_code="CHMMG1",
            subject_code="CHM",
            subject_name="Chemistry",
            group_display_name="MG1",
            school_code="sehriyo",
        )

        parsed_rows, lesson_catalog = parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]

        # Homework survives even if lecture/lab are cancelled.
        homework_grades = dashboard["homeworkGrades"]
        self.assertEqual(len(homework_grades), 1)
        self.assertEqual(homework_grades[0]["lesson"], "H/W")
        self.assertEqual(homework_grades[0]["topic"], "Moles")
        self.assertEqual(homework_grades[0]["score"], 8.0)
        self.assertEqual(homework_grades[0]["date"], "HOMEWORK")

        # Cancelled lecture/lab do not appear in AR.
        attendance_lessons = dashboard["attendanceLessons"]
        self.assertEqual(attendance_lessons, [])

        # Lesson catalog remains homework-oriented.
        self.assertEqual(len(lesson_catalog), 1)
        self.assertEqual(lesson_catalog[0]["lesson_number"], "H/W")
        self.assertEqual(lesson_catalog[0]["lesson_topic"], "Moles")

    def test_chemistry_handles_shifted_columns_after_cancellations(self):
        rows = [_blank_row(45) for _ in range(24)]

        # Header timeline (V onward) includes cancelled blocks and a month divider:
        # 14/1 | 15/1 | H/W | 21/1 | 22/1 | H/W | 28/1 | 29/1 | January 2026 | 4/2 | 6/2 | 11/2 | H/W
        rows[0][21] = "14/1"
        rows[0][22] = "15/1"
        rows[0][23] = "H/W"
        rows[0][24] = "21/1"
        rows[0][25] = "22/1"
        rows[0][26] = "H/W"
        rows[0][27] = "28/1"
        rows[0][28] = "29/1"
        rows[0][29] = "January 2026"
        rows[0][30] = "4/2"
        rows[0][31] = "6/2"
        rows[0][32] = "11/2"
        rows[0][33] = "H/W"

        rows[1][21] = "Lesson 1"
        rows[1][24] = "Lesson 2"
        rows[1][27] = "Cancelled"
        rows[1][28] = "Cancelled"
        rows[1][30] = "Cancelled"
        rows[1][31] = "Lesson 3"
        rows[1][33] = "H/W"

        rows[2][21] = "States of Matter (Lesson)"
        rows[2][22] = "States of Matter (Lab)"
        rows[2][24] = "Diffusion and Solutions (Lesson)"
        rows[2][25] = "Diffusion and Solutions (Lab)"
        rows[2][27] = "Teacher was sick"
        rows[2][28] = "Teacher was sick"
        rows[2][30] = "School activities"
        rows[2][31] = "Solubility Curves (Lesson)"
        rows[2][32] = "Solubility Curves (Lab)"

        rows[3][1] = "Dana Example"
        rows[3][21] = "P"
        rows[3][22] = "P"
        rows[3][23] = 8
        rows[3][24] = "A"
        rows[3][25] = "P"
        rows[3][26] = 9
        rows[3][31] = "P"
        rows[3][32] = "P"
        rows[3][33] = 7

        group = GroupInfo(
            title="CHMMG1",
            normalized_code="CHMMG1",
            subject_code="CHM",
            subject_name="Chemistry",
            group_display_name="MG1",
            school_code="sehriyo",
        )

        parsed_rows, lesson_catalog = parse_group_rows(
            group=group,
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]

        homework_grades = dashboard["homeworkGrades"]
        self.assertEqual([item["score"] for item in homework_grades], [8.0, 9.0, 7.0])
        self.assertEqual([item["lesson"] for item in homework_grades], ["Lesson 1", "Lesson 2", "Lesson 3"])
        self.assertEqual([item["topic"] for item in homework_grades], [
            "States of Matter",
            "Diffusion and Solutions",
            "Solubility Curves",
        ])
        self.assertEqual([item["date"] for item in homework_grades], ["HOMEWORK", "HOMEWORK", "HOMEWORK"])

        attendance_lessons = dashboard["attendanceLessons"]
        self.assertEqual(len(attendance_lessons), 6)
        lesson3_rows = [item for item in attendance_lessons if item["lesson"] == "Lesson 3"]
        self.assertEqual(len(lesson3_rows), 2)
        self.assertEqual({item["attendanceType"] for item in lesson3_rows}, {"Lecture", "Lab"})
        self.assertTrue(all(item["topic"] == "Solubility Curves" for item in lesson3_rows))

        self.assertEqual(len(lesson_catalog), 3)
        self.assertEqual([item["lesson_number"] for item in lesson_catalog], ["Lesson 1", "Lesson 2", "Lesson 3"])
        self.assertEqual([item["lesson_topic"] for item in lesson_catalog], [
            "States of Matter",
            "Diffusion and Solutions",
            "Solubility Curves",
        ])


if __name__ == "__main__":
    unittest.main()
