#!/usr/bin/env python3
"""A stand-in for `claude -p` so the orchestrator can be tested without a model.

It reads the prompt from stdin, finds the HARNESS-STAGE / HARNESS-ITERATION markers
loop.py puts at the top of every prompt, and answers the way a well-behaved stage
would. FAKE_SCENARIO bends that:

  converge  (default) iteration 1 confirms one major, iteration 2 fixes it and finds nothing → GO
  stall     tdd never closes its slice → the second pass closes nothing → ESCALATED
  vandal    refactor-review writes to the ledger, which the harness must undo
  doubt     the only finding stays INCONCLUSIVE twice → ESCALATED
  vacuous   tdd's remediation test passes without the fix → no slice closes → ESCALATED

Every call is appended to FAKE_CLAUDE_LOG as one JSON line: stage, iteration, argv, cwd.
"""
import json
import os
import pathlib
import re
import sys

argv = sys.argv[1:]
prompt = sys.stdin.read()
stage = re.search(r"HARNESS-STAGE: (\S+)", prompt).group(1)
n = int(re.search(r"HARNESS-ITERATION: (\d+)", prompt).group(1))
scenario = os.environ.get("FAKE_SCENARIO", "converge")
cwd = pathlib.Path.cwd()

if os.environ.get("FAKE_CLAUDE_LOG"):
    with open(os.environ["FAKE_CLAUDE_LOG"], "a") as fh:
        fh.write(json.dumps({"stage": stage, "n": n, "argv": argv, "cwd": str(cwd),
                             "no_background": os.environ.get("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS")}) + "\n")

FINDING = {
    "target": "acceptance criterion 3 — the window length reads from account config",
    "claim": "the cutoff window length is read from account config",
    "evidence": "check_cutoff never reads its config argument",
    "breaking_case": "cutoff_minutes 240, slot 180 minutes out → accepted; expected rejected",
    "confidence": "proven", "severity_hint": "major", "surface": "acceptance criteria",
}

if stage == "refactor":
    carried = re.findall(r"^- \*\*(N\d+)\*\*", prompt, re.M)
    if scenario == "vandal":
        led = cwd / ".workflow" / "ledger.md"
        led.write_text((led.read_text() if led.exists() else "") + "\nI tidied this up for you.\n")
    out = {"calibration": "small diff", "fixed": [{"smell": "Long Method", "technique": "Extract Function",
                                                   "severity": "worthwhile"}],
           "noted": [] if carried else [{"smell": "Dispensables / Duplicate Code", "location": "the rule helpers",
                                         "reason": "two call sites", "promote_if": "a third rule repeats it"}],
           "carried": [{"id": c, "action": "left", "reason": "condition not met"} for c in carried],
           "summary": "clean"}

elif stage == "teardown-delegate":
    first_group = "acceptance criteria" in prompt.split("**Your target:**")[1].split("\n")[0]
    reexamine = re.findall(r"^- (F\d+) — .* · settled by:", prompt, re.M)
    findings = []
    if reexamine:
        findings = [{**FINDING, "confidence": "unproven", "settled_by": "a run under another TZ",
                     "reexamines": f} for f in reexamine]
    elif n == 1 and first_group:
        findings = [dict(FINDING, confidence="unproven", settled_by="run it") if scenario == "doubt" else FINDING]
    out = {"findings": findings,
           "swept": [{"surface": s.strip(), "note": "attacked, found nothing"}
                     for s in prompt.split("**Your target:**")[1].split(".")[0].split(",") if not findings],
           "not_covered": []}

elif stage == "consolidate":
    raw = json.loads(prompt.split("Delegate findings:\n", 1)[1])
    out = {"findings": raw, "dropped": []}

elif stage == "verify":
    out = {"supports": "INCONCLUSIVE" if scenario == "doubt" else "CONFIRMED",
           "attempted": "the breaking case", "observed": "accepted", "reason": "reproduces"}

elif stage == "verdict":
    ids = re.search(r"Adjudicate exactly these findings:\*\* (.+?)\.\n", prompt).group(1).split(", ")
    if scenario == "doubt":
        verdicts = [{"finding": f, "verdict": "INCONCLUSIVE", "reason": "timezone-dependent",
                     "settled_by": "a run under TZ=UTC+5"} for f in ids]
        slices = []
    else:
        verdicts = [{"finding": f, "verdict": "CONFIRMED", "severity": "major", "reason": "reproduced"} for f in ids]
        slices = [{"finding": f, "severity": "major", "behavior": "a booking 180 minutes out is rejected at cutoff 240"}
                  for f in ids]
    out = {"verdicts": verdicts, "slices": slices, "carried_smells": "N1 ships as noted",
           "stated_verdict": "NO-GO", "summary": "done"}

elif stage == "fix":
    ids = re.findall(r"^- \[\w+\] (F\d+) —", prompt, re.M)
    if scenario == "stall":
        out = {"closed": [], "not_closed": [{"finding": f, "reason": "could not reproduce"} for f in ids],
               "brief_revised": False, "summary": "stuck"}
    else:
        # converge: a real fix with a test that fails without it. vacuous: a test that passes either way.
        if scenario != "vacuous":
            (cwd / "app.py").write_text('DEFAULT = 120\n\ndef check_cutoff(slot, config):\n'
                                        '    return config.get("cutoff", DEFAULT)\n')
        body = "assert check_cutoff(None, {'cutoff': 5}) == 5" if scenario != "vacuous" else "assert True"
        (cwd / "tests" / "test_fix.py").write_text(
            f"from app import check_cutoff\n\ndef test_cutoff_reads_config():\n    {body}\n\n"
            "test_cutoff_reads_config()\n")
        out = {"closed": [{"finding": f, "test": "tests/test_fix.py::test_cutoff_reads_config"} for f in ids],
               "not_closed": [], "brief_revised": False, "summary": "green"}

else:
    sys.exit(f"fake_claude: unknown stage {stage}")

print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "total_cost_usd": 0.01, "result": json.dumps(out), "structured_output": out}))
