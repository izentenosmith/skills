#!/usr/bin/env python3
"""Audit a database estate from its DDL or a live connection, and propose changes only where they're owed.

    python3 harness/dbreview.py --ddl sales=db/sales/ --ddl hr=db/hr.sql --out review/
    python3 harness/dbreview.py --dsn-env SALES_DB_URL --out review/          # read-only schema dump first
    python3 harness/dbreview.py --ddl … --out review/ --intent migration       # always propose (a translation)

    acquire DDL → inventory → audit per database → score → [synthesis] → gate → propose
    files, or a    CREATE counts   dbaudit, one     scoring.md's   estate,     per        dbpropose, only for
    read-only      per type        read-only        formula, in    >1 db       database   the databases the
    dump                           agent each       code                                  gate didn't pass

What code enforces, that the skills ask for in prose:
- **read-only**: a connection is used only to dump the schema (pg_dump / mysqldump with the password in
  the environment, SQLite opened `mode=ro`); credentials come from an environment variable you name and
  never appear in a command line, a log or an output file;
- **score by formula, not by feel**: agents report, per criterion, how many in-scope objects satisfy it;
  the harness computes p, the 🟢/🟡/🔴 points, the base, the Critical/High caps, the database and estate
  means — and writes the arithmetic beside every number. 🔬 needs-data never moves a score, and ⚠️
  proxy-only failures never grade a criterion 🔴;
- **the gate**: a database gets no proposal when its capped score is ≥ --good-enough (default 9.0, the
  Exemplary band, where dbpropose's default verdict is "reuse"), it has no open Critical or High finding,
  it isn't unused or a copy, and its 🔬 flags are at most --max-flag-ratio of its objects. With
  --intent migration every database is proposed — even an exemplary schema needs translating. The gate's
  decision is written down either way.

Exit status: 0 done · 1 error · 2 usage. Outputs land in --out: ddl/, audit/, gate.md, proposal/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2
RUBRIC = "v1.1"
BANDS = [(9.0, "Exemplary"), (7.0, "Good, minor debt"), (5.0, "Needs work"), (3.0, "Poor"), (0.0, "Critical / unsafe")]
OBJECT_RE = {
    "tables": r"\bCREATE\s+(?:GLOBAL\s+|LOCAL\s+)?(?:TEMP(?:ORARY)?\s+)?TABLE\b",
    "indexes": r"\bCREATE\s+(?:UNIQUE\s+)?(?:CLUSTERED\s+|NONCLUSTERED\s+)?INDEX\b",
    "views": r"\bCREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?(?:MATERIALIZED\s+)?VIEW\b",
    "procedures": r"\bCREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?(?:PROC(?:EDURE)?|FUNCTION)\b",
    "triggers": r"\bCREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?TRIGGER\b",
}


class Usage(Exception):
    pass


# ------------------------------------------------------------------ schemas

S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
obj, ARR = loop._obj, (lambda item: {"type": "array", "items": item})
AUDIT_SCHEMA = obj({
    "usage_status": {"type": "string", "enum": ["used", "barely-used", "unused", "copy", "unknown"]},
    "summary_md": S,
    "files": ARR(obj({
        "file": S, "coverage": S, "objects": I, "evaluation_md": S,
        "criteria": ARR(obj({"rubric": S, "criterion": S, "in_scope": I, "satisfied": I, "proxy_only": B})),
        "findings": ARR(obj({"id": S, "object": S, "severity": {"type": "string",
                                                                "enum": ["Critical", "High", "Medium", "Low"]},
                             "confidence": {"type": "string", "enum": ["decidable", "proxy", "needs-data"]},
                             "theory": S, "evidence": S, "summary": S})),
    })),
})
SYNTH_SCHEMA = obj({"markdown": S, "coupling": ARR(obj({"from": S, "to": S, "via": S}))})
PROPOSE_SCHEMA = obj({"files": ARR(obj({"name": S, "markdown": S}))})

AUDIT_PROMPT = """HARNESS-STAGE: db-audit · HARNESS-ITERATION: 1

Audit the **{db}** database with the dbaudit skill (`{skill}`) and its reference docs in that folder \
(scoring.md, theory.md, er-modeling.md, the per-object rubrics, detection-signals.md). Read-only: you \
never connect to anything and never change a file. The user is not available.

The final assessment must state what is good, what is bad, and what could be improved. If the score is \
at least 9.0, say that it meets the score threshold, then separately report whether open Critical/High \
findings, unused/copy usage, or the needs-data flag ratio prevent it from passing the overall gate.

DDL files for {db}:
{files}
Object counts the harness found: {counts}

For every file, return:
- `criteria`: for each criterion of each rubric that applies (tables.md, indexes.md, views.md, \
procedures.md, triggers.md), how many objects are **in scope** and how many **satisfy** it, and \
`proxy_only` when every failure behind it is a ⚠️ proxy signal. **Do not compute a score** — the harness \
applies scoring.md's formula to these counts.
- `findings`: each with severity (Critical/High/Medium/Low), confidence (`decidable` ✅, `proxy` ⚠️, \
`needs-data` 🔬 — a runtime claim is always needs-data), the theory it violates, and line evidence.
- `evaluation_md`: the per-file evaluation in scoring.md's template, **without** the score line.
- `coverage`: what was evaluated and what wasn't.
And for the database: its usage status (used / barely-used / unused / copy / unknown — unknown unless \
the DDL or the user says), and `summary_md`, its summary without the score.
"""

SYNTH_PROMPT = """HARNESS-STAGE: db-synthesis · HARNESS-ITERATION: 1

Write the estate synthesis (`estate-analysis.md`, per dbaudit's Step 4, `{skill}`) from these \
per-database summaries and the harness-computed scores. Don't recompute any score. Include the coupling \
edge list (which database reaches into which, and through what), cross-cutting patterns, the worst \
offenders, and the 🔬 tally.

{summaries}
"""

PROPOSE_PROMPT = """HARNESS-STAGE: db-propose · HARNESS-ITERATION: 1

Run dbpropose (`{skill}`, with proposal.md, er-modeling.md, physical-design.md) for **{dbs}** only — \
the gate found the other databases good enough to leave alone ({skipped}). Intent: **{intent}**{target}. \
The audit is in `{audit}`: every verdict cites the score and the finding that set it, and findings beat \
scores. Return the proposal as files (name + markdown): the reuse/rework register and, where the mode \
calls for it, the target schema or the in-place remediation register. The user is not available.
"""


# ------------------------------------------------------------------ acquire

def mask(s, dsn):
    if not dsn:
        return s
    p = urllib.parse.urlsplit(dsn)
    return s.replace(dsn, "<dsn>").replace(p.password or "\0", "***")


def dump_schema(dsn, dest):
    """Read-only schema dump. Returns the DDL text. The DSN never reaches argv, a log or the output."""
    p = urllib.parse.urlsplit(dsn)
    scheme = p.scheme.lower()
    if scheme in ("sqlite", "") or dsn.endswith((".db", ".sqlite", ".sqlite3")):
        path = p.path if scheme == "sqlite" else dsn
        path = path[1:] if path.startswith("//") else path
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
                               "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 WHEN 'view' THEN 2 "
                               "ELSE 3 END, name").fetchall()
        finally:
            con.close()
        return "".join(f"{r[0]};\n\n" for r in rows)
    db = p.path.lstrip("/")
    if scheme in ("postgres", "postgresql"):
        env = {**os.environ, "PGHOST": p.hostname or "", "PGPORT": str(p.port or 5432), "PGUSER": p.username or "",
               "PGPASSWORD": p.password or "", "PGDATABASE": db, "PGOPTIONS": "-c default_transaction_read_only=on"}
        cmd = ["pg_dump", "--schema-only", "--no-owner", "--no-privileges"]
    elif scheme in ("mysql", "mariadb"):
        env = {**os.environ, "MYSQL_PWD": p.password or ""}
        cmd = ["mysqldump", "--no-data", "--skip-comments", "--routines", "--triggers", "--single-transaction",
               "-h", p.hostname or "localhost", "-P", str(p.port or 3306), "-u", p.username or "", db]
    elif scheme in ("mssql", "sqlserver"):
        raise Usage("SQL Server has no schema-dump CLI this harness can rely on — export the DDL "
                    "(SSMS Generate Scripts, sqlpackage) and pass it with --ddl")
    else:
        raise Usage(f"unrecognised connection scheme {scheme!r} — pass the DDL with --ddl instead")
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    except FileNotFoundError:
        raise Usage(f"{cmd[0]} is not installed — install it, or export the DDL and pass --ddl")
    if r.returncode:
        raise Usage(f"{cmd[0]} failed: {mask(r.stderr.strip()[:300], dsn)}")
    return r.stdout


def collect(args, out):
    """{database: [ddl files]} from --ddl name=path / path, or from --dsn-env."""
    dbs = {}
    for spec in args.ddl or []:
        name, _, path = spec.rpartition("=") if "=" in spec else ("", "", spec)
        path = pathlib.Path(path).resolve()
        if not path.exists():
            raise Usage(f"{path} does not exist")
        name = name or (path.stem if path.is_file() else path.name)
        files = sorted(path.rglob("*.sql")) if path.is_dir() else [path]
        if not files:
            raise Usage(f"no .sql files under {path}")
        dbs[name] = files
    for var in args.dsn_env or []:
        dsn = os.environ.get(var)
        if not dsn:
            raise Usage(f"environment variable {var} is empty — export the connection string there; it is never "
                        "passed on the command line")
        name = urllib.parse.urlsplit(dsn).path.strip("/").rsplit("/", 1)[-1] or var.lower()
        name = pathlib.Path(name).stem
        ddl = dump_schema(dsn, out)
        dest = out / "ddl" / f"{name}.sql"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"-- schema of {name}, dumped read-only {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ}\n\n"
                        + ddl)
        dbs[name] = [dest]
        loop.log(f"dumped {name} read-only → {dest}")
    if not dbs:
        raise Usage("nothing to audit — pass --ddl or --dsn-env")
    return dbs


def inventory(files):
    counts = {k: 0 for k in OBJECT_RE}
    for f in files:
        text = re.sub(r"--[^\n]*|/\*.*?\*/", "", f.read_text(errors="replace"), flags=re.S)
        for k, pat in OBJECT_RE.items():
            counts[k] += len(re.findall(pat, text, re.I))
    return counts


# ------------------------------------------------------------------ scoring (scoring.md v1.1)

def band(score):
    return next(name for floor, name in BANDS if score >= floor)


def criterion_points(c):
    if c["in_scope"] <= 0:
        return None, None
    p = min(1.0, c["satisfied"] / c["in_scope"])
    pts = 2 if p >= 0.95 else 1 if p >= 0.50 else 0
    if pts == 0 and c.get("proxy_only"):
        pts = 1                                  # ⚠️ alone may grade 🟡, never 🔴
    return p, pts


def caps_for(findings):
    scored = [f for f in findings if f["confidence"] != "needs-data"]       # 🔬 never moves a score
    crit = [f for f in scored if f["severity"] == "Critical"]
    high = [f for f in scored if f["severity"] == "High"]
    if crit:
        return 2.0, crit[0]
    if high:
        return 6.0, high[0]
    return 10.0, None


def score_file(f):
    graded = []
    for c in f["criteria"]:
        p, pts = criterion_points(c)
        if pts is not None:
            graded.append({**c, "p": round(p, 3), "points": pts})
    base = round(sum(g["points"] for g in graded) / (2 * len(graded)) * 10, 2) if graded else 10.0
    cap, by = caps_for(f["findings"])
    return {"base": base, "cap": cap, "capped_by": by, "score": round(max(0.0, min(base, cap)), 1), "graded": graded}


def weighted(items):
    """items: [(score, weight)] → weighted mean, or 0 with no weight."""
    total = sum(w for _, w in items)
    return round(sum(s * w for s, w in items) / total, 2) if total else 0.0


def score_database(result, counts):
    files = []
    for f in result["files"]:
        s = score_file(f)
        files.append({**f, **s, "weight": max(1, f.get("objects") or 0)})
    uncapped = weighted([(f["score"], f["weight"]) for f in files])
    cap, by = caps_for([x for f in files for x in f["findings"]])
    findings = [x for f in files for x in f["findings"]]
    return {
        "files": files, "uncapped": uncapped, "cap": cap, "capped_by": by,
        "score": round(min(uncapped, cap), 1), "objects": sum(counts.values()) or sum(f["weight"] for f in files),
        "critical": sum(1 for x in findings if x["severity"] == "Critical" and x["confidence"] != "needs-data"),
        "high": sum(1 for x in findings if x["severity"] == "High" and x["confidence"] != "needs-data"),
        "flags": sum(1 for x in findings if x["confidence"] == "needs-data"),
        "usage": result["usage_status"],
    }


def cap_text(cap, by, before):
    """Say whether the cap binds: a cap above the score it would cap is not what set the number."""
    if not by:
        return "no cap"
    what = f"{by['severity']} {by['id']}"
    if cap < before:
        return f"capped at {cap} by {what} ({by['summary'][:80]})"
    return f"cap {cap} from {what} — not binding, the score is already lower"


def arithmetic(s):
    rows = "\n".join(f"| {g['rubric']} — {g['criterion']} | {g['satisfied']}/{g['in_scope']} | {g['p']:.2f} | "
                     f"{'🟢' if g['points'] == 2 else '🟡' if g['points'] == 1 else '🔴'} {g['points']} |"
                     for g in s["graded"])
    cap = cap_text(s["cap"], s["capped_by"], s["base"])
    return (f"\n\n## Score (computed by the harness, rubric {RUBRIC})\n\n| Criterion | Satisfied | p | Grade |\n"
            f"|---|---|---|---|\n{rows}\n\n**Base** {s['base']} · **{cap}** · **File score: {s['score']}** — "
            f"{band(s['score'])}\n")


# ------------------------------------------------------------------ the gate

def gate(name, d, a):
    """(skip_proposal, reasons). Every reason is written down whichever way it goes."""
    reasons = []
    if a.intent == "migration":
        return False, ["intent is migration — every database needs a translation proposal"]
    ok = True
    if d["score"] < a.good_enough:
        ok = False
        reasons.append(f"score {d['score']} is below {a.good_enough} ({band(d['score'])})")
    if d["critical"] or d["high"]:
        ok = False
        reasons.append(f"{d['critical']} Critical / {d['high']} High finding(s) open")
    if d["usage"] in ("unused", "copy"):
        ok = False
        reasons.append(f"usage is {d['usage']} — a drop verdict is itself a proposal")
    if d["flags"] > a.max_flag_ratio * max(1, d["objects"]):
        ok = False
        reasons.append(f"{d['flags']} 🔬 flags on {d['objects']} objects — a high score riding on unverified "
                       "claims is not a clean bill of health")
    if ok:
        reasons.append(f"score {d['score']} ≥ {a.good_enough}, no Critical/High, usage {d['usage']}, "
                       f"{d['flags']} 🔬 flag(s) — good enough: dbpropose's verdict would be reuse")
    return ok, reasons


# ------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--ddl", action="append", help="[name=]path — a .sql file or a folder of them, one database each")
    ap.add_argument("--dsn-env", action="append", help="NAME of an environment variable holding a connection "
                                                       "string; the schema is dumped read-only")
    ap.add_argument("--out", required=True, help="where the dump, audit, gate decision and proposal go")
    ap.add_argument("--intent", choices=["remediation", "migration"], default="remediation")
    ap.add_argument("--target", default="PostgreSQL 18", help="target engine for a migration proposal")
    ap.add_argument("--good-enough", type=float, default=9.0, help="capped score at which no proposal is made")
    ap.add_argument("--max-flag-ratio", type=float, default=0.10, help="🔬 flags per object above which a "
                                                                       "high score doesn't count as good enough")
    ap.add_argument("--audit-only", action="store_true", help="stop after the gate")
    ap.add_argument("--skills", default=str(HERE.parent / "skills"))
    ap.add_argument("--model")
    ap.add_argument("--delegate-model")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)

    out = pathlib.Path(a.out).resolve()
    run_dir = out / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ctx = loop.Ctx(repo=out, skills=pathlib.Path(a.skills).resolve(), test_cmd="", base="HEAD", cap=1,
                   model=a.model, delegate_model=a.delegate_model, concurrency=a.concurrency, budget=a.budget_usd,
                   timeout=a.timeout, dry=False, run_dir=run_dir, claude_bin=os.environ.get("HARNESS_CLAUDE", "claude"))
    try:
        dbs = collect(a, out)
        counts = {name: inventory(files) for name, files in dbs.items()}
        (out / "inventory.json").write_text(json.dumps(counts, indent=2))
        for name, c in counts.items():
            loop.log(f"{name}: {len(dbs[name])} file(s) · " + " · ".join(f"{v} {k}" for k, v in c.items() if v))

        audit_skill = loop.skill_path(ctx, "dbaudit")

        def job(name):
            files = "".join(f"- `{f}`\n" for f in dbs[name])
            prompt = AUDIT_PROMPT.format(db=name, skill=audit_skill, files=files, counts=json.dumps(counts[name]))
            # Read-only tools plus the DDL's folders, so the agent can read files outside the --out tree.
            return lambda: loop.claude(ctx, f"audit-{name}", prompt, AUDIT_SCHEMA, loop.READ_TOOLS,
                                       model=a.delegate_model, cwd=dbs[name][0].parent)

        results = loop.fan_out(ctx, [(name, job(name)) for name in dbs])
        failed = {n: r for n, r in results.items() if isinstance(r, Exception)}
        if failed:
            raise loop.HarnessError("audit did not return for: " + "; ".join(f"{n} ({e})" for n, e in failed.items()))

        audit = out / "audit"
        scores = {}
        for name, res in sorted(results.items()):
            d = score_database(res, counts[name])
            scores[name] = d
            ddir = audit / name
            ddir.mkdir(parents=True, exist_ok=True)
            for f in d["files"]:
                (ddir / f"{pathlib.Path(f['file']).stem}-evaluation.md").write_text(
                    f["evaluation_md"].rstrip() + arithmetic(f) + f"\n_Coverage: {f['coverage']}_\n")
            cap = cap_text(d["cap"], d["capped_by"], d["uncapped"])
            (ddir / "summary.md").write_text(
                res["summary_md"].rstrip() + f"\n\n## Score (harness, rubric {RUBRIC})\n\n"
                f"Object-weighted mean of the file scores **{d['uncapped']}** · {cap} · **Database score: "
                f"{d['score']} — {band(d['score'])}** · {d['critical']} Critical · {d['high']} High · "
                f"{d['flags']} 🔬 flag(s) open · usage: {d['usage']}\n")
            loop.log(f"{name}: {d['score']} — {band(d['score'])} ({cap}; {d['flags']} 🔬)")

        total = sum(d["objects"] for d in scores.values())
        estate_uncapped = weighted([(d["uncapped"], d["objects"]) for d in scores.values()])
        estate_cap = min([d["cap"] for d in scores.values()] + [10.0])
        estate = {"uncapped": estate_uncapped, "score": round(min(weighted([(d["score"], d["objects"])
                                                                            for d in scores.values()]), estate_cap), 1),
                  "objects": total}
        if len(scores) > 1:
            summaries = "\n\n".join(f"### {n} — {d['score']} ({band(d['score'])})\n{(audit / n / 'summary.md').read_text()}"
                                    for n, d in scores.items())
            syn = loop.claude(ctx, "synthesis", SYNTH_PROMPT.format(skill=audit_skill, summaries=summaries),
                              SYNTH_SCHEMA, loop.READ_TOOLS)
            edges = "\n".join(f"- {e['from']} → {e['to']} via {e['via']}" for e in syn["coupling"]) or "- none found"
            (audit / "estate-analysis.md").write_text(
                syn["markdown"].rstrip() + f"\n\n## Estate score (harness)\n\nCapped **{estate['score']}** — "
                f"{band(estate['score'])} · un-capped {estate['uncapped']} · {total} objects\n\n## Coupling edges\n{edges}\n")
        (audit / "scores.json").write_text(json.dumps({"rubric": RUBRIC, "estate": estate, "databases": {
            n: {k: v for k, v in d.items() if k != "files"} for n, d in scores.items()}}, indent=2, default=str))

        decisions = {n: gate(n, d, a) for n, d in scores.items()}
        lines = [f"# Proposal gate — {dt.datetime.now(dt.timezone.utc):%Y-%m-%d}", "",
                 f"Intent **{a.intent}** · good enough at **{a.good_enough}** · at most **{a.max_flag_ratio:.0%}** "
                 "🔬 flags per object", "", "| Database | Score | Proposal | Why |", "|---|---|---|---|"]
        for n, (skip, why) in decisions.items():
            lines.append(f"| {n} | {scores[n]['score']} | {'**no** — good enough' if skip else 'yes'} | {'; '.join(why)} |")
        (out / "gate.md").write_text("\n".join(lines) + "\n")
        todo = [n for n, (skip, _) in decisions.items() if not skip]
        skipped = [n for n, (skip, _) in decisions.items() if skip]
        loop.log(f"gate: propose for {', '.join(todo) or 'nothing'}; leave alone {', '.join(skipped) or 'nothing'}")

        if todo and not a.audit_only:
            res = loop.claude(ctx, "propose", PROPOSE_PROMPT.format(
                skill=loop.skill_path(ctx, "dbpropose"), dbs=", ".join(todo), skipped=", ".join(skipped) or "none",
                intent=a.intent, target=f", target {a.target}" if a.intent == "migration" else "", audit=audit),
                PROPOSE_SCHEMA, loop.READ_TOOLS)
            pdir = out / "proposal"
            pdir.mkdir(parents=True, exist_ok=True)
            for f in res["files"]:
                name = re.sub(r"[^\w.-]+", "-", f["name"]).strip("-") or "proposal.md"
                (pdir / (name if name.endswith(".md") else name + ".md")).write_text(f["markdown"].rstrip() + "\n")
            loop.log(f"proposal: {len(res['files'])} file(s) in {pdir}")
        elif not todo:
            loop.log("no proposal: every database passed the gate — see gate.md")
        return EXIT_OK
    except Usage as e:
        loop.log(f"error: {e}")
        return EXIT_USAGE
    except loop.HarnessError as e:
        loop.log(f"error: {e}")
        return EXIT_ERROR
    finally:
        if ctx.cost:
            loop.log(f"spent ${ctx.cost:.2f} this run")


if __name__ == "__main__":
    sys.exit(main())
