import unittest

from gatehouse.tokens import Token
from gatehouse.webhooks.delivery import recipients


class RecipientsTest(unittest.TestCase):
    def test_subscriber_is_a_recipient(self):
        t = Token("acme", "webhooks:export.finished", "https://acme.example/hook")
        self.assertEqual(recipients([t], "export.finished"), ["https://acme.example/hook"])

    def test_no_url_no_delivery(self):
        self.assertEqual(recipients([Token("acme", "webhooks:export.finished")], "export.finished"), [])


if __name__ == "__main__":
    unittest.main()
