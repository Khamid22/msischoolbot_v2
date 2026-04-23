import unittest

from app.integrations.sheets.parsers import parse_group_info


class GroupInfoParsingTests(unittest.TestCase):
    def test_school5_math_online_tab_is_supported(self):
        group_info = parse_group_info("MONLINE", "school5")
        self.assertIsNotNone(group_info)
        self.assertEqual(group_info.normalized_code, "MONLINE")
        self.assertEqual(group_info.subject_code, "M")
        self.assertEqual(group_info.subject_name, "IGCSE Mathematics A")
        self.assertEqual(group_info.group_display_name, "Online")
        self.assertEqual(group_info.school_code, "school5")

    def test_school5_invalid_math_suffix_is_rejected(self):
        self.assertIsNone(parse_group_info("MWHATEVER", "school5"))


if __name__ == "__main__":
    unittest.main()
