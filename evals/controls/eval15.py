#!/usr/bin/env python3
"""Controls for eval 15 (harness/loop.py end to end). No model is called; nothing costs.

Usage: python3 evals/controls/eval15.py <workspace>

Builds <workspace>/iteration-1/eval-15-harness-loop-closes-teardown/ with three runs,
each set up exactly as run.py sets up a real one, then grades them:

  with_skill/rep1  reference: what a working loop leaves behind. Both planted defects
                   CONFIRMED, check_cutoff reading account config, both slices closed, GO.
  with_skill/rep2  plausible but wrong: the real loop.py, driven by the stub model in
                   harness/tests/fake_claude.py. It reaches GO with a closed slice, but never
                   names the vacuous test and its "fix" never touches check_cutoff.
  old_skill        do nothing: the harness stopped before writing anything.

The reference must pass every assertion. The other two must fail the delta assertions
that a working loop exists to pass; the script exits non-zero if either expectation breaks.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

EVALS = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS))
import run as R  # noqa: E402

NAME = "eval-15-harness-loop-closes-teardown"

FIX = '''def check_cutoff(booking, config):
    window = timedelta(minutes=config.get("cutoff_minutes", DEFAULT_CUTOFF_MINUTES))
    if booking.slot - datetime.now() < window:
        return "CUTOFF_WINDOW"
    return None
'''

TESTS = '''

def test_cutoff_uses_the_account_window():
    service = BookingService(FakeStore(), FakeConfig({"cutoff_minutes": 240, "opens_at": 0, "closes_at": 24}))
    with pytest.raises(Rejected) as e:
        service.submit("acct-1", "venue-1", datetime.now() + timedelta(minutes=180), 2)
    assert "CUTOFF_WINDOW" in e.value.codes


def test_config_window_test_distinguishes_windows():
    service = BookingService(FakeStore(), FakeConfig({"cutoff_minutes": 60, "opens_at": 0, "closes_at": 24}))
    service.submit("acct-1", "venue-1", datetime.now() + timedelta(minutes=90), 2)
'''

LEDGER = '''
## Iteration 1

### Smells
- **N1** Dispensables / Duplicate Code at the rule helpers — noted: two call sites
  - **Promote if:** a third rule repeats the read-default-coerce pattern

### Findings (unadjudicated)
#### F1
- **Target:** acceptance criterion 3 — the window length reads from account config
- **Claim challenged:** the cutoff window length is read from account config
- **Evidence:** check_cutoff ignores its config argument and always uses DEFAULT_CUTOFF_MINUTES
- **Breaking case:** cutoff_minutes 240, slot 180 minutes out → accepted; expected rejected
- **Confidence:** proven
- **Severity hint:** major

#### F2
- **Target:** tests/test_booking.py
- **Claim challenged:** test_cutoff_window_reads_from_account_config proves the window is configurable
- **Evidence:** its slot sits inside both the configured and the default window, so it passes even with config ignored — vacuous; the mutation survives
- **Breaking case:** delete the config read in check_cutoff → the test still passes
- **Confidence:** proven
- **Severity hint:** major

### Surfaces
- **Swept:** acceptance criteria — F1
- **Swept:** test integrity — F2

### Verdicts
#### F1 — CONFIRMED major
- **Reason:** reproduced through BookingService.submit with a 240-minute account window

#### F2 — CONFIRMED major
- **Reason:** mutation of check_cutoff survives the test

### Remediation slices
- [ ] [major] F1 — a booking 180 minutes out is rejected when the account's cutoff is 240
- [ ] [major] F2 — a test fails when check_cutoff ignores the account window

### Verdict: NO-GO
- **Reason:** 2 confirmed majors open (F1, F2)

## Iteration 2

### Closed slices
- [x] F1 — verified by `test_cutoff_uses_the_account_window`
- [x] F2 — verified by `test_config_window_test_distinguishes_windows`

### Smells
- **N1** — left: condition not met

### Findings (unadjudicated)
- none

### Surfaces
- **Swept:** acceptance criteria — the configured window now holds

### Verdicts
- none

### Remediation slices
- none

### Verdict: GO
- **Reason:** nothing open
'''


def setup(run):
    r = {"run": run, "fixture": R.fixture_dir("teardown"), "runner": "loop",
         "base_fixture": R.fixture_dir("base")}
    R.prepare(r)
    return r


def record(run, code, log):
    (run / "outputs/response.md").write_text(log)
    (run / "run.json").write_text(json.dumps({"exit_code": code, "control": True}))


def main():
    ws = pathlib.Path(sys.argv[1]).resolve() / "iteration-1"
    shutil.rmtree(ws, ignore_errors=True)
    ed = ws / NAME

    ref = ed / "with_skill/rep1"
    setup(ref)
    rules = ref / "repo/reservations/rules.py"
    src = rules.read_text()
    start, end = src.index("def check_cutoff"), src.index("ACTIVE_RULES")
    rules.write_text(src[:start] + FIX + "\n\n" + src[end:])
    with open(ref / "repo/tests/test_booking.py", "a") as fh:
        fh.write(TESTS)
    with open(ref / "repo/.workflow/ledger.md", "a") as fh:
        fh.write(LEDGER)
    record(ref, 0, "[control] reference: GO — nothing open\n")

    wrong = setup(ed / "with_skill/rep2")
    wrong["cmd"] = [sys.executable, str(R.REPO_ROOT / "harness/loop.py"), "--repo", str(wrong["run"] / "repo"),
                    "--test-cmd", ".venv/bin/python -m pytest -q", "--base", "HEAD",
                    "--skills", str(R.REPO_ROOT / "skills")]
    wrong.update(eval=NAME, kind="with_skill", skill_md=None, prompt=None)
    os.environ.update(HARNESS_CLAUDE=str(R.REPO_ROOT / "harness/tests/fake_claude.py"), FAKE_SCENARIO="converge")
    R.execute(wrong, 300)

    nothing = ed / "old_skill"
    setup(nothing)
    record(nothing, 1, "[control] do nothing: the harness stopped before writing anything\n")

    subprocess.run([sys.executable, str(EVALS / "grade.py"), str(ws)], check=True)
    grades = {k: json.loads((ed / k / "grading.json").read_text())
              for k in ("with_skill/rep1", "with_skill/rep2", "old_skill")}
    problems = []
    if grades["with_skill/rep1"]["passed"] != grades["with_skill/rep1"]["total"]:
        problems.append("the reference does not pass every assertion")
    for k in ("with_skill/rep2", "old_skill"):
        g = grades[k]
        if g["delta_passed"] > g["delta_total"] - 2:
            problems.append(f"{k} passes {g['delta_passed']}/{g['delta_total']} delta assertions")
    for k, g in grades.items():
        print(f"\n{k}")
        for e in g["expectations"]:
            print(f"  {'PASS' if e['passed'] else 'fail'}  {e['kind'][:3]}  {e['text']}")
    if problems:
        sys.exit("controls broke: " + "; ".join(problems))
    print("\ncontrols hold: the reference passes everything, the other two fail where a working loop must not")


if __name__ == "__main__":
    main()
