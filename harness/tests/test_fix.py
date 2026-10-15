"""fix.py end to end, with fake_claude.py standing in for the model and a fake `gh` on PATH.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import fix  # noqa: E402
import incident as INC  # noqa: E402
import ledger as L  # noqa: E402

FAKE = HERE / "fake_claude.py"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
FAKE_GH = """#!/usr/bin/env bash
echo "$@" >> "$(dirname "$0")/gh.calls"
echo "https://github.example/acme/calc/pull/7"
"""


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


class FixTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.repo = root / "calc"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "calc.py").write_text("def total(xs):\n    return sum(round(x) for x in xs)\n")
        (self.repo / "tests" / "test_existing.py").write_text("assert True\n")
        (self.repo / "README.md").write_text("# calc\n")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.bin = root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.log = root / "calls.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_fix(self, variant="ok", *extra, profile="hotfix", report="totals are off by one on fractional lines"):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_CLAUDE_LOG": str(self.log), "FAKE_FIX": variant,
               "PATH": f"{self.bin}:{os.environ['PATH']}", **GIT_ENV}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = fix.main(["--repo", str(self.repo), "--report", report, "--slug", "totals",
                                 "--profile", profile, *extra])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = out.getvalue() + err.getvalue()
        return code

    def state(self, profile="hotfix"):
        return json.loads((self.repo / ".workflow" / f"{profile}-totals" / "state.json").read_text())

    def stages(self):
        return [json.loads(l)["stage"] for l in self.log.read_text().splitlines()] if self.log.exists() else []

    # ---------------------------------------------------------------- the lane

    def test_hotfix_reaches_a_commit_with_a_proven_red_green(self):
        self.assertEqual(self.run_fix(), fix.EXIT_OK, self.output)
        st = self.state()
        self.assertEqual(st["redgreen"]["verdict"], "red-green")
        self.assertEqual(st["ship"]["branch"], "hotfix/totals")
        self.assertEqual(sorted(st["ship"]["files"]), ["calc.py", "tests/test_total.py"])
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "fix: round the total once, not per line")
        record = (self.repo / ".workflow" / "hotfix-totals" / "record.md").read_text()
        self.assertIn("**Red → green:** `test_rounds_once` — fails on the pre-fix code", record)
        self.assertIn("defers the rest as follow-ups", record)
        self.assertIn("Follow-up item:** F1 [major]", record)      # standard mode: a major is a follow-up

    def test_stage_order_and_one_review_pass(self):
        self.run_fix()
        order = []
        for s in self.stages():
            if not order or order[-1] != s:
                order.append(s)
        self.assertEqual(order, ["discover", "triage", "rootcause", "red", "implement",
                                 "teardown-delegate", "consolidate", "verify", "verdict"])

    def test_no_pr_without_the_flag(self):
        self.run_fix()
        self.assertFalse((self.bin / "gh.calls").exists())
        self.assertIn("git push -u origin hotfix/totals", self.output)

    def test_open_pr_pushes_and_opens_a_draft(self):
        remote = pathlib.Path(self.tmp.name) / "github-remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        git(self.repo, "remote", "add", "origin", f"file://{remote}")
        self.assertEqual(self.run_fix("ok", "--open-pr"), fix.EXIT_OK, self.output)
        calls = (self.bin / "gh.calls").read_text()
        self.assertIn("pr create --draft", calls)
        self.assertIn("--base main --head hotfix/totals", calls)
        self.assertIn("hotfix/totals", git(remote, "branch"))
        self.assertEqual(self.state()["ship"]["pr"], "https://github.example/acme/calc/pull/7")

    def test_strict_mode_fixes_a_confirmed_major_once(self):
        self.assertEqual(self.run_fix("strict"), fix.EXIT_OK, self.output)
        st = self.state()
        self.assertEqual(st["review"]["fixed"], ["F1"])
        self.assertIn("tests/test_missing.py", st["ship"]["files"])
        self.assertIn("red→green checked", (self.repo / ".workflow/hotfix-totals/ledger.md").read_text())

    def test_resume_skips_finished_stages(self):
        self.run_fix("no-fix")
        before = len(self.stages())
        self.assertEqual(self.run_fix(), fix.EXIT_OK, self.output)
        later = self.stages()[before:]
        self.assertNotIn("rootcause", later)
        self.assertEqual(later[0], "implement")

    # ---------------------------------------------------------------- the gates

    def test_an_outage_is_routed_out_untouched(self):
        self.assertEqual(self.run_fix("outage"), fix.EXIT_ROUTED)
        self.assertIn("incident-fix", self.output)
        self.assertEqual(git(self.repo, "status", "--porcelain", "--", "calc.py", "tests"), "")

    def test_missing_test_command_asks_once(self):
        self.assertEqual(self.run_fix("no-test-cmd"), fix.EXIT_INPUT)
        self.assertIn("What command runs the tests?",
                      (self.repo / ".workflow/hotfix-totals/questions.md").read_text())

    def test_root_cause_may_not_edit(self):
        self.assertEqual(self.run_fix("rc-edits"), fix.EXIT_ERROR)
        self.assertIn("root-cause stage changed files", self.output)

    def test_red_may_only_touch_tests(self):
        self.assertEqual(self.run_fix("red-edits"), fix.EXIT_ERROR)
        self.assertIn("only change tests", self.output)

    def test_a_fix_that_doesnt_fix_stops_at_the_gate(self):
        self.assertEqual(self.run_fix("no-fix"), fix.EXIT_GATE)
        self.assertNotIn("ship", self.state()["done"])

    def test_pr_tool_comes_from_the_remote(self):
        self.assertEqual(fix.pr_tool("git@github.com:a/b.git"), "gh")
        self.assertEqual(fix.pr_tool("https://gitlab.example.com/a/b.git"), "glab")
        self.assertEqual(fix.pr_tool("https://dev.azure.com/org/proj/_git/repo"), "az")
        self.assertIsNone(fix.pr_tool("ssh://git.internal/b.git"))

    # ---------------------------------------------------------------- the incident profile

    def test_incident_profile_runs_the_capped_loop_and_ships_a_repair_artifact(self):
        log = "docs/incidents/2026-10-15-totals.md"
        with contextlib.redirect_stdout(io.StringIO()):
            INC.main(["new", str(self.repo / log), "--title", "totals", "--severity", "SEV2", "--why", "wrong money",
                      "--detected-by", "alert — totals"])
        self.assertEqual(self.run_fix("data", "--incident-log", log, profile="incident"), fix.EXIT_OK, self.output)
        st = self.state("incident")
        self.assertNotIn("triage", self.stages())
        self.assertIn("refactor", self.stages())
        self.assertEqual(st["repair"]["artifact"], "repair/fix_totals.py")
        self.assertEqual(st["ship"]["branch"], "incident/totals")
        ledger = (self.repo / ".workflow/incident-totals/ledger.md").read_text()
        self.assertEqual(L.status(ledger, 2)["computed"]["outcome"], "GO")
        text = (self.repo / log).read_text()
        self.assertIn("red→green proven", text)
        self.assertIn("fix committed on incident/totals", text)


if __name__ == "__main__":
    unittest.main()
