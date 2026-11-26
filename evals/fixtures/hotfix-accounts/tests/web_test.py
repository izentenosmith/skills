import unittest

from boxwise import mailer, web
from support import fresh_db


class ResetRequestTest(unittest.TestCase):
    def setUp(self):
        self.db = fresh_db()
        mailer.OUTBOX.clear()
        web.post_signup(self.db, {"email": "ana@example.com", "password": "correct-horse"})

    def test_known_email_gets_a_link(self):
        self.assertEqual(web.post_reset_request(self.db, {"email": "ana@example.com"})[0], 200)
        self.assertEqual(mailer.OUTBOX[-1]["to"], "ana@example.com")

    def test_unknown_email_is_told_so(self):
        self.assertEqual(web.post_reset_request(self.db, {"email": "bo@example.com"}),
                         (404, web.NOT_FOUND))


class SignupFormTest(unittest.TestCase):
    def test_duplicate_is_a_conflict(self):
        db = fresh_db()
        web.post_signup(db, {"email": "ana@example.com", "password": "correct-horse"})
        self.assertEqual(web.post_signup(db, {"email": "ana@example.com", "password": "correct-horse"})[0], 409)


if __name__ == "__main__":
    unittest.main()
