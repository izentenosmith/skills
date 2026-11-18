import unittest

from gatehouse.auth.scopes import has_scope, parse_scopes


class ParseScopesTest(unittest.TestCase):
    def test_single_scope(self):
        self.assertEqual(parse_scopes("reports:read"), {"reports:read"})

    def test_two_scopes(self):
        self.assertEqual(parse_scopes("reports:read,exports:run"), {"reports:read", "exports:run"})

    def test_empty_string_grants_nothing(self):
        self.assertEqual(parse_scopes(""), frozenset())


class HasScopeTest(unittest.TestCase):
    def test_granted(self):
        self.assertTrue(has_scope("reports:read", "reports:read"))

    def test_not_granted(self):
        self.assertFalse(has_scope("reports:read", "exports:run"))


if __name__ == "__main__":
    unittest.main()
