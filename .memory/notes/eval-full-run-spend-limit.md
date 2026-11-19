---
name: eval-full-run-spend-limit
description: A full eval run is 235 headless runs and about $217, which trips the org spend limit partway; run.py has no resume, so re-run the failed evals by id into the same iteration
type: gotcha
source: evals/run.py::prepare, iteration-49 run logs in the eval workspace, session 2026-11-19
verified: 2026-11-19
volatility: high
---

Iteration 49 ran all 59 evals at three reps with baselines: 235 runs, $217.54, in three batches
because the org's monthly spend limit stopped it twice (after 80 runs, then after 197).

**Symptom:** every later run fails in under ten seconds at $0, `run.py` exits 1, and each
failed run's saved Claude output says "You've hit your org's monthly spend limit". The log shows only
"failed: … see run.json".
**Avoid by:** probing with one `claude -p` call before relaunching, then re-running only the
evals that have a failed run: `run.py --iteration <same n> --evals <ids>`. `prepare` deletes and
redoes each run it is given, so an eval with one failed rep is redone whole and the finished
evals are left alone. Wrap long runs in `caffeinate -i`. See [[eval-workspace]].
