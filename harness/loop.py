#!/usr/bin/env python3
"""Drive the closing loop of the development pipeline.

    refactor-review → devils-advocate → tyr-verdict   (and on NO-GO: tdd → round again)

Each stage's judgment runs in a headless `claude -p` call. Everything the prose skills
used to ask the agent to police is done here instead: the fan-out, the read-only
teardown, the green-suite gates, the ledger writes, the iteration cap and the verdict
arithmetic. The ledger (.workflow/ledger.md) is the only state; kill the script at any
point and the next run resumes at the first stage the ledger doesn't show as done.

    python3 harness/loop.py --repo ../my-service --test-cmd ".venv/bin/python -m pytest -q"
    python3 harness/loop.py --repo ../my-service            # resume: base and test command are remembered
    python3 harness/loop.py --repo ../my-service --dry-run  # write the next stage's prompts, call nothing

Exit status: 0 GO · 1 harness error · 3 ESCALATED · 4 a green-suite gate failed.
Set HARNESS_CLAUDE to a different executable to stub the model out (see tests/).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses as dc
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger as L  # noqa: E402

EXIT_GO, EXIT_ERROR, EXIT_ESCALATED, EXIT_GATE = 0, 1, 3, 4

WRITE_TOOLS = "Read,Grep,Glob,Edit,Write,Bash"
READ_TOOLS = "Read,Grep,Glob"
HEAVY_DIRS = {".venv", "venv", "node_modules", ".tox", ".mypy_cache", ".pytest_cache"}
# No background shells, and no shell command longer than five minutes, inside any call.
# `claude -p` waits for its background tasks before it exits: in the first live run a
# verifier backgrounded a probe that blocked on stdin, and the whole verdict stage waited
# twelve minutes on a call that had spent thirteen seconds working — twice.
BASH_ENV = {"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
            "BASH_DEFAULT_TIMEOUT_MS": "120000", "BASH_MAX_TIMEOUT_MS": "300000"}

# The nine attack surfaces from devils-advocate, and how they merge on a small diff.
SURFACES = [
    "acceptance criteria", "test integrity", "listed edge cases",
    "unlisted unhappy paths", "error handling", "contracts & invariants",
    "security & permissions", "coupling & state leakage", "performance & scale",
]
SMALL_DIFF_GROUPS = [SURFACES[0:3], SURFACES[3:6], SURFACES[6:9]]
LARGE_DIFF_LINES = 400


class HarnessError(Exception):
    pass


class GateFailed(Exception):
    pass


# ------------------------------------------------------------------ schemas

def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props),
            "additionalProperties": False}


S = {"type": "string"}
SEV = {"type": "string", "enum": list(L.SEVERITIES)}

FINDING = _obj({
    "target": S, "claim": S, "evidence": S, "breaking_case": S,
    "confidence": {"type": "string", "enum": ["proven", "unproven"]},
    "settled_by": S, "severity_hint": SEV, "surface": S,
    "reopens": S, "reexamines": S,
}, ["target", "claim", "evidence", "confidence", "severity_hint"])

DELEGATE_SCHEMA = _obj({
    "findings": {"type": "array", "items": FINDING},
    "swept": {"type": "array", "items": _obj({"surface": S, "note": S})},
    "not_covered": {"type": "array", "items": _obj({"surface": S, "reason": S})},
})

CONSOLIDATE_SCHEMA = _obj({
    "findings": {"type": "array", "items": FINDING},
    "dropped": {"type": "array", "items": _obj({"summary": S, "reason": S})},
})

REFACTOR_SCHEMA = _obj({
    "calibration": S,
    "fixed": {"type": "array", "items": _obj({"smell": S, "technique": S, "severity": S})},
    "noted": {"type": "array", "items": _obj({"smell": S, "location": S, "reason": S, "promote_if": S})},
    "carried": {"type": "array", "items": _obj({
        "id": S, "action": {"type": "string", "enum": list(L.SMELL_ACTIONS)}, "reason": S})},
    "summary": S,
})

FIX_SCHEMA = _obj({
    "closed": {"type": "array", "items": _obj({"finding": S, "test": S})},
    "not_closed": {"type": "array", "items": _obj({"finding": S, "reason": S})},
    "brief_revised": {"type": "boolean"},
    "summary": S,
})

VERIFY_SCHEMA = _obj({
    "supports": {"type": "string", "enum": list(L.VERDICTS)},
    "attempted": S, "observed": S, "reason": S,
})

VERDICT_SCHEMA = _obj({
    "verdicts": {"type": "array", "items": _obj({
        "finding": S, "verdict": {"type": "string", "enum": list(L.VERDICTS)},
        "severity": SEV, "reason": S, "reopens_only_if": S, "settled_by": S,
    }, ["finding", "verdict", "reason"])},
    "slices": {"type": "array", "items": _obj({"finding": S, "severity": SEV, "behavior": S})},
    "carried_smells": S,
    "stated_verdict": {"type": "string", "enum": list(L.OUTCOMES)},
    "summary": S,
})


# ------------------------------------------------------------------ prompts

HEADER = """HARNESS-STAGE: {stage} · HARNESS-ITERATION: {n}

You are one step of an automated harness running the closing loop of a six-stage \
development workflow (iteration {n} of at most {cap}). The user is not available: do not \
ask questions — finish the job and return your structured result. The harness owns \
`.workflow/ledger.md`: read it when your skill says to, but never edit it; the harness \
records what you return. Skip your skill's handoff prompt — the harness runs the next stage.

"""

FIX_PROMPT = """Read the skill at `{skill}` and follow it in its **loop-back** role: execute \
the open remediation slices below red→green, one at a time, in the order given.

{slices}

The build plan is `.workflow/brief.md`; the feedback edge still applies — if a slice \
contradicts the brief, revise the brief in place and log it under Revisions. The test \
command is `{test_cmd}`, and the full suite must be green when you finish.

Return, for every slice you got to green, the finding id and the exact name of the test \
that verifies it. For any slice you could not close, return why.
"""

REFACTOR_PROMPT = """Read the skill at `{skill}` and follow it on the changes since `{base}` \
(`git diff {base}`, plus untracked files). The suite is green now (`{test_cmd}`) — keep it \
green through every step, running it between treatments.

Carried noted smells from earlier passes — re-examine each one and decide promote, leave \
or retire:
{carried}

The brief's **Out of scope** and **Deferred by design** sections are in `.workflow/brief.md`.

Return what you fixed, every smell you rated `noted` (each with the condition that would \
promote it), and one decision per carried smell.
"""

DELEGATE_PROMPT = """**Prior.** Assume the implementation is wrong, the tests are lying, and the \
feature does not do what it claims. Everything green is guilty until proven innocent. You are \
not here to be fair — you are here to find the failure everyone else missed. Over-report: a \
suspicion you cannot prove is still recorded, as unproven.

**Your target:** {surfaces}. Other delegates own the other surfaces — do not drift into them.

**What the change claims** (the build plan — these are the claims you are falsifying; a \
deliberately deferred decision is not a gap):

{brief}

**Already refuted — do not re-report** unless your evidence meets the reopen condition, in \
which case set `reopens` to that id:
{refuted}
{reexamine}
**The change.** The diff against `{base}` is in `{diff}`. Read it once, then read the source \
and tests it touches. Do not open `.workflow/ledger.md` or any transcript.

**No execution.** You do not run the suite, a single test, the app, or a database, and you do \
not mutate files to see what happens. If only execution can settle a claim, record it \
unproven and name the exact run in `settled_by` — that run is someone else's to make.

**Evidence rule.** Every finding carries evidence produced by reading: a code path that \
contradicts the claim; a test that survives a named mutation (show from the test body why its \
assertions would still hold); a constructed breaking case traced through the code (inputs → \
what the code yields vs what the claim says); or a missing branch. Describe code by behavior, \
not line number. The full method is in `{skill}` (Mandate, Attack surface, Evidence rule) — \
ignore its Subagents and Output sections; this harness does both.

**Budget:** about 25 tool calls. If you run out, list what you did not reach in `not_covered`.

**Return** findings and evidence, not file excerpts. For every surface you attacked and found \
nothing on, add a `swept` entry — silence reads the same as never looking.
"""

REEXAMINE = """
**Sent back for evidence** — tyr-verdict could not settle these. Gather the named evidence by \
reading, and report each as a finding with `reexamines` set to its id:
{items}
"""

CONSOLIDATE_PROMPT = """You are ranking a devils-advocate teardown. Below are the raw \
findings returned by {k} independent delegates, as JSON.

De-duplicate — two reports of the same defect become one, keeping the strongest evidence — \
then order the list most severe first. Do not soften, judge or drop findings: over-reporting \
is the teardown's job and cutting is the verdict's. Two exceptions:

- A finding that re-reports an already refuted finding (below) **without** evidence meeting \
its reopen condition is dropped — list it under `dropped` with the reason. One that does meet \
it keeps `reopens` set to that id.
- `reexamines` may only name an open INCONCLUSIVE: {inconclusive}. Clear it otherwise.

Return the findings' text as the delegates wrote it; do not rewrite evidence.

Already refuted:
{refuted}

Delegate findings:
{findings}
"""

VERIFY_PROMPT = """You are verifying **one** teardown finding. Your working directory is a \
scratch copy of the repository — edit, mutate and run anything you need **inside it**; it is \
thrown away afterwards. Never touch a path outside it.

{finding}

Attempt the reproduction: run the breaking case, apply the named mutation and run the test, \
or perform the run named under "would be settled by". The test command is `{test_cmd}`. \
Run every command non-interactively, with stdin from `/dev/null` — a probe that waits for \
input stalls every other finding's verdict behind it. \
Then report which verdict the evidence supports — CONFIRMED (it reproduces), REFUTED (it does \
not, and why), or INCONCLUSIVE (it cannot be settled here; say what would settle it). Report \
the attempt and its result, not an opinion.
"""

VERDICT_PROMPT = """Read the skill at `{skill}` and act as tyr-verdict. The ledger at \
`.workflow/ledger.md` is the loop's history; this iteration's findings are already in it.

**Adjudicate exactly these findings:** {ids}.
{inconclusive}
**Verification** — one delegate per finding, each run on a scratch copy:
{reports}

**Carried noted smells:** {smells}

**Loop state:** {state}

Return one verdict per finding: CONFIRMED with a severity and a remediation slice phrased \
as an observable behavior verifiable through the public interface; REFUTED with \
`reopens_only_if`; INCONCLUSIVE with `settled_by` (an INCONCLUSIVE goes back for evidence \
once — a second one escalates to the user). Order the slices blockers, majors, minors. \
The harness computes GO / NO-GO / ESCALATED from your verdicts by the ledger rules; state \
the verdict you reach anyway.
"""


# ------------------------------------------------------------------ plumbing

@dc.dataclass
class Ctx:
    repo: pathlib.Path
    skills: pathlib.Path
    test_cmd: str
    base: str
    cap: int
    model: str | None
    delegate_model: str | None
    concurrency: int
    budget: float | None
    timeout: int
    dry: bool
    run_dir: pathlib.Path
    claude_bin: str
    cost: float = 0.0
    lock: threading.Lock = dc.field(default_factory=threading.Lock)

    @property
    def ledger(self):
        return self.repo / ".workflow" / "ledger.md"

    @property
    def brief(self):
        return self.repo / ".workflow" / "brief.md"


def log(msg):
    print(f"[harness {dt.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def skill_path(ctx, name):
    for root in (ctx.skills, ctx.repo / ".claude" / "skills", ctx.repo / ".cursor" / "skills"):
        hits = sorted(root.glob(f"**/{name}/SKILL.md")) if root.is_dir() else []
        if hits:
            return hits[0]
    raise HarnessError(f"skill {name!r} not found under {ctx.skills} or the repo's skills folders")


def claude(ctx, label, prompt, schema, tools, *, model=None, cwd=None, write=False):
    """One headless call. Returns structured_output, or None in a dry run."""
    calls = ctx.run_dir / "calls"
    calls.mkdir(parents=True, exist_ok=True)
    (calls / f"{label}.prompt.md").write_text(prompt)
    cmd = [ctx.claude_bin, "-p", "--output-format", "json", "--no-session-persistence",
           "--json-schema", json.dumps(schema), "--tools", tools, "--allowedTools", tools,
           "--strict-mcp-config", "--setting-sources", "project", "--disable-slash-commands",
           "--add-dir", str(ctx.skills), "--add-dir", str(ctx.run_dir)]
    if write:
        cmd += ["--permission-mode", "acceptEdits"]
    if model or ctx.model:
        cmd += ["--model", model or ctx.model]
    if ctx.budget:
        cmd += ["--max-budget-usd", str(ctx.budget)]
    if ctx.dry:
        (calls / f"{label}.cmd.txt").write_text(" ".join(cmd[:4]) + " … (see prompt)\n")
        return None
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           cwd=cwd or ctx.repo, timeout=ctx.timeout, env={**os.environ, **BASH_ENV})
    except subprocess.TimeoutExpired:
        raise HarnessError(f"{label}: no answer within {ctx.timeout}s")
    (calls / f"{label}.out.json").write_text(r.stdout or r.stderr)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise HarnessError(f"{label}: unreadable output (exit {r.returncode}): {(r.stderr or r.stdout)[:300]}")
    with ctx.lock:
        ctx.cost += out.get("total_cost_usd") or 0
    if out.get("is_error") or out.get("structured_output") is None:
        raise HarnessError(f"{label}: {out.get('subtype')} — {str(out.get('result'))[:300]}")
    return out["structured_output"]


def claude_checked(ctx, label, prompt, schema, tools, validate, **kw):
    """Call, validate, and give the model one chance to correct a malformed answer."""
    out = claude(ctx, label, prompt, schema, tools, **kw)
    if out is None:
        return None
    problems = validate(out)
    if not problems:
        return out
    log(f"{label}: answer had {len(problems)} problem(s); asking once for a correction")
    retry = (prompt + "\n\nYour previous answer was:\n" + json.dumps(out, indent=2)
             + "\n\nIt had these problems — return the corrected, complete answer:\n- " + "\n- ".join(problems))
    out = claude(ctx, label + "-retry", retry, schema, tools, **kw)
    problems = validate(out)
    if problems:
        raise HarnessError(f"{label}: still malformed after a retry: {'; '.join(problems)}")
    return out


def fan_out(ctx, jobs):
    """jobs: [(key, fn)] → {key: result or Exception}. Waits for every job."""
    results = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, ctx.concurrency)) as pool:
        futs = {pool.submit(fn): key for key, fn in jobs}
        for fut in cf.as_completed(futs):
            try:
                results[futs[fut]] = fut.result()
            except Exception as e:  # a delegate that never returns is a fact to record, not a crash
                results[futs[fut]] = e
    return results


def sh(ctx, *args, check=True):
    r = subprocess.run(args, cwd=ctx.repo, capture_output=True, text=True)
    if check and r.returncode:
        raise HarnessError(f"{' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout


def run_tests(ctx, where=None):
    r = subprocess.run(ctx.test_cmd, shell=True, cwd=where or ctx.repo, capture_output=True,
                       text=True, timeout=ctx.timeout)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    return r.returncode == 0, tail[0][:200]


def gate(ctx, when):
    if ctx.dry:
        return
    ok, tail = run_tests(ctx)
    log(f"gate {when}: {'GREEN' if ok else 'RED'} — {tail}")
    if not ok:
        raise GateFailed(f"suite is red {when}: {tail}")


def diff_text(ctx):
    out = sh(ctx, "git", "diff", ctx.base, "--", ".", ":(exclude).workflow")
    for path in sh(ctx, "git", "ls-files", "--others", "--exclude-standard").splitlines():
        if path.startswith(".workflow/"):
            continue
        try:
            body = (ctx.repo / path).read_text()
        except (UnicodeDecodeError, OSError):
            continue
        out += f"\n--- /dev/null\n+++ b/{path}  (untracked)\n" + "".join(f"+{l}\n" for l in body.splitlines())
    return out


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


class LedgerGuard:
    """The harness is the ledger's only writer. Snapshot before a stage's agents run;
    restore if one of them wrote to it anyway; then append through ledger.render_*."""

    def __init__(self, ctx, stage):
        self.ctx, self.stage = ctx, stage

    def __enter__(self):
        self.before = self.ctx.ledger.read_text() if self.ctx.ledger.exists() else ""
        self.brief = digest(self.ctx.brief)
        return self

    def __exit__(self, *exc):
        now = self.ctx.ledger.read_text() if self.ctx.ledger.exists() else ""
        if now != self.before:
            log(f"{self.stage}: an agent edited the ledger — restored; the harness is its only writer")
            (self.ctx.run_dir / f"ledger-edit-by-{self.stage}.md").write_text(now)
            self.ctx.ledger.write_text(self.before)
        if self.stage != "fix" and digest(self.ctx.brief) != self.brief:
            log(f"warning: {self.stage} changed .workflow/brief.md — only tdd's feedback edge may revise it")
        return False


def append(ctx, n, *chunks):
    """Append to the ledger, opening iteration n if it isn't open yet, then re-check it all."""
    if ctx.dry:
        return
    before = ctx.ledger.read_text() if ctx.ledger.exists() else ""
    text = before
    if not text.strip():
        text = L.render_header(brief_title(ctx))
    led = L.parse(text)
    if not led.iterations or led.iterations[-1].n < n:
        text = text.rstrip("\n") + "\n" + L.render_iteration(n)
    text = text.rstrip("\n") + "\n" + "".join(chunks)
    ok, _ = L.append_only(before, text)
    assert ok, "harness bug: append rewrote earlier content"
    ctx.ledger.parent.mkdir(parents=True, exist_ok=True)
    ctx.ledger.write_text(text)


def brief_title(ctx):
    if ctx.brief.exists():
        m = re.search(r"^# Build Plan:\s*(.+)$", ctx.brief.read_text(), re.M)
        if m:
            return m.group(1).strip()
    return ctx.repo.name


def status(ctx):
    text = ctx.ledger.read_text() if ctx.ledger.exists() else ""
    return L.status(text, ctx.cap)


def bullet(items, fmt, empty="- none"):
    return "\n".join(fmt(i) for i in items) or empty


# ------------------------------------------------------------------ stages

def stage_fix(ctx, n, st):
    slices = st["open_slices"]
    log(f"iteration {n} · tdd on {len(slices)} remediation slice(s)")
    prompt = HEADER.format(stage="fix", n=n, cap=ctx.cap) + FIX_PROMPT.format(
        skill=skill_path(ctx, "tdd"), test_cmd=ctx.test_cmd,
        slices=bullet(slices, lambda s: f"- [{s['severity']}] {s['id']} — {s['behavior']}"))
    open_ids = {s["id"] for s in slices}

    def validate(out):
        return [f"{c['finding']} is not an open slice" for c in out["closed"] if c["finding"] not in open_ids]

    with LedgerGuard(ctx, "fix"):
        out = claude_checked(ctx, f"i{n}-fix", prompt, FIX_SCHEMA, WRITE_TOOLS, validate, write=True)
    if out is None:
        return
    gate(ctx, "after tdd")
    closed = []
    for c in out["closed"]:
        if test_exists(ctx, c["test"]):
            closed.append(c)
        else:
            log(f"  {c['finding']}: tdd named `{c['test']}`, which isn't in the repo — the slice stays open")
    for nc in out["not_closed"]:
        log(f"  {nc['finding']} not closed: {nc['reason']}")
    append(ctx, n, L.render_closed(closed))
    log(f"  closed {len(closed)}/{len(slices)}{' · brief revised' if out['brief_revised'] else ''}")


def test_exists(ctx, name):
    leaf = re.split(r"[:.\s/]+", name.strip("`() "))[-1]
    if not leaf:
        return False
    r = subprocess.run(["git", "grep", "-q", "--untracked", "-w", leaf, "--", ".", ":(exclude).workflow"],
                       cwd=ctx.repo)
    return r.returncode == 0


def stage_refactor(ctx, n, st):
    carried = st["carried_smells"]
    log(f"iteration {n} · refactor-review ({len(carried)} carried smell(s))")
    gate(ctx, "before refactor-review")
    prompt = HEADER.format(stage="refactor", n=n, cap=ctx.cap) + REFACTOR_PROMPT.format(
        skill=skill_path(ctx, "refactor-review"), base=ctx.base, test_cmd=ctx.test_cmd,
        carried=bullet(carried, lambda s: f"- **{s['id']}** {s['what']} (noted iteration {s['since']}) — "
                                          f"promote if: {s['promote_if']}", "- none (first pass)"))
    ids = {s["id"] for s in carried}

    def validate(out):
        return [f"carried smell {c['id']} does not exist" for c in out["carried"] if c["id"] not in ids]

    with LedgerGuard(ctx, "refactor"):
        out = claude_checked(ctx, f"i{n}-refactor", prompt, REFACTOR_SCHEMA, WRITE_TOOLS, validate, write=True)
    if out is None:
        return
    gate(ctx, "after refactor-review")
    actions = {c["id"]: c for c in out["carried"]}
    for sid in ids - set(actions):
        log(f"  {sid}: no decision returned — recorded as left, unexamined")
        actions[sid] = {"id": sid, "action": "left", "reason": "not re-examined by the stage (recorded by the harness)"}
    led = L.parse(ctx.ledger.read_text() if ctx.ledger.exists() else "")
    nid = int(led.next_id("N")[1:])
    noted = []
    for i, s in enumerate(out["noted"]):
        smell = re.sub(r"^\s*\*{0,2}N\d+\*{0,2}[\s:—-]*", "", s["smell"])   # the id is ours to assign
        noted.append({**s, "id": f"N{nid + i}", "smell": smell})
    append(ctx, n, L.render_smells(noted, [actions[k] for k in sorted(actions, key=lambda x: int(x[1:]))]))
    log(f"  {len(out['fixed'])} fixed, {len(noted)} noted, {len(actions)} carried decided")


def stage_teardown(ctx, n, st):
    diff = diff_text(ctx)
    diff_path = ctx.run_dir / f"diff-i{n}.patch"
    diff_path.write_text(diff)
    changed = sum(1 for l in diff.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    groups = [[s] for s in SURFACES] if changed > LARGE_DIFF_LINES else SMALL_DIFF_GROUPS
    reexam = st["inconclusive"]
    log(f"iteration {n} · devils-advocate: {len(groups)} read-only delegates over {changed} changed lines"
        + (f", {len(reexam)} sent back for evidence" if reexam else ""))

    brief = ctx.brief.read_text() if ctx.brief.exists() else (
        "(no build plan — derive the claims from the diff, and say that is what you did)")
    brief = re.split(r"^## Revisions", brief, flags=re.M)[0].strip()
    refuted = bullet(st["refuted"], lambda r: f"- {r['id']} — {r['claim']} · reopens only if: {r['reopens_only_if']}")
    skill = skill_path(ctx, "devils-advocate")

    def job(i, surfaces, extra=""):
        prompt = HEADER.format(stage="teardown-delegate", n=n, cap=ctx.cap) + DELEGATE_PROMPT.format(
            surfaces=", ".join(surfaces), brief=brief, refuted=refuted, reexamine=extra,
            base=ctx.base, diff=diff_path, skill=skill)
        return lambda: claude(ctx, f"i{n}-teardown-{i}", prompt, DELEGATE_SCHEMA, READ_TOOLS,
                              model=ctx.delegate_model)

    jobs = [(tuple(g), job(i + 1, g)) for i, g in enumerate(groups)]
    if reexam:
        items = bullet(reexam, lambda r: f"- {r['id']} — {r['claim']} · settled by: {r['settled_by']}")
        jobs.append((("re-examination",), job(len(jobs) + 1, ["the findings sent back for evidence"],
                                              REEXAMINE.format(items=items))))
    with LedgerGuard(ctx, "teardown"):
        results = fan_out(ctx, jobs)
        if ctx.dry:
            return
        raw, swept, unattacked = [], [], []
        for key, res in results.items():
            if isinstance(res, Exception):
                unattacked += [{"surface": s, "reason": f"delegate did not return ({res})"} for s in key]
                continue
            raw += res["findings"]
            swept += res["swept"]
            unattacked += [{"surface": c["surface"], "reason": c["reason"]} for c in res["not_covered"]]
        findings = consolidate(ctx, n, raw, st) if raw else []

    refuted_ids = {r["id"] for r in st["refuted"]}
    inconclusive_ids = {r["id"] for r in reexam}
    nid = int(L.parse(ctx.ledger.read_text() if ctx.ledger.exists() else "").next_id("F")[1:])
    numbered, reexamined = [], set()
    for f in findings:
        if f.get("reopens") and f["reopens"] not in refuted_ids:
            f["reopens"] = ""
        if f.get("reexamines") in inconclusive_ids and f["reexamines"] not in reexamined:
            reexamined.add(f["reexamines"])
            numbered.append({**f, "id": f["reexamines"]})
            continue
        f["reexamines"] = ""
        numbered.append({**f, "id": f"F{nid}"})
        nid += 1
    append(ctx, n, L.render_findings(numbered), L.render_surfaces(swept, unattacked))
    log(f"  {len(numbered)} finding(s), {len(swept)} surface(s) swept clean, {len(unattacked)} unattacked")


def consolidate(ctx, n, raw, st):
    prompt = HEADER.format(stage="consolidate", n=n, cap=ctx.cap) + CONSOLIDATE_PROMPT.format(
        k=len(raw), findings=json.dumps(raw, indent=2),
        refuted=bullet(st["refuted"], lambda r: f"- {r['id']} — {r['claim']} · reopens only if: {r['reopens_only_if']}"),
        inconclusive=", ".join(r["id"] for r in st["inconclusive"]) or "none")
    out = claude(ctx, f"i{n}-teardown-rank", prompt, CONSOLIDATE_SCHEMA, "")
    for d in out["dropped"]:
        log(f"  dropped: {d['summary']} — {d['reason']}")
    return out["findings"]


def stage_verdict(ctx, n, st):
    led = L.parse(ctx.ledger.read_text())
    it = led.iterations[-1]
    findings = {e.fid: e for e in it.sections.get("findings", [])}
    pending = list(findings) + [r["id"] for r in st["inconclusive"] if r["id"] not in findings]
    log(f"iteration {n} · tyr-verdict on {len(pending)} finding(s)")
    if not pending:
        append(ctx, n, L.render_verdicts([]), L.render_slices([]))
        return record_outcome(ctx, n, None)

    def fields_of(fid):
        if fid in findings:
            return findings[fid].fields
        for prior in reversed(led.iterations):
            for e in prior.sections.get("findings", []):
                if e.fid == fid:
                    return e.fields
        return {}

    def job(fid):
        text = f"**{fid}**\n" + "\n".join(f"- **{k}:** {v}" for k, v in fields_of(fid).items())
        prompt = HEADER.format(stage="verify", n=n, cap=ctx.cap) + VERIFY_PROMPT.format(
            finding=text, test_cmd=ctx.test_cmd)

        def run():
            scratch = scratch_copy(ctx)
            try:
                return claude(ctx, f"i{n}-verify-{fid}", prompt, VERIFY_SCHEMA, WRITE_TOOLS,
                              model=ctx.delegate_model, cwd=scratch, write=True)
            finally:
                shutil.rmtree(scratch.parent, ignore_errors=True)
        return run

    with LedgerGuard(ctx, "verdict"):
        reports = fan_out(ctx, [(fid, job(fid)) for fid in pending])
        report_text = "\n".join(
            f"- {fid}: verification incomplete ({r})" if isinstance(r, Exception) or r is None else
            f"- {fid}: supports **{r['supports']}** — attempted: {r['attempted']}; observed: {r['observed']}; {r['reason']}"
            for fid, r in sorted(reports.items(), key=lambda kv: int(kv[0][1:])))
        counts = {r["id"]: r["pass"] for r in st["inconclusive"]}
        state = (f"iteration {n} of {ctx.cap}; open slices before this pass: {len(st['open_slices'])}; "
                 f"already refuted: {', '.join(r['id'] for r in st['refuted']) or 'none'}")
        prompt = HEADER.format(stage="verdict", n=n, cap=ctx.cap) + VERDICT_PROMPT.format(
            skill=skill_path(ctx, "tyr-verdict"), ids=", ".join(pending), reports=report_text,
            inconclusive=("Already INCONCLUSIVE once (a second INCONCLUSIVE escalates): "
                          + ", ".join(counts) + "\n") if counts else "",
            smells=bullet(st["carried_smells"], lambda s: f"{s['id']} {s['what']}", "none"),
            state=state)

        def validate(out):
            p = []
            got = [v["finding"] for v in out["verdicts"]]
            for fid in pending:
                if got.count(fid) != 1:
                    p.append(f"{fid} needs exactly one verdict (got {got.count(fid)})")
            sliced = {s["finding"]: s for s in out["slices"]}
            for v in out["verdicts"]:
                if v["finding"] not in pending:
                    p.append(f"{v['finding']} was not yours to adjudicate")
                elif v["verdict"] == "CONFIRMED":
                    if not v.get("severity"):
                        p.append(f"{v['finding']} is CONFIRMED without a severity")
                    elif v["finding"] not in sliced:
                        p.append(f"{v['finding']} is CONFIRMED without a remediation slice")
                    elif sliced[v["finding"]]["severity"] != v["severity"]:
                        p.append(f"{v['finding']}'s slice severity differs from its verdict")
                elif v["verdict"] == "REFUTED" and not v.get("reopens_only_if"):
                    p.append(f"{v['finding']} is REFUTED without reopens_only_if")
                elif v["verdict"] == "INCONCLUSIVE" and not v.get("settled_by"):
                    p.append(f"{v['finding']} is INCONCLUSIVE without settled_by")
            return p

        out = claude_checked(ctx, f"i{n}-verdict", prompt, VERDICT_SCHEMA, READ_TOOLS, validate)
    if out is None:
        return
    confirmed = {v["finding"] for v in out["verdicts"] if v["verdict"] == "CONFIRMED"}
    order = {s: i for i, s in enumerate(L.SEVERITIES)}
    slices = sorted((s for s in out["slices"] if s["finding"] in confirmed), key=lambda s: order[s["severity"]])
    verdicts = []
    for v in sorted(out["verdicts"], key=lambda v: int(v["finding"][1:])):
        r = reports.get(v["finding"])
        extra = {"pass": counts.get(v["finding"], 0) + 1} if v["verdict"] == "INCONCLUSIVE" else {}
        if isinstance(r, dict):
            extra["verification"] = f"supports {r['supports']} — {r['observed']}"
        verdicts.append({**v, **extra})
    append(ctx, n, L.render_verdicts(verdicts), L.render_slices(slices))
    return record_outcome(ctx, n, out)


def record_outcome(ctx, n, out):
    rep = status(ctx)
    hard = [e for e in rep["errors"] if not e.startswith("E51")]   # the outcome line is what we're about to write
    if hard:
        raise HarnessError("ledger check failed before the verdict:\n  " + "\n  ".join(hard))
    led = L.parse(ctx.ledger.read_text())
    stv, _, _ = L.replay(led, ctx.cap)
    outcome, reason = L.judge(stv, n, ctx.cap)
    note = ""
    if out and out["stated_verdict"] != outcome:
        note = f"tyr-verdict stated {out['stated_verdict']}; the ledger rules compute {outcome}"
    if out and out.get("carried_smells"):
        reason += f". Carried smells: {out['carried_smells']}"
    append(ctx, n, L.render_outcome(outcome, reason, note))
    log(f"  verdict: {outcome} — {reason}" + (f" ({note})" if note else ""))


def scratch_copy(ctx):
    root = pathlib.Path(tempfile.mkdtemp(prefix="harness-verify-"))
    dest = root / ctx.repo.name

    def ignore(d, names):
        skip = {".workflow"} if pathlib.Path(d) == ctx.repo else set()
        return [x for x in names if x in skip or (pathlib.Path(d) == ctx.repo and x in HEAVY_DIRS)]

    shutil.copytree(ctx.repo, dest, symlinks=True, ignore=ignore)
    for heavy in HEAVY_DIRS:
        if (ctx.repo / heavy).exists():
            (dest / heavy).symlink_to(ctx.repo / heavy)
    return dest


STAGES = {"fix": stage_fix, "refactor": stage_refactor, "teardown": stage_teardown, "verdict": stage_verdict}


# ------------------------------------------------------------------ main

def resolve_base(repo, given):
    if given:
        return given
    for ref in ("main", "master", "origin/main", "origin/master"):
        r = subprocess.run(["git", "merge-base", "HEAD", ref], cwd=repo, capture_output=True, text=True)
        if r.returncode == 0:
            base = r.stdout.strip()
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
            return base if base != head else "HEAD"
    return "HEAD"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--repo", required=True, help="the repository under review (a git work tree)")
    ap.add_argument("--test-cmd", help="the full suite, run from the repo root (remembered after the first run)")
    ap.add_argument("--base", help="the ref the change is measured against (default: merge-base with main; remembered)")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"), help="where the SKILL.md folders live")
    ap.add_argument("--cap", type=int, default=L.CAP, help="maximum iterations (default 3)")
    ap.add_argument("--model", help="model for the stages that judge or write code")
    ap.add_argument("--delegate-model", help="model for teardown and verification delegates")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float, help="spend cap per claude call")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per claude call or suite run")
    ap.add_argument("--once", action="store_true", help="run one stage, then stop")
    ap.add_argument("--dry-run", action="store_true", help="write the next stage's prompts and stop")
    a = ap.parse_args(argv)

    repo = pathlib.Path(a.repo).resolve()
    if not (repo / ".git").exists():
        print(f"{repo} is not the root of a git work tree", file=sys.stderr)
        return EXIT_ERROR
    cfg_path = repo / ".workflow" / "harness.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    test_cmd = a.test_cmd or cfg.get("test_cmd")
    if not test_cmd:
        print("--test-cmd is required on the first run", file=sys.stderr)
        return EXIT_ERROR
    base = a.base or cfg.get("base") or resolve_base(repo, None)
    if not a.dry_run:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({"test_cmd": test_cmd, "base": base}, indent=2) + "\n")

    run_dir = repo / ".workflow" / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(repo=repo, skills=pathlib.Path(a.skills).resolve(), test_cmd=test_cmd, base=base, cap=a.cap,
              model=a.model, delegate_model=a.delegate_model, concurrency=a.concurrency,
              budget=a.budget_usd, timeout=a.timeout, dry=a.dry_run, run_dir=run_dir,
              claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))
    log(f"repo {repo} · base {base} · run artifacts in {run_dir.relative_to(repo)}")
    if not ctx.brief.exists():
        log("no .workflow/brief.md — the teardown will derive its claims from the diff")

    code = EXIT_ERROR
    try:
        while True:
            st = status(ctx)
            if st["errors"]:
                raise HarnessError("the ledger does not check:\n  " + "\n  ".join(st["errors"]))
            n, stage = st["iteration"], st["next_stage"]
            if stage == "done":
                log(f"GO — {st['computed']['reason']}")
                code = EXIT_GO
                break
            if stage == "escalated":
                log(f"ESCALATED — {st['computed']['reason']}")
                log("your call: accept the risk and waive (### Decisions), fix by hand, "
                    "or take it back to agent-brief / architect-deep-dive")
                code = EXIT_ESCALATED
                break
            if n > ctx.cap:
                raise HarnessError(f"iteration {n} would exceed the cap of {ctx.cap}")
            STAGES[stage](ctx, n, st)
            if ctx.dry:
                log(f"dry run: prompts for '{stage}' (iteration {n}) are in {(run_dir / 'calls').relative_to(repo)}")
                code = EXIT_GO
                break
            if a.once:
                code = EXIT_GO
                break
    except GateFailed as e:
        log(f"stopped: {e}")
        code = EXIT_GATE
    except HarnessError as e:
        log(f"error: {e}")
        code = EXIT_ERROR
    finally:
        if ctx.cost:
            log(f"spent ${ctx.cost:.2f} this run")
    return code


if __name__ == "__main__":
    sys.exit(main())
