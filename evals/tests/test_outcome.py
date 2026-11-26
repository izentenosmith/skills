"""The outcome gain is the benchmark's headline: capability with the skill minus
capability without it. Delta, which a baseline that never read the skill mostly
fails by construction, is the secondary instruction-following column, and an
eval whose baseline already passes every capability assertion is flagged.
Run: python3 -m unittest discover evals/tests"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

EVALS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS))

import aggregate  # noqa: E402

# Real eval names, so aggregate.py finds their skills in evals.json; neither is held out.
SUCCEEDS = "eval-8-hotfix-node-shared-cause"
GAINS = "eval-12-incident-webapp-contain-by-flag"


def grading(delta, cap):
    """delta: delta assertions passed of 4; cap: capability assertions passed of 2."""
    exp = ([{"text": f"d{i}", "passed": i < delta, "evidence": "", "kind": "delta"} for i in range(4)]
           + [{"text": f"c{i}", "passed": i < cap, "evidence": "", "kind": "capability"} for i in range(2)])
    return {"expectations": exp, "delta_passed": delta, "delta_total": 4, "delta_rate": delta / 4,
            "capability_rate": cap / 2, "pass_rate": (delta + cap) / 6,
            "passed": delta + cap, "total": 6}


class Workspace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ws = pathlib.Path(tmp.name)

    def write(self, name, rel, g):
        d = self.ws / "iteration-1" / name / rel
        d.mkdir(parents=True)
        (d / "grading.json").write_text(json.dumps(g))
        (d / "run.json").write_text(json.dumps({"ok": True, "response": "written", "cost_usd": 1.0}))

    def eval_(self, name, with_skill, baselines):
        for i, (d, c) in enumerate(with_skill, 1):
            self.write(name, f"with_skill/rep{i}", grading(d, c))
        if len(baselines) == 1:
            self.write(name, "old_skill", grading(*baselines[0]))
        else:
            for i, (d, c) in enumerate(baselines, 1):
                self.write(name, f"old_skill/rep{i}", grading(d, c))

    def health(self, name):
        _, reps, base, _, runs, _ = aggregate.collect([self.ws / "iteration-1"])[name]
        rate = lambda rows, k: aggregate.mean(r[k] for r in rows)
        sd = aggregate.st.stdev([r["delta_rate"] for r in reps]) if len(reps) > 1 else 0.0
        row = {"delta_mean": rate(reps, "delta_rate"), "delta_base": rate(base, "delta_rate"),
               "delta_sd": sd, "cap_mean": rate(reps, "capability_rate"),
               "cap_base": rate(base, "capability_rate")}
        row["delta_gain"] = row["delta_mean"] - row["delta_base"]
        row["outcome_gain"] = row["cap_mean"] - row["cap_base"]
        return aggregate.health(row, reps, base, runs)


class Health(Workspace):
    def test_a_baseline_that_passes_every_capability_assertion_already_succeeds(self):
        self.eval_(SUCCEEDS, [(4, 2)] * 3, [(1, 2)])
        h = self.health(SUCCEEDS)
        self.assertEqual(h["flags"][0], "baseline already succeeds")
        self.assertNotIn("outcome below baseline", h["flags"])
        self.assertNotIn("no outcome gain", h["flags"])

    def test_a_skill_that_does_worse_than_a_succeeding_baseline_is_a_regression(self):
        self.eval_(SUCCEEDS, [(4, 2), (4, 1), (4, 2)], [(1, 2)])
        h = self.health(SUCCEEDS)
        self.assertIn("baseline already succeeds", h["flags"])
        self.assertIn("outcome below baseline", h["flags"])

    def test_no_outcome_gain_over_one_failing_baseline_is_flagged(self):
        self.eval_(GAINS, [(4, 1)] * 3, [(0, 1)])
        h = self.health(GAINS)
        self.assertIsNone(h["outcome_noise"])
        self.assertIn("no outcome gain", h["flags"])
        self.assertNotIn("baseline already succeeds", h["flags"])

    def test_an_outcome_gain_inside_the_run_to_run_spread_is_within_noise(self):
        self.eval_(GAINS, [(4, 2), (4, 0), (4, 2)], [(0, 1), (0, 2), (0, 0)])
        h = self.health(GAINS)
        self.assertGreater(h["outcome_noise"], 0)
        self.assertIn("outcome within noise", h["flags"])

    def test_a_clear_outcome_gain_over_repeated_baselines_carries_no_outcome_flag(self):
        self.eval_(GAINS, [(4, 2)] * 3, [(0, 0), (0, 1), (0, 0)])
        h = self.health(GAINS)
        self.assertGreater(h["outcome_noise"], 0)
        self.assertFalse([f for f in h["flags"] if "outcome" in f or "baseline already" in f])


class Recorded(Workspace):
    """aggregate.py end to end on synthetic grading: the table, the overall
    lines, benchmark.json and scores.json all lead with the outcome gain."""

    def setUp(self):
        super().setUp()
        self.eval_(SUCCEEDS, [(4, 2)] * 3, [(1, 2)])
        self.eval_(GAINS, [(4, 2)] * 3, [(2, 1)])
        subprocess.run([sys.executable, str(EVALS / "aggregate.py"), str(self.ws / "iteration-1")],
                       check=True, capture_output=True)
        self.md = (self.ws / "benchmark.md").read_text().split("\n")

    def rows(self, header):
        i = next(k for k, l in enumerate(self.md) if l.startswith(header))
        head = [c.strip() for c in self.md[i].strip("|").split("|")]
        out = {}
        for l in self.md[i + 2:]:
            if not l.startswith("|"):
                break
            cells = [c.strip() for c in l.strip("|").split("|")]
            out[cells[0]] = dict(zip(head, cells))
        return out

    def test_the_score_table_leads_with_the_outcome_gain_and_flags_a_succeeding_baseline(self):
        rows = self.rows("| eval | from |")
        first = next(l for l in self.md if l.startswith("| eval | from |"))
        self.assertTrue(first.startswith("| eval | from | outcome gain | cap | cap base |"))
        ok, gain = rows[SUCCEEDS.replace("eval-", "")], rows[GAINS.replace("eval-", "")]
        self.assertEqual((ok["outcome gain"], ok["delta gain"], ok["outcome note"]),
                         ("+0.00", "+0.75", "baseline already succeeds"))
        self.assertEqual((gain["outcome gain"], gain["cap base"], gain["delta gain"], gain["outcome note"]),
                         ("+0.50", "0.50", "+0.50", "—"))

    def test_the_overall_lines_put_outcome_first_and_count_the_succeeding_baselines(self):
        bold = [l for l in self.md if l.startswith("**") and not l.startswith("**Outcome first.**")]
        self.assertEqual(bold[0], "**Outcome gain +0.25 — capability current 1.00 vs baseline 0.75**")
        self.assertTrue(bold[1].startswith("**Instruction-following gain +0.62 — delta"))
        self.assertTrue(bold[2].startswith("**1 of 2 evals: baseline already succeeds**"))

    def test_the_health_table_carries_the_flag_and_both_gains(self):
        rows = self.rows("| eval | runs |")
        ok = rows[SUCCEEDS.replace("eval-", "")]
        self.assertEqual((ok["outcome gain"], ok["delta gain"]), ("+0.00", "+0.75"))
        self.assertTrue(ok["flags"].startswith("baseline already succeeds"))

    def test_benchmark_json_and_scores_json_carry_the_outcome_gain(self):
        bench = json.loads((self.ws / "benchmark.json").read_text())
        self.assertEqual(bench["headline"], "outcome_gain")
        by = {r["eval"]: r for r in bench["evals"]}
        self.assertEqual((by[GAINS]["outcome_gain"], by[GAINS]["baseline_succeeds"]), (0.5, False))
        self.assertTrue(by[SUCCEEDS]["baseline_succeeds"])
        scores = json.loads((self.ws / "scores.json").read_text())["evals"]
        self.assertEqual((scores[GAINS]["cap_base"], scores[GAINS]["outcome_gain"]), (0.5, 0.5))
        # The fields check_repo.py reads are still there.
        for key in ("skill", "iteration", "staging", "skill_hash", "delta_mean", "cap_mean"):
            self.assertIn(key, scores[SUCCEEDS])


if __name__ == "__main__":
    unittest.main()
