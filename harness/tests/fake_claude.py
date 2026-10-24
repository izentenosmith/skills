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

netreview.py's stages (FAKE_NET):
  good (default) two redundant firewalls in front of a managed VNet; every criterion satisfied
  mixed          the network named `legacy` has a High finding and a weak criterion
  spof           one firewall only, so the critical pair has node connectivity 1
  nopairs        no critical pairs declared
  flags          every object carries a 🔬 flag
  dead           usage is decommissioned
  badtopo        topology_json is not JSON (twice, so the correction round fails)

networkflow.py's stages (FAKE_NF):
  ok (default)   design → diagrams → proposal → blueprint, all in convention
  badcidr        the diagram labels the networks with the wrong CIDR
  nolegend       the diagram has no 'Network diagram conventions' legend

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

elif stage.startswith(("net-", "nf-")):
    def topology(redundant=True, pairs=True, status="recovered"):
        ev = "main.tf"
        nodes = [{"id": "internet", "kind": "internet", "zone": "internet", "site": "global", "attrs": {}, "evidence": f"{ev}:1"},
                 {"id": "fw-a", "kind": "firewall", "zone": "edge", "site": "r1", "attrs": {}, "evidence": f"{ev}:10"},
                 {"id": "vnet-hub", "kind": "vnet", "zone": "app", "site": "r1", "attrs": {"managed_ha": True}, "evidence": f"{ev}:2"},
                 {"id": "snet-app", "kind": "subnet", "zone": "app", "site": "r1", "attrs": {}, "evidence": f"{ev}:5"}]
        edges = [{"id": "e-inet-fwa", "a": "internet", "b": "fw-a", "kind": "l3-adjacency", "redundancy_group": None, "attrs": {}, "evidence": f"{ev}:11"},
                 {"id": "e-fwa-hub", "a": "fw-a", "b": "vnet-hub", "kind": "l3-adjacency", "redundancy_group": None, "attrs": {}, "evidence": f"{ev}:12"},
                 {"id": "e-hub-app", "a": "vnet-hub", "b": "snet-app", "kind": "l3-adjacency", "redundancy_group": None,
                  "attrs": {"managed_ha": True}, "evidence": f"{ev}:5"}]
        if redundant:
            nodes.append({"id": "fw-b", "kind": "firewall", "zone": "edge", "site": "r1", "attrs": {}, "evidence": f"{ev}:20"})
            edges += [{"id": "e-inet-fwb", "a": "internet", "b": "fw-b", "kind": "l3-adjacency", "redundancy_group": None, "attrs": {}, "evidence": f"{ev}:21"},
                      {"id": "e-fwb-hub", "a": "fw-b", "b": "vnet-hub", "kind": "l3-adjacency", "redundancy_group": None, "attrs": {}, "evidence": f"{ev}:22"}]
        return {"meta": {"name": "demo", "source_version": "test", "rubric": "v1.0", "stage": "audit", "status": status},
                "nodes": nodes, "edges": edges,
                "networks": [{"id": "vnet-hub", "cidr": "10.0.0.0/16", "parent": None, "purpose": "hub", "evidence": f"{ev}:2"},
                             {"id": "snet-app", "cidr": "10.0.1.0/24", "parent": "vnet-hub", "purpose": "app", "evidence": f"{ev}:5"}],
                "zones": [{"id": "internet", "trust": 0, "purpose": "untrusted"}, {"id": "edge", "trust": 1, "purpose": "edge"},
                          {"id": "app", "trust": 2, "purpose": "app"}],
                "flows": [{"id": "f-web", "from_zone": "internet", "to_zone": "edge", "proto": "tcp", "ports": "443", "action": "allow", "priority": 100, "evidence": f"{ev}:30"},
                          {"id": "f-app", "from_zone": "edge", "to_zone": "app", "proto": "tcp", "ports": "8443", "action": "allow", "priority": 100, "evidence": f"{ev}:31"},
                          {"id": "f-deny-edge", "from_zone": "*", "to_zone": "edge", "proto": "any", "ports": "*", "action": "deny", "priority": 4096, "evidence": f"{ev}:32"},
                          {"id": "f-deny-app", "from_zone": "*", "to_zone": "app", "proto": "any", "ports": "*", "action": "deny", "priority": 4096, "evidence": f"{ev}:33"}],
                "critical_pairs": [{"from": "internet", "to": "snet-app", "why": "storefront"}] if pairs else []}

    def drawio(topo, cidr_ok=True, legend=True):
        leg = '<mxCell id="deco-legend" value="Network diagram conventions — legend" vertex="1" parent="1"/>' if legend else ""
        cidr = {n["id"]: n["cidr"] for n in topo["networks"]}
        cells = []
        for n in topo["nodes"]:
            label = f"{n['id']}&lt;br&gt;{cidr[n['id']] if cidr_ok else '192.0.2.0/24'}" if n["id"] in cidr else n["id"]
            cells.append(f'<mxCell id="{n["id"]}" value="{label}" vertex="1" parent="1"/>')
        cells += [f'<mxCell id="{e["id"]}" edge="1" source="{e["a"]}" target="{e["b"]}" parent="1"/>' for e in topo["edges"]]
        zones = [f'<mxCell id="{z["id"]}" value="{z["id"]} — trust {z["trust"]}" vertex="1" parent="1"/>' for z in topo["zones"]]
        flows = [f'<mxCell id="{f["id"]}" value="{f["proto"]}/{f["ports"]}" edge="1" parent="1"/>'
                 for f in topo["flows"] if f["action"] == "allow"]

        def page(name, body):
            return (f'<mxfile><diagram name="{name}"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                    f'{leg}{"".join(body)}</root></mxGraphModel></diagram></mxfile>')
        return {"logical-topology.drawio": page("Logical topology (L3)", cells),
                "segmentation.drawio": page("Segmentation (zones and flows)", zones + flows)}

    NET = os.environ.get("FAKE_NET", "good")
    NF = os.environ.get("FAKE_NF", "ok")
    if stage == "net-audit":
        net = re.search(r"Audit the \*\*(.+?)\*\* network", prompt).group(1)
        bad = NET == "mixed" and net == "legacy"
        crit = [{"rubric": "segmentation", "criterion": "2 Not an any-any allow", "in_scope": 10,
                 "satisfied": 4 if bad else 10, "proxy_only": False}]
        findings = [{"id": "S-1", "object": "nsg-legacy", "severity": "High", "confidence": "decidable",
                     "theory": "theory §11", "evidence": "main.tf:40", "summary": "broad source"}] if bad else []
        if NET == "flags":
            findings += [{"id": f"F-{i}", "object": f"r{i}", "severity": "Medium", "confidence": "needs-data",
                          "theory": "§2", "evidence": "-", "summary": "utilization unknown"} for i in range(10)]
        topo = topology(redundant=NET != "spof", pairs=NET != "nopairs")
        out = {"usage_status": "decommissioned" if NET == "dead" else "in-use", "summary_md": f"# {net}\n\nSummary.",
               "topology_json": json.dumps(topo) if NET != "badtopo" else "{not json",
               "domains": [{"domain": "segmentation", "coverage": "all rules", "objects": 10,
                            "evaluation_md": "# segmentation\n\nFindings.", "criteria": crit, "findings": findings}]}
    elif stage == "net-synthesis":
        out = {"markdown": "# Estate analysis\n\nPatterns.",
               "coupling": [{"from": "legacy", "to": "prod", "via": "peering", "count": 1}]}
    elif stage == "net-propose":
        nets = re.search(r"for \*\*(.+?)\*\* only", prompt).group(1)
        out = {"files": [{"name": "proposal.md", "markdown": f"# Proposal\n\nProposed for: {nets}\n"}]}
    elif stage == "nf-design":
        out = {"files": [{"name": "design.md", "content": "# Design\n\nHub with two firewalls."},
                         {"name": "topology.json", "content": json.dumps(topology(status="proposed"))}]}
    elif stage == "nf-diagram":
        views = drawio(topology(status="proposed"), cidr_ok=NF != "badcidr", legend=NF != "nolegend")
        out = {"files": [{"name": k, "content": v} for k, v in views.items()]}
    elif stage == "nf-propose":
        out = {"files": [{"name": "proposal.md", "content": "# Proposal\n\nAcceptance is required before netblueprint."}]}
    elif stage == "nf-blueprint":
        final = topology(status="accepted")
        out = {"files": [{"name": "network-design.md", "content": "# Network design (accepted)\n"},
                         {"name": "topology.json", "content": json.dumps(final)},
                         *({"name": k, "content": v} for k, v in drawio(final).items())]}
    else:
        sys.exit(f"fake_claude: unknown stage {stage}")

else:
    sys.exit(f"fake_claude: unknown stage {stage}")

print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "total_cost_usd": 0.01, "result": json.dumps(out), "structured_output": out}))
