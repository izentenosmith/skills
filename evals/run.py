#!/usr/bin/env python3
"""Dispatch the eval runs headless, then grade and aggregate them.

Usage: python3 run.py [--evals 0,5] [--reps 3] [--baseline-ref REF|none]
                      [--workspace DIR] [--iteration N] [--concurrency 4]
                      [--timeout 1800] [--model MODEL] [--dry-run]

For each selected eval in evals.json this builds

  <workspace>/iteration-N/eval-<id>-<name>/
  ├── with_skill/rep1..repK/{repo,outputs}/   current skill, from this checkout
  └── old_skill/{repo,outputs}/               skill as of --baseline-ref

copies the fixture into each repo/, and launches one `claude -p` per run with
its working directory set to that repo/. Every run is isolated (--safe-mode:
no CLAUDE.md, no installed skills or plugins, no MCP), so the only skill it
sees is the SKILL.md named in its prompt. A failed or timed-out run is
recorded in run.json and the batch carries on. grade.py and aggregate.py run
on the iteration afterwards.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

EVALS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
FIXTURES = EVALS_DIR / "fixtures"

# The commit before the session that the recorded benchmark measures.
DEFAULT_BASELINE = "3b71f54^"

UNAVAILABLE = "The user is unavailable, so produce the deliverable instead of asking."

# Copied fixtures are working copies; build output that is not part of the
# fixture stays behind. The venv is kept: the runs and grade.py both use it.
IGNORE = [".pytest_cache", "__pycache__"]

# Harness files that live in a fixture folder but must not reach the run.
# incident/README.md lists every planted defect — it is the answer key.
HARNESS_ONLY = {"incident": ["README.md", "make-history.sh"]}


def fixture_dir(name):
    """evals.json names fixtures after the original throwaway workspace
    (`fixture`, `fixture-tdd`, ...); the folders here are `base`, `tdd`, ...
    This is the one place the two spellings meet."""
    if name == "fixture":
        name = "base"
    elif name.startswith("fixture-"):
        name = name[len("fixture-"):]
    d = FIXTURES / name
    if not d.is_dir():
        sys.exit(f"fixture {name!r} not found under {FIXTURES}")
    return d


def fixture_built(d):
    """setup.sh output: a venv for the pipeline fixtures, a git history for incident."""
    if (d / "tests").is_dir() and not (d / ".venv/bin/python").exists():
        return False
    if (d / "make-history.sh").exists() and not (d / "repo/.git").is_dir():
        return False
    return True


# Never searched for skills: the eval and loop harnesses, agent state (which
# holds whole worktrees of this repo), and build output.
SKIP_DIRS = {"evals", "harness", ".claude", ".git", ".venv", "node_modules"}

# `claude -p` waits for its own background shells before it exits, so one
# that hangs (on input, say) holds the run until --timeout while the work
# itself finished long before, and the run still reports success. Same
# settings as harness/loop.py.
RUN_ENV = {"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
           "BASH_DEFAULT_TIMEOUT_MS": "120000",
           "BASH_MAX_TIMEOUT_MS": "300000"}


def find_skill(root, skill):
    """SKILL.md for `skill` at any depth under root, so the family layout can
    move (<family>/<skill>/, skills/<family>/<skill>/, ...) without touching
    this. Falls back to the oldest layout, a flat <skill>.md at the root."""
    hits = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(n for n in dirs if n not in SKIP_DIRS)
        if pathlib.Path(d).name == skill and "SKILL.md" in files:
            hits.append(pathlib.Path(d) / "SKILL.md")
    if len(hits) > 1:
        sys.exit(f"skill {skill!r} is ambiguous under {root}: "
                 + ", ".join(str(h.relative_to(root)) for h in hits))
    if hits:
        return hits[0]
    flat = root / f"{skill}.md"
    return flat if flat.is_file() else None


def default_workspace():
    """Next to the main checkout, outside any git repo — a run inside this
    repo could read the current skills and contaminate the baseline."""
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return pathlib.Path(common.stdout.strip()).parent.parent / "skills-workspace"


def next_iteration(ws):
    taken = [int(p.name.split("-", 1)[1]) for p in ws.glob("iteration-*")
             if p.name.split("-", 1)[1].isdigit()]
    return max(taken, default=0) + 1


def snapshot(ref, dest):
    """git archive <ref> into dest. Returns the resolved commit."""
    sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()
    dest.mkdir(parents=True, exist_ok=True)
    arc = subprocess.Popen(["git", "archive", sha], cwd=REPO_ROOT, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(dest)], stdin=arc.stdout, check=True)
    if arc.wait() != 0:
        sys.exit(f"git archive {ref} failed")
    # A later ref carries the harness itself; keep the assertions out of reach.
    shutil.rmtree(dest / "evals", ignore_errors=True)
    return sha


def agent_prompt(skill_md, eval_prompt, outputs):
    lines = []
    if skill_md:
        lines.append(f"Follow the skill at {skill_md}. Read it first; the files next to "
                     "it are its references.")
        lines.append("")
    lines += [eval_prompt, "", UNAVAILABLE, "",
              f"When you are done, save your final response — the full deliverable you "
              f"would have shown the user — to {outputs / 'response.md'}."]
    return "\n".join(lines)


def claude_cmd(run, skill_md, prompt, model):
    cmd = ["claude", "-p", "--output-format", "json",
           "--safe-mode", "--disable-slash-commands", "--strict-mcp-config",
           "--no-session-persistence", "--permission-mode", "bypassPermissions",
           "--add-dir", str(run)]
    if skill_md:
        cmd += ["--add-dir", str(skill_md.parent)]
    if model:
        cmd += ["--model", model]
    return cmd + ["--", prompt]


def stage_skill(skill_md, dest_root):
    """Copy the skill's folder out of this checkout, so a run pointed at it is
    not one `..` away from evals/ and the assertions it is graded by."""
    rel = skill_md.parent.relative_to(REPO_ROOT)
    dest = dest_root / rel
    if not dest.exists():
        shutil.copytree(skill_md.parent, dest)
    return dest / skill_md.name


def stage_harness(src_root, dest_root):
    """harness/ and skills/ from src_root, copied to dest_root. Returns (loop.py, skills dir),
    or None when src_root has no harness (a baseline ref older than it)."""
    if not (src_root / "harness/loop.py").is_file():
        return None
    shutil.copytree(src_root / "harness", dest_root / "harness", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    skills = src_root / "skills" if (src_root / "skills").is_dir() else src_root
    shutil.copytree(skills, dest_root / "skills", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("evals", "harness", ".git", ".claude"))
    return dest_root / "harness/loop.py", dest_root / "skills"


def plan_loop(ev, ed, fix, args, snap_dir, cur_dir):
    """An eval of harness/loop.py itself: no prompt, the loop drives the stages.

    The run's repo is a git work tree whose one commit is the base fixture and
    whose working tree is `fixture` on top, uncommitted — so `--base HEAD` hands
    the teardown exactly the change under review."""
    cfg = ev["loop"]
    base_fix = fixture_dir(cfg["base_fixture"])
    variants = [(ed / "with_skill" / f"rep{i}", stage_harness(REPO_ROOT, cur_dir), "with_skill")
                for i in range(1, args.reps + 1)]
    if snap_dir:
        old = stage_harness(snap_dir, snap_dir.parent / "snapshot-harness")
        if old:
            variants.append((ed / "old_skill", old, "old_skill"))
        else:
            print(f"note: {ed.name} has no baseline — harness/loop.py is absent at the baseline ref",
                  file=sys.stderr)
    runs = []
    for run, (loop_py, skills), kind in variants:
        cmd = [sys.executable, str(loop_py), "--repo", str(run / "repo"),
               "--test-cmd", cfg["test_cmd"], "--base", "HEAD", "--skills", str(skills)]
        if cfg.get("delegate_model"):
            cmd += ["--delegate-model", cfg["delegate_model"]]
        if args.model:
            cmd += ["--model", args.model]
        runs.append({"eval": ed.name, "kind": kind, "run": run, "fixture": fix, "runner": "loop",
                     "base_fixture": base_fix, "skill_md": loop_py, "prompt": None,
                     "timeout": cfg.get("timeout"), "cmd": cmd})
    return runs


GIT_ID = ["-c", "user.name=evals", "-c", "user.email=evals@example.invalid", "-c", "commit.gpgsign=false"]
LOOP_EXCLUDE = ".venv/\n.pytest_cache/\n__pycache__/\n.workflow/runs/\n"


def git_base(repo, base_fix):
    """Init `repo` with base_fix as its only commit, leaving repo's own files as the change."""
    git = lambda *a, **kw: subprocess.run(["git", *GIT_ID, *a], check=True, capture_output=True, **kw)
    git("init", "-q", "-b", "main", str(repo))
    (repo / ".git/info/exclude").write_text(LOOP_EXCLUDE)
    git(f"--git-dir={repo / '.git'}", f"--work-tree={base_fix}", "add", "-A", ".", cwd=base_fix)
    git("commit", "-q", "-m", f"base: {base_fix.name} fixture", cwd=repo)


def plan(args, ws_iter, snap_dir, cur_dir):
    data = json.loads((EVALS_DIR / "evals.json").read_text())
    wanted = set(args.evals) if args.evals is not None else None
    runs = []
    for ev in data["evals"]:
        if wanted is not None and ev["id"] not in wanted:
            continue
        ed = ws_iter / f"eval-{ev['id']}-{ev['name']}"
        fix = fixture_dir(ev["fixture"])
        if ev.get("runner") == "loop":
            runs += plan_loop(ev, ed, fix, args, snap_dir, cur_dir)
            continue
        current = find_skill(REPO_ROOT, ev["skill"])
        if current is None:
            sys.exit(f"skill {ev['skill']!r} not found in this checkout")
        current = stage_skill(current, cur_dir)
        variants = [(ed / "with_skill" / f"rep{i}", current, "with_skill")
                    for i in range(1, args.reps + 1)]
        if snap_dir:
            # A skill that did not exist at the baseline ref gets a no-skill baseline.
            variants.append((ed / "old_skill", find_skill(snap_dir, ev["skill"]), "old_skill"))
        for run, skill_md, kind in variants:
            prompt = agent_prompt(skill_md, ev["prompt"], run / "outputs")
            runs.append({"eval": ed.name, "kind": kind, "run": run, "fixture": fix,
                         "skill_md": skill_md, "prompt": prompt,
                         "cmd": claude_cmd(run, skill_md, prompt, args.model)})
    if wanted is not None and (missing := wanted - {e["id"] for e in data["evals"]}):
        sys.exit(f"no eval with id {sorted(missing)}")
    return runs


def prepare(r):
    run = r["run"]
    if run.exists():
        shutil.rmtree(run)
    harness = {r["fixture"] / n for n in HARNESS_ONLY.get(r["fixture"].name, [])}
    patterns = shutil.ignore_patterns(*IGNORE)
    ignore = lambda d, names: patterns(d, names) | {n for n in names
                                                    if pathlib.Path(d) / n in harness}
    shutil.copytree(r["fixture"], run / "repo", symlinks=True, ignore=ignore)
    (run / "outputs").mkdir(parents=True)
    if r.get("runner") == "loop":
        git_base(run / "repo", r["base_fixture"])


class _Done(Exception):
    pass


def execute(r, timeout):
    run, t0 = r["run"], time.time()
    timeout = max(timeout, r.get("timeout") or 0)
    rec = {"eval": r["eval"], "kind": r["kind"],
           "skill_md": str(r["skill_md"]) if r["skill_md"] else None,
           "cmd": r["cmd"] if r["prompt"] is None else r["cmd"][:-1] + ["<prompt>"],
           "prompt": r["prompt"]}
    try:
        # Own process group, so a timeout also kills whatever the run spawned.
        p = subprocess.Popen(r["cmd"], cwd=run / "repo", env=os.environ | RUN_ENV,
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             start_new_session=True)
        try:
            stdout, stderr = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise
        rec.update(exit_code=p.returncode, timed_out=False, stderr_tail=stderr[-2000:])
        if r.get("runner") == "loop":
            # loop.py logs to stderr; that log is the run's response. 0 GO and
            # 3 ESCALATED are both verdicts — grade.py scores which one it was.
            (run / "outputs" / "response.md").write_text(stdout + stderr)
            spent = re.findall(r"spent \$([\d.]+) this run", stderr)
            rec.update(cost_usd=float(spent[-1]) if spent else None,
                       response="harness log", is_error=p.returncode not in (0, 3))
            raise _Done
        (run / "claude.json").write_text(stdout)
        try:
            out = json.loads(stdout)
        except json.JSONDecodeError:
            out = {}
        rec.update(is_error=out.get("is_error"), cost_usd=out.get("total_cost_usd"),
                   num_turns=out.get("num_turns"), models=sorted(out.get("modelUsage") or {}))
        resp = run / "outputs" / "response.md"
        if resp.exists():
            rec["response"] = "written by the agent"
        elif p.returncode == 0 and out.get("result"):
            # The agent answered but did not save it; grade what it said.
            resp.write_text(out["result"])
            rec["response"] = "fallback: final message from claude.json"
        else:
            rec["response"] = "missing"
    except _Done:
        pass
    except subprocess.TimeoutExpired:
        rec.update(exit_code=None, timed_out=True, response="missing")
    except Exception as e:  # never let one run abort the batch
        rec.update(exit_code=None, timed_out=False, error=repr(e), response="missing")
    rec["seconds"] = round(time.time() - t0, 1)
    rec["ok"] = rec["response"] != "missing" and not rec.get("is_error") and (
        rec.get("exit_code") == 0 or (r.get("runner") == "loop" and rec.get("exit_code") == 3))
    (run / "run.json").write_text(json.dumps(rec, indent=2))
    return rec


def print_plan(runs, ws_iter, baseline, args_timeout):
    print(f"iteration: {ws_iter}")
    print(f"baseline:  {baseline}")
    print(f"runs:      {len(runs)}\n")
    for r in runs:
        print(f"== {r['eval']}/{r['run'].relative_to(ws_iter / r['eval'])}")
        skip = HARNESS_ONLY.get(r["fixture"].name)
        print(f"   copy     {r['fixture']} -> {r['run'] / 'repo'}"
              + (f"  (without {', '.join(skip)})" if skip else ""))
        print(f"   mkdir    {r['run'] / 'outputs'}")
        if r.get("runner") == "loop":
            print(f"   git      init; commit {r['base_fixture']} as the only commit; "
                  f"{r['fixture'].name} stays on top, uncommitted (exclude: {LOOP_EXCLUDE.strip().replace(chr(10), ' ')})")
            print(f"   loop     {r['skill_md']}")
            print(f"   timeout  {max(args_timeout, r.get('timeout') or 0)}s")
            print(f"   command  {shlex.join(r['cmd'])}")
            print()
            continue
        print(f"   skill    {r['skill_md'] or '(none: skill absent at baseline ref)'}")
        print(f"   cwd      {r['run'] / 'repo'}")
        print(f"   env      {' '.join(f'{k}={v}' for k, v in RUN_ENV.items())}")
        print(f"   command  {shlex.join(r['cmd'][:-1])} <prompt>")
        print("   prompt   | " + r["prompt"].replace("\n", "\n            | "))
        print()
    print(f"then: python3 {EVALS_DIR / 'grade.py'} {ws_iter}")
    print(f"      python3 {EVALS_DIR / 'aggregate.py'} <every iteration-* in {ws_iter.parent}, oldest first>")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--evals", type=lambda s: [int(x) for x in s.split(",")],
                    help="comma-separated eval ids (default: all)")
    ap.add_argument("--reps", type=int, default=3, help="with-skill repetitions per eval")
    ap.add_argument("--baseline-ref", default=DEFAULT_BASELINE,
                    help=f"git ref for the old_skill run, or 'none' (default: {DEFAULT_BASELINE})")
    ap.add_argument("--workspace", type=pathlib.Path, help="default: ../skills-workspace "
                    "next to the main checkout")
    ap.add_argument("--iteration", type=int, help="default: the next unused number")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per run")
    ap.add_argument("--model", help="passed to claude --model")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and touch nothing")
    args = ap.parse_args()

    ws = (args.workspace or default_workspace()).expanduser().resolve()
    ws_iter = ws / f"iteration-{args.iteration or next_iteration(ws)}"
    use_baseline = args.baseline_ref.lower() != "none"

    with tempfile.TemporaryDirectory(prefix="skills-evals-") as tmp:
        # Snapshotted even on --dry-run (into a temp dir) so the plan's
        # baseline skill paths are the real ones.
        snap_dir, label = None, "none"
        if use_baseline:
            snap_dir = pathlib.Path(tmp) / "snapshot"
            sha = snapshot(args.baseline_ref, snap_dir)
            label = f"{args.baseline_ref} ({sha}) via git archive -> {snap_dir}"
        runs = plan(args, ws_iter, snap_dir, pathlib.Path(tmp) / "current")
        unbuilt = sorted({str(r["fixture"]) for r in runs if not fixture_built(r["fixture"])})

        if args.dry_run:
            print_plan(runs, ws_iter, label, args.timeout)
            if unbuilt:
                print(f"\nwarning: run ./setup.sh first — not built: {', '.join(unbuilt)}")
            return
        if unbuilt:
            sys.exit(f"run ./setup.sh first — not built: {', '.join(unbuilt)}")

        if not shutil.which("claude"):
            sys.exit("claude CLI not on PATH")
        ws_iter.mkdir(parents=True, exist_ok=True)
        for r in runs:
            prepare(r)
        longer = "".join(f" ({r['eval']}: {r['timeout']}s)" for r in runs
                         if (r.get("timeout") or 0) > args.timeout)
        print(f"{len(runs)} runs in {ws_iter}, concurrency {args.concurrency}, "
              f"timeout {args.timeout}s per run{longer}, baseline {label}", flush=True)

        results = []
        with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futs = {pool.submit(execute, r, args.timeout): r for r in runs}
            for f in cf.as_completed(futs):
                rec = f.result()
                results.append(rec)
                name = f"{rec['eval']}/{futs[f]['run'].name}"
                status = "ok" if rec["ok"] else ("TIMEOUT" if rec.get("timed_out") else "FAILED")
                cost = f"${rec['cost_usd']:.2f}" if rec.get("cost_usd") else "-"
                print(f"  [{len(results)}/{len(runs)}] {status:7} {rec['seconds']:>7.0f}s "
                      f"{cost:>7}  {name}", flush=True)

    failed = [r for r in results if not r["ok"]]
    total = sum(r.get("cost_usd") or 0 for r in results)
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    (ws_iter / "dispatch.json").write_text(json.dumps({
        "baseline": label, "reps": args.reps, "claude_version": version,
        "models": sorted({m for r in results for m in r.get("models") or []}),
        "runs": len(results), "failed": len(failed), "cost_usd": round(total, 2)}, indent=2))
    print(f"\n{len(results) - len(failed)}/{len(results)} runs ok, ${total:.2f} total")
    for r in failed:
        print(f"  failed: {r['eval']} {r['kind']} — see run.json")

    print()
    subprocess.run([sys.executable, str(EVALS_DIR / "grade.py"), str(ws_iter)], check=False)
    iters = sorted((p for p in ws.glob("iteration-*") if p.name.split("-", 1)[1].isdigit()),
                   key=lambda p: int(p.name.split("-", 1)[1]))
    print()
    subprocess.run([sys.executable, str(EVALS_DIR / "aggregate.py"), *map(str, iters)], check=False)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
