import unittest

from gatehouse.api.reports import get_report
from gatehouse.tokens import Token


class GetReportTest(unittest.TestCase):
    def test_reader_gets_rows(self):
        status, body = get_report(Token("acme", "reports:read"), "weekly-signups")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["rows"]), 2)

    def test_empty_report_has_a_list(self):
        self.assertEqual(get_report(Token("acme", "reports:read"), "churn")[1]["rows"], [])


if __name__ == "__main__":
    unittest.main()
