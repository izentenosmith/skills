"""incident.py — the log's clock, its confirmation rule and its closing gate.
Run: python3 -m unittest discover harness/tests"""
import contextlib
import io
import pathlib
import re
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import incident as I  # noqa: E402

SPEC = (HERE.parent.parent / "skills/operations/incident-fix/incident-log.md").read_text()


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = I.main(list(argv))
    return code, out.getvalue() + err.getvalue()


class IncidentLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(pathlib.Path(self.tmp.name) / "docs" / "incidents" / "2026-10-15-checkout.md")
        code, _ = run("new", self.path, "--title", "checkout 5xx", "--severity", "SEV2",
                      "--why", "checkout down for 30%", "--detected-by", "alert — orders 5xx > 5%")
        self.assertEqual(code, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return pathlib.Path(self.path).read_text()

    def log(self, kind, *text, at=None):
        return run("log", self.path, kind, *text, *(["--at", at] if at else []))

    def test_the_spec_example_is_a_valid_log(self):
        example = re.search(r"```markdown\n(.*?)```", SPEC, re.S).group(1).replace("- …\n", "")
        errors, _ = I.verify(I.parse(example))
        self.assertEqual([I.fmt(e) for e in errors], [])

    def test_new_stamps_detection_from_the_clock(self):
        entry = I.parse(self.text()).entries[0]
        self.assertEqual(entry.kind, "detected")
        self.assertLess(abs((I.now() - entry.at).total_seconds()), 5)

    def test_a_production_action_needs_its_own_confirmation(self):
        code, out = self.log("action[prod]", "rollback to v41")
        self.assertEqual(code, 1)
        self.assertIn("no confirmation", out)
        self.log("proposed", "rollback to v41")
        self.log("confirmed", "user approved rollback to v41")
        self.assertEqual(self.log("action[prod]", "rolled back to v41")[0], 0)
        code, _ = self.log("action[prod]", "scaled workers to 0")      # the earlier approval is spent
        self.assertEqual(code, 1)

    def test_only_backfilled_kinds_take_a_time(self):
        self.assertEqual(self.log("note", "x", at="2026-10-15T10:00:00Z")[0], 1)
        self.assertEqual(self.log("impact-start", "first 5xx in logs", at="2026-01-01T00:00:00Z")[0], 0)
        self.assertEqual(I.verify(I.parse(self.text()))[0], [])

    def test_hand_edited_violations_are_caught(self):
        t = self.text().replace("## Contributing factors",
                                "- 2026-10-15T00:00:00Z · action[prod] · flipped a flag\n"
                                "- 2026-10-15T00:00:01Z · resolved · fixed\n\n## Contributing factors")
        codes = {e[0] for e in I.verify(I.parse(t))[0]}
        self.assertTrue({"I05", "I07", "I08"} <= codes, codes)

    def test_phases_run_in_order(self):
        self.log("phase", "diagnose")
        self.log("phase", "contain")
        self.assertIn("I06", {e[0] for e in I.verify(I.parse(self.text()))[0]})

    def test_closing_requires_every_factor_owned_or_accepted(self):
        for kind in ("mitigated", "resolved"):
            self.log(kind, "done")
        code, out = self.log("closed", "item closed")
        self.assertEqual(code, 1)
        self.assertIn("no contributing factors", out)
        self.assertEqual(run("factor", self.path, "migration rewrote all rows", "--follow-up", "x")[0], 1)
        run("factor", self.path, "migration rewrote all rows unbounded", "--follow-up",
            "migrations over N rows need a dry-run artifact", "--owner", "platform", "--due", "2026-11-01")
        run("factor", self.path, "vendor API truncates silently", "--accepted", "two hits in three years",
            "--by", "payments lead")
        self.assertEqual(self.log("closed", "item closed")[0], 0)
        self.assertEqual(run("check", self.path)[0], 0)

    def test_human_detection_requires_a_detection_follow_up(self):
        path = str(pathlib.Path(self.tmp.name) / "u.md")
        run("new", path, "--title", "t", "--severity", "SEV3", "--why", "w", "--detected-by", "user report via support")
        for kind in ("mitigated", "resolved"):
            run("log", path, kind, "done")
        run("factor", path, "batch writes unchecked", "--follow-up", "row counts asserted", "--owner", "a", "--due", "d")
        code, out = run("log", path, "closed", "x")
        self.assertEqual(code, 1)
        self.assertIn("I10", out)
        run("factor", path, "no alert on job output", "--follow-up", "alert when the job writes zero rows",
            "--owner", "a", "--due", "d")
        self.assertEqual(run("log", path, "closed", "x")[0], 0)

    def test_timeline_measures_the_intervals(self):
        self.log("impact-start", "first error", at="2026-10-15T00:00:00Z")
        self.log("mitigated", "flag off")
        code, out = run("timeline", self.path)
        self.assertEqual(code, 0)
        self.assertIn("Time to detect", out)
        self.assertNotIn("Time to mitigate** (detected → mitigated): unknown", out)

    def test_never_started_twice(self):
        code, _ = run("new", self.path, "--title", "t", "--severity", "SEV1", "--why", "w", "--detected-by", "d")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
