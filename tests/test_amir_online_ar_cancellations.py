import unittest

from app.integrations.sheets.parsers import GroupInfo, parse_group_rows


def _blank_row(width=32):
    return [""] * width


class AmirOnlineArCancellationsTests(unittest.TestCase):
    def _base_rows(self):
        rows = [_blank_row() for _ in range(24)]
        # Header timeline for one lesson.
        rows[0][21] = "2026-04-01"  # V date
        rows[1][21] = "L1"          # V lesson label
        rows[2][21] = "Linear Equations"
        return rows

    def _online_group(self):
        return GroupInfo(
            title="MONLINE",
            normalized_code="MONLINE",
            subject_code="M",
            subject_name="IGCSE Mathematics A",
            group_display_name="Online",
            school_code="school5",
        )

    def test_amir_online_counts_cancelled_as_absent_for_ar(self):
        rows = self._base_rows()
        # Student data row.
        rows[3][0] = 1
        rows[3][1] = "Амир"
        rows[3][21] = "Cancelled"

        parsed_rows, _lesson_catalog = parse_group_rows(
            group=self._online_group(),
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]
        attendance = dashboard["attendanceRecord"]
        self.assertEqual(attendance["absentCount"], 1)
        self.assertEqual(attendance["presentCount"], 0)
        self.assertEqual(attendance["justifiedAbsentCount"], 0)
        self.assertEqual(attendance["totalCount"], 1)
        self.assertEqual(len(dashboard["attendanceLessons"]), 1)
        self.assertEqual(dashboard["attendanceLessons"][0]["status"], "absent")
        # AAP should stay untouched (no score for cancelled lesson).
        self.assertEqual(dashboard["homeworkGrades"], [])

    def test_amir_online_header_cancelled_counts_absent_with_empty_cell(self):
        rows = self._base_rows()
        rows[1][21] = "Lesson 1 Cancelled"
        rows[2][21] = "Linear Equations"

        rows[3][0] = 1
        rows[3][1] = "Амир"
        rows[3][21] = ""

        parsed_rows, _lesson_catalog = parse_group_rows(
            group=self._online_group(),
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]
        attendance = dashboard["attendanceRecord"]
        self.assertEqual(attendance["absentCount"], 1)
        self.assertEqual(attendance["totalCount"], 1)
        self.assertEqual(len(dashboard["attendanceLessons"]), 1)
        self.assertEqual(dashboard["attendanceLessons"][0]["status"], "absent")
        self.assertEqual(dashboard["homeworkGrades"], [])

    def test_amir_online_cancelled_topic_without_lesson_label_is_visible_in_ar(self):
        rows = self._base_rows()
        rows[1][21] = ""
        rows[2][21] = "Cancelled"
        rows[0][21] = "2026-04-02"

        rows[3][0] = 1
        rows[3][1] = "Амир"
        rows[3][21] = ""

        parsed_rows, _lesson_catalog = parse_group_rows(
            group=self._online_group(),
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]
        attendance = dashboard["attendanceRecord"]
        self.assertEqual(attendance["absentCount"], 1)
        self.assertEqual(attendance["totalCount"], 1)
        self.assertEqual(len(dashboard["attendanceLessons"]), 1)
        self.assertEqual(dashboard["attendanceLessons"][0]["status"], "absent")
        self.assertTrue(
            str(dashboard["attendanceLessons"][0]["lesson"]).startswith(
                "Cancelled Session"
            )
        )
        self.assertEqual(dashboard["homeworkGrades"], [])

    def test_non_amir_online_cancelled_stays_empty_for_ar(self):
        rows = self._base_rows()
        rows[3][0] = 1
        rows[3][1] = "Ali"
        rows[3][21] = "Cancelled"

        parsed_rows, _lesson_catalog = parse_group_rows(
            group=self._online_group(),
            rows=rows,
            used_student_ids=set(),
        )

        self.assertEqual(len(parsed_rows), 1)
        dashboard = parsed_rows[0]["dashboard"]
        attendance = dashboard["attendanceRecord"]
        self.assertEqual(attendance["absentCount"], 0)
        self.assertEqual(attendance["presentCount"], 0)
        self.assertEqual(attendance["justifiedAbsentCount"], 0)
        self.assertEqual(attendance["totalCount"], 0)
        self.assertEqual(dashboard["attendanceLessons"], [])


if __name__ == "__main__":
    unittest.main()
