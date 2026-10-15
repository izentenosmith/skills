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

fix.py's stages run against a tiny `calc.py` repo (FAKE_FIX names the variant):
  ok (default)   discover → triage → root cause → red → fix, all well-behaved
  outage         triage routes to incident-fix
  strict         triage marks the fix strict (money)
  no-test-cmd    discovery can't find a test command
  rc-edits       the root-cause stage writes a file
  red-edits      the red stage also edits non-test code
  no-fix         the implement stage changes nothing
  data           the root cause wrote data: the incident profile adds a repair artifact

postmortem.py's stages (FAKE_PM):
  ok (default)   a clean, blameless, descriptive record with two factors
  blame-once     the first draft blames ("should have"); the correction is clean
  blame          every draft blames
  names          every draft puts a git author's name next to "caused"

dbreview.py's stages (FAKE_DB):
  good (default) every database satisfies every criterion and has no findings
  mixed          the database named `legacy` has a High finding and weak criteria; the rest are good
  flags          good scores, but every object carries a 🔬 needs-data flag
  dead           good scores, but usage is unused

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
FIX = os.environ.get("FAKE_FIX", "ok")
PM = os.environ.get("FAKE_PM", "ok")
DB = os.environ.get("FAKE_DB", "good")
SUITE = 'for f in tests/test_*.py; do PYTHONPATH=. python3 "$f" || exit 1; done'
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

elif stage == "fix" and (cwd / "calc.py").exists():
    # fix.py's review round: a confirmed defect in calc — total() chokes on missing values.
    ids = re.findall(r"^- \[\w+\] (F\d+) —", prompt, re.M)
    (cwd / "calc.py").write_text("def total(xs):\n    return round(sum(x for x in xs if x is not None))\n")
    (cwd / "tests" / "test_missing.py").write_text(
        "from calc import total\n\ndef test_total_skips_missing():\n    assert total([1, None]) == 1\n\n"
        "test_total_skips_missing()\n")
    out = {"closed": [{"finding": f, "test": "tests/test_missing.py::test_total_skips_missing"} for f in ids],
           "not_closed": [], "brief_revised": False, "summary": "green"}

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

elif stage == "discover":
    import subprocess
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True).stdout.strip()
    (cwd / ".workflow").mkdir(exist_ok=True)
    (cwd / ".workflow" / "env.md").write_text(
        f"# Environment profile\n- **Recorded:** 2026-10-15 at {head}\n- **Sources:** README.md\n")
    if FIX == "no-test-cmd":
        out = {"test_cmd": "", "lint_cmds": [], "default_branch": "main", "preprod": "", "tracker": "none",
               "unanswered": ["What command runs the tests?"]}
    else:
        out = {"test_cmd": SUITE, "lint_cmds": ["python3 -m py_compile calc.py"], "default_branch": "main",
               "preprod": "none", "tracker": "none", "unanswered": []}

elif stage == "triage":
    out = {"route": "incident" if FIX == "outage" else "hotfix", "strict": FIX == "strict",
           "strict_reason": "money: totals" if FIX == "strict" else "", "revert_commit": "",
           "reason": "checkout is down" if FIX == "outage" else "the system is up; one total is wrong"}

elif stage == "rootcause":
    if FIX == "rc-edits":
        (cwd / "calc.py").write_text((cwd / "calc.py").read_text() + "# poked\n")
    out = {"title": "fix: round the total once, not per line", "symptom": "total([0.4]*3) is 0, expected 1",
           "cause": "total rounds each value before summing", "why_no_test": "only whole numbers were tested",
           "evidence": "calc.total: sum(round(x) for x in xs)", "shared_place": "calc.total",
           "callers": [{"where": "report.py", "status": "shares-the-bug", "why": "sums line totals"}],
           "data_affected": FIX == "data"}

elif stage == "red":
    (cwd / "tests" / "test_total.py").write_text(
        "from calc import total\n\ndef test_rounds_once():\n    assert total([0.4, 0.4, 0.4]) == 1\n\n"
        "test_rounds_once()\n")
    if FIX == "red-edits":
        (cwd / "calc.py").write_text("def total(xs):\n    return round(sum(xs))\n")
    out = {"tests": ["tests/test_total.py"], "test_names": ["test_rounds_once"],
           "focused_cmd": "PYTHONPATH=. python3 tests/test_total.py", "no_test_framework": False}

elif stage == "implement":
    if FIX != "no-fix":
        (cwd / "calc.py").write_text("def total(xs):\n    return round(sum(xs))\n")
    out = {"summary": "round the sum once", "files": ["calc.py"], "band_aid": False}

elif stage == "repair":
    (cwd / "repair").mkdir(exist_ok=True)
    (cwd / "repair" / "fix_totals.py").write_text("# dry run by default; --apply writes; backs up first\n")
    out = {"artifact": "repair/fix_totals.py", "test": "tests/test_repair.py", "dry_run": "default, prints counts",
           "backup": "copies affected rows first", "selector": "rows whose total != round(sum)",
           "runbook": "dry run → staging → production with confirmation"}

elif stage == "postmortem":
    retry = "Your previous answer was" in prompt
    bad = {"blame": "The on-call engineer should have noticed the alert.",
           "names": "Dana caused the outage with the rounding change.",
           "blame-once": "" if retry else "Review failed to catch the change."}.get(PM, "")
    md = ("# Post-mortem: totals\n\n## Summary\nInvoices were short by a cent for 2 days.\n\n"
          "## Timeline\n| Time | Event | Source |\n|---|---|---|\n| 13:41Z | impact start | logs |\n\n"
          f"## Impact\n- 12 orders, 0.4% of the period's orders. {bad}\n\n"
          "## Contributing factors\n- **C1 — trigger:** the totals helper rounds per line.\n"
          "- **C2 — detection:** no alert compares invoice sums with order totals.\n\n"
          "## What went well\n- The flag took effect in 30 s.\n\n## Open questions\n- None.\n")
    out = {"markdown": md, "tier": "Standard", "open_questions": [],
           "factors": [{"id": "C1", "category": "trigger", "factor": "the totals helper rounds per line",
                        "evidence": "git", "confidence": "high"},
                       {"id": "C2", "category": "detection", "factor": "no alert compares invoice sums with totals",
                        "evidence": "log", "confidence": "high"}]}

elif stage == "followthrough":
    out = {"proposals": [
        {"factor": "the totals helper rounds per line", "kind": "follow-up",
         "outcome": "totals are computed once from unrounded amounts", "why": "removes the class"},
        {"factor": "no alert compares invoice sums with totals", "kind": "follow-up",
         "outcome": "an alert fires when invoice sums and order totals diverge", "why": "detection"}]}

elif stage == "db-audit":
    db = re.search(r"Audit the \*\*(.+?)\*\* database", prompt).group(1)
    files = re.findall(r"^- `(.+?)`$", prompt, re.M)
    bad = DB == "mixed" and db == "legacy"
    crit = [{"rubric": "tables", "criterion": "1 Primary key present", "in_scope": 10, "satisfied": 4 if bad else 10,
             "proxy_only": False},
            {"rubric": "tables", "criterion": "4 Right-sized types", "in_scope": 10, "satisfied": 7 if bad else 10,
             "proxy_only": False}]
    findings = []
    if bad:
        findings.append({"id": "T-1", "object": "orders", "severity": "High", "confidence": "decidable",
                         "theory": "entity integrity", "evidence": "tables.sql:12", "summary": "orders has no PK"})
    if DB == "flags":
        findings += [{"id": f"F-{i}", "object": f"t{i}", "severity": "Medium", "confidence": "needs-data",
                      "theory": "cardinality", "evidence": "-", "summary": "row counts unknown"} for i in range(10)]
    out = {"usage_status": "unused" if DB == "dead" else "used", "summary_md": f"# {db}\n\nSummary.",
           "files": [{"file": f, "coverage": "all objects", "objects": 10, "evaluation_md": f"# {f}\n\nFindings.",
                      "criteria": crit, "findings": findings} for f in files]}

elif stage == "db-synthesis":
    out = {"markdown": "# Estate analysis\n\nPatterns.", "coupling": [{"from": "legacy", "to": "sales", "via": "a view"}]}

elif stage == "db-propose":
    dbs = re.search(r"for \*\*(.+?)\*\* only", prompt).group(1)
    out = {"files": [{"name": "reuse-rework-register.md", "markdown": f"# Register\n\nProposed for: {dbs}\n"}]}

else:
    sys.exit(f"fake_claude: unknown stage {stage}")

print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "total_cost_usd": 0.01, "result": json.dumps(out), "structured_output": out}))
