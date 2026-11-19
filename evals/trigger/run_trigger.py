#!/usr/bin/env python3
"""Triggering eval: does a skill's description make an agent pick it up when
it should, and leave it alone when it should not?

Usage: python3 evals/trigger/run_trigger.py [--dry-run] [--model MODEL] [--reps 1]
           [--split train|heldout|all] [--skills a,b] [--cases id,id]
           [--max-turns 3] [--max-budget-usd 0.25] [--concurrency 4]
           [--timeout 180] [--out DIR]

Every skill in this repo is staged in a throwaway directory outside any git
repo (<tmp>/skills-home/.claude/skills/<name>/), and each case in cases.json is
sent to one headless `claude -p` whose working directory is an empty folder
beside it (<tmp>/work/), with the skills folder attached by --add-dir so a
search of the working directory does not land in the skill files.
`--setting-sources project` keeps the user's own skills, plugins and CLAUDE.md
out; `--strict-mcp-config` keeps their MCP servers out. The prompt is the
case's text and nothing else: no skill is named.

The run is watched through `--output-format stream-json` and stopped at the
first skill it picks up (a Skill tool call, or a Read of a staged SKILL.md), so
it pays for the choice and not for the work. A run that picks none ends on its
own or at --max-turns. Only the Skill tool and read-only file tools are on.

Written to --out (default <skills-workspace>/trigger/<stamp>/):
  results.jsonl   one line per run: case, split, expected, picked, outcome
  transcripts/    the stream-json of every run
  summary.json    rates and the confusion table, train and held-out apart
  summary.md      the same, readable
"""
import argparse
import collections
import concurrent.futures as cf
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SKILLS = REPO_ROOT / "skills"
CASES = HERE / "cases.json"

NONE = "(none)"
READ_ONLY_TOOLS = "Skill,Read,Glob,Grep"
STAGE_IGNORE = ("__pycache__", "*.pyc", ".DS_Store")

# Rough cost of one run in USD, measured on this repo's 43 staged skills with
# claude 2.1.295 (see README.md "Cost"). Nearly all of it is the system prompt
# and skill listing, written to the prompt cache once and read by later runs,
# so a batch costs less per run than a single case. Models not listed fall back
# to the dearest figure.
EST_USD_PER_RUN = {"haiku": 0.01, "sonnet": 0.05, "opus": 0.10, "fable": 0.20}


# ------------------------------------------------------------------ cases

def load_cases(path=CASES):
    doc = json.loads(pathlib.Path(path).read_text())
    cases = doc["cases"]
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        sys.exit("cases.json: duplicate case ids")
    for c in cases:
        if c["split"] not in ("train", "heldout"):
            sys.exit(f"cases.json: {c['id']}: split must be train or heldout")
        if c["should_trigger"] != (c["expected"] == c["skill"]):
            sys.exit(f"cases.json: {c['id']}: should_trigger and expected disagree")
    return cases


def select(cases, split="all", skills=None, ids=None):
    out = [c for c in cases
           if (split == "all" or c["split"] == split)
           and (not skills or c["skill"] in skills)
           and (not ids or c["id"] in ids)]
    return out


# ---------------------------------------------------------------- staging

def repo_skills():
    """{name: folder} for every skill in the repo."""
    return {p.parent.name: p.parent for p in sorted(SKILLS.glob("*/*/SKILL.md"))}


def description_hash(skill_md):
    """Hash of the frontmatter description: the only text a trigger rate is
    attributable to, so a summary can say which wording it measured."""
    m = re.search(r"^description:[ \t]*(.*)$", pathlib.Path(skill_md).read_text(), re.M)
    return hashlib.sha256((m.group(1) if m else "").encode()).hexdigest()[:12]


def stage(dest):
    """Build dest/skills-home/.claude/skills/<name>/ for every skill and an
    empty dest/work/. Returns (work, skills_home, names)."""
    dest = pathlib.Path(dest)
    home, work = dest / "skills-home", dest / "work"
    root = home / ".claude" / "skills"
    root.mkdir(parents=True)
    work.mkdir()
    names = []
    for name, folder in repo_skills().items():
        shutil.copytree(folder, root / name, ignore=shutil.ignore_patterns(*STAGE_IGNORE))
        names.append(name)
    return work, home, names


# ------------------------------------------------------------- transcript

SKILL_MD = re.compile(r"\.claude/skills/([^/]+)/SKILL\.md$")


def parse_events(lines):
    """stream-json lines → events; lines that are not JSON objects are dropped
    (a killed run can end mid-line)."""
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict):
            events.append(e)
    return events


def listed_skills(events):
    """The skills the run was offered, from the init event; None if it never started."""
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            return list(e.get("skills") or [])
    return None


def first_skill(events):
    """The first skill the main agent picked up, and how.

    Returns {"skill": name or None, "via": "Skill" | "Read" | None, "turn": n},
    turn being the assistant message it happened in (or how many there were).
    A Skill tool call names it in input.skill (a plugin skill as plugin:name;
    the plugin prefix is dropped). A Read of a staged SKILL.md counts too: an
    agent that opens the file has chosen the skill. Subagent messages
    (parent_tool_use_id set) are ignored.
    """
    turn, seen = 0, set()
    for e in events:
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        mid = (e.get("message") or {}).get("id")
        if mid is None or mid not in seen:      # one event per content block
            turn += 1
            seen.add(mid)
        for block in (e.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            inp = block.get("input") or {}
            if block.get("name") == "Skill" and inp.get("skill"):
                return {"skill": str(inp["skill"]).lstrip("/").split(":")[-1], "via": "Skill", "turn": turn}
            if block.get("name") == "Read":
                m = SKILL_MD.search(str(inp.get("file_path") or ""))
                if m:
                    return {"skill": m.group(1), "via": "Read", "turn": turn}
    return {"skill": None, "via": None, "turn": turn}


def usage_of(events):
    """Tokens billed, summed over distinct assistant messages (stream-json
    repeats a message once per content block), and the cost if the run got as
    far as its result event."""
    seen, tot = set(), collections.Counter()
    cost = None
    for e in events:
        if e.get("type") == "assistant":
            msg = e.get("message") or {}
            if msg.get("id") in seen:
                continue
            seen.add(msg.get("id"))
            for k, v in (msg.get("usage") or {}).items():
                if isinstance(v, int):
                    tot[k] += v
        elif e.get("type") == "result":
            cost = e.get("total_cost_usd")
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    return {k: tot[k] for k in keys}, cost


# ---------------------------------------------------------------- outcome

def outcome(case, picked):
    """One run's verdict. `picked` is a skill name or None.

    should-trigger:  hit (picked the skill) / miss
    should-not:      false_trigger (picked the skill under test) / quiet;
                     `expected_ok` says whether it picked what it should have
                     (the neighbour, or nothing).
    """
    if case["should_trigger"]:
        kind = "hit" if picked == case["skill"] else "miss"
    else:
        kind = "false_trigger" if picked == case["skill"] else "quiet"
    return {"outcome": kind, "expected_ok": picked == case["expected"]}


def rate(n, d):
    return None if not d else round(n / d, 3)


def summarize(results):
    """Rates per split and per skill, and expected → picked counts per split.
    Runs that errored are counted and left out of every rate."""
    out = {}
    for split in ("train", "heldout"):
        rs = [r for r in results if r["split"] == split]
        ok = [r for r in rs if r["status"] == "ok"]
        should = [r for r in ok if r["should_trigger"]]
        shouldnt = [r for r in ok if not r["should_trigger"]]
        per_skill = {}
        for skill in sorted({r["skill"] for r in ok}):
            s = [r for r in should if r["skill"] == skill]
            n = [r for r in shouldnt if r["skill"] == skill]
            per_skill[skill] = {
                "should": len(s), "hits": sum(r["outcome"] == "hit" for r in s),
                "should_not": len(n), "false_triggers": sum(r["outcome"] == "false_trigger" for r in n)}
        confusion = collections.defaultdict(collections.Counter)
        for r in ok:
            confusion[r["expected"] or NONE][r["picked"] or NONE] += 1
        hits = sum(r["outcome"] == "hit" for r in should)
        false = sum(r["outcome"] == "false_trigger" for r in shouldnt)
        out[split] = {
            "runs": len(rs), "errors": len(rs) - len(ok),
            "should": len(should), "hits": hits, "trigger_rate": rate(hits, len(should)),
            "should_not": len(shouldnt), "false_triggers": false,
            "false_trigger_rate": rate(false, len(shouldnt)),
            "expected_ok": sum(r["expected_ok"] for r in ok),
            "expected_ok_rate": rate(sum(r["expected_ok"] for r in ok), len(ok)),
            "per_skill": per_skill,
            "confusion": {e: dict(sorted(p.items())) for e, p in sorted(confusion.items())}}
    return out


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def render(summary, meta):
    L = ["# Trigger eval", "",
         f"model `{meta.get('model') or 'CLI default'}` · reps {meta.get('reps')} · "
         f"{meta.get('claude_version', '')} · {meta.get('started', '')}", ""]
    if meta.get("cost_usd") is not None:
        L += [f"Cost reported by finished runs: ${meta['cost_usd']:.2f} "
              f"({meta.get('stopped_early', 0)} runs were stopped at the skill choice and report tokens only).", ""]
    L += ["| split | trigger rate (should) | false-trigger rate (should not) | picked what was expected | errors |",
          "|---|---|---|---|---|"]
    for split, s in summary.items():
        L.append(f"| {split} | {s['hits']}/{s['should']} ({pct(s['trigger_rate'])}) "
                 f"| {s['false_triggers']}/{s['should_not']} ({pct(s['false_trigger_rate'])}) "
                 f"| {s['expected_ok']}/{s['runs'] - s['errors']} ({pct(s['expected_ok_rate'])}) | {s['errors']} |")
    for split, s in summary.items():
        if not s["per_skill"]:
            continue
        L += ["", f"## {split}: per skill", "", "| skill | triggered when it should | triggered when it should not |",
              "|---|---|---|"]
        for skill, p in s["per_skill"].items():
            L.append(f"| {skill} | {p['hits']}/{p['should']} | {p['false_triggers']}/{p['should_not']} |")
        L += ["", f"## {split}: expected → picked", "",
              "Rows off the diagonal are the confusions: which skill was picked first instead of the expected one.",
              "", "| expected | picked first | runs |", "|---|---|---|"]
        for exp, picks in s["confusion"].items():
            for picked, n in picks.items():
                L.append(f"| {exp} | {picked}{'' if picked == exp else ' ✗'} | {n} |")
    return "\n".join(L) + "\n"


# -------------------------------------------------------------------- run

def claude_cmd(prompt, model, max_turns, budget, skills_home="<skills-home>"):
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence",
           "--tools", READ_ONLY_TOOLS, "--permission-mode", "bypassPermissions",
           "--add-dir", str(skills_home),
           "--max-turns", str(max_turns), "--max-budget-usd", str(budget)]
    if model:
        cmd += ["--model", model]
    return cmd + ["--", prompt]


def run_case(case, rep, work, skills_home, transcripts, args):
    """One headless run, stopped as soon as a skill is picked."""
    lines, stopped_early = [], False
    p = subprocess.Popen(claude_cmd(case["prompt"], args.model, args.max_turns, args.max_budget_usd,
                                    skills_home),
                         cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    timer = threading.Timer(args.timeout, p.kill)
    timer.start()
    try:
        for line in p.stdout:
            lines.append(line)
            if '"tool_use"' in line and first_skill(parse_events([line]))["skill"]:
                stopped_early = True
                p.terminate()
                break
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
        stderr = p.stderr.read()
    finally:
        timed_out = not timer.is_alive() and not stopped_early
        timer.cancel()
    name = f"{case['id']}-rep{rep}.jsonl"
    (transcripts / name).write_text("".join(lines))
    events = parse_events(lines)
    pick = first_skill(events)
    usage, cost = usage_of(events)
    rec = {"id": case["id"], "rep": rep, "skill": case["skill"], "split": case["split"],
           "should_trigger": case["should_trigger"], "expected": case["expected"],
           "picked": pick["skill"], "via": pick["via"], "turn": pick["turn"],
           "stopped_early": stopped_early, "usage": usage, "cost_usd": cost, "transcript": name}
    if listed_skills(events) is None or (timed_out and not pick["skill"]) or not pick["turn"]:
        rec.update(status="error", outcome=None, expected_ok=False,
                   error=("timed out" if timed_out else (stderr.strip()[-300:] or "no assistant message")))
    else:
        rec.update(status="ok", **outcome(case, pick["skill"]))
    return rec, events


def default_out():
    """Beside the main checkout, where the other eval runs live (outside git)."""
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return pathlib.Path(common).parent.parent / "skills-workspace" / "trigger" / stamp


def estimate(n_runs, model, budget):
    per = EST_USD_PER_RUN.get(next((k for k in EST_USD_PER_RUN if k in (model or "")), ""),
                              max(EST_USD_PER_RUN.values()))
    return per, n_runs * per, n_runs * budget


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print the plan and cost estimate; touch nothing")
    ap.add_argument("--model", help="passed to claude --model (default: the CLI's own default)")
    ap.add_argument("--reps", type=int, default=1, help="runs per case (default 1)")
    ap.add_argument("--split", choices=("train", "heldout", "all"), default="all")
    ap.add_argument("--skills", help="comma-separated skills under test")
    ap.add_argument("--cases", help="comma-separated case ids")
    ap.add_argument("--max-turns", type=int, default=3,
                    help="turns a run gets to pick a skill before it is cut off (default 3)")
    ap.add_argument("--max-budget-usd", type=float, default=0.25, help="hard cap per run (default 0.25)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=180, help="seconds per run")
    ap.add_argument("--out", type=pathlib.Path, help="results folder")
    args = ap.parse_args(argv)

    split = lambda s: set(filter(None, (s or "").split(",")))
    cases = select(load_cases(), args.split, split(args.skills), split(args.cases))
    if not cases:
        sys.exit("no cases selected")
    staged = repo_skills()
    named = {c["skill"] for c in cases} | {c["expected"] for c in cases if c["expected"]}
    unknown = sorted(named - set(staged))
    if unknown:
        sys.exit(f"cases name skills this repo does not have: {', '.join(unknown)}")
    n_runs = len(cases) * args.reps
    per, est, cap = estimate(n_runs, args.model, args.max_budget_usd)

    print(f"{len(cases)} cases × {args.reps} rep(s) = {n_runs} runs · model {args.model or 'CLI default'} · "
          f"{len(staged)} skills staged")
    for sp in ("train", "heldout"):
        cs = [c for c in cases if c["split"] == sp]
        print(f"  {sp:8} {len(cs):3} cases: {sum(c['should_trigger'] for c in cs)} should trigger, "
              f"{sum(not c['should_trigger'] for c in cs)} should not")
    print(f"estimated cost ≈ ${est:.2f} (${per:.2f}/run, rough); hard ceiling ${cap:.2f} "
          f"({n_runs} × --max-budget-usd {args.max_budget_usd})")
    if args.dry_run:
        for c in cases:
            print(f"  {c['id']:22} {c['split']:8} expect {c['expected'] or NONE}")
        print("command per run (cwd = an empty folder beside the staged skills):")
        print("  " + " ".join(claude_cmd("<prompt>", args.model, args.max_turns, args.max_budget_usd)))
        print("dry run: nothing staged, nothing run")
        return 0

    if not shutil.which("claude"):
        sys.exit("claude CLI not on PATH")
    out = args.out or default_out()
    transcripts = out / "transcripts"
    transcripts.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    meta = {"model": args.model, "reps": args.reps, "max_turns": args.max_turns, "claude_version": version,
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "description_hashes": {s: description_hash(staged[s] / "SKILL.md")
                                   for s in sorted({c["skill"] for c in cases})}}
    results, offered = [], None
    with tempfile.TemporaryDirectory(prefix="trigger-eval-") as tmp:
        work, skills_home, _ = stage(tmp)
        jobs = [(c, r) for c in cases for r in range(1, args.reps + 1)]
        with cf.ThreadPoolExecutor(args.concurrency) as pool:
            futs = [pool.submit(run_case, c, r, work, skills_home, transcripts, args) for c, r in jobs]
            for f in cf.as_completed(futs):
                rec, events = f.result()
                offered = offered or listed_skills(events)
                results.append(rec)
                print(f"  {rec['id']:22} rep{rec['rep']} {rec['split']:8} expected {rec['expected'] or NONE:14} "
                      f"picked {rec['picked'] or NONE:14} {rec['outcome'] or 'ERROR: ' + rec.get('error', '')}",
                      flush=True)
    results.sort(key=lambda r: (r["id"], r["rep"]))
    (out / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results))

    # What the runs were offered: every staged skill must be there, and anything
    # else is recorded so a leak from the user's own setup is visible.
    offered = offered or []
    meta["skills_missing"] = sorted(set(staged) - set(offered))
    meta["skills_not_from_repo"] = sorted(set(offered) - set(staged))
    costs = [r["cost_usd"] for r in results if r["cost_usd"] is not None]
    meta["cost_usd"] = round(sum(costs), 4) if costs else None
    meta["stopped_early"] = sum(r["stopped_early"] for r in results)
    summary = summarize(results)
    (out / "summary.json").write_text(json.dumps({"meta": meta, "summary": summary}, indent=1) + "\n")
    text = render(summary, meta)
    (out / "summary.md").write_text(text)
    print("\n" + text)
    if meta["skills_missing"]:
        print(f"WARNING: staged skills the runs did not list: {', '.join(meta['skills_missing'])}")
    print(f"results in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
