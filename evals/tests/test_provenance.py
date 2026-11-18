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
            self.assertEqual(score["eval-7-postmortem-widens-range-and-describes"],
                             {"skill": "post-mortem", "iteration": "iteration-2", "n": 1,
                              "staging": "standalone", "skill_hash": "abc"})


if __name__ == "__main__":
    unittest.main()
