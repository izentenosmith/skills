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
        (self.repo / "tests" / "test_app.py").write_text("def test_placeholder():\n    assert True\n")
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

    def run_loop(self, scenario="converge", test_cmd="true", *extra):
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
        self.assertIn("- [x] F1 — verified by `test_cutoff_reads_config`", text)
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
        self.assertEqual(self.run_loop("converge", "true", "--once"), loop.EXIT_GO)
        self.assertEqual(L.status(self.ledger())["next_stage"], "teardown")
        self.assertEqual(self.run_loop("converge", "true"), loop.EXIT_GO, self.output)
        self.assertEqual(L.status(self.ledger())["next_stage"], "done")
        self.assertEqual(sum(1 for c in self.calls() if c["stage"] == "refactor" and c["n"] == 1), 1)

    def test_settings_are_remembered(self):
        self.run_loop("converge", "true", "--once")
        cfg = json.loads((self.repo / ".workflow" / "harness.json").read_text())
        self.assertEqual(cfg["test_cmd"], "true")
        self.assertTrue(cfg["base"])

    # ---------------------------------------------------------------- the rules

    def test_red_suite_stops_at_the_gate(self):
        self.assertEqual(self.run_loop("converge", "false"), loop.EXIT_GATE)
        self.assertEqual(self.calls(), [])

    def test_a_pass_that_closes_nothing_escalates(self):
        self.assertEqual(self.run_loop("stall"), loop.EXIT_ESCALATED, self.output)
        rep = L.status(self.ledger())
        self.assertEqual(rep["errors"], [])
        self.assertIn("stalled", rep["computed"]["reason"])

    def test_second_inconclusive_escalates(self):
        self.assertEqual(self.run_loop("doubt"), loop.EXIT_ESCALATED, self.output)
        text = self.ledger()
        self.assertIn("#### F1 (re-examined)", text)
        self.assertIn("INCONCLUSIVE a second time", L.status(text)["computed"]["reason"])

    def test_an_agent_cannot_write_the_ledger(self):
        self.assertEqual(self.run_loop("vandal"), loop.EXIT_GO, self.output)
        self.assertNotIn("I tidied this up", self.ledger())
        self.assertIn("restored", self.output)

    def test_dry_run_writes_prompts_and_calls_nothing(self):
        self.assertEqual(self.run_loop("converge", "true", "--dry-run"), loop.EXIT_GO)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.repo / ".workflow" / "ledger.md").exists())
        prompts = list((self.repo / ".workflow" / "runs").glob("*/calls/*.prompt.md"))
        self.assertEqual(len(prompts), 1)
        self.assertIn("refactor-review", prompts[0].read_text())


if __name__ == "__main__":
    unittest.main()
