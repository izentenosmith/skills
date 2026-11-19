import unittest

from gatehouse.tokens import issue


class IssueTest(unittest.TestCase):
    def test_scopes_are_stored_readably(self):
        self.assertEqual(issue("acme", ["reports:read", "exports:run"]).scopes, "reports:read, exports:run")

    def test_webhook_url_is_optional(self):
        self.assertEqual(issue("acme", ["reports:read"]).webhook_url, "")


if __name__ == "__main__":
    unittest.main()
