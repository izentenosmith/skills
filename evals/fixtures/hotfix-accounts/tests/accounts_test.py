import unittest

from boxwise import accounts
from support import fresh_db


class SignupTest(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()

    def test_signup_creates_an_account(self):
        uid = accounts.signup(self.db, "sam@example.com", "correct-horse")
        self.assertEqual(accounts.get_user(self.db, uid)["email"], "sam@example.com")

    def test_surrounding_whitespace_is_dropped(self):
        uid = accounts.signup(self.db, "  sam@example.com ", "correct-horse")
        self.assertEqual(accounts.get_user(self.db, uid)["email"], "sam@example.com")

    def test_the_same_email_cannot_sign_up_twice(self):
        accounts.signup(self.db, "sam@example.com", "correct-horse")
        with self.assertRaises(accounts.EmailTaken):
            accounts.signup(self.db, "sam@example.com", "another-pass")

    def test_rejects_an_address_without_a_domain_dot(self):
        with self.assertRaises(accounts.InvalidEmail):
            accounts.signup(self.db, "sam@localhost", "correct-horse")

    def test_rejects_a_short_password(self):
        with self.assertRaises(ValueError):
            accounts.signup(self.db, "sam@example.com", "short")


class FindByEmailTest(unittest.TestCase):
    def test_finds_the_account(self):
        db = fresh_db()
        uid = accounts.signup(db, "ana@example.com", "correct-horse")
        self.assertEqual(accounts.find_by_email(db, "ana@example.com")["id"], uid)

    def test_none_for_an_unknown_address(self):
        self.assertIsNone(accounts.find_by_email(fresh_db(), "nobody@example.com"))


if __name__ == "__main__":
    unittest.main()
