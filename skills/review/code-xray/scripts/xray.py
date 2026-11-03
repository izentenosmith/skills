#!/usr/bin/env python3
"""code-xray — behavioural code analysis from git history (Tornhill, *Software Design X-Rays*).

    python3 -I xray.py pr        --repo . --base main [--json xray.json]   # signals for one change
    python3 -I xray.py hotspots  --repo . [--top 20]                       # change frequency × size
    python3 -I xray.py coupling  --repo . [--min-shared 20 --min-degree 0.5]
    python3 -I xray.py knowledge --repo . [--top 20]                       # main developer, fragmentation, loss
    python3 -I xray.py xray  FILE --repo .                                 # the functions inside one hotspot
    python3 -I xray.py trend FILE --repo . [--samples 12]                  # size and complexity over time

Every command prints markdown; `--json PATH` also writes the full result. Stdlib only, Python 3.10+,
read-only: it runs `git log`, `git diff`, `git ls-tree` and `git cat-file`, and never writes to the repo.

Windows count back from a fixed commit (the merge-base in `pr`, `--rev` elsewhere), not from today, so a
re-run on the same commits gives the same answer. Merge commits, mass commits (more than --max-files
files after exclusions) and excluded paths (lockfiles, vendored, generated, minified, snapshots, binaries,
plus every --exclude glob) are left out of every count.

Knowledge data — who wrote what — exists to route a review to someone who knows the code and to flag
knowledge loss. It is never a measure of a person. `--no-names` replaces authors with stable pseudonyms.

Exit: 0 done · 2 usage (not a repo, unknown ref, missing file).
"""
from __future__ import annotations

import argparse
import collections
import fnmatch
import json
import math
import pathlib
import re
import subprocess
import sys

DAY = 86400
MONTH = 30.44 * DAY
EXCLUDE = [
    "*.lock", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "go.sum", "*.min.*", "*.map",
    "vendor/*", "*/vendor/*", "node_modules/*", "*/node_modules/*", "dist/*", "build/*", "third_party/*",
    "*_pb2.py", "*_pb2_grpc.py", "*.pb.go", "*.generated.*", "*.g.dart", "*.designer.cs",
    "__snapshots__/*", "*/__snapshots__/*", "*.snap", "CHANGELOG*",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg", "*.pdf", "*.woff", "*.woff2", "*.ttf", "*.zip",
]
THIN = 150           # commits in the window below which every signal is a weak one (XR p.191)
CODE = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".kts", ".scala", ".go", ".rs",
        ".rb", ".php", ".cs", ".fs", ".vb", ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm", ".swift", ".dart",
        ".ex", ".exs", ".erl", ".clj", ".lua", ".pl", ".sh", ".bash", ".sql", ".tf", ".vue", ".svelte"}


class Usage(Exception):
    pass


# ------------------------------------------------------------------ git

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args],
                       capture_output=True, text=True, errors="replace")
    if check and r.returncode:
        raise Usage(f"git {' '.join(args[:2])}: {r.stderr.strip()[:300]}")
    return r.stdout


def rev_parse(repo, ref):
    out = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False).strip()
    if not out:
        raise Usage(f"{ref!r} is not a commit in {repo}")
    return out


def commit_time(repo, rev):
    return int(git(repo, "log", "-1", "--format=%ct", rev).strip())


def excluded(path, patterns):
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def read_log(repo, rev, patterns, paths=()):
    """Every non-merge commit reachable from rev, oldest last: {sha, at, author, files: {path: added}}."""
    out = git(repo, "log", "--no-merges", "--no-renames", "--numstat",
              "--format=tformat:@@%H\t%at\t%aN", rev, "--", *paths)
    commits, cur = [], None
    for line in out.splitlines():
        if line.startswith("@@"):
            sha, at, author = line[2:].split("\t", 2)
            cur = {"sha": sha, "at": int(at), "author": author, "files": {}}
            commits.append(cur)
        elif line and cur is not None:
            parts = line.split("\t")
            if len(parts) == 3 and not excluded(parts[2], patterns):
                cur["files"][parts[2]] = int(parts[0]) if parts[0].isdigit() else 0
    return commits


def files_at(repo, rev, patterns):
    return {p for p in git(repo, "ls-tree", "-r", "--name-only", rev).splitlines() if not excluded(p, patterns)}


def blobs(repo, specs):
    """{spec: text or None} for 'rev:path' specs, through one `git cat-file --batch`. None = missing or binary."""
    if not specs:
        return {}
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"],
                       input="".join(s + "\n" for s in specs).encode(), capture_output=True)
    out, i, res = r.stdout, 0, {}
    for spec in specs:
        nl = out.index(b"\n", i)
        header = out[i:nl].decode(errors="replace").split()
        i = nl + 1
        if len(header) == 3 and header[2].isdigit():
            size = int(header[2])
            data = out[i:i + size]
            i += size + 1
            res[spec] = None if header[1] != "blob" or b"\0" in data[:8000] else data.decode(errors="replace")
        else:
            res[spec] = None
    return res


# ------------------------------------------------------------------ measures

def measure(text):
    """(non-blank lines, indentation complexity, max depth). A tab or four spaces is one logical level."""
    loc = total = deepest = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        lead = line[:len(line) - len(line.lstrip(" \t"))]
        level = lead.count("\t") + lead.count(" ") // 4
        loc, total, deepest = loc + 1, total + level, max(deepest, level)
    return loc, total, deepest


def normalised_lines(text):
    return {ln.strip() for ln in text.splitlines() if len(ln.strip()) > 3 and re.search(r"\w", ln)}


def similarity(a, b):
    la, lb = normalised_lines(a), normalised_lines(b)
    if len(la) < 10 or len(lb) < 10:
        return 0.0
    return len(la & lb) / len(la | lb)


def fragmentation(counts):
    total = sum(counts.values())
    return round(1 - sum((n / total) ** 2 for n in counts.values()), 2) if total else 0.0


# ------------------------------------------------------------------ the history model

class History:
    """One pass over `git log rev`, cleaned and windowed; every analysis reads from it."""

    def __init__(self, repo, rev, months, patterns, max_files, active_days):
        self.repo, self.rev, self.patterns = repo, rev, patterns
        self.ref = commit_time(repo, rev)
        self.since = self.ref - months * MONTH
        everything = read_log(repo, rev, patterns)
        self.mass = [c for c in everything if len(c["files"]) > max_files]
        self.all = [c for c in everything if len(c["files"]) <= max_files and c["files"]]
        self.window = [c for c in self.all if c["at"] >= self.since]
        self.months, self.active_days = months, active_days
        self.files = files_at(repo, rev, patterns)
        self.last_seen = {}
        for c in self.all:                                   # newest first
            self.last_seen.setdefault(c["author"], c["at"])
        self.revs = collections.Counter(f for c in self.window for f in c["files"])
        self.shared = collections.Counter()
        for c in self.window:
            fs = sorted(c["files"])
            for i, a in enumerate(fs):
                for b in fs[i + 1:]:
                    self.shared[a, b] += 1

    def active(self, author):
        return self.last_seen.get(author, 0) >= self.ref - self.active_days * DAY

    def degree(self, a, b):
        n = self.shared[tuple(sorted((a, b)))]
        return n, (n / ((self.revs[a] + self.revs[b]) / 2) if n else 0.0)

    def partners(self, f):
        for (a, b), n in self.shared.items():
            if f in (a, b):
                g = b if a == f else a
                yield g, n, n / ((self.revs[a] + self.revs[b]) / 2)

    def hotspots(self, since=None, until=None):
        commits = [c for c in self.all if c["at"] >= (since or self.since) and c["at"] <= (until or self.ref)]
        revs = collections.Counter(f for c in commits for f in c["files"] if f in self.files)
        return revs

    def ranking(self, texts):
        rows = []
        for f, n in self.revs.items():
            t = texts.get(f"{self.rev}:{f}")
            if f not in self.files or t is None:
                continue
            loc, comp, _ = measure(t)
            rows.append({"file": f, "revisions": n, "loc": loc, "complexity": comp})
        rows.sort(key=lambda r: (-r["revisions"], -r["loc"], r["file"]))
        k = max(1, min(10, math.ceil(0.1 * len(rows))))
        for i, r in enumerate(rows, 1):
            r["rank"], r["hotspot"] = i, i <= k and r["revisions"] >= 3
        then = self.hotspots(self.since - 2 * MONTH, self.ref - 2 * MONTH)
        order = sorted(then, key=lambda f: (-then[f], f))
        rank_then = {f: i for i, f in enumerate(order, 1)}
        for r in rows:
            was = rank_then.get(r["file"])
            r["rank_two_months_ago"] = was
            r["rising"] = r["revisions"] >= 3 and (was - r["rank"] >= 10 if was else r["rank"] <= 10 and len(rows) > 10)
        return rows

    def knowledge(self, f, commits=None):
        commits = [c for c in (commits or self.window) if f in c["files"]] or [c for c in self.all if f in c["files"]]
        added, count = collections.Counter(), collections.Counter()
        for c in commits:
            added[c["author"]] += c["files"][f]
            count[c["author"]] += 1
        if not count:
            return None
        weight = added if sum(added.values()) else count
        total = sum(weight.values())
        main, top = weight.most_common(1)[0]
        return {"main_developer": main, "main_share": round(top / total, 2), "main_active": self.active(main),
                "authors": len(count), "fragmentation": fragmentation(count),
                "shares": {a: round(w / total, 2) for a, w in weight.most_common()}}

    def age_days(self, f):
        last = next((c["at"] for c in self.all if f in c["files"]), None)
        return None if last is None else int((self.ref - last) / DAY)


def is_code(path):
    return pathlib.PurePosixPath(path).suffix.lower() in CODE


def function_counts(repo, rev, path, allowed):
    """{function context: commits in the window that touched it}, from git's hunk headers (approximate:
    git names the enclosing context with its funcname rules — set a `diff=<lang>` gitattribute for better).
    `allowed` is the set of commit shas the window kept, so mass commits don't count here either."""
    out = git(repo, "log", "--no-merges", "--full-history", "-p", "-U0", "--format=tformat:@@%H %at", rev, "--", path)
    counts, sha, seen = collections.Counter(), None, set()
    for line in out.splitlines():
        if line.startswith("@@") and not line.startswith("@@ "):
            sha = line[2:].split()[0]
        elif line.startswith("@@ ") and sha in allowed:
            ctx = line.split("@@", 2)[2].strip() if line.count("@@") >= 2 else ""
            if ctx and (sha, ctx) not in seen:
                seen.add((sha, ctx))
                counts[ctx] += 1
    return counts


def touched_functions(repo, base, head, path):
    out = git(repo, "diff", "-U0", "--no-renames", base, head, "--", path)
    return sorted({ln.split("@@", 2)[2].strip() for ln in out.splitlines()
                   if ln.startswith("@@ ") and ln.count("@@") >= 2 and ln.split("@@", 2)[2].strip()})


class Names:
    def __init__(self, on):
        self.on, self.map = on, {}

    def __call__(self, author):
        if self.on or author is None:
            return author
        return self.map.setdefault(author, f"dev-{len(self.map) + 1}")


# ------------------------------------------------------------------ pr

def analyse_pr(a):
    repo = pathlib.Path(a.repo).resolve()
    head = rev_parse(repo, a.head)
    base = git(repo, "merge-base", rev_parse(repo, a.base), head).strip()
    patterns = EXCLUDE + (a.exclude or [])
    names = Names(not a.no_names)
    h = History(repo, base, a.months, patterns, a.max_files, a.active_days)

    status = {}
    for line in git(repo, "diff", "--name-status", "--no-renames", base, head).splitlines():
        st, path = line.split("\t", 1)
        status[path] = st[0]
    skipped = sorted(p for p in status if excluded(p, patterns))
    changed = {p: s for p, s in status.items() if p not in skipped}
    head_files = files_at(repo, head, patterns)
    author = a.author or git(repo, "log", "-1", "--format=%aN", head).strip()

    texts = blobs(repo, [f"{base}:{f}" for f in h.revs if f in h.files])
    ranking = {r["file"]: r for r in h.ranking(texts)}
    branch = git(repo, "rev-list", f"{base}..{head}").split()
    window_shas = {c["sha"] for c in h.window}

    rows, signals, missing, twins = [], [], [], []
    reviewer_score, reviewer_files = collections.Counter(), collections.defaultdict(set)

    def signal(f, kind, weight, detail):
        signals.append({"file": f, "kind": kind, "weight": weight, "detail": detail})

    for f, st in sorted(changed.items()):
        row = {"file": f, "status": st}
        r = ranking.get(f)
        row.update({"revisions": h.revs.get(f, 0), "hotspot_rank": r["rank"] if r else None,
                    "hotspot": bool(r and r["hotspot"]), "rising": bool(r and r["rising"])})
        if row["hotspot"]:
            signal(f, "hotspot", "high", f"hotspot #{r['rank']} ({r['revisions']} commits in {a.months} months, "
                                         f"{r['loc']} lines)")
        if row["rising"]:
            signal(f, "rising", "medium", f"rising hotspot: #{r['rank']} now, "
                                          f"{'#' + str(r['rank_two_months_ago']) if r['rank_two_months_ago'] else 'unranked'}"
                                          " two months ago")
        if st != "D":
            specs = [f"{head}:{f}", f"{base}:{f}"] + [f"{c}:{f}" for c in branch]
            got = blobs(repo, specs)
            head_m = measure(got[specs[0]]) if got[specs[0]] is not None else None
            base_m = measure(got[specs[1]]) if got[specs[1]] is not None else None
            history = [measure(t)[1] for s, t in got.items() if t is not None and s != specs[0]]
            row["loc"], row["complexity"] = (head_m[0], head_m[1]) if head_m else (None, None)
            row["complexity_base"] = base_m[1] if base_m else None
            floor = min(history) if history else None
            row["complexity_branch_min"] = floor
            growth = (head_m[1] - floor) / floor if head_m and floor else None
            row["complexity_growth"] = round(growth, 3) if growth is not None else None
            if (growth is not None and growth > 0.10 and head_m[1] - floor >= 4 and base_m and base_m[0] >= 20
                    and is_code(f)):
                signal(f, "complexity-growth", "high" if row["hotspot"] else "medium",
                       f"complexity +{growth:.0%} vs the branch minimum ({floor} → {head_m[1]})")
        row["age_days"] = h.age_days(f)
        if row["age_days"] is not None and row["age_days"] >= 365 and st == "M":
            signal(f, "stable-code", "medium", f"unchanged for {row['age_days']} days before this change")

        k = h.knowledge(f) if st != "A" else None
        row["knowledge"] = None
        if k:
            row["knowledge"] = {"main_developer": names(k["main_developer"]), "main_share": k["main_share"],
                                "main_active": k["main_active"], "authors": k["authors"],
                                "fragmentation": k["fragmentation"]}
            familiar = any(author == c["author"] for c in h.all if f in c["files"])
            row["author_familiar"] = familiar
            if not k["main_active"] and k["main_share"] >= 0.5:
                signal(f, "knowledge-loss", "high", f"main developer ({names(k['main_developer'])}, "
                                                    f"{k['main_share']:.0%} of added lines) inactive for "
                                                    f"{a.active_days}+ days")
            if not familiar and k["authors"] >= 3:
                signal(f, "unfamiliar", "medium", f"the author has not changed this file before; "
                                                  f"{k['authors']} authors, fragmentation {k['fragmentation']}")
            for who, share in k["shares"].items():
                if who != author and h.active(who):
                    reviewer_score[who] += share
                    reviewer_files[who].add(f)

        if st == "M" and row["revisions"] >= 3 and is_code(f):
            counts = function_counts(repo, base, f, window_shas)
            fns = [{"function": fn, "commits": counts.get(fn, 0)} for fn in touched_functions(repo, base, head, f)]
            row["functions"] = sorted(fns, key=lambda x: -x["commits"])[:5]
            for fn in row["functions"]:
                if fn["commits"] >= 3 and fn["commits"] >= 0.25 * row["revisions"]:
                    signal(f, "hot-function", "medium", f"`{fn['function']}` changed in {fn['commits']} of "
                                                        f"{row['revisions']} commits to this file")

        partners = sorted(h.partners(f), key=lambda x: (-x[2], -x[1], x[0]))
        for g, n, deg in partners:
            if g not in changed and g in head_files and n >= a.min_shared and deg >= a.warn_degree:
                missing.append({"file": f, "partner": g, "shared": n, "degree": round(deg, 2)})
                signal(f, "missing-cochange", "high", f"usually changes with `{g}` ({n} shared commits, "
                                                      f"{deg:.0%}) — absent from this change")
        if st != "D":
            stem = f.rsplit("/", 1)[-1]
            candidates = {g for g, n, deg in partners if n >= 3 and deg >= 0.5}
            candidates |= {g for g in head_files if g != f and g.rsplit("/", 1)[-1] == stem}
            specs = [f"{head}:{f}"] + [f"{head}:{g}" for g in sorted(candidates)]
            got = blobs(repo, specs)
            mine = got[specs[0]]
            for g in sorted(candidates):
                other = got.get(f"{head}:{g}")
                if mine is None or other is None:
                    continue
                sim = similarity(mine, other)
                if sim >= 0.5:
                    absent = g not in changed
                    twins.append({"file": f, "twin": g, "similarity": round(sim, 2), "twin_changed": not absent})
                    signal(f, "clone-twin", "high" if absent else "low",
                           f"near-duplicate of `{g}` ({sim:.0%} shared lines)"
                           + (" — the twin is not in this change; check it needs the same edit" if absent
                              else " — both changed; check they got the same edit"))
        rows.append(row)

    reviewers = [{"name": names(who), "files": sorted(reviewer_files[who]), "weight": round(s, 2)}
                 for who, s in reviewer_score.most_common(a.reviewers)]
    caveats = []
    if len(h.window) < THIN:
        caveats.append(f"thin history: {len(h.window)} commits in the window (under {THIN}) — every signal is weak")
    authors = {c["author"] for c in h.window}
    if h.window and len(authors) == 1:
        caveats.append("one author in the window — squash merges or migrated history hide the social data")
    return {
        "meta": {"tool": "code-xray", "version": 1, "repo": str(repo), "base": base, "head": head,
                 "window_months": a.months, "commits_in_window": len(h.window), "commits_total": len(h.all),
                 "mass_commits_dropped": len(h.mass), "max_files": a.max_files, "authors_in_window": len(authors),
                 "excluded_from_diff": skipped, "names": not a.no_names, "author": names(author),
                 "thresholds": {"min_shared": a.min_shared, "warn_degree": a.warn_degree,
                                "active_days": a.active_days}, "caveats": caveats,
                 "note": "Knowledge data routes reviews and flags knowledge loss. It never rates people."},
        "changed": rows, "missing_cochanges": missing, "clone_twins": twins, "reviewers": reviewers,
        "signals": signals,
    }


def pr_markdown(x):
    m = x["meta"]
    lines = [f"# History signals — {m['base'][:8]}..{m['head'][:8]}", "",
             f"**Data:** {m['commits_in_window']} commits in {m['window_months']} months before the merge-base "
             f"({m['commits_total']} in all), {m['mass_commits_dropped']} mass commits dropped, merges excluded"
             + (f", {len(m['excluded_from_diff'])} changed file(s) excluded as generated/vendored/lock"
                if m["excluded_from_diff"] else "") + "."]
    lines += [f"**Caveat:** {c}." for c in m["caveats"]]
    by_file = collections.defaultdict(list)
    for s in x["signals"]:
        by_file[s["file"]].append(s)
    quiet = [row for row in x["changed"] if not by_file[row["file"]]]
    if len(quiet) < len(x["changed"]):
        lines += ["", "| File | Signals |", "|---|---|"]
    for row in x["changed"]:
        if not by_file[row["file"]]:
            continue
        sig = " · ".join(f"**{s['detail']}**" if s["weight"] == "high" else s["detail"] for s in by_file[row["file"]])
        k = row.get("knowledge")
        if k:
            sig += f" · main developer {k['main_developer']} ({k['main_share']:.0%})" + (
                "" if k["main_active"] else ", inactive")
        lines.append(f"| `{row['file']}` ({row['status']}) | {sig} |")
    lines += ["", f"{len(quiet)} of {len(x['changed'])} changed file(s) carry no history signal."]
    if x["missing_cochanges"]:
        lines += ["", "**Missing co-changes** — each one is an omission question, not a block:"]
        lines += [f"- `{c['file']}` changed with `{c['partner']}` in {c['shared']} commits ({c['degree']:.0%}); "
                  "the partner is absent here" for c in x["missing_cochanges"]]
    if x["reviewers"]:
        lines += ["", "**Suggested reviewers** (they know the touched code; a suggestion, never a ranking): "
                  + ", ".join(f"{r['name']} ({', '.join('`' + f + '`' for f in r['files'][:3])})"
                              for r in x["reviewers"])]
    lines += ["", f"_{m['note']}_"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ codebase commands

def history_for(a):
    repo = pathlib.Path(a.repo).resolve()
    rev = rev_parse(repo, a.rev)
    return repo, rev, History(repo, rev, a.months, EXCLUDE + (a.exclude or []), a.max_files, a.active_days)


def cmd_hotspots(a):
    repo, rev, h = history_for(a)
    rows = h.ranking(blobs(repo, [f"{rev}:{f}" for f in h.revs if f in h.files]))
    for r in rows:
        r["age_days"] = h.age_days(r["file"])
    md = [f"# Hotspots — {len(h.window)} commits in {a.months} months to {rev[:8]}", "",
          "| # | File | Commits | Lines | Complexity | Age (days) | |", "|---|---|---|---|---|---|---|"]
    md += [f"| {r['rank']} | `{r['file']}` | {r['revisions']} | {r['loc']} | {r['complexity']} | {r['age_days']} | "
           + " ".join(x for x, on in (("hotspot", r["hotspot"]), ("rising", r["rising"])) if on) + " |"
           for r in rows[:a.top]]
    return {"meta": {"rev": rev, "commits_in_window": len(h.window), "window_months": a.months}, "hotspots": rows}, md


def cmd_coupling(a):
    repo, rev, h = history_for(a)
    pairs = []
    for (x, y), n in h.shared.items():
        deg = n / ((h.revs[x] + h.revs[y]) / 2)
        if n >= a.min_shared and deg >= a.min_degree and x in h.files and y in h.files:
            cross = x.split("/")[0] != y.split("/")[0]
            pairs.append({"a": x, "b": y, "shared": n, "degree": round(deg, 2), "cross_boundary": cross})
    pairs.sort(key=lambda p: (-p["degree"], -p["shared"], p["a"]))
    md = [f"# Change coupling — ≥ {a.min_shared} shared commits, degree ≥ {a.min_degree:.0%}", "",
          "| A | B | Shared | Degree | |", "|---|---|---|---|---|"]
    md += [f"| `{p['a']}` | `{p['b']}` | {p['shared']} | {p['degree']:.0%} | "
           f"{'crosses a top-level boundary' if p['cross_boundary'] else ''} |" for p in pairs[:a.top]]
    return {"meta": {"rev": rev, "commits_in_window": len(h.window)}, "pairs": pairs}, md


def cmd_knowledge(a):
    repo, rev, h = history_for(a)
    names = Names(not a.no_names)
    rows = []
    for f in sorted(h.revs, key=lambda f: -h.revs[f]):
        if f not in h.files:
            continue
        k = h.knowledge(f)
        if k:
            rows.append({"file": f, "revisions": h.revs[f], "main_developer": names(k["main_developer"]),
                         "main_share": k["main_share"], "main_active": k["main_active"], "authors": k["authors"],
                         "fragmentation": k["fragmentation"],
                         "knowledge_loss": not k["main_active"] and k["main_share"] >= 0.5})
    md = ["# Knowledge map — for routing reviews and spotting loss, never for rating people", "",
          "| File | Commits | Main developer | Share | Authors | Fragmentation | |", "|---|---|---|---|---|---|---|"]
    md += [f"| `{r['file']}` | {r['revisions']} | {r['main_developer']} | {r['main_share']:.0%} | {r['authors']} | "
           f"{r['fragmentation']} | {'knowledge loss' if r['knowledge_loss'] else ''} |" for r in rows[:a.top]]
    return {"meta": {"rev": rev, "names": not a.no_names}, "files": rows}, md


def cmd_xray(a):
    repo, rev, h = history_for(a)
    if a.file not in h.files:
        raise Usage(f"{a.file} is not a tracked, analysed file at {rev[:8]}")
    counts = function_counts(repo, rev, a.file, {c["sha"] for c in h.window})
    rows = [{"function": fn, "commits": n} for fn, n in counts.most_common()]
    md = [f"# X-ray — `{a.file}`: {h.revs.get(a.file, 0)} commits in {a.months} months", "",
          "| Function (git hunk context) | Commits |", "|---|---|"]
    md += [f"| `{r['function']}` | {r['commits']} |" for r in rows[:a.top]]
    return {"meta": {"rev": rev, "file": a.file}, "functions": rows}, md


def cmd_trend(a):
    repo = pathlib.Path(a.repo).resolve()
    rev = rev_parse(repo, a.rev)
    log = git(repo, "log", "--no-merges", "--full-history", "--format=%H %ct", rev, "--", a.file).split("\n")
    shas = [ln.split() for ln in log if ln.strip()][::-1]
    if not shas:
        raise Usage(f"{a.file} has no history at {rev[:8]}")
    step = max(1, math.ceil(len(shas) / a.samples))
    picked = shas[::step] + ([shas[-1]] if (len(shas) - 1) % step else [])
    specs = [f"{s}:{a.file}" for s, _ in picked] + [f"{rev}:{a.file}"]
    got = blobs(repo, specs)
    if got[specs[-1]] is not None and got[specs[-1]] != got[f"{picked[-1][0]}:{a.file}"]:
        picked.append([rev, str(commit_time(repo, rev))])   # end at rev itself: a merge can differ from every branch commit
    rows = []
    for s, t in picked:
        text = got.get(f"{s}:{a.file}")
        if text is not None:
            loc, comp, deep = measure(text)
            rows.append({"commit": s[:10], "at": int(t), "loc": loc, "complexity": comp, "max_depth": deep,
                         "mean": round(comp / loc, 2) if loc else 0})
    md = [f"# Complexity trend — `{a.file}`", "", "| Commit | Lines | Complexity | Mean | Max depth |",
          "|---|---|---|---|---|"]
    md += [f"| {r['commit']} | {r['loc']} | {r['complexity']} | {r['mean']} | {r['max_depth']} |" for r in rows]
    return {"meta": {"rev": rev, "file": a.file}, "trend": rows}, md


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=".")
    common.add_argument("--months", type=int, default=12, help="analysis window, counted back from the commit")
    common.add_argument("--exclude", action="append", help="extra glob to leave out of every count (repeatable)")
    common.add_argument("--max-files", type=int, default=50, help="commits touching more files are mass commits")
    common.add_argument("--active-days", type=int, default=90, help="an author with no commit this long is inactive")
    common.add_argument("--no-names", action="store_true", help="pseudonyms instead of author names")
    common.add_argument("--json", help="also write the full result here")
    common.add_argument("--top", type=int, default=20)

    p = sub.add_parser("pr", parents=[common], help="history signals for one change")
    p.add_argument("--base", required=True)
    p.add_argument("--head", default="HEAD")
    p.add_argument("--author", help="the change's author (default: the head commit's)")
    p.add_argument("--min-shared", type=int, default=20)
    p.add_argument("--warn-degree", type=float, default=0.8)
    p.add_argument("--reviewers", type=int, default=3)
    for name in ("hotspots", "coupling", "knowledge"):
        q = sub.add_parser(name, parents=[common])
        q.add_argument("--rev", default="HEAD")
        if name == "coupling":
            q.add_argument("--min-shared", type=int, default=20)
            q.add_argument("--min-degree", type=float, default=0.5)
    for name in ("xray", "trend"):
        q = sub.add_parser(name, parents=[common])
        q.add_argument("file")
        q.add_argument("--rev", default="HEAD")
        q.add_argument("--samples", type=int, default=12)
    a = ap.parse_args(argv)

    try:
        if a.cmd == "pr":
            result = analyse_pr(a)
            md = pr_markdown(result)
        else:
            handler = {"hotspots": cmd_hotspots, "coupling": cmd_coupling, "knowledge": cmd_knowledge,
                       "xray": cmd_xray, "trend": cmd_trend}[a.cmd]
            result, lines = handler(a)
            md = "\n".join(lines) + "\n"
    except Usage as e:
        print(f"xray: {e}", file=sys.stderr)
        return 2
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(result, indent=2) + "\n")
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
