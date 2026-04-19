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

        rows[2][21] = "Atomic Structure"
        rows[2][24] = "Chemical Bonding"

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
        self.assertEqual(homework_grades[0]["score"], 6.0)
        self.assertEqual(homework_grades[1]["lesson"], "L2")
        self.assertEqual(homework_grades[1]["topic"], "Chemical Bonding")
        self.assertEqual(homework_grades[1]["score"], 7.0)

        # AR: topic name explicitly marks Lesson/Lab
        attendance_lessons = dashboard["attendanceLessons"]
        attendance_topics = {item["topic"] for item in attendance_lessons}
        self.assertIn("Atomic Structure (Lesson)", attendance_topics)
        self.assertIn("Atomic Structure (Lab)", attendance_topics)
        self.assertIn("Chemical Bonding (Lesson)", attendance_topics)
        self.assertIn("Chemical Bonding (Lab)", attendance_topics)

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


if __name__ == "__main__":
    unittest.main()
