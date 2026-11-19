#!/usr/bin/env python3
"""Run the development pipeline from a resolved design to a verdict.

    architect-deep-dive (you, in conversation) → .workflow/designs/<stamp>-<slug>.md
                                                      │
        agent-brief → acceptance-tests → tdd → refactor-review → devils-advocate → tyr-verdict
           brief.md     red, from the     green,   └──────────── loop.py, to GO or ESCALATED ───────────┘
                        outside           committed

    python3 harness/pipeline.py --repo . --design .workflow/designs/20261112-1105-cutoff.md --test-cmd "pytest -q"
    python3 harness/pipeline.py --repo .                       # resume: design, settings and progress are remembered
    python3 harness/pipeline.py --repo . --pause-at-brief      # stop once, after the brief, for your review
    python3 harness/pipeline.py --repo . --from-brief          # no design: start from an approved brief.md

Stage 1 stays a conversation: a design is decided with you, one question at a time, and a headless
call cannot ask you anything. Everything after it runs here, each stage a headless `claude -p` call
following its skill, each gated by code:

- the design must say `**Status:** resolved`; an unfinished design is not built on;
- the suite is green and the tree clean before anything starts, and the work happens on a branch;
- the brief stage may change nothing outside `.workflow/`, and the brief must have criteria;
- the acceptance tests must be red — and red on behavior, not on a load error — before any code;
- tdd is done when the suite *and* the acceptance tests are green, and gets told what is still red;
- every stage that leaves the tree green ends in a commit; `**Base:**` is recorded before the first;
- the closing loop is loop.py unchanged: its gates, its ledger, its three-iteration cap, its verdict.

Each design is its own file, so several can sit in one repo; --design picks one, and with a single
resolved design in .workflow/designs/ it is found without being named. State is
`.workflow/pipeline.json`; re-running resumes at the first stage not done. On GO the design is marked
`built` and the change's working files (brief, ledger, report, state) move to
`.workflow/archive/<design name>/`, so the shared paths are free for the next change and two
branches that each built something never meet in the same file when they merge.
Exit status: 0 GO · 1 error · 3 ESCALATED · 4 a gate failed · 5 needs you (no resolved design,
a brief that belongs to other work, or the pause you asked for).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger as L  # noqa: E402
import loop  # noqa: E402
import redgreen  # noqa: E402

EXIT_GO, EXIT_ERROR, EXIT_ESCALATED, EXIT_GATE, EXIT_INPUT = 0, 1, 3, 4, 5
STAGES = ("brief", "acceptance", "build", "loop")
APPROVED_BY_DESIGN = "approved — from the resolved design, by harness/pipeline.py (no separate review)"
APPROVED_BY_USER = "approved — reviewed at the pause, then re-run"


class NeedsInput(Exception):
    pass


# ------------------------------------------------------------------ schemas and prompts

S = {"type": "string"}
BRIEF_SCHEMA = loop._obj({"title": S, "criteria": {"type": "integer"},
                          "assumptions": {"type": "array", "items": S}, "summary": S})
ACCEPT_SCHEMA = loop._obj({"command": S, "tests": {"type": "integer"},
                           "not_testable": {"type": "array", "items": S}, "summary": S})
BUILD_SCHEMA = loop._obj({"criteria_done": {"type": "integer"}, "commits": {"type": "integer"},
                          "brief_revised": {"type": "boolean"},
                          "open_ship_items": {"type": "array", "items": S}, "summary": S})

HEADER = """HARNESS-STAGE: {stage} · HARNESS-ITERATION: 0

You are one stage of an automated harness running a seven-stage development workflow from a \
resolved design to a verdict. The user is not available: do not ask questions — where your skill \
says to ask or to wait for approval, make the narrowest reasonable assumption, record it, and \
finish the job. Return your structured result. Skip your skill's handoff prompt — the harness \
runs the next stage.

"""

BRIEF_PROMPT = """Read the skill at `{skill}` and follow it: write the build plan to \
`.workflow/brief.md`.

The design is resolved and on disk at `{design}` — it is your upstream, in full. Every decision \
in it is settled; do not reopen one. Where it leaves something the plan needs unanswered, choose \
the narrowest reading, write the plan on it, and return it under `assumptions`, one sentence each, \
so the user can see what was decided for them.

Leave `**Status:** draft — awaiting approval` exactly as the template has it: the harness sets \
the status. Change no file outside `.workflow/` — this stage writes a plan, not code.
"""

ACCEPT_PROMPT = """Read the skill at `{skill}` and follow it: write the acceptance tests for the \
build plan in `.workflow/brief.md`, and record them in the brief's **Acceptance tests** section \
with the command that runs only them.

The full suite is `{test_cmd}` and is green now. When you finish, every new acceptance test must \
fail, and fail on the missing behavior — not on an import, a missing name or a collection error. \
Do not implement anything beyond the declared-but-unimplemented interfaces your skill allows. \
Do not commit.
"""

BUILD_PROMPT = """Read the skill at `{skill}` and follow it as stage 4: build the plan in \
`.workflow/brief.md`, one red→green slice per criterion, in the order given.

The full suite is `{test_cmd}`.{acceptance} The brief's `**Base:**` is already recorded \
(`{base}`) and you are on the working branch `{branch}`: commit each green slice here as your \
skill's **Save points** section says — staged by name, one slice per commit, never a red tree. \
Do not push, and do not switch branches. Tick each criterion in the brief as your skill says, and \
tick the **Ship checklist** items this build delivers.
{again}"""

STILL_RED = """
**This is attempt {n}.** The previous attempt ended with the tree not green:

{tail}

Pick up from the code as it is — do not start over — and finish the criteria that are still unticked.
"""


# ------------------------------------------------------------------ the run

class Run:
    def __init__(self, a):
        self.a = a
        self.repo = pathlib.Path(a.repo).resolve()
        self.wf = self.repo / ".workflow"
        self.wf.mkdir(exist_ok=True)
        self.state_path = self.wf / "pipeline.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"done": []}
        given = a.design or self.state.get("design")
        self.design = (self.repo / given) if given else None       # else found in preflight
        run_dir = self.wf / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S-pipeline")
        run_dir.mkdir(parents=True, exist_ok=True)
        test_cmd = a.test_cmd or self.state.get("test_cmd") or ""
        self.ctx = loop.Ctx(
            repo=self.repo, skills=pathlib.Path(a.skills).resolve(), test_cmd=test_cmd,
            base=self.state.get("base", "HEAD"), cap=a.cap, model=a.model, delegate_model=a.delegate_model,
            concurrency=a.concurrency, budget=a.budget_usd, timeout=a.timeout, dry=a.dry_run, run_dir=run_dir,
            claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"), save_points=True)
        self.assumptions = self.state.get("assumptions", [])
        self.spent = 0.0

    def save(self):
        self.state["cost"] = round(self.state.get("cost", 0) + self.ctx.cost, 2)
        self.spent += self.ctx.cost
        self.ctx.cost = 0.0
        self.state_path.write_text(json.dumps(self.state, indent=2) + "\n")

    def done(self, stage):
        if stage not in self.state["done"]:
            self.state["done"].append(stage)
        self.save()

    def is_done(self, stage):
        return stage in self.state["done"]

    def call(self, stage, prompt, schema, name):
        return loop.claude(self.ctx, f"pl-{stage}", HEADER.format(stage=f"pl-{stage}") + prompt.format(
            skill=loop.skill_path(self.ctx, name), **self.fields), schema, loop.WRITE_TOOLS, write=True)

    fields: dict = {}


def git(repo, *args, check=True):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode:
        raise loop.HarnessError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def slug(text):
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:6]) or "change"


def find_design(r):
    """--design, else the one this run already started from, else the only resolved design in the folder."""
    if r.design is not None:
        return r.design
    found = sorted((r.wf / "designs").glob("*.md")) if (r.wf / "designs").is_dir() else []
    resolved = [d for d in found if (design_status(d) or "").startswith("resolved")]
    rel = lambda d: str(d.relative_to(r.repo))
    if len(resolved) == 1:
        return resolved[0]
    if len(resolved) > 1:
        raise NeedsInput("more than one resolved design is waiting — name the one to build with --design:\n  "
                         + "\n  ".join(rel(d) for d in resolved))
    waiting = [f"{rel(d)} ({design_status(d) or 'no status'})" for d in found]
    raise NeedsInput(
        "no resolved design in .workflow/designs/ — run architect-deep-dive first; it writes the design to "
        "its own file there and sets `**Status:** resolved` at its handoff (or start from a brief you already "
        "approved with --from-brief)" + (". Found: " + "; ".join(waiting) if waiting else ""))


def set_line(path, key, value, after=r"^\*\*Status:\*\*.*\n"):
    """Set a `**Key:** value` header line, adding it after the status line when it isn't there."""
    text = path.read_text()
    line = f"**{key}:** {value}"
    if re.search(rf"^\*\*{key}:\*\*.*$", text, re.M):
        text = re.sub(rf"^\*\*{key}:\*\*.*$", lambda m: line, text, count=1, flags=re.M)
    elif re.search(after, text, re.M):
        text = re.sub(after, lambda m: m.group(0) + line + "\n", text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n\n{line}\n"
    path.write_text(text)


def design_status(path):
    m = loop.STATUS_RE.search(path.read_text()) if path.exists() else None
    return m.group(1).strip().lower() if m else None


def set_status(brief, value):
    text = brief.read_text()
    if loop.STATUS_RE.search(text):
        text = loop.STATUS_RE.sub(f"**Status:** {value}", text, count=1)
    else:
        text = re.sub(r"^(# Build Plan:.*\n)", rf"\1\n**Status:** {value}\n", text, count=1, flags=re.M)
    brief.write_text(text)


def set_base(brief, sha):
    text = brief.read_text()
    line = f"**Base:** `{sha}`"
    if re.search(r"^\*\*Base:\*\*.*$", text, re.M):
        text = re.sub(r"^\*\*Base:\*\*.*$", line, text, count=1, flags=re.M)
    elif "## Revisions" in text:
        text = text.replace("## Revisions", f"{line}\n\n## Revisions", 1)
    else:
        text = text.rstrip("\n") + f"\n\n{line}\n"
    brief.write_text(text)


def criteria(brief):
    """(ticked, total) over the brief's Acceptance criteria section."""
    m = re.search(r"\*\*Acceptance criteria\*\*[^\n]*\n(.*?)(?=\n\s*\n\*\*|\n##|\Z)", brief.read_text(), re.S)
    items = re.findall(r"^\s*-\s*\[([ xX])\]", m.group(1), re.M) if m else []
    return sum(1 for i in items if i != " "), len(items)


def commit_rest(r, message):
    """Whatever a green stage left in the tree becomes one commit, so the loop starts from a clean one."""
    paths = loop.dirty(r.repo)
    if paths:
        git(r.repo, "add", "-A", "--", *paths)
        git(r.repo, "commit", "-q", "-m", message)
        loop.log(f"  save point: {git(r.repo, 'rev-parse', '--short', 'HEAD')} — {message}")


def changed_outside_workflow(repo, before):
    now = redgreen.snapshot(repo)
    out = redgreen.git(repo, "diff", "--name-only", before, now)
    return [p for p in out.splitlines() if p and not p.startswith(".workflow/")]


# ------------------------------------------------------------------ stages

def preflight(r):
    a, ctx = r.a, r.ctx
    if not (r.repo / ".git").exists():
        raise loop.HarnessError(f"{r.repo} is not the root of a git work tree")
    if not ctx.test_cmd:
        raise NeedsInput("--test-cmd is required on the first run: the command that runs the full suite")
    r.state["test_cmd"] = ctx.test_cmd
    if r.is_done("brief") or ctx.dry:
        return
    if a.from_brief:
        if not ctx.brief.exists():
            raise NeedsInput("--from-brief, but there is no .workflow/brief.md")
        r.design = None
    else:
        r.design = find_design(r)
        status = design_status(r.design)
        if status is None:
            raise NeedsInput(f"{r.design} is not a design file with a `**Status:**` line — architect-deep-dive "
                             "writes one under .workflow/designs/")
        if status.startswith("built"):
            raise NeedsInput(f"{r.design.relative_to(r.repo)} is already `{status}`")
        if not status.startswith("resolved"):
            raise NeedsInput(f"the design is `{status}`, not resolved — finish the architect-deep-dive "
                             "conversation; a design with open questions is not built on")
        r.state["design"] = str(r.design.relative_to(r.repo))
        if ctx.brief.exists() and not r.state.get("brief_started"):
            raise NeedsInput(
                "a .workflow/brief.md is already there and this pipeline did not write it. If it is this "
                "change's plan, re-run with --from-brief; otherwise finish or archive that change first "
                "(agent-brief moves a finished brief and its ledger to .workflow/archive/<slug>/)")
    if ctx.ledger.exists() and not r.state.get("brief_started") and not a.from_brief:
        raise NeedsInput("a .workflow/ledger.md from another change is still there — archive it with its "
                         "brief before starting a new one")
    left = loop.dirty(r.repo)
    if left:
        raise NeedsInput(f"the tree has uncommitted changes ({', '.join(left[:3])}{'…' if len(left) > 3 else ''}) — "
                         "commit or set them aside; the pipeline commits as it goes and must not sweep them in")
    ok, tail = loop.run_tests(ctx)
    loop.log(f"gate before the pipeline: {'GREEN' if ok else 'RED'} — {tail}")
    if not ok:
        raise loop.GateFailed(f"the suite is red before anything was built: {tail}")
    branch = loop.current_branch(r.repo)
    if not branch or branch in loop.DEFAULT_BRANCHES:
        title = loop.brief_title(ctx) if a.from_brief else (
            re.search(r"^# Design:\s*(.+)$", r.design.read_text(), re.M) or [None, "change"])[1]
        branch = a.branch or f"pipeline/{slug(title)}"
        git(r.repo, "switch", "-c", branch)
        loop.log(f"working branch: {branch} (the pipeline never commits to the default branch)")
    r.state.update(branch=branch, base=git(r.repo, "rev-parse", "HEAD"), brief_started=True)
    ctx.base = r.state["base"]
    r.save()


def stage_brief(r):
    ctx, a = r.ctx, r.a
    if not a.from_brief:
        if r.design is None:                                    # a dry run skips the preflight that finds it
            r.design = find_design(r)
        loop.log(f"stage 2 · agent-brief from {r.design.relative_to(r.repo)}")
        before = None if ctx.dry else redgreen.snapshot(r.repo)
        r.fields = {"design": r.design}
        out = r.call("brief", BRIEF_PROMPT, BRIEF_SCHEMA, "agent-brief")
        if out is None:
            return False
        strayed = changed_outside_workflow(r.repo, before)
        if strayed:
            raise loop.GateFailed(f"the brief stage changed files outside .workflow/ ({', '.join(strayed[:3])}) — "
                                  "it writes a plan, not code")
        if not ctx.brief.exists():
            raise loop.GateFailed("agent-brief returned without writing .workflow/brief.md")
        r.assumptions = r.state["assumptions"] = out["assumptions"]
        set_line(ctx.brief, "Design", f"`{r.design.relative_to(r.repo)}`")
    done, total = criteria(ctx.brief)
    if not total:
        raise loop.GateFailed("the brief has no acceptance criteria — there is nothing to build or to judge against")
    loop.log(f"  brief: “{loop.brief_title(ctx)}” · {total} criteria · {len(r.assumptions)} assumption(s)")
    for s in r.assumptions:
        loop.log(f"  assumed: {s}")
    if a.pause_at_brief and not r.state.get("paused"):
        r.state["paused"] = True
        r.save()
        raise NeedsInput("paused after the brief, as asked: read .workflow/brief.md, edit it if you want, "
                         "then re-run without --pause-at-brief to build it")
    status = loop.brief_status(ctx.brief) or ""
    if not status.lower().startswith("approved"):
        set_status(ctx.brief, APPROVED_BY_USER if r.state.get("paused") else APPROVED_BY_DESIGN)
    return True


def stage_acceptance(r):
    ctx = r.ctx
    if r.a.skip_acceptance:
        loop.log("stage 3 · acceptance-tests skipped (--skip-acceptance): tdd's own red tests are the proof")
        return True
    loop.log("stage 3 · acceptance-tests")
    r.fields = {"test_cmd": ctx.test_cmd}
    out = r.call("acceptance", ACCEPT_PROMPT, ACCEPT_SCHEMA, "acceptance-tests")
    if out is None:
        return False
    cmd = loop.acceptance_from_brief(ctx.brief)
    if not cmd:
        raise loop.GateFailed("acceptance-tests did not record a **Command:** in the brief's Acceptance tests "
                              "section — nothing downstream can run them")
    res = subprocess.run(cmd, shell=True, cwd=r.repo, capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, timeout=ctx.timeout)
    text = res.stdout + res.stderr
    tail = (text.strip().splitlines()[-1:] or [""])[0][:200]
    if res.returncode == 0:
        raise loop.GateFailed(f"the acceptance tests pass before anything is built (`{cmd}`: {tail}) — "
                              "a test that is green now proves nothing about the change")
    load = [ln.strip() for ln in text.splitlines() if redgreen.LOAD_ERROR_RE.search(ln)]
    if load:
        raise loop.GateFailed(f"the acceptance tests are red for the wrong reason — they fail to load, not on "
                              f"the behavior: {load[0][:160]}")
    r.state["acceptance_cmd"] = cmd
    loop.log(f"  {out['tests']} acceptance test(s), red on behavior — `{cmd}`: {tail}")
    for s in out["not_testable"]:
        loop.log(f"  not acceptance-testable: {s}")
    return True


def stage_build(r):
    ctx = r.ctx
    ctx.acceptance_cmd = r.state.get("acceptance_cmd")
    set_base(ctx.brief, r.state["base"])
    r.fields = {"test_cmd": ctx.test_cmd, "base": r.state["base"][:12], "branch": r.state["branch"],
                "acceptance": (f" The acceptance tests are `{ctx.acceptance_cmd}`: you are done when they pass, "
                               "and you never edit one to make it pass." if ctx.acceptance_cmd else ""),
                "again": ""}
    tail = ""
    for n in range(1, r.a.build_attempts + 1):
        loop.log(f"stage 4 · tdd (attempt {n} of {r.a.build_attempts})")
        if n > 1:
            r.fields["again"] = STILL_RED.format(n=n, tail=tail)
        out = loop.claude(ctx, f"pl-build-{n}", HEADER.format(stage="pl-build") + BUILD_PROMPT.format(
            skill=loop.skill_path(ctx, "tdd"), **r.fields), BUILD_SCHEMA, loop.WRITE_TOOLS, write=True)
        if out is None:
            return False
        try:
            loop.gate(ctx, "after tdd")
        except loop.GateFailed as e:
            tail = str(e)
            loop.log(f"  not green yet: {tail}")
            continue
        done, total = criteria(ctx.brief)
        loop.log(f"  green · {done}/{total} criteria ticked · {out['commits']} commit(s) by tdd")
        if done < total:
            loop.log(f"  warning: {total - done} criterion/criteria left unticked in the brief — the teardown "
                     "will read them as unbuilt")
        commit_rest(r, "tdd: what the slices left uncommitted")
        return True
    raise loop.GateFailed(f"tdd did not reach green in {r.a.build_attempts} attempt(s): {tail}")


def stage_loop(r):
    ctx = r.ctx
    ctx.acceptance_cmd = r.state.get("acceptance_cmd")
    cfg = {"test_cmd": ctx.test_cmd, "base": r.state["base"]}
    if ctx.acceptance_cmd:
        cfg["acceptance_cmd"] = ctx.acceptance_cmd
    (r.wf / "harness.json").write_text(json.dumps(cfg, indent=2) + "\n")   # so `loop.py --repo .` can resume by hand
    loop.log("stages 5–7 · the closing loop")
    code, st = loop.run_loop(ctx)
    r.state["verdict"] = {loop.EXIT_GO: "GO", loop.EXIT_ESCALATED: "ESCALATED"}.get(code, "?")
    r.state["reason"] = (st.get("computed") or {}).get("reason", "")
    return code


RUN = {"brief": stage_brief, "acceptance": stage_acceptance, "build": stage_build}


def report(r):
    ctx, st = r.ctx, r.state
    commits = git(r.repo, "log", "--format=- %h %s", f"{st['base']}..HEAD", check=False) or "- none"
    ship = loop.open_ship_items(ctx.brief)
    lines = [f"# Pipeline report — {loop.brief_title(ctx)}", "",
             f"**Verdict:** {st.get('verdict', '—')} — {st.get('reason', '')}",
             f"**Branch:** `{st.get('branch')}` · **Base:** `{st['base'][:12]}` · **Spent:** ${st.get('cost', 0):.2f}",
             "", "## Commits", commits, "",
             "## Decided for you (assumptions the brief was written on)",
             "\n".join(f"- {s}" for s in r.assumptions) or "- none", "",
             "## Open before this ships (the brief's Ship checklist)",
             "\n".join(f"- {s}" for s in ship) or "- none", "",
             "The plan is `.workflow/brief.md`, the loop's record `.workflow/ledger.md`. Nothing was pushed.", ""]
    (r.wf / "pipeline-report.md").write_text("\n".join(lines))
    loop.log(f"report: .workflow/pipeline-report.md · {st.get('verdict', '—')}")


def archive(r):
    """On GO the change is finished: its working files leave the shared paths for a folder named after
    the design, and the design says it was built. The next change — here or on a branch that will merge
    with this one — starts from empty paths and never meets this one's brief or ledger."""
    name = r.design.stem if r.design else dt.datetime.now().strftime("%Y%m%d-%H%M-") + slug(loop.brief_title(r.ctx))
    dest = r.wf / "archive" / name
    dest.mkdir(parents=True, exist_ok=True)
    r.save()
    for f in ("brief.md", "ledger.md", "pipeline-report.md", "pipeline.json", "harness.json"):
        if (r.wf / f).exists():
            (r.wf / f).replace(dest / f)
    r.state_path = dest / "pipeline.json"
    rel = dest.relative_to(r.repo)
    if r.design:
        set_line(r.design, "Status", f"built — branch `{r.state.get('branch')}`, record in `{rel}/`")
    loop.log(f"archived: the brief, ledger and report are in {rel}/ — read {rel}/pipeline-report.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--repo", required=True, help="the repository to build in (a git work tree)")
    ap.add_argument("--test-cmd", help="the full suite, run from the repo root (remembered)")
    ap.add_argument("--design", help="the design file to build, e.g. .workflow/designs/20261112-1105-cutoff.md "
                                     "(default: the only resolved one in .workflow/designs/; remembered)")
    ap.add_argument("--from-brief", action="store_true",
                    help="skip stage 2: build the .workflow/brief.md that is already there")
    ap.add_argument("--pause-at-brief", action="store_true",
                    help="stop once after the brief is written, so you can review it before anything is built")
    ap.add_argument("--skip-acceptance", action="store_true", help="skip stage 3 (the Trivial tier)")
    ap.add_argument("--branch", help="working branch to create when started on the default branch")
    ap.add_argument("--build-attempts", type=int, default=2, help="tdd calls before giving up on green (default 2)")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"), help="where the SKILL.md folders live")
    ap.add_argument("--cap", type=int, default=L.CAP, help="maximum closing-loop iterations (default 3)")
    ap.add_argument("--model", help="model for the stages that judge or write code")
    ap.add_argument("--delegate-model", help="model for teardown and verification delegates")
    ap.add_argument("--concurrency", type=int, default=0,
                    help="parallel delegate calls; 0 (the default) is no limit")
    ap.add_argument("--budget-usd", type=float, help="spend cap per claude call")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds per claude call or suite run")
    ap.add_argument("--dry-run", action="store_true", help="write the next stage's prompt and stop")
    a = ap.parse_args(argv)

    r = Run(a)
    code = EXIT_ERROR
    try:
        preflight(r)
        for stage in STAGES[:3]:
            if r.is_done(stage):
                continue
            if not RUN[stage](r):
                loop.log(f"dry run: the prompt for '{stage}' is in {r.ctx.run_dir.relative_to(r.repo) / 'calls'}")
                return EXIT_GO
            r.done(stage)
        code = stage_loop(r)
        r.done("loop")
        report(r)
        if code == EXIT_GO:
            archive(r)
        if code == EXIT_ESCALATED:
            loop.log("your call: accept the risk and waive (### Decisions in the ledger), fix by hand, or take it "
                     "back to the design — the last `### Verdict` in .workflow/ledger.md says what is open")
    except NeedsInput as e:
        loop.log(f"needs you: {e}")
        code = EXIT_INPUT
    except loop.GateFailed as e:
        loop.log(f"stopped: {e}")
        code = EXIT_GATE
    except loop.HarnessError as e:
        loop.log(f"error: {e}")
        code = EXIT_ERROR
    finally:
        r.save()
        if r.spent:
            loop.log(f"spent ${r.spent:.2f} this run, ${r.state.get('cost', 0):.2f} in all")
    return code


if __name__ == "__main__":
    sys.exit(main())
