"""Ledger grammar and loop rules. Run: python3 -m unittest discover harness/tests"""
import pathlib
import re
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import ledger as L  # noqa: E402

REPO = HERE.parent.parent
SPEC = (HERE.parent / "LEDGER.md").read_text()
LEGACY = (REPO / "evals/fixtures/verdict/.workflow/ledger.md").read_text()


def codes(text):
    return [e.split()[0] for e in L.status(text)["errors"]]


def finding(fid, conf="proven", **kw):
    return {"id": fid, "target": "criterion 3", "claim": "config is honored",
            "evidence": "the rule never reads config", "breaking_case": "240 vs 180 → accepted",
            "confidence": conf, "severity_hint": "major", **kw}


def confirmed(fid, sev="major"):
    return {"finding": fid, "verdict": "CONFIRMED", "severity": sev, "reason": "reproduced"}


def refuted(fid):
    return {"finding": fid, "verdict": "REFUTED", "reason": "the test fails under mutation",
            "reopens_only_if": "a mutation that survives"}


def inconclusive(fid):
    return {"finding": fid, "verdict": "INCONCLUSIVE", "reason": "no tz data", "settled_by": "a run under TZ=UTC+5"}


def slice_(fid, sev="major"):
    return {"finding": fid, "severity": sev, "behavior": "a booking 180 min out is rejected at cutoff 240"}


def iteration(n, closed=None, noted=(), actions=(), findings=(), verdicts=(), slices=(), outcome=None):
    out = L.render_iteration(n)
    if closed is not None:
        out += L.render_closed(closed)
    out += L.render_smells(list(noted), list(actions))
    out += L.render_findings(list(findings))
    out += L.render_surfaces([{"surface": "security", "note": "nothing new"}], [])
    if outcome != "skip-verdicts":
        out += L.render_verdicts(list(verdicts))
        out += L.render_slices(list(slices))
    if outcome and outcome != "skip-verdicts":
        out += L.render_outcome(outcome, "stated")
    return out


HEAD = L.render_header("cutoff")
NOTED = [{"id": "N1", "smell": "Dispensables / Duplicate Code", "location": "the validators",
          "reason": "accidental duplication", "promote_if": "a third instance"}]


class SpecExample(unittest.TestCase):
    def test_the_example_in_ledger_md_is_valid_and_ends_go(self):
        example = re.search(r"```markdown\n(.*?)```", SPEC, re.S).group(1)
        rep = L.status(example)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["computed"]["outcome"], "GO")
        self.assertEqual(rep["next_stage"], "done")


class RoundTrip(unittest.TestCase):
    def test_rendered_two_iteration_loop_parses_clean(self):
        text = HEAD + iteration(1, noted=NOTED, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        text += iteration(2, closed=[{"finding": "F1", "test": "test_cutoff_config"}],
                          actions=[{"id": "N1", "action": "left", "reason": "condition not met"}], outcome="GO")
        self.assertEqual(L.status(text)["errors"], [])

    def test_multiline_values_fold_into_continuations(self):
        f = finding("F1", evidence="line one\nline two")
        text = HEAD + iteration(1, findings=[f], verdicts=[confirmed("F1")], slices=[slice_("F1")], outcome="NO-GO")
        led = L.parse(text)
        self.assertEqual(led.iterations[0].sections["findings"][0].fields["evidence"], "line one line two")


class Rules(unittest.TestCase):
    def test_stated_verdict_must_match_the_computed_one(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="GO")
        self.assertIn("E50", codes(text))

    def test_refuted_is_sticky(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[refuted("F1")], outcome="GO")
        text += iteration(2, findings=[], verdicts=[confirmed("F1")], slices=[slice_("F1")], outcome="NO-GO")
        self.assertIn("E21", codes(text))

    def test_reopens_must_name_a_refuted_finding(self):
        text = HEAD + iteration(1, findings=[finding("F1"), finding("F2", reopens="F1")],
                                verdicts=[confirmed("F1"), refuted("F2")], slices=[slice_("F1")], outcome="NO-GO")
        self.assertIn("E14", codes(text))

    def test_unproven_must_name_what_settles_it(self):
        f = finding("F1", conf="unproven")
        text = HEAD + iteration(1, findings=[f], verdicts=[refuted("F1")], outcome="GO")
        text = text.replace("- **Would be settled by:** —\n", "")
        self.assertIn("E13", codes(text))

    def test_confirmed_needs_a_slice(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")], outcome="NO-GO")
        self.assertIn("E30", codes(text))

    def test_slice_severity_matches_verdict(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1", "major")],
                                slices=[slice_("F1", "minor")], outcome="NO-GO")
        self.assertIn("E31", codes(text))

    def test_every_finding_is_adjudicated(self):
        text = HEAD + iteration(1, findings=[finding("F1"), finding("F2")], verdicts=[refuted("F1")], outcome="GO")
        self.assertIn("E25", codes(text))

    def test_ids_are_never_reused(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[refuted("F1")], outcome="GO")
        text += iteration(2, findings=[finding("F1")], verdicts=[], outcome="GO")
        self.assertIn("E10", codes(text))

    def test_carried_smell_must_be_reexamined(self):
        text = HEAD + iteration(1, noted=NOTED, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        text += iteration(2, closed=[{"finding": "F1", "test": "t"}], outcome="GO")
        self.assertIn("E42", codes(text))

    def test_noted_smell_needs_a_promote_condition(self):
        text = HEAD + iteration(1, noted=NOTED, outcome="GO").replace("  - **Promote if:** a third instance\n", "")
        self.assertIn("E40", codes(text))

    def test_closing_a_slice_names_its_test(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        text += iteration(2, closed=[{"finding": "F1", "test": "t"}], outcome="GO").replace(" — verified by `t`", " — done")
        self.assertIn("E32", codes(text))

    def test_append_only(self):
        old = HEAD + iteration(1, findings=[finding("F1")], verdicts=[refuted("F1")], outcome="GO")
        self.assertTrue(L.append_only(old, old + "\nmore\n")[0])
        self.assertFalse(L.append_only(old, old.replace("reproduced", "edited").replace("config", "cfg"))[0])

    def test_iteration_cap(self):
        text = HEAD
        for n in range(1, 5):
            text += iteration(n, findings=[finding(f"F{n}")], verdicts=[refuted(f"F{n}")], outcome="GO")
        self.assertIn("E02", codes(text))


class Verdicts(unittest.TestCase):
    def test_open_major_is_no_go(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertEqual((rep["iteration"], rep["next_stage"]), (2, "fix"))

    def test_open_minor_still_ships(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1", "minor")],
                                slices=[slice_("F1", "minor")], outcome="GO")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertIn("minor", rep["computed"]["reason"])

    def test_inconclusive_goes_back_to_teardown_once_then_escalates(self):
        text = HEAD + iteration(1, findings=[finding("F1", conf="unproven", settled_by="TZ run")],
                                verdicts=[inconclusive("F1")], outcome="NO-GO")
        rep = L.status(text)
        self.assertEqual((rep["iteration"], rep["next_stage"]), (2, "teardown"))
        text += iteration(2, findings=[finding("F1", reexamines=True)], verdicts=[inconclusive("F1")],
                          outcome="ESCALATED")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["next_stage"], "escalated")

    def test_third_iteration_with_open_blocker_escalates(self):
        text = HEAD
        for n in range(1, 4):
            closed = [{"finding": f"F{n - 1}", "test": "t"}] if n > 1 else None
            outcome = "ESCALATED" if n == 3 else "NO-GO"
            text += iteration(n, closed=closed, findings=[finding(f"F{n}")], verdicts=[confirmed(f"F{n}", "blocker")],
                              slices=[slice_(f"F{n}", "blocker")], outcome=outcome)
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertIn("iteration 3 of 3", rep["computed"]["reason"])

    def test_a_pass_that_closes_nothing_while_open_is_a_stall(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        text += iteration(2, closed=[], outcome="ESCALATED")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertIn("stalled", rep["computed"]["reason"])

    def test_waiver_removes_a_finding_from_open(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1")],
                                slices=[slice_("F1")], outcome="NO-GO")
        text = text.replace("\n### Verdict: NO-GO", "\n### Decisions\n- **F1** — waived: user accepts\n\n### Verdict: GO")
        self.assertEqual(L.status(text)["errors"], [])


class Resume(unittest.TestCase):
    def test_partial_iteration_resumes_at_the_missing_stage(self):
        text = HEAD + L.render_iteration(1) + L.render_smells([], [])
        self.assertEqual(L.status(text)["next_stage"], "teardown")
        text += L.render_findings([finding("F1")]) + L.render_surfaces([], [])
        self.assertEqual(L.status(text)["next_stage"], "verdict")

    def test_empty_ledger_starts_at_refactor(self):
        self.assertEqual(L.status("")["next_stage"], "refactor")


class Legacy(unittest.TestCase):
    def test_old_prose_ledger_is_preamble_and_reserves_its_ids(self):
        rep = L.status(LEGACY)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["next_ids"]["F"], "F6")
        self.assertEqual(rep["next_stage"], "refactor")


if __name__ == "__main__":
    unittest.main()
