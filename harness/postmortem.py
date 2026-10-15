#!/usr/bin/env python3
"""Turn a resolved incident's log into a blameless post-mortem, then make the follow-through stick.

    python3 harness/postmortem.py --repo . --log docs/incidents/2026-10-15-checkout.md [--docs docs/incident-x/ …]
    python3 harness/postmortem.py --repo . --log <log> --close                 # once every factor is owned
    python3 harness/postmortem.py --repo . --log <log> --close --create-items  # also open tracker items

Phase 4 of incident-fix is the one phase with fixed inputs and one document out, so it runs headless:

    check the log → widen the git range → timeline → post-mortem (claude -p) → lint → follow-through → [close]
    resolved?        14 days before        from the     the post-mortem skill,     blame,    every factor:
                     impact, 1 after       log, by       or the fallback template   prescrip- an owned follow-up
                     resolution            incident.py   when it isn't installed    tion, and  or an accepted risk
                                                                                    structure

What code enforces: the log is resolved and checks before anything is written; the record is linted
for blame (counterfactuals, "human error", git authors' names next to failure words) and for prescription,
and gets one correction round; follow-up owners and dates are never invented — the harness drafts the
outcomes and waits for you (exit 5) until each factor is recorded with `incident.py factor`; tracker items
are created only with --create-items, and the incident is closed only with --close.

Exit status: 0 complete · 1 error · 4 the record failed the lint after a correction · 5 needs your input.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fix  # noqa: E402
import incident as INC  # noqa: E402
import loop  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_LINT, EXIT_INPUT = 0, 1, 4, 5
WIDEN_BEFORE, WIDEN_AFTER = dt.timedelta(days=14), dt.timedelta(days=1)

S = {"type": "string"}
obj = loop._obj
PM_SCHEMA = obj({
    "markdown": S, "tier": {"type": "string", "enum": ["Lightweight", "Standard", "Deep"]},
    "factors": {"type": "array", "items": obj({"id": S, "category": S, "factor": S, "evidence": S, "confidence": S})},
    "open_questions": {"type": "array", "items": S},
})
FT_SCHEMA = obj({"proposals": {"type": "array", "items": obj({
    "factor": S, "kind": {"type": "string", "enum": ["follow-up", "accepted risk"]}, "outcome": S, "why": S})}})

# Blame leaks in through grammar (post-mortem/blameless-culture.md); prescription through modal verbs.
BLAME = [r"\bshould have\b", r"\bcould have\b", r"\bfailed to\b", r"\bdidn'?t (notice|catch|check|see)\b",
         r"\bhuman error\b", r"\bcareless(ly|ness)?\b", r"\bobviously\b", r"\bclearly\b", r"\bsimply\b",
         r"\bnegligen"]
PRESCRIBE = [r"\bwe (need|must|should|have) to\b", r"\bwe (must|should)\b", r"\bthe team (must|should|needs to)\b",
             r"\b(must|should) (add|implement|introduce|be (added|implemented|changed))\b", r"\baction items?\b",
             r"\bremediation plan\b"]
FAILURE_WORDS = r"(fail\w*|forg[eo]t\w*|miss\w*|broke|mistake\w*|error|caus\w*|overlook\w*|neglect\w*|blame\w*)"
REQUIRED_SECTIONS = [r"(?im)^#+\s*timeline", r"(?im)^#+\s*impact", r"(?im)^#+\s*contributing factors"]

PROMPT = """HARNESS-STAGE: postmortem · HARNESS-ITERATION: 1

Write the post-mortem for this **resolved** incident. Follow {method} exactly — it is the method, \
and its stopping rule is your finish line. The user is not available; produce the record.

Inputs, all already gathered — cite them, don't re-derive them:
- the incident log: `{log}` (UTC, clock-stamped, the spine of the timeline)
- the timeline exported from it, with time to detect / mitigate / resolve: `{timeline}`
- the git history from {since} to {until}, widened past the incident window on purpose: `{gitlog}`
{docs}
Rules this harness checks mechanically, so don't make it send the record back:
- **Blameless.** No "should have", "could have", "failed to", "didn't notice", "human error", \
"obviously", "clearly", "simply"; no person's name attached to a mistake — roles and system properties.
- **Describe, don't prescribe.** No "we need to", "we must", "the team should", no action items or \
remediation plan. Owners and follow-ups are a separate step after this record.
- **Sections:** Timeline, Impact, Contributing factors (plural, every category swept, "none found" \
recorded), What went well and where we got lucky, What was done, Open questions.
Quoting a source verbatim is fine inside a `>` blockquote; the lint skips quoted lines.

Return the whole record as `markdown`, its tier, every contributing factor (id, category, the factor as \
a property of the system, its evidence, its confidence), and the open questions.
"""

FT_PROMPT = """HARNESS-STAGE: followthrough · HARNESS-ITERATION: 1

The post-mortem is written: `{record}`. Now the **follow-through**, a separate step that comes after the \
record ({method}). For each contributing factor below, propose exactly one outcome: a **follow-up** \
stated as an observable property of the system (not an instruction to people), or an **accepted risk** \
with the reason it is acceptable. Don't name owners or dates — people agree to those, not this step. \
{detection}

Factors:
{factors}
"""


def read_log(path):
    log = INC.parse(path.read_text())
    errors, _ = INC.verify(log)
    errors = [e for e in errors if e[0] not in ("I09", "I10")]       # closing rules apply at close
    kinds = {e.kind for e in log.entries}
    if errors:
        raise loop.HarnessError("the incident log does not check:\n  " + "\n  ".join(INC.fmt(e) for e in errors))
    if "resolved" not in kinds:
        raise loop.HarnessError("the incident isn't resolved yet — a post-mortem reconstructs a resolved incident")
    return log


def window(log, since=None, until=None):
    times = {}
    for e in log.entries:
        times.setdefault(e.kind, e.at)
    start = min(t for k, t in times.items() if k in ("change", "impact-start", "detected"))
    end = times.get("resolved") or max(e.at for e in log.entries)
    return (dt.datetime.fromisoformat(since.replace("Z", "+00:00")) if since else start - WIDEN_BEFORE,
            dt.datetime.fromisoformat(until.replace("Z", "+00:00")) if until else end + WIDEN_AFTER)


def git_range(repo, since, until):
    fmt = "%H%x09%aI%x09%an%x09%s"
    r = subprocess.run(["git", "log", f"--since={since.isoformat()}", f"--until={until.isoformat()}",
                        f"--format={fmt}", "--stat", "--no-merges"], cwd=repo, capture_output=True, text=True)
    authors = set(re.findall(r"^[0-9a-f]{40}\t[^\t]+\t([^\t]+)\t", r.stdout, re.M))
    return r.stdout, authors


def lint(markdown, authors):
    """Problems a reviewer would send back. Quoted lines (> …) are sources, not the record's voice."""
    problems = []
    lines = [(i + 1, l) for i, l in enumerate(markdown.splitlines()) if not l.lstrip().startswith(">")]
    for i, l in lines:
        for pat in BLAME:
            if re.search(pat, l, re.I):
                problems.append(f"line {i}: blame — {re.search(pat, l, re.I).group(0)!r} in {l.strip()[:90]!r}")
        for pat in PRESCRIBE:
            if re.search(pat, l, re.I):
                problems.append(f"line {i}: prescription — {re.search(pat, l, re.I).group(0)!r} in {l.strip()[:90]!r}")
        for name in authors:
            first = name.split()[0]
            if len(first) > 2 and re.search(rf"\b{re.escape(first)}\b[^.]{{0,60}}\b{FAILURE_WORDS}", l, re.I):
                problems.append(f"line {i}: a person's name next to a failure — {l.strip()[:90]!r}")
    for pat in REQUIRED_SECTIONS:
        if not re.search(pat, markdown):
            problems.append(f"missing section: {pat.split('*')[-1]}")
    return problems


def draft_follow_through(path, log_path, proposals, logged):
    rows = []
    for p in proposals:
        done = any(p["factor"][:40].lower() in f["factor"].lower() or f["factor"][:40].lower() in p["factor"].lower()
                   for f in logged)
        if p["kind"] == "follow-up":
            cmd = (f'python3 harness/incident.py factor {log_path} "{p["factor"]}" --follow-up "{p["outcome"]}" '
                   '--owner <who agreed> --due <YYYY-MM-DD>')
        else:
            cmd = (f'python3 harness/incident.py factor {log_path} "{p["factor"]}" --accepted "{p["outcome"]}" '
                   '--by <who accepts it>')
        rows.append(f"- [{'x' if done else ' '}] **{p['factor']}** → {p['kind']}: {p['outcome']}\n"
                    f"  - why: {p['why']}\n  - record it: `{cmd}`")
    path.write_text("# Follow-through — draft\n\nProposed outcomes only. Owners, dates and acceptances are "
                    "people's decisions: record each with the command beside it, then re-run with --close.\n\n"
                    + "\n".join(rows) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--log", required=True, help="the incident log, relative to the repo")
    ap.add_argument("--docs", nargs="*", default=[], help="incident documents: reports, chat exports, PDFs")
    ap.add_argument("--since", help="override the start of the git range (ISO, UTC)")
    ap.add_argument("--until", help="override the end of the git range (ISO, UTC)")
    ap.add_argument("--out", help="where the record goes (default: next to the log, -postmortem.md)")
    ap.add_argument("--close", action="store_true", help="log `closed` once the record and follow-through are done")
    ap.add_argument("--create-items", action="store_true", help="open one tracker item per follow-up (needs --close)")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)

    repo = pathlib.Path(a.repo).resolve()
    log_path = repo / a.log
    out = repo / (a.out or a.log.replace(".md", "-postmortem.md"))
    work = repo / ".workflow" / f"postmortem-{log_path.stem}"
    run_dir = work / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = loop.Ctx(repo=repo, skills=pathlib.Path(a.skills).resolve(), test_cmd="", base="HEAD", cap=1,
                   model=a.model, delegate_model=None, concurrency=1, budget=a.budget_usd, timeout=a.timeout,
                   dry=False, run_dir=run_dir, claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))
    try:
        log = read_log(log_path)
        since, until = window(log, a.since, a.until)
        gitlog, authors = git_range(repo, since, until)
        (work / "git-range.txt").write_text(gitlog or "(no commits in range)\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            INC.main(["timeline", str(log_path)])
        (work / "timeline.md").write_text(buf.getvalue())
        loop.log(f"log resolved · git {since:%Y-%m-%d} → {until:%Y-%m-%d}: {gitlog.count(chr(9)) // 3} commit(s), "
                 f"{len(authors)} author(s)")

        if not out.exists():
            try:
                method = loop.skill_path(ctx, "post-mortem")
            except loop.HarnessError:
                method = loop.skill_path(ctx, "incident-fix").parent / "postmortem-fallback.md"
            docs = "".join(f"- an incident document: `{d}`\n" for d in a.docs)
            prompt = PROMPT.format(method=method, log=log_path, timeline=work / "timeline.md",
                                   gitlog=work / "git-range.txt", since=f"{since:%Y-%m-%d}",
                                   until=f"{until:%Y-%m-%d}", docs=docs)

            def validate(res):
                p = lint(res["markdown"], authors)
                if len(res["factors"]) < 2:
                    p.append("contributing factors must be plural — sweep every category")
                return p

            try:
                res = loop.claude_checked(ctx, "postmortem", prompt, PM_SCHEMA, loop.READ_TOOLS, validate)
            except loop.HarnessError as e:
                if "still malformed" not in str(e):
                    raise
                loop.log(f"the record failed the lint after a correction round:\n  {e}")
                return EXIT_LINT
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(res["markdown"].rstrip() + "\n")
            (work / "factors.json").write_text(json.dumps(res["factors"], indent=2))
            loop.log(f"post-mortem written: {out.relative_to(repo)} · {res['tier']} · {len(res['factors'])} factors · "
                     f"{len(res['open_questions'])} open question(s)")
        else:
            problems = lint(out.read_text(), authors)
            if problems:
                loop.log("the existing record fails the lint:\n  " + "\n  ".join(problems))
                return EXIT_LINT

        factors = json.loads((work / "factors.json").read_text()) if (work / "factors.json").exists() else []
        draft = work / "follow-through.md"
        if not draft.exists() and factors:
            human = INC.human_detected(log.fields.get("detected by", ""))
            res = loop.claude(ctx, "followthrough", FT_PROMPT.format(
                record=out, method=loop.skill_path(ctx, "incident-fix").parent / "follow-through.md",
                detection=("A person detected this incident, so one proposal must be the alert or monitoring "
                           "that would have caught it." if human else ""),
                factors="\n".join(f"- {f['id']} ({f['category']}): {f['factor']}" for f in factors)),
                FT_SCHEMA, loop.READ_TOOLS)
            (work / "proposals.json").write_text(json.dumps(res["proposals"], indent=2))
        proposals = json.loads((work / "proposals.json").read_text()) if (work / "proposals.json").exists() else []
        log = INC.parse(log_path.read_text())
        draft_follow_through(draft, a.log, proposals, log.factors)
        missing = len(factors) - len(log.factors)
        if missing > 0:
            loop.log(f"follow-through: {missing} factor(s) still need an owner and a date, or an accepted risk — "
                     f"see {draft.relative_to(repo)}")
            return EXIT_INPUT
        loop.log("follow-through: every factor is owned or accepted")

        if not a.close:
            loop.log("record and follow-through complete — re-run with --close to close the incident")
            return EXIT_OK
        if a.create_items:
            create_items(repo, log)
        code = INC.main(["log", str(log_path), "closed", f"post-mortem at {out.relative_to(repo)}"])
        if code:
            return EXIT_INPUT
        loop.log("incident closed in the log; commit it with the post-mortem")
        return EXIT_OK
    except loop.HarnessError as e:
        loop.log(f"error: {e}")
        return EXIT_ERROR
    finally:
        if ctx.cost:
            loop.log(f"spent ${ctx.cost:.2f} this run")


def create_items(repo, log):
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo, capture_output=True, text=True)
    tool = fix.pr_tool(remote.stdout) if remote.returncode == 0 else None
    for f in [f for f in log.factors if f["outcome"] == "follow-up"]:
        title, body = f["detail"].split(" — ")[0].replace("follow-up: ", ""), f"{f['factor']}\n\n{f['detail']}"
        cmd = {"gh": ["gh", "issue", "create", "--title", title, "--body", body],
               "glab": ["glab", "issue", "create", "--title", title, "--description", body, "--yes"],
               "az": ["az", "boards", "work-item", "create", "--type", "Task", "--title", title,
                      "--description", body]}.get(tool)
        if not cmd:
            loop.log(f"no tracker CLI for this remote — create by hand: {title}")
            continue
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        loop.log(f"tracker item for {f['id']}: {(r.stdout.strip().splitlines() or [r.stderr.strip()])[-1]}")


if __name__ == "__main__":
    sys.exit(main())
