#!/usr/bin/env python3
"""Take a bug report to a pull request: the hotfix lane, or an incident's fix phase, run by code.

    python3 harness/fix.py --repo . --report "<what's wrong>"                   # hotfix (default profile)
    python3 harness/fix.py --repo . --report @report.md --profile incident --incident-log docs/incidents/x.md
    python3 harness/fix.py --repo . --report "<…>" --open-pr                     # also push and open a draft PR

Stages, each a headless `claude -p` call, each gated by code:

    discover → triage → root cause → red → fix → review → [repair] → ship
     env.md    route out  3 lines +    a test   minimal   teardown +   incident    branch, commit,
     (cached)  or strict  callers      that      at the    verdict;    profile     record, and a PR
                                       fails     cause     blockers    only        only with --open-pr

What code enforces, that the skills ask for in prose:
- the root-cause stage changes no file; the red stage changes only test files;
- the red test fails on the pre-fix code and passes after (redgreen.py), not just "a test exists";
- the suite and every lint command discovered are green before review and before ship;
- review is one devils-advocate + tyr-verdict pass (hotfix) or the full closing loop capped at two
  (incident); a hotfix fixes blockers — and majors in strict mode — once, everything else is a follow-up;
- nothing outward-facing happens without --open-pr, which pushes the branch and opens a *draft* PR.
  Nothing is ever merged or deployed.

State lives in .workflow/<profile>-<slug>/ (state.json, brief.md, ledger.md, record.md); re-running
resumes at the first stage not done. Exit status: 0 ready (or PR opened) · 1 error · 3 escalate — leave
the lane · 4 a gate failed · 5 needs your input · 6 routed out of this lane.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import incident as INC  # noqa: E402
import ledger as L  # noqa: E402
import loop  # noqa: E402
import redgreen  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_ESCALATED, EXIT_GATE, EXIT_INPUT, EXIT_ROUTED = 0, 1, 3, 4, 5, 6
READ_TOOLS, READ_RUN_TOOLS, WRITE_TOOLS = "Read,Grep,Glob", "Read,Grep,Glob,Bash", loop.WRITE_TOOLS
STAGES = ("discover", "triage", "rootcause", "red", "implement", "review", "repair", "ship")


class NeedsInput(Exception):
    pass


class Routed(Exception):
    pass


class Escalate(Exception):
    pass


# ------------------------------------------------------------------ schemas

S, B = {"type": "string"}, {"type": "boolean"}
ARR = lambda item: {"type": "array", "items": item}  # noqa: E731
obj = loop._obj

DISCOVER_SCHEMA = obj({"test_cmd": S, "lint_cmds": ARR(S), "default_branch": S, "preprod": S,
                       "tracker": S, "unanswered": ARR(S)})
TRIAGE_SCHEMA = obj({"route": {"type": "string", "enum": ["hotfix", "incident", "design"]},
                     "strict": B, "strict_reason": S, "revert_commit": S, "reason": S},
                    ["route", "strict", "reason"])
ROOTCAUSE_SCHEMA = obj({
    "title": S, "symptom": S, "cause": S, "why_no_test": S, "evidence": S, "shared_place": S,
    "callers": ARR(obj({"where": S, "status": {"type": "string",
                                               "enum": ["shares-the-bug", "unaffected", "needs-different"]},
                        "why": S})),
    "data_affected": B,
}, ["title", "symptom", "cause", "why_no_test", "evidence", "shared_place", "callers", "data_affected"])
RED_SCHEMA = obj({"tests": ARR(S), "test_names": ARR(S), "focused_cmd": S, "no_test_framework": B},
                 ["tests", "test_names", "no_test_framework"])
IMPLEMENT_SCHEMA = obj({"summary": S, "files": ARR(S), "band_aid": B,
                        "follow_up": obj({"outcome": S, "why_not_now": S, "target_date": S})},
                       ["summary", "files", "band_aid"])
REPAIR_SCHEMA = obj({"artifact": S, "test": S, "dry_run": S, "backup": S, "selector": S, "runbook": S})


# ------------------------------------------------------------------ prompts

HEADER = """HARNESS-STAGE: {stage} · HARNESS-ITERATION: 1

You are one stage of an automated harness running the `{skill}` skill ({skill_path}). The user is not \
available: don't ask — finish this stage and return the structured result. Do only this stage; the \
harness runs the others. Never push, merge, deploy, publish or create tickets.
"""

DISCOVER = """Work the discovery checklist in `{discovery}` for this repository and write the profile to \
`.workflow/env.md` in the format it gives. Return the full test command **as CI runs it**, every lint / \
type-check command CI runs (empty list if none), the default branch, whether a pre-production environment \
exists, the tracker (or "none"), and — in `unanswered` — each thing you could not discover, as one short \
question with your best guess.
"""

TRIAGE = """The report:

{report}

Apply the skill's Step 1 triage gate. Route `incident` if the system is down or degraded, data is being \
corrupted, lost or exposed now, or there is a security exposure. Route `design` if there are several \
reasonable fixes with different trade-offs, or the fix needs a new boundary. Otherwise `hotfix`. Set \
`strict` when the fix touches persistent data, money, permissions or tenancy, and say why. If one \
identifiable commit introduced the bug and reverting it loses nothing still wanted, name it in \
`revert_commit`. Read the code you need; change nothing.
"""

ROOTCAUSE = """The report:

{report}

Find the root cause from evidence and write the three-line note the skill describes (symptom · cause · \
why no existing test caught it), using its `root-cause-note.md`. Then the caller sweep: every direct \
caller, indirect reach and copy of the logic, each marked `shares-the-bug`, `unaffected` or \
`needs-different`. Name the shared place the fix belongs in. Set `data_affected` if the bug has already \
written wrong data anywhere. Give a commit subject in `title`, following the repo's commit convention \
(`.workflow/env.md`). You may run commands to reproduce; **change no file**.
"""

RED = """Root cause:
{note}

Write the test that fails **because of this bug** — through the highest public seam that reproduces it \
cheaply, in the repo's existing test conventions and location — and **nothing else**: no fix, no \
non-test file. Watch it fail for the right reason (an assertion about the behavior, not an import error). \
If the repo has no test framework, write the smallest runnable check that fails without the fix, named \
like a test (`test_*` or under `tests/`), and set `no_test_framework`. Return the test files, the test \
names, and a command that runs just them.
"""

IMPLEMENT = """Root cause:
{note}

The failing test(s): {tests}. Make them pass with the **minimal fix in the shared place** ({shared}), \
covering every caller marked `shares-the-bug`. Follow the repo's conventions; no adjacent cleanup; do \
not edit the tests. Then run `{test_cmd}`{lint} — all must be green. If the fix guards a symptom rather \
than removing the cause, set `band_aid` and describe the proper fix as a follow-up with a target date.
"""

REPAIR = """Root cause:
{note}

This bug already wrote wrong data. Write the **data repair as its own artifact**, following the \
incident-fix skill's `data-repair.md`: it selects exactly the affected records by the defect's \
signature, takes a backup of what it will change, defaults to a dry run that prints before/after counts, \
writes only with an explicit apply flag, is idempotent, and has a test against a small fixture holding \
affected and unaffected records. **Do not run it against any real database.** Return the artifact path, \
its test, the dry-run and backup behavior, the selector, and the runbook a human will follow (dry run → \
non-production → production with confirmation).
"""


# ------------------------------------------------------------------ state

class Run:
    def __init__(self, a):
        self.a = a
        self.repo = pathlib.Path(a.repo).resolve()
        self.profile = a.profile
        self.skill_name = "hotfix" if self.profile == "hotfix" else "incident-fix"
        self.report = read_report(a.report, self.repo)
        self.slug = a.slug or slugify(self.report)
        self.dir = self.repo / ".workflow" / f"{self.profile}-{self.slug}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ignore = {a.incident_log} if a.incident_log else set()
        self.state_path = self.dir / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"done": []}
        run_dir = self.dir / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        self.ctx = loop.Ctx(
            repo=self.repo, skills=pathlib.Path(a.skills).resolve(), test_cmd=a.test_cmd or "",
            base="HEAD", cap=2, model=a.model, delegate_model=a.delegate_model, concurrency=a.concurrency,
            budget=a.budget_usd, timeout=a.timeout, dry=False, run_dir=run_dir,
            claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"),
            ledger_path=self.dir / "ledger.md", brief_path=self.dir / "brief.md")
        if self.state.get("test_cmd"):
            self.ctx.test_cmd = a.test_cmd or self.state["test_cmd"]
        if self.state.get("snapshot"):
            self.ctx.base = self.state["snapshot"]

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2) + "\n")

    def done(self, stage):
        if stage not in self.state["done"]:
            self.state["done"].append(stage)
        self.save()

    def skill(self, name=None):
        return loop.skill_path(self.ctx, name or self.skill_name)

    def ref(self, doc):
        return self.skill().parent / doc

    def header(self, stage):
        return HEADER.format(stage=stage, skill=self.skill_name, skill_path=self.skill())

    def note(self):
        rc = self.state["rootcause"]
        callers = "\n".join(f"  - {c['where']}: {c['status']} — {c.get('why', '')}" for c in rc["callers"])
        return (f"- **Symptom:** {rc['symptom']}\n- **Cause:** {rc['cause']}\n"
                f"- **Why no test caught it:** {rc['why_no_test']}\n- **Evidence:** {rc['evidence']}\n"
                f"- **Shared place:** {rc['shared_place']}\n- **Callers:**\n{callers}")

    def gate(self, when):
        loop.gate(self.ctx, when)
        for cmd in self.state.get("lint_cmds", []):
            ok, tail = loop.run_tests(self.ctx, cmd=cmd)
            loop.log(f"gate {when}: `{cmd}` {'GREEN' if ok else 'RED'} — {tail}")
            if not ok:
                raise loop.GateFailed(f"`{cmd}` fails {when}: {tail}")

    def incident_log(self, kind, text):
        if self.a.incident_log:
            INC.main(["log", str(self.repo / self.a.incident_log), kind, text])


def read_report(report, repo):
    if report.startswith("@"):
        path = pathlib.Path(report[1:])
        return (path if path.is_absolute() else repo / path).read_text().strip()
    return report.strip()


def slugify(text):
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "fix"


def changed_since(repo, base, ignore=()):
    now = redgreen.snapshot(repo)
    out = redgreen.git(repo, "diff", "--name-only", base, now)
    return [p for p in out.splitlines() if p and not p.startswith(".workflow/") and p not in ignore]


def tracked(repo, path):
    return subprocess.run(["git", "ls-files", "--error-unmatch", "--", path], cwd=repo,
                          capture_output=True).returncode == 0


# ------------------------------------------------------------------ stages

def env_is_current(repo):
    """discovery.md's freshness rules, checked rather than trusted."""
    env = repo / ".workflow" / "env.md"
    if not env.exists():
        return False
    text = env.read_text()
    m = re.search(r"\*\*Recorded:\*\*.*?\bat\s+`?([0-9a-f]{7,40})`?", text)
    if not m:
        return False
    sha = m.group(1)
    if subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=repo).returncode:
        return False
    src = re.search(r"\*\*Sources:\*\*\s*(.+)", text)
    paths = [p.strip(" `") for p in re.split(r"[,;]", src.group(1))] if src else []
    paths = [p for p in paths if p and (repo / p).exists()]
    if paths and redgreen.git(repo, "diff", "--name-only", sha, "HEAD", "--", *paths):
        return False
    return True


def stage_discover(r):
    if env_is_current(r.repo) and r.state.get("test_cmd"):
        loop.log("discover: .workflow/env.md is current — reusing it")
        return
    out = loop.claude(r.ctx, "discover", r.header("discover") + DISCOVER.format(discovery=r.ref("discovery.md")),
                      DISCOVER_SCHEMA, WRITE_TOOLS, write=True)
    test_cmd = r.a.test_cmd or out["test_cmd"].strip()
    r.state.update(test_cmd=test_cmd, lint_cmds=r.a.lint_cmd or out["lint_cmds"],
                   default_branch=out["default_branch"] or default_branch(r.repo), preprod=out["preprod"],
                   tracker=out["tracker"])
    if out["unanswered"]:
        (r.dir / "questions.md").write_text("# Discovery questions\n\n" + "\n".join(f"- {q}" for q in out["unanswered"]) +
                                            "\n\nAnswer them in `.workflow/env.md` (or pass --test-cmd / --lint-cmd), "
                                            "then re-run.\n")
    if not test_cmd:
        r.save()
        raise NeedsInput(f"no test command could be discovered — see {r.dir / 'questions.md'}")
    r.ctx.test_cmd = test_cmd
    loop.log(f"discover: test `{test_cmd}` · lint {r.state['lint_cmds'] or 'none'} · "
             f"default branch {r.state['default_branch']}")


def stage_triage(r):
    if r.profile == "incident":
        r.state.update(strict=True, strict_reason="incident: production impact")
        return
    out = loop.claude(r.ctx, "triage", r.header("triage") + TRIAGE.format(report=r.report), TRIAGE_SCHEMA, READ_TOOLS)
    r.state["triage"] = out
    if out["route"] == "incident":
        raise Routed(f"this is an incident, not a hotfix — {out['reason']}. Run incident-fix.")
    if out["route"] == "design":
        raise Routed(f"this needs a design decision — {out['reason']}. Run architect-deep-dive → agent-brief.")
    r.state.update(strict=out["strict"], strict_reason=out.get("strict_reason", ""))
    loop.log(f"triage: hotfix lane · {'STRICT — ' + out.get('strict_reason', '') if out['strict'] else 'standard'}")


def stage_rootcause(r):
    before = redgreen.snapshot(r.repo)
    out = loop.claude(r.ctx, "rootcause", r.header("rootcause") + ROOTCAUSE.format(report=r.report),
                      ROOTCAUSE_SCHEMA, READ_RUN_TOOLS)
    touched = changed_since(r.repo, before, r.ignore)
    if touched:
        raise loop.HarnessError(f"the root-cause stage changed files ({', '.join(touched)}); "
                                "it may only read and reproduce")
    different = [c for c in out["callers"] if c["status"] == "needs-different"]
    if different:
        raise Routed("callers need different behavior — a design question: "
                     + "; ".join(f"{c['where']} ({c.get('why', '')})" for c in different))
    r.state["rootcause"] = out
    r.state["snapshot"] = redgreen.snapshot(r.repo)        # the pre-fix code, exactly
    r.ctx.base = r.state["snapshot"]
    n = len(out["callers"])
    loop.log(f"root cause: {out['cause'][:100]} · {n} caller(s), "
             f"{sum(c['status'] == 'shares-the-bug' for c in out['callers'])} share the bug")
    r.incident_log("finding", f"cause (known): {out['cause']}")


def stage_red(r):
    def validate(out):
        changed = changed_since(r.repo, r.state["snapshot"], r.ignore)
        bad = [p for p in changed if not (redgreen.TEST_RE.search(p) or p in out["tests"])]
        return [f"the red stage may only change tests; it also changed {', '.join(bad)}"] if bad else []

    out = loop.claude_checked(r.ctx, "red", r.header("red") + RED.format(note=r.note()), RED_SCHEMA,
                              WRITE_TOOLS, validate, write=True)
    cmd = out.get("focused_cmd") or r.ctx.test_cmd
    ok, tail = loop.run_tests(r.ctx, cmd=cmd)
    if ok:
        raise loop.GateFailed(f"the new test passes on the unfixed code — it doesn't reproduce the bug: {tail}")
    r.state["red"] = {**out, "cmd": cmd, "red_tail": tail}
    loop.log(f"red: {', '.join(out['test_names'])} fail on the unfixed code — {tail}")


def stage_implement(r):
    lint = "".join(f", `{c}`" for c in r.state.get("lint_cmds", []))
    out = loop.claude(r.ctx, "implement", r.header("implement") + IMPLEMENT.format(
        note=r.note(), tests=", ".join(r.state["red"]["test_names"]), shared=r.state["rootcause"]["shared_place"],
        test_cmd=r.ctx.test_cmd, lint=lint), IMPLEMENT_SCHEMA, WRITE_TOOLS, write=True)
    r.gate("after the fix")
    proof = redgreen.check(r.repo, r.state["red"]["cmd"], base=r.state["snapshot"],
                           tests=r.state["red"]["tests"] or None, timeout=r.ctx.timeout)
    r.state["redgreen"] = {k: v for k, v in proof.items() if k not in ("before", "after")}
    if proof["verdict"] != "red-green":
        raise loop.GateFailed(f"red→green not proven: {proof['verdict']} — {proof['reason']}")
    r.state["implement"] = out
    loop.log(f"fix: {out['summary'][:100]} · red→green proven")
    r.incident_log("evidence", f"red→green proven for {', '.join(r.state['red']['test_names'])}")


def write_brief(r):
    rc = r.state["rootcause"]
    r.ctx.brief.write_text(
        f"# Build Plan: {rc['title']}\n\n**Category:** bug\n**Summary:** {rc['symptom']}\n\n"
        f"**Current behavior:**\n{rc['symptom']}\n\n**Desired behavior:**\nThe cause is removed at "
        f"{rc['shared_place']}: {rc['cause']}\n\n**Acceptance criteria:**\n"
        + "".join(f"- [x] {t}\n" for t in r.state["red"]["test_names"])
        + "\n**Callers:**\n" + "".join(f"- {c['where']} — {c['status']}\n" for c in rc["callers"])
        + "\n**Out of scope:**\n- Anything beyond the fix at the shared place\n\n## Revisions\n- (none)\n")


def stage_review(r):
    write_brief(r)
    ctx = r.ctx
    if r.profile == "hotfix":
        # One teardown, one adjudication, then one round on what must be fixed — no loop.
        ctx.skip_refactor = "the hotfix lane has no refactor pass"
        code, st = loop.run_loop(ctx, max_iterations=1)
        open_ = L.status(ctx.ledger.read_text(), ctx.cap)
        must = {"blocker", "major"} if r.state.get("strict") else {"blocker"}
        must_fix = [s for s in open_["open_slices"] if s["severity"] in must]
        follow = [s for s in open_["open_slices"] if s["severity"] not in must]
        if must_fix:
            loop.log(f"review: fixing {len(must_fix)} confirmed {'/'.join(sorted(must))} once, red→green")
            loop.stage_fix(ctx, 2, {**open_, "open_slices": must_fix})
            r.gate("after the review fixes")
            still = [s for s in L.status(ctx.ledger.read_text(), ctx.cap)["open_slices"] if s["severity"] in must]
            if still:
                raise Escalate("confirmed " + ", ".join(f"{s['id']} [{s['severity']}]" for s in still)
                               + " could not be fixed inside the lane — hand the change to the full pipeline")
        r.state["review"] = {"verdict": (open_["computed"] or {}).get("outcome", "GO"), "fixed": [s["id"] for s in must_fix],
                             "follow_ups": follow}
    else:
        ctx.cap = 2
        code, st = loop.run_loop(ctx)
        if code == loop.EXIT_ESCALATED:
            raise Escalate(f"the fix loop hit its cap of two — {st['computed']['reason']}")
        r.state["review"] = {"verdict": "GO", "fixed": [], "follow_ups": [
            {"id": f, "severity": "minor", "behavior": "tracked minor"} for f in st["open_minor"]]}
    loop.log(f"review: {r.state['review']['verdict']} · {len(r.state['review']['follow_ups'])} follow-up(s)")


def stage_repair(r):
    if r.profile != "incident" or not r.state["rootcause"]["data_affected"]:
        return
    out = loop.claude(r.ctx, "repair", HEADER.format(stage="repair", skill="incident-fix", skill_path=r.skill())
                      + REPAIR.format(note=r.note()), REPAIR_SCHEMA, WRITE_TOOLS, write=True)
    if not (r.repo / out["artifact"]).exists():
        raise loop.HarnessError(f"the repair artifact {out['artifact']} was not written")
    r.gate("after the repair artifact")
    r.state["repair"] = out
    loop.log(f"repair: {out['artifact']} (dry run: {out['dry_run'][:60]}) — not executed; it ships for review")


# ------------------------------------------------------------------ ship

def default_branch(repo):
    r = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo,
                       capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip().split("/", 1)[-1]
    for b in ("main", "master"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", b], cwd=repo, capture_output=True).returncode == 0:
            return b
    return "main"


def pr_tool(remote_url):
    """The CLI that opens a PR on this host — from the remote, never assumed."""
    u = remote_url.lower()
    if "github" in u:
        return "gh"
    if "gitlab" in u:
        return "glab"
    if "dev.azure.com" in u or "visualstudio.com" in u:
        return "az"
    return None


def pr_command(tool, title, body_file, base, head):
    body = pathlib.Path(body_file).read_text()
    if tool == "gh":
        return ["gh", "pr", "create", "--draft", "--title", title, "--body-file", str(body_file),
                "--base", base, "--head", head]
    if tool == "glab":
        return ["glab", "mr", "create", "--draft", "--title", title, "--description", body,
                "--target-branch", base, "--source-branch", head, "--yes"]
    if tool == "az":
        return ["az", "repos", "pr", "create", "--draft", "true", "--title", title, "--description", body,
                "--target-branch", base, "--source-branch", head]
    return None


def render_record(r, branch):
    rc, red, imp = r.state["rootcause"], r.state["red"], r.state["implement"]
    rg, rev = r.state["redgreen"], r.state["review"]
    tri = r.state.get("triage", {})
    lint = r.state.get("lint_cmds", [])
    mode = "strict — " + r.state.get("strict_reason", "") if r.state.get("strict") else "standard"
    follow = rev["follow_ups"] + ([{"id": "band-aid", "severity": "follow-up", "behavior": imp["follow_up"]["outcome"]
                                    + f" (by {imp['follow_up'].get('target_date', '?')})"}]
                                  if imp["band_aid"] and imp.get("follow_up") else [])
    lines = [
        f"# {'Hotfix' if r.profile == 'hotfix' else 'Incident fix'}: {r.slug} — {rc['symptom'][:80]}", "",
        f"- **Date:** {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        f"- **Triage:** {r.profile} lane · {mode} · revert: {tri.get('revert_commit') or 'no'}",
        f"- **Branch:** `{branch}`", "",
        "## Root cause", r.note(), "",
        "## Checklist",
        "- [x] **Root-cause note** written before the fix, from evidence — the root-cause stage changed no file",
        f"- [x] **Red → green:** {', '.join(f'`{t}`' for t in red['test_names'])} — fails on the pre-fix code "
        f"({red['red_tail'][:80]}), passes after; checked by redgreen against snapshot `{rg['base'][:10]}`",
        f"- [x] **Suite:** `{r.ctx.test_cmd}` → green",
        f"- [x] **Lint / type-check:** " + (", ".join(f"`{c}` → green" for c in lint) or "none in this repo"),
        f"- [x] **Review pass:** devils-advocate + tyr-verdict ({'one pass' if r.profile == 'hotfix' else 'closing loop, cap 2'})"
        f" — verdict {rev['verdict']}"
        + (" by the pipeline's rules; this lane fixes blockers"
           + (" and majors" if r.state.get("strict") else "") + " and defers the rest as follow-ups"
           if rev["verdict"] != "GO" else "")
        + f" — fixed: {', '.join(rev['fixed']) or 'none needed'}, follow-ups: {len(follow)}",
        "- [x] **Follow-up item:** " + ("; ".join(f"{f['id']} [{f['severity']}] {f['behavior']}" for f in follow)
                                        or "not a band-aid, nothing deferred"),
    ]
    if r.state.get("repair"):
        rp = r.state["repair"]
        lines.append(f"- [x] **Data repair artifact:** `{rp['artifact']}` (test `{rp['test']}`) — **not executed**. "
                     f"Runbook: {rp['runbook']}")
    lines += [
        "- [ ] **Shipped by:** this PR — merging is a human decision",
        f"- [ ] **Pre-production verification:** {r.state.get('preprod') or 'no pre-production environment found'} — "
        "after merge, hit the affected behavior and record the result here",
        "- [ ] **Production verification:** after promotion, the same, at the shipped commit",
        "", "## Skipped",
        "- " + ("no test framework: the proof is a runnable check; a follow-up for a real harness is owed"
                if red.get("no_test_framework") else "nothing skipped by the harness; verification happens after merge"),
        "", f"<sub>Ledger: `{r.ctx.ledger.relative_to(r.repo)}` · state: `{r.state_path.relative_to(r.repo)}`</sub>",
    ]
    return "\n".join(lines) + "\n"


def stage_ship(r):
    repo = r.repo
    current = redgreen.git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    base_branch = r.state.get("default_branch") or default_branch(repo)
    branch = current
    if current in (base_branch, "HEAD"):
        branch = f"{'hotfix' if r.profile == 'hotfix' else 'incident'}/{r.slug}"
        redgreen.git(repo, "switch", "-c", branch)
    changed = changed_since(repo, r.state["snapshot"], r.ignore)
    declared = set(r.state["red"]["tests"]) | set(r.state["implement"]["files"])
    if r.state.get("repair"):
        declared |= {r.state["repair"]["artifact"], r.state["repair"]["test"]}
    # Tracked changes always ship; an untracked file ships only if a stage declared it or it is a test —
    # build output and scratch files a stage left behind stay out of the commit.
    paths = [p for p in changed if tracked(repo, p) or p in declared or redgreen.TEST_RE.search(p)]
    left = sorted(set(changed) - set(paths))
    if left:
        loop.log(f"ship: leaving {len(left)} undeclared untracked file(s) out of the commit: {', '.join(left[:5])}")
    record = r.dir / "record.md"
    record.write_text(render_record(r, branch))
    if paths:
        redgreen.git(repo, "add", "--", *paths)
        msg = f"{r.state['rootcause']['title']}\n\n{r.note()}\n"
        subprocess.run(["git", "commit", "-q", "-F", "-"], input=msg, text=True, cwd=repo, check=True)
    sha = redgreen.git(repo, "rev-parse", "HEAD")
    r.state["ship"] = {"branch": branch, "commit": sha, "files": paths}
    loop.log(f"ship: committed {len(paths)} file(s) on `{branch}` at {sha[:10]}; record {record.relative_to(repo)}")
    r.incident_log("action", f"fix committed on {branch} at {sha[:10]}")
    if r.a.incident_log:            # the log is committed at every phase gate, on its own
        redgreen.git(repo, "add", "--", r.a.incident_log)
        subprocess.run(["git", "commit", "-q", "-m", f"incident log: fix phase for {r.slug}"], cwd=repo,
                       capture_output=True)

    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, capture_output=True, text=True)
    tool = pr_tool(remote.stdout) if remote.returncode == 0 else None
    title = r.state["rootcause"]["title"]
    cmd = pr_command(tool, title, record, base_branch, branch) if tool else None
    if not r.a.open_pr:
        loop.log("not opening a PR — pass --open-pr to push and open a draft. To do it yourself:")
        print(f"git push -u origin {shlex.quote(branch)}")
        print(" ".join(shlex.quote(c) for c in cmd) if cmd else
              f"(no PR CLI for this remote — open a PR from `{branch}` into `{base_branch}`; body: {record})")
        return
    if remote.returncode:
        raise loop.HarnessError("--open-pr: this repository has no `origin` remote")
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=repo, check=True, capture_output=True)
    if not cmd:
        loop.log(f"pushed `{branch}`; no PR CLI for this host — open the PR by hand with {record} as its body")
        return
    out = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if out.returncode:
        raise loop.HarnessError(f"{tool} could not open the PR: {(out.stderr or out.stdout).strip()[:300]}")
    url = (out.stdout.strip().splitlines() or [""])[-1]
    r.state["ship"]["pr"] = url
    loop.log(f"draft PR opened: {url}")
    r.incident_log("action", f"draft PR opened: {url}")


STAGE_FN = {"discover": stage_discover, "triage": stage_triage, "rootcause": stage_rootcause, "red": stage_red,
            "implement": stage_implement, "review": stage_review, "repair": stage_repair, "ship": stage_ship}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--report", required=True, help="the bug report, or @file")
    ap.add_argument("--profile", choices=["hotfix", "incident"], default="hotfix")
    ap.add_argument("--slug", help="short name for the branch and the .workflow folder (default: from the report)")
    ap.add_argument("--test-cmd", help="override the discovered test command")
    ap.add_argument("--lint-cmd", action="append", help="override the discovered lint commands (repeatable)")
    ap.add_argument("--incident-log", help="incident profile: log entries into this incident log")
    ap.add_argument("--open-pr", action="store_true", help="push the branch and open a DRAFT PR — the only "
                                                          "outward action this harness takes, and only with this flag")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--delegate-model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    if not (pathlib.Path(a.repo) / ".git").exists():
        print(f"{a.repo} is not the root of a git work tree", file=sys.stderr)
        return EXIT_ERROR
    r = Run(a)
    loop.log(f"{r.profile} · {r.slug} · state in {r.dir.relative_to(r.repo)}")
    code = EXIT_OK
    try:
        for stage in STAGES:
            if stage in r.state["done"]:
                continue
            STAGE_FN[stage](r)
            r.done(stage)
    except NeedsInput as e:
        loop.log(f"needs input: {e}")
        code = EXIT_INPUT
    except Routed as e:
        loop.log(f"routed out: {e}")
        code = EXIT_ROUTED
    except Escalate as e:
        loop.log(f"leave the lane: {e}")
        code = EXIT_ESCALATED
    except loop.GateFailed as e:
        loop.log(f"stopped: {e}")
        code = EXIT_GATE
    except (loop.HarnessError, subprocess.CalledProcessError, redgreen.Usage) as e:
        loop.log(f"error: {e}")
        code = EXIT_ERROR
    finally:
        r.save()
        if r.ctx.cost:
            loop.log(f"spent ${r.ctx.cost:.2f} this run")
    return code


if __name__ == "__main__":
    sys.exit(main())
