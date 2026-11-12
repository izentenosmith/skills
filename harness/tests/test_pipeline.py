"""pipeline.py end to end — design.md to a verdict — with fake_claude.py standing in for the model.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import ledger as L  # noqa: E402
import loop  # noqa: E402
import pipeline  # noqa: E402

FAKE = HERE / "fake_claude.py"
SUITE = 'for f in tests/test_*.py; do PYTHONPATH=. python3 "$f" || exit 1; done'
DESIGN = """# Design: Cutoff window

**Status:** {status}
**Solving:** bookings too close to the slot are accepted.

## Decisions
- **Data model — window length:** 120 minutes by default — simplest. Rejected: per-venue, no demand yet.
"""
IDENT = {f"GIT_{who}_{what}": "t@t" for who in ("AUTHOR", "COMMITTER") for what in ("NAME", "EMAIL")}


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                          check=True, capture_output=True, text=True).stdout.strip()


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "svc"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "app.py").write_text("def check_cutoff(slot, config):\n    return None\n")
        (self.repo / "tests" / "test_app.py").write_text("assert True\n")
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / ".git" / "info" / "exclude").write_text(".workflow/\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.wf = self.repo / ".workflow"
        self.wf.mkdir()
        self.design("resolved")
        self.log = pathlib.Path(self.tmp.name) / "calls.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    NAME = "20261112-1105-cutoff-window"

    def design(self, status, name=NAME):
        (self.wf / "designs").mkdir(exist_ok=True)
        (self.wf / "designs" / f"{name}.md").write_text(DESIGN.format(status=status))

    @property
    def done(self):
        """Where a finished change's files are: archived under the design's name on GO."""
        return self.wf / "archive" / self.NAME

    def run_pipeline(self, *extra, pl="ok", scenario="converge"):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_CLAUDE_LOG": str(self.log), "FAKE_PL": pl,
               "FAKE_SCENARIO": scenario, **IDENT}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                code = pipeline.main(["--repo", str(self.repo), "--test-cmd", SUITE, *extra])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = err.getvalue()
        return code

    def stages(self):
        calls = [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []
        out = []
        for c in calls:
            if not out or out[-1] != c["stage"]:
                out.append(c["stage"])
        return out

    def brief(self):
        live = self.wf / "brief.md"
        return (live if live.exists() else self.done / "brief.md").read_text()

    # ---------------------------------------------------------------- the whole pipeline

    def test_design_to_go(self):
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GO, self.output)
        self.assertEqual(self.stages()[:5], ["pl-brief", "pl-acceptance", "pl-build", "refactor", "teardown-delegate"])
        self.assertIn("fix", self.stages())                       # the loop's NO-GO went back through tdd
        ledger = (self.done / "ledger.md").read_text()
        self.assertEqual(L.status(ledger)["errors"], [])
        self.assertIn("### Verdict: GO", ledger)
        self.assertIn("Open ship-checklist items (1): Rollback: revert the commit", ledger)
        state = json.loads((self.done / "pipeline.json").read_text())
        self.assertEqual(state["done"], ["brief", "acceptance", "build", "loop"])
        self.assertEqual(state["verdict"], "GO")
        report = (self.done / "pipeline-report.md").read_text()
        self.assertIn("**Verdict:** GO", report)
        self.assertIn("the default applies to every account", report)   # what was decided for the user
        self.assertIn("Rollback: revert the commit", report)

    def test_it_works_on_a_branch_and_commits_as_it_goes(self):
        self.run_pipeline()
        self.assertEqual(git(self.repo, "rev-parse", "main"), self.base)          # the default branch never moves
        self.assertEqual(git(self.repo, "symbolic-ref", "--short", "HEAD"), "pipeline/cutoff-window")
        subjects = git(self.repo, "log", "--format=%s", f"{self.base}..HEAD").splitlines()
        self.assertEqual(subjects[-1], "the cutoff defaults to 120 minutes")      # tdd's own slice commit
        self.assertIn("tdd: what the slices left uncommitted", subjects)          # the acceptance test it didn't stage
        self.assertIn("loop iteration 2: tdd closes F1", subjects)
        self.assertEqual(loop.dirty(self.repo), [])
        self.assertIn(f"**Base:** `{self.base}`", self.brief())

    def test_the_brief_is_marked_approved_by_the_design_not_as_reviewed(self):
        self.run_pipeline()
        self.assertIn("**Status:** approved — from the resolved design, by harness/pipeline.py (no separate review)",
                      self.brief())

    def test_resumes_at_the_first_stage_not_done(self):
        self.assertEqual(self.run_pipeline(pl="build-never"), pipeline.EXIT_GATE, self.output)
        self.assertIn("did not reach green in 2 attempt(s)", self.output)
        self.assertEqual(self.stages(), ["pl-brief", "pl-acceptance", "pl-build"])
        self.log.unlink()
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GO, self.output)
        self.assertEqual(self.stages()[0], "pl-build")            # brief and acceptance are not run again

    # ---------------------------------------------------------------- what it refuses

    def test_no_design_needs_you(self):
        (self.wf / "designs" / f"{self.NAME}.md").unlink()
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_INPUT)
        self.assertIn("run architect-deep-dive first", self.output)
        self.assertEqual(self.stages(), [])

    def test_an_unfinished_design_is_not_built_on(self):
        self.design("in progress")
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_INPUT)
        self.assertIn(f"{self.NAME}.md (in progress)", self.output)          # found, and why it doesn't count
        self.assertEqual(self.run_pipeline("--design", f".workflow/designs/{self.NAME}.md"), pipeline.EXIT_INPUT)
        self.assertIn("not resolved", self.output)                           # naming it doesn't get round it
        self.assertEqual(self.stages(), [])

    def test_a_brief_from_other_work_is_not_overwritten(self):
        (self.wf / "brief.md").write_text("# Build Plan: Something else\n\n- [ ] Tracer bullet: x\n")
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_INPUT)
        self.assertIn("this pipeline did not write it", self.output)
        self.assertIn("Something else", self.brief())
        self.assertEqual(self.stages(), [])

    def test_a_dirty_tree_or_a_red_suite_stops_before_any_call(self):
        (self.repo / "scratch.py").write_text("x = 1\n")
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_INPUT)
        self.assertIn("uncommitted changes (scratch.py)", self.output)
        (self.repo / "scratch.py").unlink()
        (self.repo / "tests" / "test_app.py").write_text("assert False\n")
        git(self.repo, "commit", "-qam", "red")
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GATE)
        self.assertEqual(self.stages(), [])

    def test_the_brief_stage_may_not_write_code(self):
        self.assertEqual(self.run_pipeline(pl="strays"), pipeline.EXIT_GATE)
        self.assertIn("changed files outside .workflow/ (app.py)", self.output)
        self.assertEqual(self.stages(), ["pl-brief"])

    def test_a_brief_without_criteria_stops(self):
        self.assertEqual(self.run_pipeline(pl="nocriteria"), pipeline.EXIT_GATE)
        self.assertIn("no acceptance criteria", self.output)

    def test_acceptance_tests_must_be_red_and_red_on_behavior(self):
        self.assertEqual(self.run_pipeline(pl="accept-green"), pipeline.EXIT_GATE)
        self.assertIn("pass before anything is built", self.output)
        self.assertNotIn("pl-build", self.stages())

    def test_acceptance_tests_that_cannot_load_are_not_red(self):
        self.assertEqual(self.run_pipeline(pl="accept-load"), pipeline.EXIT_GATE)
        self.assertIn("red for the wrong reason", self.output)
        self.assertNotIn("pl-build", self.stages())

    def test_tdd_gets_a_second_attempt_and_is_told_what_is_red(self):
        self.assertEqual(self.run_pipeline(pl="build-slow"), pipeline.EXIT_GO, self.output)
        prompts = sorted(self.wf.glob("runs/*/calls/pl-build-2.prompt.md"))
        self.assertEqual(len(prompts), 1)
        self.assertIn("suite is red after tdd", prompts[0].read_text())   # told what is still red

    # ---------------------------------------------------------------- one file per design, nothing shared

    def test_go_archives_the_change_under_the_designs_name_and_marks_it_built(self):
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GO, self.output)
        for f in ("brief.md", "ledger.md", "pipeline.json", "pipeline-report.md"):
            self.assertFalse((self.wf / f).exists(), f)            # the shared paths are free for the next change
            self.assertTrue((self.done / f).exists(), f)
        design = (self.wf / "designs" / f"{self.NAME}.md").read_text()
        self.assertIn("**Status:** built — branch `pipeline/cutoff-window`, record in "
                      f"`.workflow/archive/{self.NAME}/`", design)
        self.assertIn(f"**Design:** `.workflow/designs/{self.NAME}.md`", self.brief())

    def test_a_second_design_builds_next_without_touching_the_first(self):
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GO, self.output)
        self.design("resolved", "20261113-0900-cutoff-window")     # same title, another day: its own file
        self.assertEqual(self.run_pipeline("--design", ".workflow/designs/20261113-0900-cutoff-window.md",
                                           "--dry-run"), pipeline.EXIT_GO, self.output)
        self.assertIn("20261113-0900-cutoff-window.md", self.output)
        self.assertTrue((self.done / "ledger.md").exists())

    def test_two_resolved_designs_must_be_told_apart(self):
        self.design("resolved", "20261113-0900-opening-hours")
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_INPUT)
        self.assertIn("more than one resolved design", self.output)
        self.assertIn("20261113-0900-opening-hours.md", self.output)
        self.assertEqual(self.stages(), [])
        self.assertEqual(self.run_pipeline("--design", f".workflow/designs/{self.NAME}.md"),
                         pipeline.EXIT_GO, self.output)
        self.assertIn("**Status:** resolved", (self.wf / "designs" / "20261113-0900-opening-hours.md").read_text())

    def test_an_escalated_change_stays_in_place_to_be_resumed(self):
        self.assertEqual(self.run_pipeline(scenario="stall"), pipeline.EXIT_ESCALATED, self.output)
        self.assertTrue((self.wf / "ledger.md").exists())
        self.assertFalse((self.wf / "archive").exists())
        self.assertIn("**Status:** resolved", (self.wf / "designs" / f"{self.NAME}.md").read_text())

    # ---------------------------------------------------------------- the two ways in

    def test_pause_at_brief_stops_once_then_builds(self):
        self.assertEqual(self.run_pipeline("--pause-at-brief"), pipeline.EXIT_INPUT)
        self.assertIn("paused after the brief", self.output)
        self.assertIn("**Status:** draft — awaiting approval", self.brief())
        self.assertEqual(self.stages(), ["pl-brief"])
        self.log.unlink()
        self.assertEqual(self.run_pipeline(), pipeline.EXIT_GO, self.output)
        self.assertEqual(self.stages()[0], "pl-brief")            # written once more is fine; what matters:
        self.assertIn("**Status:** approved — reviewed at the pause, then re-run", self.brief())

    def test_from_brief_skips_the_design_and_stage_two(self):
        (self.wf / "designs" / f"{self.NAME}.md").unlink()
        (self.wf / "brief.md").write_text(
            "# Build Plan: Cutoff window\n\n**Status:** approved\n\n**Acceptance criteria** (ordered):\n"
            "- [ ] Tracer bullet: the cutoff defaults to 120 minutes\n- [ ] Edge case: an empty config\n\n"
            "**Acceptance tests** (filled in by stage 3):\n- **Command:** —\n\n## Revisions\n- (none yet)\n")
        self.assertEqual(self.run_pipeline("--from-brief"), pipeline.EXIT_GO, self.output)
        self.assertEqual(self.stages()[:2], ["pl-acceptance", "pl-build"])
        archived = list(self.wf.glob("archive/*-cutoff-window/brief.md"))   # no design: named by when and what
        self.assertEqual(len(archived), 1)
        self.assertIn("**Status:** approved\n", archived[0].read_text())   # the user's own approval is left as written

    def test_dry_run_writes_the_next_prompt_and_calls_nothing(self):
        self.assertEqual(self.run_pipeline("--dry-run"), pipeline.EXIT_GO, self.output)
        self.assertEqual(self.stages(), [])
        prompts = list(self.wf.glob("runs/*/calls/pl-brief.prompt.md"))
        self.assertEqual(len(prompts), 1)
        self.assertIn(f"designs/{self.NAME}.md", prompts[0].read_text())
        self.assertFalse((self.wf / "brief.md").exists())


if __name__ == "__main__":
    unittest.main()
