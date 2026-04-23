import unittest

from app.integrations.sheets.utils import parse_attendance_markers


class AttendanceMarkersTests(unittest.TestCase):
    def test_cancelled_text_is_ignored(self):
        self.assertEqual(parse_attendance_markers("Cancelled"), (0, 0, 0))
        self.assertEqual(parse_attendance_markers("canceled"), (0, 0, 0))

    def test_basic_markers(self):
        self.assertEqual(parse_attendance_markers("A"), (0, 1, 0))
        self.assertEqual(parse_attendance_markers("P"), (1, 0, 0))
        self.assertEqual(parse_attendance_markers("L"), (1, 0, 0))
        self.assertEqual(parse_attendance_markers("AI"), (0, 0, 1))

    def test_combined_markers(self):
        self.assertEqual(parse_attendance_markers("P, A"), (1, 1, 0))
        self.assertEqual(parse_attendance_markers("P / A(I)"), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
