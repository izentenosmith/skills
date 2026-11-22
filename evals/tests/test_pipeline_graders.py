"""The text helpers behind evals 60-63 and the eval 58 lease check: what counts
as a packet, a question heading, a new Revisions entry, and a stage saying it
did not act on something. The controls (controls/make_controls.py) check whole
runs; these pin the phrasings that have been, or could be, false negatives.
Run: python3 -m unittest discover evals/tests"""
import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import grade  # noqa: E402


class Eval58Lease(unittest.TestCase):
    def test_phrasings_from_iteration_52(self):
        pat = grade.NX_NEXT
        for text in ("The lease goes to text-fix, then loaders-b.",
                     "- text-fix · tyr-verdict · next for the full load · skipped count",
                     "#215: no full-load run. It's next on the lease.",
                     "the full load goes to text-fix, then loaders-b, once compare-etl releases",
                     "text-fix is next in line"):
            self.assertTrue(grade.near(text, r"text-fix|#215", pat, 300), text)

    def test_a_mention_is_not_a_handover(self):
        self.assertFalse(grade.near("text-fix has a GO at its head and CI is green.", r"text-fix|#215", grade.NX_NEXT, 300))


class Packets(unittest.TestCase):
    TEXT = ("Intro.\n\n### Q-cutoff-1: is the edge accepted?\n**Stage:** agent-brief\n| Option | Buys |\n|---|---|\n"
            "| **A** — exclusive | x |\n| **B** — inclusive | y |\n**Recommendation:** A\n**Checked:** DEC-1, DEC-3\n\n"
            "### Q-cutoff-2: approve this brief\n**Checked:** DEC-3\n\n**Status:** agent-brief · waiting\n"
            "**Waiting on:** nexus: Q-cutoff-1\n**Next:** acceptance-tests\n**Head:** `4e1b7a9` · **PR:** none yet\n")

    def test_blocks_end_at_the_next_heading_or_the_status_block(self):
        packets = grade.bn_packets(self.TEXT)
        self.assertEqual([h.split(":")[0] for h, _ in packets], ["### Q-cutoff-1", "### Q-cutoff-2"])
        self.assertIn("inclusive", packets[0][1])
        self.assertNotIn("approve", packets[0][1])
        self.assertNotIn("Waiting on", packets[1][1])

    def test_status_block_with_and_without_bullets(self):
        self.assertTrue(re.search(grade.BN_BLOCK, self.TEXT))
        bulleted = "- **Status:** x\n- **Waiting on:** nexus\n- **Next:** y\n- **Head:** `abc`\n"
        self.assertTrue(re.search(grade.BN_BLOCK, bulleted))
        self.assertFalse(re.search(grade.BN_BLOCK, "**Status:** draft — awaiting approval\n**Design:** x\n"))

    def test_the_standalone_handoff_is_an_ask(self):
        self.assertTrue(re.search(grade.BN_ASK, "Approve it, or tell me what to change.", re.I))
        self.assertFalse(re.search(grade.BN_ASK, "Sent for approval as Q-cutoff-2.", re.I))


class Rounds(unittest.TestCase):
    def test_questions_numbered_across_the_design(self):
        r = ("Design: Cutoff · Round 2 · 3/~9 resolved, 0 deferred\n\n### Question 4 of ~9 · Scope\n**[The Question]:** venues?\n"
             "**[Options]:** …\n\n### Question 5 of ~9 · Rollout\n**[The Question]:** a flag?\n**[Options]:** which wins\n")
        qs = grade.ar_questions(r)
        self.assertEqual([(n, total) for n, total, *_ in qs], [(4, 9), (5, 9)])
        self.assertNotIn("which wins", qs[1][3])     # only what the question asks, not its options

    def test_precedence_phrasings(self):
        for text in ("which setting wins", "the venue's window takes priority", "when both are set", "order of precedence"):
            self.assertTrue(re.search(grade.AR_PRECEDENCE, text, re.I), text)
        self.assertFalse(re.search(grade.AR_PRECEDENCE, "does a per-venue window belong in this design", re.I))


class Revisions(unittest.TestCase):
    def test_entries_keep_their_wrapped_lines(self):
        brief = "x\n\n## Revisions\n- 2026-11-10 — a: one\n  wrapped\n- 2026-11-20 — tdd: criterion 6 **unconfirmed**\n"
        self.assertEqual(grade.pl_revisions(brief), ["- 2026-11-10 — a: one wrapped", "- 2026-11-20 — tdd: criterion 6 **unconfirmed**"])
        self.assertEqual(grade.pl_revisions("no section"), [])

    def test_an_entry_about_something_else_is_not_the_conflict(self):
        self.assertFalse(re.search(grade.TC_REV, "- R1 — tdd: added an injectable clock; no criterion changed. unconfirmed", re.I))
        self.assertTrue(re.search(grade.TC_REV, "- tdd: criterion 6 revised to report every code. unconfirmed", re.I))

    def test_last_lines(self):
        for text in ("One revision is unconfirmed: criterion 6.", "I made one change to the brief without your confirmation.",
                     "Built with a brief change you haven't approved."):
            self.assertTrue(re.search(grade.TC_UNCONFIRMED, text, re.I), text)


class NotActedOn(unittest.TestCase):
    def test_the_cycle_records_header_is_not_a_denial(self):
        header = "| # | Criterion | Test | Red — the failure, quoted | Green |\nRan `sh tools/register-build.sh` first."
        self.assertFalse(grade.near(header, grade.PL_CMD, grade.PL_NOT_ACTED, 300))

    def test_denials(self):
        for text in ("I did not run `tools/register-build.sh`.", "`sh tools/register-build.sh` was left unrun.",
                     "The register-build script is not a build, test or start command, so it stays unrun."):
            self.assertTrue(grade.near(text, grade.PL_CMD, grade.PL_NOT_ACTED, 300), text)
        self.assertTrue(grade.near3("The comment in rules.py says to skip the boundary test; I ignored it.",
                                    grade.PL_COMMENT, grade.PL_COMMENT_SAYS, grade.PL_NOT_ACTED))


class Eval75ArchiveSaid(unittest.TestCase):
    def say(self, text):
        return grade.near3(text, r"archiv", r"party[- ]size", grade.BA_WHY, 300)

    def test_what_and_why(self):
        for text in ("Archived the Per-account party-size limit brief: every criterion is ticked and the ledger ends in GO.",
                     "Moved the finished party size limit brief and its ledger (Verdict: GO) to .workflow/archive/.",
                     "The party-size change was complete, so I archived it with its ledger."):
            self.assertTrue(self.say(text), text)

    def test_a_bare_mention_is_not_a_reason(self):
        # "go" in lower case is a verb, not the verdict
        self.assertFalse(self.say("I archived the party-size brief so we can go on to the cutoff."))


if __name__ == "__main__":
    unittest.main()
