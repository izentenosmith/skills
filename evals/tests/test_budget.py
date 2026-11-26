"""The SKILL.md body budget check_repo.py applies to every skill
(.github/scripts/budget.py). Run: python3 -m unittest discover evals/tests"""
import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".github/scripts"))

import budget  # noqa: E402

TODAY = datetime.date(2026, 12, 1)
OVER = (budget.MAX_LINES + 20, budget.MAX_WORDS + 300)


class Size(unittest.TestCase):
    def test_frontmatter_is_not_counted(self):
        text = "---\nname: demo\ndescription: Turns a long description into words.\n---\n# demo\n\ntwo words\n"
        self.assertEqual(budget.size(text), (3, 4))

    def test_no_frontmatter_counts_everything(self):
        self.assertEqual(budget.size("a b\nc\n"), (2, 3))


class Problems(unittest.TestCase):
    def check(self, sizes, allowlist=None):
        return budget.problems(sizes, allowlist or {}, TODAY)

    def test_under_budget_passes(self):
        self.assertEqual(self.check({"demo": (budget.MAX_LINES, budget.MAX_WORDS)}), [])

    def test_over_on_lines_or_words_fails(self):
        for size in ((budget.MAX_LINES + 1, 10), (10, budget.MAX_WORDS + 1)):
            msgs = self.check({"demo": size})
            self.assertEqual([n for n, _ in msgs], ["demo"], size)
            self.assertIn("budget", msgs[0][1])

    def test_allowlisted_at_its_size_passes(self):
        self.assertEqual(self.check({"demo": OVER}, {"demo": (*OVER, "2027-02-28")}), [])

    def test_allowlisted_may_grow_by_the_slack_only(self):
        allow = {"demo": (*OVER, "2027-02-28")}
        lines, words = OVER
        self.assertEqual(self.check({"demo": (lines + budget.SLACK[0], words + budget.SLACK[1])}, allow), [])
        msgs = self.check({"demo": (lines, words + budget.SLACK[1] + 1)}, allow)
        self.assertEqual(len(msgs), 1)
        self.assertIn("may not grow", msgs[0][1])

    def test_expired_allowance_fails(self):
        msgs = self.check({"demo": OVER}, {"demo": (*OVER, "2026-11-30")})
        self.assertEqual(len(msgs), 1)
        self.assertIn("ended 2026-11-30", msgs[0][1])

    def test_allowance_is_good_through_its_last_day(self):
        self.assertEqual(self.check({"demo": OVER}, {"demo": (*OVER, "2026-12-01")}), [])

    def test_stale_entry_fails(self):
        msgs = self.check({"demo": (100, 1000)}, {"demo": (*OVER, "2027-02-28")})
        self.assertEqual(len(msgs), 1)
        self.assertIn("remove its entry", msgs[0][1])

    def test_entry_for_a_missing_skill_fails(self):
        msgs = self.check({"demo": (100, 1000)}, {"gone": (*OVER, "2027-02-28")})
        self.assertEqual([n for n, _ in msgs], ["gone"])

    def test_allowlist_entries_are_well_formed(self):
        for name, (lines, words, until) in budget.ALLOWLIST.items():
            self.assertTrue(budget.over(lines, words), f"{name} is listed but fits the budget")
            datetime.date.fromisoformat(until)


if __name__ == "__main__":
    unittest.main()
