"""Ledger grammar and loop rules. Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile
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


    def test_the_red_run_example_is_valid_goes_no_go_then_go(self):
        example = re.findall(r"```markdown\n(.*?)```", SPEC, re.S)[1]
        self.assertIn("R1 — red run:", example)
        rep = L.status("# Ledger — cutoff\n\n" + example)
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["computed"]["outcome"], "GO")
        first = L.status("# Ledger — cutoff\n\n" + example.split("## Iteration 2")[0])
        self.assertEqual((first["errors"], first["computed"]["outcome"]), ([], "NO-GO"))


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


class RedRun(unittest.TestCase):
    """tyr-verdict's own run before a GO was red: a slice with an R id, no finding behind it."""
    RED = L.red_run_slice("R1", "`test_cutoff_reads_config`, `test_accept`")

    def one(self, outcome="NO-GO", slices=None):
        return HEAD + iteration(1, slices=[self.RED] if slices is None else slices, outcome=outcome)

    def test_a_red_run_is_no_go_and_goes_back_to_tdd(self):
        self.assertIn("- [ ] [blocker] R1 — red run: `test_cutoff_reads_config`, `test_accept`", self.one())
        rep = L.status(self.one())
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["computed"]["outcome"], "NO-GO")
        self.assertIn("the run before the verdict was red (R1)", rep["computed"]["reason"])
        self.assertEqual((rep["iteration"], rep["next_stage"]), (2, "fix"))
        self.assertEqual(rep["open_red"], ["R1"])
        self.assertEqual(rep["open_slices"][0]["id"], "R1")
        self.assertEqual(rep["next_ids"]["R"], "R2")

    def test_a_go_stated_over_a_red_run_does_not_check(self):
        self.assertIn("E50", codes(self.one(outcome="GO")))

    def test_the_next_iteration_closes_it_naming_the_test(self):
        text = self.one() + iteration(2, closed=[{"finding": "R1", "test": "test_cutoff_reads_config"}], outcome="GO")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertEqual((rep["computed"]["outcome"], rep["next_stage"], rep["open_red"]), ("GO", "done", []))
        self.assertIn("E32", codes(text.replace(" — verified by `test_cutoff_reads_config`", " — fixed")))

    def test_left_open_it_stalls_and_at_the_cap_escalates(self):
        text = self.one() + iteration(2, closed=[], outcome="ESCALATED")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertIn("stalled", rep["computed"]["reason"])

    def test_it_sits_beside_a_confirmed_finding(self):
        text = HEAD + iteration(1, findings=[finding("F1")], verdicts=[confirmed("F1", "minor")],
                                slices=[slice_("F1", "minor"), self.RED], outcome="NO-GO")
        rep = L.status(text)
        self.assertEqual(rep["errors"], [])
        self.assertEqual([s["id"] for s in rep["open_slices"]], ["F1", "R1"])

    def test_a_malformed_red_run_is_e33(self):
        not_blocker = {**self.RED, "severity": "major"}
        no_marker = {**self.RED, "behavior": "the suite failed"}
        names_nothing = self.one().replace("red run: `test_cutoff_reads_config`, `test_accept`", "red run:")
        self.assertIn("E33", codes(self.one(slices=[not_blocker])))
        self.assertIn("E33", codes(self.one(slices=[no_marker])))
        self.assertTrue({"E33", "E04"} & set(codes(names_nothing)))

    def test_a_red_run_id_is_never_reused(self):
        text = self.one() + iteration(2, closed=[{"finding": "R1", "test": "t"}], slices=[self.RED], outcome="NO-GO")
        self.assertIn("E34", codes(text))

    def test_closing_an_unknown_red_run_is_e32(self):
        text = HEAD + iteration(1, outcome="GO") + iteration(2, closed=[{"finding": "R7", "test": "t"}], outcome="GO")
        self.assertIn("E32", codes(text))

    def test_a_red_run_cannot_be_waived(self):
        text = self.one().replace("\n### Verdict: NO-GO", "\n### Decisions\n- **R1** — waived: ship it\n\n### Verdict: GO")
        self.assertTrue(codes(text))


class Unchanged(unittest.TestCase):
    """Ledgers written before the red-run slice existed read exactly as they did."""
    def test_ledgers_without_a_red_run_compute_what_they_always_did(self):
        f1 = dict(findings=[finding("F1")], verdicts=[confirmed("F1")], slices=[slice_("F1")], outcome="NO-GO")
        cases = {
            "GO": HEAD + iteration(1, outcome="GO"),
            "NO-GO": HEAD + iteration(1, **f1),
            "GO ": HEAD + iteration(1, **f1) + iteration(2, closed=[{"finding": "F1", "test": "t"}], outcome="GO"),
            "ESCALATED": HEAD + iteration(1, **f1) + iteration(2, closed=[], outcome="ESCALATED"),
        }
        for outcome, text in cases.items():
            rep = L.status(text)
            self.assertEqual(rep["errors"], [], outcome)
            self.assertEqual(rep["computed"]["outcome"], outcome.strip())
            self.assertEqual(rep["open_red"], [])


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

    def test_a_verdict_or_waiver_on_a_preamble_only_id_is_e20_and_reusing_it_is_e10(self):
        head = HEAD + "\nLegacy notes: F7 was discussed before the grammar existed.\n\n"
        text = head + iteration(1, verdicts=[confirmed("F7")], slices=[slice_("F7")], outcome="NO-GO")
        self.assertIn("E20", codes(text))
        text = head + iteration(1, outcome="GO").replace(
            "\n### Verdict: GO", "\n### Decisions\n- **F7** — waived: user accepts\n\n### Verdict: GO")
        self.assertEqual(codes(text), ["E20"])
        self.assertEqual(L.status(text)["waived"], [])
        self.assertIn("E10", codes(head + iteration(1, findings=[finding("F7")], verdicts=[refuted("F7")], outcome="GO")))


WAIVED = (HEAD + iteration(1, findings=[finding("F1"), finding("F2")], verdicts=[confirmed("F1"), confirmed("F2")],
                           slices=[slice_("F1"), slice_("F2")], outcome="NO-GO"))
WAIVED_F2 = WAIVED.replace("\n### Verdict: NO-GO", "\n### Decisions\n- **F2** — waived: user accepts\n\n### Verdict: NO-GO")


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def ledger(self, text, name="ledger.md"):
        (self.dir / name).write_text(text)
        return str(self.dir / name)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = L.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_check_and_status_on_a_path_that_is_not_a_file_exit_2(self):
        for path in (str(self.dir / "nope.md"), str(self.dir)):
            for cmd in ("check", "status"):
                for extra in ((), ("--json",)):
                    code, out, err = self.cli(cmd, path, *extra)
                    self.assertEqual((code, out), (2, ""), (cmd, path))
                    self.assertIn(f"no such file: {path}", err)

    def test_check_against_a_missing_older_copy_exits_2(self):
        code, out, err = self.cli("check", self.ledger(WAIVED), "--against", str(self.dir / "old.md"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("no such file", err)

    def test_next_id_on_a_ledger_not_yet_written_is_the_first_id(self):
        for kind in "FNR":
            self.assertEqual(self.cli("next-id", str(self.dir / "nope.md"), kind), (0, f"{kind}1\n", ""))
        self.assertEqual(self.cli("next-id", str(self.dir), "F")[0], 2)
        self.assertEqual(self.cli("next-id", self.ledger(WAIVED), "F"), (0, "F3\n", ""))

    def test_an_existing_ledger_still_checks(self):
        self.assertEqual(self.cli("check", self.ledger(WAIVED))[:2], (0, "0 error(s), 0 warning(s)\n"))

    def test_status_prints_the_waived_ids_on_one_line(self):
        code, out, _ = self.cli("status", self.ledger(WAIVED_F2))
        self.assertEqual(code, 0, out)
        lines = out.splitlines()
        self.assertIn("waived: F2", lines)
        self.assertIn("open blocking: F1", lines)
        self.assertEqual(lines[0], "iteration 2 · next stage: fix")
        _, out, _ = self.cli("status", self.ledger(WAIVED_F2.replace("- **F2** — waived", "- **F1** — waived: ok\n- **F2** — waived")
                                                   .replace("### Verdict: NO-GO", "### Verdict: GO")))
        self.assertIn("waived: F1, F2", out.splitlines())

    def test_status_says_waived_none(self):
        _, out, _ = self.cli("status", self.ledger(WAIVED))
        self.assertIn("waived: none", out.splitlines())

    def test_json_carries_the_waived_ids(self):
        for cmd in ("status", "check"):
            _, out, _ = self.cli(cmd, self.ledger(WAIVED_F2), "--json")
            self.assertEqual(json.loads(out)["waived"], ["F2"])
        self.assertEqual(L.status(WAIVED)["waived"], [])


if __name__ == "__main__":
    unittest.main()
