"""Behaviour partners rely on. A change that breaks one of these is a breaking change."""
import unittest

from gatehouse.api.exports import run_export
from gatehouse.api.reports import get_report
from gatehouse.tokens import Token


class MissingScopeContract(unittest.TestCase):
    def test_403_names_the_missing_scope(self):
        self.assertEqual(run_export(Token("acme", "reports:read"), "churn"),
                         (403, {"error": "missing_scope", "scope": "exports:run"}))

    def test_a_longer_scope_is_not_the_scope(self):
        self.assertEqual(run_export(Token("acme", "exports:runner"), "churn")[0], 403)

    def test_a_prefix_is_not_the_scope(self):
        self.assertEqual(get_report(Token("acme", "reports"), "churn")[0], 403)

    def test_matching_is_case_sensitive(self):
        self.assertEqual(get_report(Token("acme", "Reports:Read"), "churn")[0], 403)


class ExportContract(unittest.TestCase):
    def test_csv_has_a_header_line(self):
        status, body = run_export(Token("acme", "exports:run"), "weekly-signups")
        self.assertEqual(status, 200)
        self.assertEqual(body["csv"][0], "week,signups")


if __name__ == "__main__":
    unittest.main()
