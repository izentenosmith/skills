"""The orchestrator end to end, with fake_claude.py standing in for the model.
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

FAKE = HERE / "fake_claude.py"
# Each test file is a script that exits non-zero when an assertion fails.
SUITE = 'for f in tests/test_*.py; do PYTHONPATH=. python3 "$f" || exit 1; done'
BRIEF = """# Build Plan: Cutoff window

**Acceptance criteria** (ordered):
- [x] Tracer bullet: a booking inside the window is rejected
- [x] The window length reads from account config

## Revisions
- (none yet)
"""


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo,
                   check=True, capture_output=True)


class LoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "svc"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "app.py").write_text("def check_cutoff(slot, config):\n    return None\n")
        (self.repo / "tests" / "test_app.py").write_text("assert True\n")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "checkout", "-qb", "feature")
        (self.repo / "app.py").write_text("DEFAULT = 120\n\ndef check_cutoff(slot, config):\n    return DEFAULT\n")
        (self.repo / ".workflow").mkdir()
        (self.repo / ".workflow" / "brief.md").write_text(BRIEF)
        self.log = pathlib.Path(self.tmp.name) / "calls.jsonl"
        self.env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_CLAUDE_LOG": str(self.log)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_loop(self, scenario="converge", test_cmd=SUITE, *extra):
        old = {k: os.environ.get(k) for k in [*self.env, "FAKE_SCENARIO"]}
        os.environ.update(self.env, FAKE_SCENARIO=scenario)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                code = loop.main(["--repo", str(self.repo), "--test-cmd", test_cmd, *extra])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = err.getvalue()
        return code

    def ledger(self):
        return (self.repo / ".workflow" / "ledger.md").read_text()

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    # ---------------------------------------------------------------- the happy loop

    def test_converges_to_go_in_two_iterations(self):
        self.assertEqual(self.run_loop(), loop.EXIT_GO, self.output)
        rep = L.status(self.ledger())
        self.assertEqual(rep["errors"], [])
        self.assertEqual((rep["iteration"], rep["next_stage"]), (2, "done"))
        text = self.ledger()
        self.assertIn("### Verdict: NO-GO", text)
        self.assertIn("### Verdict: GO", text)
        self.assertIn("- [x] F1 — verified by `tests/test_fix.py::test_cutoff_reads_config`", text)
        self.assertIn("- **N1** — left: condition not met", text)

    def test_stage_order_is_the_pipeline(self):
        self.run_loop()
        order = []
        for c in self.calls():
            if not order or order[-1] != (c["n"], c["stage"]):
                order.append((c["n"], c["stage"]))
        self.assertEqual(order, [
            (1, "refactor"), (1, "teardown-delegate"), (1, "consolidate"), (1, "verify"), (1, "verdict"),
            (2, "fix"), (2, "refactor"), (2, "teardown-delegate"),
        ])  # nothing found in iteration 2, so there is nothing to verify or adjudicate

    def test_teardown_fans_out_read_only(self):
        self.run_loop()
        delegates = [c for c in self.calls() if c["stage"] == "teardown-delegate" and c["n"] == 1]
        self.assertEqual(len(delegates), 3)
        for c in delegates:
            tools = c["argv"][c["argv"].index("--tools") + 1]
            self.assertEqual(tools, "Read,Grep,Glob")
            self.assertNotIn("--permission-mode", c["argv"])

    def test_no_call_can_leave_a_background_shell_behind(self):
        # claude -p waits for background shells before exiting; one stalled a live verdict for 12 minutes
        self.run_loop()
        self.assertTrue(self.calls())
        self.assertTrue(all(c["no_background"] == "1" for c in self.calls()))

    def test_verification_runs_in_a_scratch_copy(self):
        self.run_loop()
        verify = [c for c in self.calls() if c["stage"] == "verify"]
        self.assertTrue(verify)
        for c in verify:
            self.assertNotEqual(pathlib.Path(c["cwd"]).resolve(), self.repo.resolve())
            self.assertIn("harness-verify-", c["cwd"])

    def test_resumes_from_the_ledger(self):
        self.assertEqual(self.run_loop("converge", SUITE, "--once"), loop.EXIT_GO)
        self.assertEqual(L.status(self.ledger())["next_stage"], "teardown")
        self.assertEqual(self.run_loop("converge", SUITE), loop.EXIT_GO, self.output)
        self.assertEqual(L.status(self.ledger())["next_stage"], "done")
        self.assertEqual(sum(1 for c in self.calls() if c["stage"] == "refactor" and c["n"] == 1), 1)

    def test_settings_are_remembered(self):
        self.run_loop("converge", SUITE, "--once")
        cfg = json.loads((self.repo / ".workflow" / "harness.json").read_text())
        self.assertEqual(cfg["test_cmd"], SUITE)
        self.assertTrue(cfg["base"])

    # ---------------------------------------------------------------- the rules

    def test_red_acceptance_tests_stop_at_the_gate(self):
        brief = self.repo / ".workflow" / "brief.md"
        brief.write_text(brief.read_text().replace(
            "## Revisions", "**Acceptance tests** (stage 3):\n- **Command:** `false`\n\n## Revisions"))
        self.assertEqual(self.run_loop(), loop.EXIT_GATE)
        self.assertIn("acceptance tests are red", self.output)
        self.assertEqual(self.calls(), [])

    def test_green_acceptance_tests_from_the_brief_are_gated_every_time(self):
        brief = self.repo / ".workflow" / "brief.md"
        brief.write_text(brief.read_text().replace(
            "## Revisions", "**Acceptance tests** (stage 3):\n- **Command:** `true`\n\n## Revisions"))
        self.assertEqual(self.run_loop(), loop.EXIT_GO, self.output)
        self.assertGreaterEqual(self.output.count("acceptance GREEN"), 4)

    def test_acceptance_cmd_flag_overrides_and_is_remembered(self):
        self.assertEqual(self.run_loop("converge", SUITE, "--acceptance-cmd", "false"), loop.EXIT_GATE)
        cfg = json.loads((self.repo / ".workflow" / "harness.json").read_text())
        self.assertEqual(cfg["acceptance_cmd"], "false")

    def test_red_suite_stops_at_the_gate(self):
        self.assertEqual(self.run_loop("converge", "false"), loop.EXIT_GATE)
        self.assertEqual(self.calls(), [])

    def test_a_pass_that_closes_nothing_escalates(self):
        self.assertEqual(self.run_loop("stall"), loop.EXIT_ESCALATED, self.output)
        rep = L.status(self.ledger())
        self.assertEqual(rep["errors"], [])
        self.assertIn("stalled", rep["computed"]["reason"])

    def test_a_remediation_test_that_passes_without_the_fix_closes_nothing(self):
        self.assertEqual(self.run_loop("vacuous"), loop.EXIT_ESCALATED, self.output)
        self.assertIn("not-red", self.output)
        self.assertNotIn("- [x] F1", self.ledger())
        self.assertIn("stalled", L.status(self.ledger())["computed"]["reason"])

    def test_closed_slices_record_the_red_green_proof(self):
        self.run_loop()
        self.assertIn("— verified by `tests/test_fix.py::test_cutoff_reads_config` — red→green checked",
                      self.ledger())

    def test_second_inconclusive_escalates(self):
        self.assertEqual(self.run_loop("doubt"), loop.EXIT_ESCALATED, self.output)
        text = self.ledger()
        self.assertIn("#### F1 (re-examined)", text)
        self.assertIn("INCONCLUSIVE a second time", L.status(text)["computed"]["reason"])

    def test_an_agent_cannot_write_the_ledger(self):
        self.assertEqual(self.run_loop("vandal"), loop.EXIT_GO, self.output)
        self.assertNotIn("I tidied this up", self.ledger())
        self.assertIn("restored", self.output)

    # ---------------------------------------------------------------- the bar, the base, save points

    def test_bar_signals_point_at_a_weakened_check(self):
        diff = "\n".join([
            "--- a/tests/test_old.py", "+++ /dev/null", "-def test_gone():", "-    assert total() == 1",
            "--- a/tests/test_app.py", "+++ b/tests/test_app.py",
            "+@pytest.mark.skip(reason='flaky')", "-    assert fee == 15", "+    assert fee",
            "-    assert code == 'CUTOFF'",
            "--- a/app.py", "+++ b/app.py", "+    x = compute()  # type: ignore", "+    raise NotImplementedError",
            "", "--- a/setup.cfg", "+++ b/setup.cfg", "-fail_under = 80", "+fail_under = 60",
        ])
        got = "\n".join(loop.bar_signals(diff))
        for want in ("`tests/test_old.py` — a test file deleted", "a test skipped", "a checker suppressed",
                     "work left unfinished", "a threshold or gate line changed",
                     "`tests/test_app.py` — 2 assertion line(s) removed, 1 added"):
            self.assertIn(want, got)
        self.assertNotIn("test_old.py` — 1 assertion", got)   # a deleted file is reported once, as deleted
        self.assertEqual(loop.bar_signals("--- a/app.py\n+++ b/app.py\n+    return config.get('cutoff')\n"), [])

    def test_the_bar_delegate_gets_the_leads_and_only_that_delegate(self):
        (self.repo / "tests" / "test_app.py").write_text("# @pytest.mark.skip\nassert True\n")
        self.run_loop("converge", SUITE, "--once")           # refactor
        self.run_loop("converge", SUITE, "--once")           # teardown
        prompts = sorted((self.repo / ".workflow" / "runs").glob("*/calls/i1-teardown-[0-9].prompt.md"))
        self.assertEqual(len(prompts), 3)
        with_leads = [p for p in prompts if "a test skipped" in p.read_text()]
        self.assertEqual(len(with_leads), 1)
        self.assertIn("the bar itself", with_leads[0].read_text().split("**Your target:**")[1].split("\n")[0])

    def test_base_comes_from_the_brief_once_slices_are_committed(self):
        base = subprocess.run(["git", "rev-parse", "main"], cwd=self.repo, capture_output=True, text=True).stdout.strip()
        brief = self.repo / ".workflow" / "brief.md"
        brief.write_text(brief.read_text().replace("## Revisions", f"**Base:** `{base}`\n\n## Revisions"))
        git(self.repo, "branch", "-D", "main")                # no main to take a merge-base from
        git(self.repo, "add", "app.py")
        git(self.repo, "commit", "-qm", "slice 1")            # tdd's save point: HEAD is now after the change
        self.assertEqual(self.run_loop("converge", SUITE, "--once"), loop.EXIT_GO, self.output)
        cfg = json.loads((self.repo / ".workflow" / "harness.json").read_text())
        self.assertEqual(cfg["base"], base)

    def test_head_as_base_is_pinned_to_a_commit(self):
        self.run_loop("converge", SUITE, "--base", "HEAD", "--once")
        cfg = json.loads((self.repo / ".workflow" / "harness.json").read_text())
        self.assertRegex(cfg["base"], r"^[0-9a-f]{40}$")

    def test_an_empty_diff_is_an_error_not_a_clean_teardown(self):
        git(self.repo, "add", "app.py")
        git(self.repo, "commit", "-qm", "slice 1")
        self.assertEqual(self.run_loop("converge", SUITE, "--base", "HEAD"), loop.EXIT_ERROR)
        self.assertIn("nothing to tear down", self.output)
        self.assertNotIn("### Findings", self.ledger())

    def test_save_points_commit_each_write_stage(self):
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True).stdout.strip()
        (self.repo / ".git" / "info" / "exclude").write_text(".workflow/\n")
        git(self.repo, "add", "app.py")
        git(self.repo, "commit", "-qm", "slice 1")
        env = {k: os.environ.get(k) for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                                              "GIT_COMMITTER_EMAIL")}
        os.environ.update({k: "t@t" for k in env})
        try:
            code = self.run_loop("converge", SUITE, "--base", base, "--save-points")
        finally:
            for k, v in env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(code, loop.EXIT_GO, self.output)
        subjects = subprocess.run(["git", "log", "--format=%s", f"{base}..HEAD"], cwd=self.repo,
                                  capture_output=True, text=True).stdout.splitlines()
        self.assertEqual(subjects, ["loop iteration 2: tdd closes F1", "slice 1"])
        self.assertEqual(loop.dirty(self.repo), [])
        fix = next(c for c in self.calls() if c["stage"] == "fix")
        self.assertTrue(fix)

    def test_save_points_refuse_a_dirty_tree_and_the_default_branch(self):
        self.assertEqual(self.run_loop("converge", SUITE, "--save-points"), loop.EXIT_ERROR)   # app.py uncommitted
        self.assertEqual(self.calls(), [])
        git(self.repo, "add", "app.py")
        git(self.repo, "commit", "-qm", "slice 1")
        (self.repo / ".git" / "info" / "exclude").write_text(".workflow/\n")
        git(self.repo, "checkout", "-q", "main")
        self.assertEqual(self.run_loop("converge", SUITE, "--save-points"), loop.EXIT_ERROR)
        self.assertEqual(self.calls(), [])

    def test_go_names_the_open_ship_checklist_items(self):
        brief = self.repo / ".workflow" / "brief.md"
        brief.write_text(brief.read_text().replace(
            "## Revisions", "**Ship checklist** (what no test can prove):\n"
            "- [x] Rollout: flag `cutoff` defaults off — in config.py\n"
            "- [ ] Rollback: turn the flag off\n- [ ] Observability: alert on rejections\n\n## Revisions"))
        self.assertEqual(self.run_loop(), loop.EXIT_GO, self.output)
        reason = L.status(self.ledger())
        self.assertEqual(reason["errors"], [])
        self.assertIn("Open ship-checklist items (2): Rollback: turn the flag off; Observability: alert on rejections",
                      self.ledger())
        self.assertNotIn("Rollout: flag", self.ledger())

    def test_a_draft_brief_is_called_out(self):
        brief = self.repo / ".workflow" / "brief.md"
        brief.write_text(brief.read_text().replace(
            "**Acceptance criteria**", "**Status:** draft — awaiting approval\n\n**Acceptance criteria**"))
        self.run_loop("converge", SUITE, "--once")
        self.assertIn("draft — awaiting approval", self.output)

    def test_a_teardown_no_delegate_answered_is_not_a_clean_one(self):
        # Seen live: every delegate hit the account's spend limit, nothing was attacked, and the loop called GO.
        self.assertEqual(self.run_loop("mute"), loop.EXIT_ERROR, self.output)
        self.assertIn("no surface was attacked", self.output)
        self.assertNotIn("### Verdict", self.ledger())
        self.assertNotIn("### Surfaces", self.ledger())
        self.assertEqual(L.status(self.ledger())["next_stage"], "teardown")   # the next run retries it

    def test_a_slice_reported_twice_closes_once(self):
        # Seen live (eval 15, iteration 39): "closed 9/7", two `- [x] F1` lines, E32, and the loop stopped.
        self.assertEqual(self.run_loop("twice"), loop.EXIT_GO, self.output)
        self.assertEqual(self.ledger().count("- [x] F1 —"), 1)
        self.assertIn("tests/test_fix.py::test_cutoff_reads_config + tests/test_fix.py::check_cutoff", self.ledger())
        self.assertEqual(L.status(self.ledger())["errors"], [])

    def test_dry_run_writes_prompts_and_calls_nothing(self):
        self.assertEqual(self.run_loop("converge", SUITE, "--dry-run"), loop.EXIT_GO)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / ".workflow" / "ledger.md").exists())
        prompts = list((self.repo / ".workflow" / "runs").glob("*/calls/*.prompt.md"))
        self.assertEqual(len(prompts), 1)
        self.assertIn("refactor-review", prompts[0].read_text())


if __name__ == "__main__":
    unittest.main()
