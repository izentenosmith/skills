#!/usr/bin/env python3
"""Prove that new tests were red before the fix and are green after it.

A test written alongside its fix can pass for the wrong reason: it asserts on a
fixture that hides the bug, or on behavior that was never broken. The only proof
it captures the defect is running it against the code *without* the fix. This does
that mechanically, for any language: it checks out the pre-fix code in a temporary
worktree, applies only the test files from your working tree, runs the test command
there (it must fail), then runs it in your working tree (it must pass).

    python3 -I redgreen.py check --repo . --cmd "<test command>" [--base REF] [--tests PATH ...]
                                 [--expect REGEX] [--timeout 600] [--shell] [--json]
    python3 -I redgreen.py snapshot --repo .   # the current working tree as a commit, for --base later

(This file runs from wherever it is copied: it is `scripts/redgreen.py` beside a skill.)

--base     the pre-fix code (default HEAD — right when test and fix are uncommitted).
           Take a `snapshot` before writing a fix to pin "before" exactly.
--tests    the test files to carry over; default: every changed file that looks like a test.
--cmd      run from the repo root; `{tests}` is replaced with the test paths. It is split into
           words (shlex) and run directly, WITHOUT a shell: leading `NAME=value` words become
           environment variables (`FOO=1 pytest -q` works), quotes group words, and nothing is
           expanded (no globs, no `~`). A command that needs a shell — it contains `;`, `|`,
           `&`, `>`, `<`, a backtick, `$(`, `${` or `$NAME` — is refused with exit status 2.
--shell    run --cmd through the shell instead. This is a person's decision, never a default:
           the command usually comes from a file anyone who can push can edit
           (`.workflow/brief.md`), and a shell runs whatever that file says. Pass it only for a
           command you have read, or put the pipeline in a script and name the script in --cmd.
--expect   a regex the *before* output must contain, so a failure for the wrong reason
           (an import error, a typo) doesn't count as red. Without it, a before-run that only
           failed to load — a collection or import error, a compile error, a missing module or
           symbol — is `wrong-reason`: a test that imports what the fix adds fails before the
           fix whether or not the behavior was ever broken. When --expect matches, it decides.

The "before" run is not sealed off from your tree. The temporary worktree gets symlinks to
the real dependency directories that exist in the repo (`.venv`, `venv`, `node_modules`,
`vendor`, `.gradle`, `target`, `.tox`), so the pre-fix code can run without a reinstall — and so
a test command that writes there (installs a package, fills a cache, builds into `target`)
writes into the real ones.

Exit status: 0 red→green · 1 anything else (not red, not green, no tests) · 2 usage error:
no such --repo, a --tests path that exists neither in the working tree nor at the base, a
--cmd that needs a shell without --shell.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

# Path shapes test files take across ecosystems: tests/ and spec/ trees, __tests__,
# test_x / x_test / x.test / x.spec / XTest / XTests / XSpec.
TEST_RE = re.compile(
    r"(^|/)(tests?|spec|specs|__tests__|testing)/"
    r"|(^|/)test_[^/]+$"
    r"|[._-](test|spec|tests|specs)\.[^/]+$"
    r"|(Test|Tests|Spec|IT)\.[^/.]+$"
)
HEAVY_DIRS = (".venv", "venv", "node_modules", "vendor", ".gradle", "target", ".tox")

# Output lines that mean the tests never ran: the before-tree failed to collect, import,
# compile or link them. Red for that reason proves nothing about the behavior. (Syntax errors
# are left out: JSON.parse throws one at runtime, and one in a test file fails after the fix too.)
LOAD_ERROR_RE = re.compile("|".join([
    # Python / pytest
    r"\bModuleNotFoundError\b", r"\bImportError\b", r"cannot import name",
    r"AttributeError: module \S+ has no attribute", r"\berrors? collecting\b",
    r"\berrors? during collection\b", r"\bno tests ran\b", r"\bcollected 0 items\b",
    # JVM: javac, Maven, Gradle, Kotlin
    r"cannot find symbol", r"error: package \S+ does not exist", r"COMPILATION ERROR", r"Compilation failure",
    r"compile\w*Java FAILED", r"compile\w*Kotlin FAILED", r"Unresolved reference",
    # Node / TypeScript
    r"Cannot find module", r"ERR_MODULE_NOT_FOUND", r"does not provide an export named",
    r"is not exported by", r"\berror TS\d+", r"Test suite failed to run",
    # Go, Rust, .NET, Ruby, and anything that says so
    r"^\s*\S+\.go:\d+:\d+: undefined: ", r"\[(build|setup) failed\]", r"\berror\[E\d{4}\]", r"could not compile",
    r"\berror CS\d{4}\b", r"\bLoadError\b", r"cannot load such file", r"uninitialized constant",
    r"\b(compilation|compile|build) (failed|error)", r"\bfailed to compile\b",
]), re.IGNORECASE | re.MULTILINE)
PYTEST_RE = re.compile(r"=+ test session starts =+|^Interrupted: ", re.MULTILINE)
# What only a shell can do with a command line: chain, pipe, background, redirect, substitute,
# expand a variable. Matched anywhere, quoted or not — refusing too much costs a flag, not a run.
SHELL_RE = re.compile(r"[;|&<>`\n]|\$[({A-Za-z_]")
ENV_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)


class Usage(Exception):
    pass


def git(repo, *args, env=None, check=True):
    if not pathlib.Path(repo).is_dir():
        raise Usage(f"no such directory: {repo}")
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env=env)
    if check and r.returncode:
        raise Usage(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def snapshot(repo) -> str:
    """The working tree (tracked + untracked, minus ignored) as a dangling commit.
    Uses a throwaway index, so the user's staging area is never touched."""
    repo = pathlib.Path(repo)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="redgreen-index-"))
    try:
        env = {**os.environ, "GIT_INDEX_FILE": str(tmp / "index")}
        git(repo, "read-tree", "HEAD", env=env)
        git(repo, "add", "-A", ".", env=env)
        tree = git(repo, "write-tree", env=env)
        # The snapshot is a dangling commit that never reaches a branch, so it gets its
        # own identity: a CI runner or container has none, and git refuses to guess one.
        ident = {f"GIT_{who}_{what}": value for who in ("AUTHOR", "COMMITTER")
                 for what, value in (("NAME", "redgreen"), ("EMAIL", "redgreen@localhost"))}
        return git(repo, "commit-tree", tree, "-p", "HEAD", "-m", "redgreen snapshot", env={**env, **ident})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def changed_tests(repo, base, explicit=None):
    """(present, deleted): test paths that differ between base and the working tree."""
    if explicit:
        paths = [str(pathlib.Path(p)) for p in explicit]
        nowhere = [p for p in paths if not (pathlib.Path(repo) / p).exists() and subprocess.run(
            ["git", "cat-file", "-e", f"{base}:{p}"], cwd=repo, capture_output=True).returncode]
        if nowhere:
            raise Usage(f"no such test file, in the working tree or at {base[:12]}: {', '.join(nowhere)}")
    else:
        after = snapshot(repo)
        paths = [p for p in git(repo, "diff", "--name-only", base, after).splitlines() if TEST_RE.search(p)]
    present = [p for p in paths if (pathlib.Path(repo) / p).exists()]
    deleted = [p for p in paths if p not in present]
    return present, deleted


def argv_for(cmd, tests=()):
    """(argv, env) to run `cmd` without a shell: the words of the command, and the leading
    `NAME=value` words as environment variables. Raises Usage for a command only a shell can run."""
    found = SHELL_RE.search(cmd)
    if found:
        raise Usage(f"--cmd needs a shell (it contains {found.group().strip() or 'a newline'!r}): {cmd!r}. "
                    "It is run without one by default. Read the command, then pass --shell to allow it, "
                    "or put it in a script and name the script")
    try:
        words = shlex.split(cmd.replace("{tests}", " ".join(shlex.quote(t) for t in tests)))
    except ValueError as e:
        raise Usage(f"--cmd does not parse ({e}): {cmd!r}")
    env = {}
    while words and ENV_RE.match(words[0]):
        name, value = ENV_RE.match(words.pop(0)).groups()
        env[name] = value
    if not words:
        raise Usage(f"--cmd names no command: {cmd!r}")
    return words, env


def run(cmd, cwd, tests, timeout, shell=False):
    if shell:
        args, env = cmd.replace("{tests}", " ".join(shlex.quote(t) for t in tests)), None
    else:
        args, extra = argv_for(cmd, tests)
        env = {**os.environ, **extra}
    try:
        r = subprocess.run(args, shell=shell, cwd=cwd, env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return {"code": r.returncode, "tail": out.splitlines()[-12:], "output": out}
    except subprocess.TimeoutExpired:
        return {"code": None, "tail": [f"timed out after {timeout}s"], "output": ""}
    except OSError as e:        # no such program, or not executable: what a shell reports as 127 / 126
        out = f"{args[0]}: {e.strerror or e}"
        return {"code": 126 if isinstance(e, PermissionError) else 127, "tail": [out], "output": out}


def load_errors(before, after, wt, repo):
    """Lines saying the pre-fix run never got to execute the tests, unless the same line
    also shows up in the post-fix run (then it is noise the suite always prints)."""
    out = before["output"].replace(str(wt.resolve()), str(repo)).replace(str(wt), str(repo))
    seen_after = {ln.strip() for ln in after["output"].splitlines()}
    hits = [ln.strip() for ln in out.splitlines() if LOAD_ERROR_RE.search(ln) and ln.strip() not in seen_after]
    # pytest: 2 = interrupted (collection errors), 4 = usage error, 5 = nothing collected.
    if before["code"] in (2, 4, 5) and PYTEST_RE.search(out):
        hits.append(f"pytest exit {before['code']}: the tests were not run")
    return hits[:5]


def check(repo, cmd, base="HEAD", tests=None, expect=None, timeout=600, shell=False):
    """`shell=True` runs `cmd` through the shell. A caller passes it only for a command a person
    chose to run that way (the CLI's --shell) — never because the command happened to need it."""
    repo = pathlib.Path(repo).resolve()
    if not shell:
        argv_for(cmd)                   # refuse before any worktree exists
    base = git(repo, "rev-parse", "--verify", f"{base}^{{commit}}")
    present, deleted = changed_tests(repo, base, tests)
    result = {"base": base, "tests": present, "deleted_tests": deleted, "before": None, "after": None}
    if not present:
        result["verdict"] = "no-tests"
        result["reason"] = "no test file differs from the base — there is nothing to prove red"
        return result

    root = pathlib.Path(tempfile.mkdtemp(prefix="redgreen-"))
    wt = root / repo.name
    try:
        git(repo, "worktree", "add", "--detach", "--quiet", str(wt), base)
        for rel in present:
            dest = wt / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / rel, dest)
        for rel in deleted:
            (wt / rel).unlink(missing_ok=True)
        for heavy in HEAVY_DIRS:
            if (repo / heavy).exists() and not (wt / heavy).exists():
                (wt / heavy).symlink_to(repo / heavy)     # the real one: the before-run can write into it
        result["before"] = run(cmd, wt, present, timeout, shell)
    finally:
        git(repo, "worktree", "remove", "--force", str(wt), check=False)
        shutil.rmtree(root, ignore_errors=True)
        git(repo, "worktree", "prune", check=False)
    result["after"] = run(cmd, repo, present, timeout, shell)

    before, after = result["before"], result["after"]
    red = before["code"] not in (0, None)
    if expect:
        right_reason, unloaded = bool(re.search(expect, before["output"])), []
    else:
        unloaded = load_errors(before, after, wt, repo) if red else []
        right_reason = not unloaded
    green = after["code"] == 0
    if red and right_reason and green:
        result["verdict"], result["reason"] = "red-green", "the tests fail on the pre-fix code and pass with the fix"
    elif not red:
        result["verdict"] = "not-red"
        result["reason"] = ("the tests pass on the pre-fix code — they don't capture the defect"
                            if before["code"] == 0 else "the pre-fix run timed out, which proves nothing")
    elif not right_reason and unloaded:
        result["verdict"], result["load_errors"] = "wrong-reason", unloaded
        result["reason"] = ("the pre-fix run failed before the tests ran (it could not load, import or compile "
                            f"them: {unloaded[0][:160]}) — that proves nothing about the behavior")
    elif not right_reason:
        result["verdict"] = "wrong-reason"
        result["reason"] = f"the pre-fix run failed, but its output doesn't match {expect!r} — likely not the bug"
    else:
        result["verdict"], result["reason"] = "not-green", "the tests still fail with the fix"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd_name", required=True)
    c = sub.add_parser("check")
    c.add_argument("--repo", default=".")
    c.add_argument("--cmd", required=True)
    c.add_argument("--base", default="HEAD")
    c.add_argument("--tests", nargs="+")
    c.add_argument("--expect")
    c.add_argument("--timeout", type=int, default=600)
    c.add_argument("--shell", action="store_true",
                   help="run --cmd through the shell (a person's decision: read the command first)")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("snapshot")
    s.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    try:
        if a.cmd_name == "snapshot":
            print(snapshot(a.repo))
            return 0
        res = check(a.repo, a.cmd, a.base, a.tests, a.expect, a.timeout, a.shell)
    except Usage as e:
        print(f"redgreen: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({k: v for k, v in res.items() if k not in ("before", "after")} | {
            p: {"code": res[p]["code"], "tail": res[p]["tail"]} for p in ("before", "after") if res[p]}, indent=2))
    else:
        print(f"{res['verdict']}: {res['reason']}")
        print(f"  base {res['base'][:12]} · tests: {', '.join(res['tests']) or 'none'}")
        for phase in ("before", "after"):
            if res[phase]:
                print(f"  {phase} (exit {res[phase]['code']}): {res[phase]['tail'][-1] if res[phase]['tail'] else ''}")
    return 0 if res["verdict"] == "red-green" else 1


if __name__ == "__main__":
    sys.exit(main())
