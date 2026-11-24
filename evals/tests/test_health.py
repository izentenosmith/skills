"""What the two eval articles asked of the harness: a kept transcript, a baseline
that can be repeated, and a health table that says when a score is not evidence.
Run: python3 -m unittest discover evals/tests"""
import argparse
import json
import pathlib
import sys
import tempfile
import unittest

EVALS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS))

import aggregate  # noqa: E402
import run  # noqa: E402
import transcript  # noqa: E402

STREAM = "\n".join(json.dumps(e) for e in [
    {"type": "system", "subtype": "init"},
    {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Running it."},
        {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "content": [{"type": "text", "text": "1 failed"}], "is_error": True}]}},
    {"type": "result", "is_error": False, "total_cost_usd": 0.5, "num_turns": 2, "result": "done"},
    {"type": "system", "subtype": "task_summary"},
]) + "\nnot json\n"


def grading(delta_passed, delta_total=4):
    exp = [{"text": f"d{i}", "passed": i < delta_passed, "evidence": "", "kind": "delta"}
           for i in range(delta_total)]
    return {"expectations": exp, "delta_passed": delta_passed, "delta_total": delta_total,
            "delta_rate": delta_passed / delta_total, "pass_rate": delta_passed / delta_total,
            "capability_rate": None, "passed": delta_passed, "total": delta_total}


class Tmp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)

    def write_run(self, rel, g, **rec):
        d = self.tmp / "iteration-1/eval-0-x" / rel
        (d / "repo").mkdir(parents=True)
        if g is not None:
            (d / "grading.json").write_text(json.dumps(g))
        (d / "run.json").write_text(json.dumps({"ok": True, "response": "written by the agent",
                                                "cost_usd": 1.0, **rec}))
        return d

    def row(self):
        found = aggregate.collect([self.tmp / "iteration-1"])
        _, reps, base, _, runs, _ = found["eval-0-x"]
        dm = aggregate.mean(r["delta_rate"] for r in reps)
        db = aggregate.mean(b["delta_rate"] for b in base)
        sd = aggregate.st.stdev([r["delta_rate"] for r in reps]) if len(reps) > 1 else 0.0
        row = {"delta_mean": dm, "delta_base": db, "delta_sd": sd,
               "delta_gain": None if dm is None or db is None else dm - db}
        return aggregate.health(row, reps, base, runs)


class Transcript(Tmp):
    def test_the_result_event_is_found_though_it_is_not_the_last_line(self):
        self.assertEqual(run.result_event(STREAM)["total_cost_usd"], 0.5)
        self.assertEqual(run.result_event("killed before any result"), {})

    def test_steps_and_tool_calls_are_read_from_the_kept_transcript(self):
        (self.tmp / "transcript.jsonl").write_text(STREAM)
        self.assertEqual([k for k, _ in transcript.steps(self.tmp)], ["says", "calls Bash", "error"])
        self.assertEqual(transcript.tool_calls(self.tmp), [("Bash", {"command": "pytest -q"})])
        self.assertEqual(transcript.tool_calls(self.tmp / "absent"), [])


class Baseline(Tmp):
    def test_one_baseline_stays_at_old_skill_and_more_get_a_folder_each(self):
        ed = self.tmp / "eval-0-x"
        self.assertEqual(run.baseline_dirs(ed, 1), [ed / "old_skill"])
        self.assertEqual([d.name for d in run.baseline_dirs(ed, 3)], ["rep1", "rep2", "rep3"])

    def test_a_single_baseline_run_is_not_mistaken_for_its_repo_folder(self):
        self.write_run("with_skill/rep1", grading(4))
        self.write_run("old_skill", grading(1))
        _, _, base, _, runs, _ = aggregate.collect([self.tmp / "iteration-1"])["eval-0-x"]
        self.assertEqual([b["delta_passed"] for b in base], [1])
        self.assertEqual(len(runs["base"]), 1)

    def test_repeated_baselines_are_all_collected(self):
        self.write_run("with_skill/rep1", grading(4))
        for i, passed in enumerate((1, 3), 1):
            self.write_run(f"old_skill/rep{i}", grading(passed))
        _, _, base, _, _, _ = aggregate.collect([self.tmp / "iteration-1"])["eval-0-x"]
        self.assertEqual([b["delta_passed"] for b in base], [1, 3])


class Health(Tmp):
    def test_a_perfect_score_is_saturated_and_one_baseline_leaves_noise_unknown(self):
        for i in (1, 2, 3):
            self.write_run(f"with_skill/rep{i}", grading(4))
        self.write_run("old_skill", grading(1))
        h = self.row()
        self.assertEqual((h["all_delta_passed"], h["graded"], h["base_n"]), (3, 3, 1))
        self.assertIn("saturated", h["flags"])
        self.assertIn("noise unknown", h["flags"])
        self.assertIsNone(h["noise"])

    def test_a_gain_smaller_than_the_spread_of_the_runs_is_within_noise(self):
        for i, passed in enumerate((1, 3, 2), 1):
            self.write_run(f"with_skill/rep{i}", grading(passed))
        for i, passed in enumerate((0, 3, 2), 1):
            self.write_run(f"old_skill/rep{i}", grading(passed))
        h = self.row()
        self.assertGreater(h["noise"], 0)
        self.assertIn("gain within noise", h["flags"])
        self.assertIn("inconsistent", h["flags"])
        self.assertNotIn("saturated", h["flags"])

    def test_a_clear_gain_over_repeated_baselines_carries_no_noise_flag(self):
        for i in (1, 2, 3):
            self.write_run(f"with_skill/rep{i}", grading(3))
        for i, passed in enumerate((0, 1, 0), 1):
            self.write_run(f"old_skill/rep{i}", grading(passed))
        self.assertEqual(self.row()["flags"], ["inconsistent"])

    def test_a_run_that_timed_out_is_counted_as_lost_not_dropped_silently(self):
        self.write_run("with_skill/rep1", grading(4))
        self.write_run("with_skill/rep2", None, ok=False, timed_out=True, response="missing")
        self.write_run("old_skill", grading(4))
        h = self.row()
        self.assertEqual((h["graded"], h["dispatched"], h["lost_runs"]), (1, 2, 1))
        self.assertIn("1 run(s) lost", h["flags"])
        self.assertIn("baseline high", h["flags"])
        self.assertIn("no gain", h["flags"])


class Overall(unittest.TestCase):
    ROWS = [{"eval": "eval-8-a", "delta_mean": 1.0, "delta_base": 0.4, "delta_gain": 0.6,
             "cap_mean": 1.0, "cap_base": 1.0, "outcome_gain": 0.0},
            {"eval": "eval-59-b", "delta_mean": 0.5, "delta_base": 0.0, "delta_gain": 0.5,
             "cap_mean": 1.0, "cap_base": None, "outcome_gain": None}]

    def test_a_held_out_eval_stays_out_of_the_suite_averages(self):
        lines = aggregate.overall(self.ROWS, {"eval-59-b"})
        self.assertIn("**Instruction-following gain +0.60 — delta current 1.00 vs baseline 0.40**", lines)
        self.assertTrue(any(l.startswith("**Held-out (eval 59)") and "delta current 0.50 vs baseline 0.00" in l
                            for l in lines))

    def test_the_outcome_line_comes_first_and_the_baseline_count_last(self):
        self.assertEqual(aggregate.overall(self.ROWS, set()),
                         ["", "**Outcome gain +0.00 — capability current 1.00 vs baseline 1.00**",
                          "**Instruction-following gain +0.55 — delta current 0.75 vs baseline 0.20**",
                          "**1 of 1 evals: baseline already succeeds** (capability baseline 1.00). On "
                          "outcome they can only catch a regression; what the skill adds there shows on "
                          "delta alone.", ""])


if __name__ == "__main__":
    unittest.main()
