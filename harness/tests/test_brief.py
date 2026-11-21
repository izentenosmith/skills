"""The brief linter. Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import brief as B  # noqa: E402

REPO = HERE.parent.parent
FIXTURES = sorted((REPO / "evals" / "fixtures").glob("*/.workflow/brief.md"))

DRAFT = """# Build Plan: Enforce a cutoff window

**Status:** draft — awaiting approval
**Design:** `.workflow/designs/20261112-1105-cutoff.md`
**Category:** enhancement
**Summary:** Reject change requests inside the cutoff window.

**Current behavior:**
Any well-formed request is accepted.

**Desired behavior:**
A request inside the window is rejected with `CUTOFF_WINDOW`.

**Key interfaces (test seams):**
- The change-request handler — the public seam tests drive

**Acceptance criteria** (ordered — first is the tracer-bullet candidate):
- [ ] Tracer bullet: a request for a target inside the cutoff window is
      rejected with error code `CUTOFF_WINDOW`
- [ ] A request whose targets are all outside the window is accepted and persists
- [ ] The window length reads from account config, not a hard-coded default
- [ ] Edge case: a multi-part request with one part inside the window is rejected as a whole

**Test seams & prior art:**
- Mirror the existing handler tests

**Parallel tracks:** none — one rule behind one seam

**Out of scope:**
- Administrator overrides

**Ship checklist** (what no acceptance test can prove):
- [ ] Rollback: revert the deploy

**Base:** — (filled in by tdd before its first slice)

**Acceptance tests** (filled in by stage 3, acceptance-tests — leave empty here):
- **Command:** —

## Revisions
- (empty at creation; TDD's feedback edge appends here)
"""

MAPPING = """**Acceptance tests** (stage 3 — tdd is done when these pass):
- **Command:** `pytest tests/acceptance -q`
- [ ] Tracer bullet: a request for a target inside the cutoff window is rejected with error code `CUTOFF_WINDOW` → `test_inside_window_rejected`
- [ ] A request whose targets are all outside the window is accepted and persists → `test_outside_window_accepted`
- [ ] Edge case: a multi-part request with one part inside the window is rejected as a whole → `test_multipart_rejected`
- Not acceptance-testable: The window length reads from account config, not a hard-coded default — no config
  seam at the boundary; covered by tdd at the validator
"""
EMPTY = "**Acceptance tests** (filled in by stage 3, acceptance-tests — leave empty here):\n- **Command:** —\n"
MAPPED = DRAFT.replace(EMPTY, MAPPING)
assert MAPPED != DRAFT
BUILT = (MAPPED.replace("**Base:** — (filled in by tdd before its first slice)", "**Base:** `3f9c2ab41d07`")
         .replace("- [ ] Tracer bullet: a request for a target inside the cutoff window is\n"
                  "      rejected with error code `CUTOFF_WINDOW`",
                  "- [x] Tracer bullet: a request for a target inside the cutoff window is\n"
                  "      rejected with error code `CUTOFF_WINDOW` — verified by `test_inside_window_rejected`")
         .replace("**Status:** draft — awaiting approval", "**Status:** approved"))


def codes(text):
    return [p[0] for p in B.check(text)[0]]


def notes(text):
    return [n[0] for n in B.check(text)[1]]


class WhatPasses(unittest.TestCase):
    def test_the_fixture_briefs_all_pass(self):
        self.assertGreaterEqual(len(FIXTURES), 4)
        for path in FIXTURES:
            self.assertEqual(B.check(path.read_text())[0], [], path)

    def test_a_brief_at_each_stage_passes(self):
        for name, text in (("draft", DRAFT), ("mapped", MAPPED), ("built", BUILT)):
            self.assertEqual(B.check(text), ([], []), name)

    def test_the_mapping_may_name_criteria_by_number(self):
        by_number = MAPPED.replace(MAPPING, """**Acceptance tests** (stage 3):
- **Command:** `pytest tests/acceptance -q`
- [ ] Criterion 1 (tracer bullet) → `test_inside_window_rejected`
- [ ] Criterion 2 → `test_outside_window_accepted`
- [ ] Criterion 3 → `test_reads_config`
- [ ] Edge case: one part inside the window rejects the whole request → `test_multipart_rejected`
- [ ] Journey: a member books, edits and is refused inside the window → `test_journey`
""")
        self.assertEqual(codes(by_number), [])        # the reworded one is counted, the Journey line is extra


class Status(unittest.TestCase):
    def test_the_allowed_forms(self):
        for ok in ("draft — awaiting approval", "approved", "approved — by the user at launch (`--approve-brief`)"):
            self.assertEqual(codes(DRAFT.replace("draft — awaiting approval", ok)), [], ok)
        for bad in ("done", "draft", "ready for review", "approved by nobody in particular"):
            self.assertEqual(codes(DRAFT.replace("draft — awaiting approval", bad)), ["B02"], bad)

    def test_no_status_line_is_a_note_not_a_problem(self):
        text = DRAFT.replace("**Status:** draft — awaiting approval\n", "")
        self.assertEqual((codes(text), notes(text)), ([], ["I02"]))


class Sections(unittest.TestCase):
    def test_a_missing_required_section_is_b10(self):
        text = DRAFT.replace("**Out of scope:**\n- Administrator overrides\n\n", "")
        self.assertEqual(codes(text), ["B10"])
        self.assertEqual(codes(DRAFT.replace("## Revisions", "## Notes")), ["B10"])
        self.assertEqual(codes("# Build Plan: x\n")[:1], ["B10"])
        self.assertIn("B01", codes("nothing here\n"))

    def test_criteria_section_without_a_criterion_is_b11(self):
        import re
        text = re.sub(r"(\*\*Acceptance criteria\*\*[^\n]*\n).*?(\n\*\*Test seams)", r"\1- to be decided\n\2",
                      DRAFT, flags=re.S)
        self.assertEqual(codes(text), ["B11"])

    def test_no_ship_checklist_is_a_note(self):
        text = DRAFT.replace("**Ship checklist** (what no acceptance test can prove):\n- [ ] Rollback: revert the deploy\n\n", "")
        self.assertEqual((codes(text), notes(text)), ([], ["I03"]))


class Mapping(unittest.TestCase):
    def test_filled_without_a_command_is_b20(self):
        self.assertEqual(codes(MAPPED.replace("- **Command:** `pytest tests/acceptance -q`", "- **Command:** —")), ["B20"])

    def test_an_unmapped_criterion_is_b21_at_its_line(self):
        text = MAPPED.replace("- [ ] Edge case: a multi-part request with one part inside the window is rejected "
                              "as a whole → `test_multipart_rejected`\n", "")
        problems = B.check(text)[0]
        self.assertEqual([p[0] for p in problems], ["B21"])
        self.assertIn("Edge case: a multi-part", text.splitlines()[problems[0][1] - 1])

    def test_a_criterion_mapped_twice_is_b22(self):
        text = MAPPED.replace("- Not acceptance-testable:", "- [ ] A request whose targets are all outside the window "
                              "is accepted and persists → `test_again`\n- Not acceptance-testable:")
        self.assertEqual(codes(text), ["B22"])

    def test_a_line_in_another_shape_is_b23(self):
        self.assertIn("B23", codes(MAPPED.replace(" → `test_multipart_rejected`", " (see the test file)")))
        self.assertIn("B23", codes(MAPPED.replace("- Not acceptance-testable:", "- red on behavior, 3 failed\n"
                                                  "- Not acceptance-testable:")))

    def test_not_testable_needs_its_reason(self):
        text = MAPPED.replace(" — no config\n  seam at the boundary; covered by tdd at the validator", "")
        self.assertEqual(codes(text), ["B23"])

    def test_too_few_or_too_many_lines_when_wording_differs(self):
        loose = MAPPED.replace("- [ ] A request whose targets are all outside the window is accepted and persists →",
                               "- [ ] Happy path →")
        self.assertEqual(codes(loose), [])
        self.assertEqual(codes(loose.replace("- [ ] Edge case: a multi-part request with one part inside the window "
                                             "is rejected as a whole → `test_multipart_rejected`\n", "")), ["B21"])
        self.assertEqual(codes(loose.replace("- Not acceptance-testable:", "- [ ] Another → `test_x`\n"
                                             "- Not acceptance-testable:")), ["B22"])


class Ticks(unittest.TestCase):
    def test_a_bare_tick_is_b30(self):
        text = BUILT.replace(" — verified by `test_inside_window_rejected`", "")
        problems = B.check(text)[0]
        self.assertEqual([p[0] for p in problems], ["B30"])
        self.assertIn("- [x] Tracer bullet", text.splitlines()[problems[0][1] - 1])

    def test_a_tick_without_a_base_commit_is_b31(self):
        self.assertEqual(codes(BUILT.replace("**Base:** `3f9c2ab41d07`", "**Base:** —")), ["B31"])
        self.assertEqual(codes(BUILT.replace("**Base:** `3f9c2ab41d07`\n\n", "")), ["B31"])
        self.assertEqual(codes(BUILT.replace("**Base:** `3f9c2ab41d07`", "**Base:** 3f9c2ab")), [])


class Unconfirmed(unittest.TestCase):
    TEXT = BUILT.replace("- (empty at creation; TDD's feedback edge appends here)",
                         "- 2026-11-19: the default applies to every account — unconfirmed (nobody to ask)\n"
                         "- 2026-11-19: approved by the user\n"
                         "- 2026-11-20: window edge read as exclusive; `unconfirmed`")

    def test_every_unconfirmed_revision_is_listed_and_is_not_a_problem(self):
        problems, found = B.check(self.TEXT)
        self.assertEqual(problems, [])
        self.assertEqual([n[0] for n in found], ["I01", "I01"])
        self.assertIn("every account", self.TEXT.splitlines()[found[0][1] - 1])


class Cli(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = B.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def test_exit_codes_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = pathlib.Path(tmp) / "good.md", pathlib.Path(tmp) / "bad.md"
            good.write_text(Unconfirmed.TEXT)
            bad.write_text(BUILT.replace("**Base:** `3f9c2ab41d07`", "**Base:** —"))
            code, out = self.run_cli("check", str(good))
            self.assertEqual(code, 0)
            self.assertRegex(out, r"note: I01 line \d+: unconfirmed: 2026-11-19: the default applies")
            self.assertIn("0 problem(s), 2 note(s)", out)
            code, out = self.run_cli("check", str(bad))
            self.assertEqual(code, 1)
            self.assertRegex(out, r"error: B31 line \d+: ")
            self.assertEqual(self.run_cli("check", str(pathlib.Path(tmp) / "none.md"))[0], 2)
            self.assertEqual(self.run_cli()[0], 2)
            self.assertEqual(self.run_cli("check")[0], 2)

    def test_it_runs_alone_from_another_folder(self):
        """It is copied into skill folders as scripts/brief.py: no sibling imports, and -I."""
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / "scripts" / "brief.py"
            copy.parent.mkdir()
            copy.write_text((HERE.parent / "brief.py").read_text())
            r = subprocess.run([sys.executable, "-I", str(copy), "check", str(FIXTURES[0])],
                               capture_output=True, text=True, cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("0 problem(s)", r.stdout)


if __name__ == "__main__":
    unittest.main()
