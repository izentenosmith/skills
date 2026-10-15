"""postmortem.py end to end, with fake_claude.py as the model. Run: python3 -m unittest discover harness/tests"""
import contextlib
import datetime as dt
import io
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import incident as INC  # noqa: E402
import postmortem as PM  # noqa: E402

FAKE = HERE / "fake_claude.py"
LOG = "docs/incidents/2026-10-15-totals.md"


def git(repo, *args, env=None):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True,
                          env={**os.environ, **(env or {})}).stdout.strip()


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)


class PostmortemTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.repo = self.root / "svc"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        ten_days = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)).isoformat()
        (self.repo / "totals.py").write_text("x = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "round totals per line", env={
            "GIT_AUTHOR_NAME": "Dana Example", "GIT_AUTHOR_EMAIL": "d@e", "GIT_COMMITTER_NAME": "Dana Example",
            "GIT_COMMITTER_EMAIL": "d@e", "GIT_AUTHOR_DATE": ten_days, "GIT_COMMITTER_DATE": ten_days})
        self.log = self.repo / LOG
        quiet(INC.main, ["new", str(self.log), "--title", "totals", "--severity", "SEV2", "--why", "wrong money",
                         "--detected-by", "user report via support"])

    def tearDown(self):
        self.tmp.cleanup()

    def resolve(self):
        two_h = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for args in (["impact-start", "first short invoice", "--at", two_h], ["mitigated", "job paused"],
                     ["resolved", "fix verified"]):
            quiet(INC.main, ["log", str(self.log), *args])

    def run_pm(self, variant="ok", *extra):
        env = {"HARNESS_CLAUDE": str(FAKE), "FAKE_PM": variant}
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = PM.main(["--repo", str(self.repo), "--log", LOG, *extra])
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.output = out.getvalue()
        return code

    def record(self):
        return (self.repo / LOG.replace(".md", "-postmortem.md")).read_text()

    def work(self):
        return self.repo / ".workflow" / "postmortem-2026-10-15-totals"

    def test_refuses_an_unresolved_incident(self):
        self.assertEqual(self.run_pm(), PM.EXIT_ERROR)
        self.assertIn("isn't resolved", self.output)

    def test_writes_the_record_then_waits_for_owners(self):
        self.resolve()
        self.assertEqual(self.run_pm(), PM.EXIT_INPUT, self.output)
        self.assertIn("## Contributing factors", self.record())
        draft = (self.work() / "follow-through.md").read_text()
        self.assertIn("--owner <who agreed> --due <YYYY-MM-DD>", draft)
        self.assertIn("an alert fires", draft)

    def test_the_git_range_reaches_past_the_incident_window(self):
        self.resolve()
        self.run_pm()
        self.assertIn("round totals per line", (self.work() / "git-range.txt").read_text())

    def test_closes_once_every_factor_is_owned(self):
        self.resolve()
        self.run_pm()
        quiet(INC.main, ["factor", str(self.log), "the totals helper rounds per line", "--follow-up",
                         "totals computed once", "--owner", "billing", "--due", "2026-11-01"])
        quiet(INC.main, ["factor", str(self.log), "no alert compares invoice sums with totals", "--follow-up",
                         "an alert on divergence", "--owner", "sre", "--due", "2026-11-01"])
        self.assertEqual(self.run_pm("ok"), PM.EXIT_OK, self.output)
        self.assertNotIn("· closed ·", self.log.read_text())
        self.assertEqual(self.run_pm("ok", "--close"), PM.EXIT_OK, self.output)
        self.assertIn("· closed ·", self.log.read_text())

    def test_blame_gets_one_correction(self):
        self.resolve()
        self.assertEqual(self.run_pm("blame-once"), PM.EXIT_INPUT, self.output)
        self.assertNotIn("failed to", self.record())

    def test_stubborn_blame_stops_at_the_lint(self):
        self.resolve()
        self.assertEqual(self.run_pm("blame"), PM.EXIT_LINT, self.output)
        self.assertIn("should have", self.output)
        self.assertFalse((self.repo / LOG.replace(".md", "-postmortem.md")).exists())

    def test_an_authors_name_next_to_a_failure_is_blame(self):
        self.resolve()
        self.assertEqual(self.run_pm("names"), PM.EXIT_LINT, self.output)
        self.assertIn("a person's name next to a failure", self.output)

    def test_lint_skips_quoted_sources(self):
        md = "## Timeline\n## Impact\n## Contributing factors\n> The report: \"Dana should have caught it.\"\n"
        self.assertEqual(PM.lint(md, {"Dana Example"}), [])

    def test_create_items_opens_one_per_follow_up(self):
        self.resolve()
        bindir = self.root / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text('#!/usr/bin/env bash\necho "$@" >> "$(dirname "$0")/gh.calls"\necho https://x/issues/1\n')
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        git(self.repo, "remote", "add", "origin", "git@github.com:acme/svc.git")
        self.run_pm()
        for f in ("the totals helper rounds per line", "no alert compares invoice sums with totals"):
            quiet(INC.main, ["factor", str(self.log), f, "--follow-up", f"fix: {f}", "--owner", "x", "--due", "d"])
        old = os.environ["PATH"]
        os.environ["PATH"] = f"{bindir}:{old}"
        try:
            self.assertEqual(self.run_pm("ok", "--close", "--create-items"), PM.EXIT_OK, self.output)
        finally:
            os.environ["PATH"] = old
        self.assertEqual((bindir / "gh.calls").read_text().count("issue create"), 2)


if __name__ == "__main__":
    unittest.main()
