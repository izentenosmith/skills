"""Score provenance: the skill_hash run.py records for a staged skill, what
aggregate.py carries into scores.json, and that check_repo.py can recompute it.
Run: python3 -m unittest discover evals/tests"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
EVALS = HERE.parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS))

import aggregate  # noqa: E402
import run  # noqa: E402

# incident-fix carries a synced copy of hotfix's diagnosis.md.
SKILL = REPO / "skills/operations/incident-fix"


class StagedHash(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)

    def test_staged_folder_hashes_as_the_check_recomputes_it(self):
        for staging in ("harness", "standalone"):
            with self.subTest(staging=staging):
                skill_md, digest = run.stage_skill(SKILL / "SKILL.md", self.tmp / "current", staging)
                self.assertTrue(skill_md.is_file())
                self.assertEqual(digest, run.skill_hash(SKILL, staging))

    def test_standalone_stands_alone(self):
        skill_md, _ = run.stage_skill(SKILL / "SKILL.md", self.tmp / "current", "standalone")
        self.assertIsNone(run.staged_harness(skill_md))
        root = self.tmp / "current-standalone" / SKILL.name
        self.assertEqual([p.name for p in (root / "skills").rglob("SKILL.md")], ["SKILL.md"])

    def test_a_staging_run_py_no_longer_does_has_no_hash(self):
        with self.assertRaises(ValueError):
            run.skill_hash(SKILL, "package")

    def test_os_litter_does_not_change_the_hash(self):
        folder = self.tmp / "skill"
        (folder / "scripts/__pycache__").mkdir(parents=True)
        (folder / "SKILL.md").write_text("body\n")
        before = run.tree_hash(run.folder_files(folder))
        (folder / ".DS_Store").write_bytes(b"\0")
        (folder / "scripts/__pycache__/x.cpython-314.pyc").write_bytes(b"\0")
        self.assertEqual(run.tree_hash(run.folder_files(folder)), before)
        (folder / "SKILL.md").write_text("body, edited\n")
        self.assertNotEqual(run.tree_hash(run.folder_files(folder)), before)


class Aggregate(unittest.TestCase):
    def test_provenance_from_runs_or_unknown(self):
        skills = {"eval-7-x": "post-mortem"}
        recorded = {"skill": "post-mortem", "staging": "standalone", "skill_hash": "abc"}
        self.assertEqual(aggregate.provenance("eval-7-x", [recorded, dict(recorded)], skills), recorded)
        self.assertEqual(aggregate.provenance("eval-7-x", [{}, {}], skills),
                         {"skill": "post-mortem", "staging": None, "skill_hash": None})
        mixed = [recorded, dict(recorded, skill_hash="def")]
        self.assertIsNone(aggregate.provenance("eval-7-x", mixed, skills)["skill_hash"])

    def test_later_iteration_wins_in_scores_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp)
            for it, digest in (("iteration-1", None), ("iteration-2", "abc")):
                rep = ws / it / "eval-7-postmortem-widens-range-and-describes/with_skill/rep1"
                rep.mkdir(parents=True)
                (rep / "grading.json").write_text(json.dumps(
                    {"pass_rate": 1.0, "delta_rate": 1.0, "capability_rate": 1.0, "expectations": []}))
                if digest:
                    (rep / "run.json").write_text(json.dumps(
                        {"skill": "post-mortem", "staging": "standalone", "skill_hash": digest}))
            subprocess.run([sys.executable, str(EVALS / "aggregate.py"),
                            str(ws / "iteration-1"), str(ws / "iteration-2")],
                           check=True, capture_output=True)
            score = json.loads((ws / "scores.json").read_text())["evals"]
            day = aggregate.run_date([ws / "iteration-2/eval-7-postmortem-widens-range-and-describes"
                                      "/with_skill/rep1"])[0]
            self.assertEqual(score["eval-7-postmortem-widens-range-and-describes"],
                             {"skill": "post-mortem", "iteration": "iteration-2", "n": 1,
                              "staging": "standalone", "skill_hash": "abc",
                              "date": day, "date_from": "run.json mtime",
                              "delta_mean": 1.0, "cap_mean": 1.0,
                              "cap_base": None, "outcome_gain": None})


class RunDate(unittest.TestCase):
    """The day a score's runs ended: run.py's `finished` stamp, else run.json's mtime."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)

    def rep(self, name, record):
        p = self.tmp / name
        p.mkdir()
        if record is not None:
            (p / "run.json").write_text(json.dumps(record))
        return p

    def test_latest_finished_stamp_wins(self):
        reps = [self.rep("rep1", {"finished": "2026-11-20T23:59:00Z"}),
                self.rep("rep2", {"finished": "2026-11-21T00:10:00Z"})]
        self.assertEqual(aggregate.run_date(reps), ("2026-11-21", "run.json finished"))

    def test_old_runs_fall_back_to_run_json_mtime_in_utc(self):
        import os
        reps = [self.rep("rep1", {}), self.rep("rep2", {"finished": "2026-11-21T00:10:00Z"})]
        # 2026-11-18T23:30Z, and an earlier one: the later mtime gives the day.
        os.utime(reps[0] / "run.json", (1795044600, 1795044600))
        os.utime(reps[1] / "run.json", (1794916800, 1794916800))
        self.assertEqual(aggregate.run_date(reps), ("2026-11-18", "run.json mtime"))

    def test_no_run_json_means_no_date(self):
        self.assertEqual(aggregate.run_date([self.rep("rep1", None)]), (None, None))

    def test_run_py_stamps_finished_in_utc(self):
        run_dir = self.tmp / "run"
        (run_dir / "repo").mkdir(parents=True)
        (run_dir / "outputs").mkdir()
        rec = run.execute({"run": run_dir, "eval": "eval-15-x", "kind": "with_skill",
                           "skill_md": None, "runner": "loop", "prompt": None,
                           "cmd": [sys.executable, "-c", "pass"]}, timeout=60)
        self.assertRegex(rec["finished"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(json.loads((run_dir / "run.json").read_text())["finished"], rec["finished"])


if __name__ == "__main__":
    unittest.main()
