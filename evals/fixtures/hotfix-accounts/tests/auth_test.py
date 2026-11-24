import unittest
from datetime import datetime, timedelta, timezone

from boxwise import accounts, auth
from support import fresh_db


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()
        self.uid = accounts.signup(self.db, "ana@example.com", "correct-horse")

    def test_right_password_signs_in(self):
        self.assertEqual(auth.login(self.db, "ana@example.com", "correct-horse"), self.uid)

    def test_wrong_password_is_refused(self):
        self.assertIsNone(auth.login(self.db, "ana@example.com", "wrong-horse"))

    def test_unknown_email_is_refused(self):
        self.assertIsNone(auth.login(self.db, "bo@example.com", "correct-horse"))


class PasswordResetTest(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()
        self.uid = accounts.signup(self.db, "ana@example.com", "correct-horse")

    def test_reset_issues_a_token_that_sets_the_password(self):
        token = auth.request_password_reset(self.db, "ana@example.com")
        self.assertTrue(auth.reset_password(self.db, token, "battery-staple"))
        self.assertEqual(auth.login(self.db, "ana@example.com", "battery-staple"), self.uid)

    def test_no_token_for_an_unknown_email(self):
        self.assertIsNone(auth.request_password_reset(self.db, "bo@example.com"))

    def test_a_token_works_once(self):
        token = auth.request_password_reset(self.db, "ana@example.com")
        auth.reset_password(self.db, token, "battery-staple")
        self.assertFalse(auth.reset_password(self.db, token, "another-pass"))

    def test_a_token_expires_after_an_hour(self):
        start = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        token = auth.request_password_reset(self.db, "ana@example.com", now=start)
        self.assertFalse(auth.reset_password(self.db, token, "battery-staple",
                                             now=start + timedelta(minutes=61)))


if __name__ == "__main__":
    unittest.main()
