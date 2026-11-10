#!/usr/bin/env python3
"""Aggregate grading across iterations.

Usage: python3 aggregate.py [--record] <iter-dir> [<iter-dir> ...]

Later directories win: an eval present in iteration-2 supersedes iteration-1.
Reports capability and delta pass rates separately — only the delta column is
evidence that this session's edits helped.

Writes benchmark.md, benchmark.json and scores.json next to the iteration
directories. scores.json says, per eval, which iteration its score comes from
and the skill_hash and staging run.py recorded for it; check_repo.py compares
that hash with the skill as it is now. --record also writes benchmark.md and
scores.json into evals/, the copies this repo commits.
"""
import argparse
import json
import pathlib
import statistics as st

EVALS_DIR = pathlib.Path(__file__).resolve().parent


def load(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def collect(dirs):
    found = {}
    for d in dirs:
        d = pathlib.Path(d)
        if not d.is_dir():
            continue
        for ed in sorted(d.iterdir()):
            if not ed.is_dir() or not ed.name.startswith("eval-"):
                continue
            graded = [p for p in sorted(ed.glob("with_skill/rep*")) if load(p / "grading.json")]
            reps = [load(p / "grading.json") for p in graded]
            runs = [load(p / "run.json") or {} for p in graded]
            base = load(ed / "old_skill/grading.json")
            if reps or base:
                found[ed.name] = (d.name, reps, base, runs)
    return found


def provenance(name, runs, skills):
    """What the scored with-skill runs saw: the skill, how run.py staged it, and
    the hash of the staged folder. Runs from before run.py recorded these give
    None, as do reps that disagree."""
    def agreed(key):
        values = {r.get(key) for r in runs}
        return values.pop() if len(values) == 1 else None
    return {"skill": agreed("skill") or skills.get(name),
            "staging": agreed("staging"), "skill_hash": agreed("skill_hash")}


def rate(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return vals


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dirs", nargs="+", help="iteration directories, oldest first")
    ap.add_argument("--record", action="store_true",
                    help="also write benchmark.md and scores.json into evals/")
    args = ap.parse_args()
    evals = json.loads((EVALS_DIR / "evals.json").read_text())["evals"]
    skills = {f"eval-{e['id']}-{e['name']}": e["skill"] for e in evals if e.get("runner") != "loop"}
    found = collect(args.dirs)
    out = []
    for name in sorted(found):
        src, reps, base, runs = found[name]
        row = {"eval": name, "source": src, "n": len(reps), **provenance(name, runs, skills)}
        for label, key in (("all", "pass_rate"), ("delta", "delta_rate"),
                           ("cap", "capability_rate")):
            v = rate(reps, key)
            row[f"{label}_mean"] = round(st.mean(v), 3) if v else None
            row[f"{label}_sd"] = round(st.stdev(v), 3) if len(v) > 1 else 0.0
            row[f"{label}_base"] = (round(base[key], 3)
                                    if base and base.get(key) is not None else None)
        row["delta_gain"] = (round(row["delta_mean"] - row["delta_base"], 3)
                             if row["delta_mean"] is not None
                             and row["delta_base"] is not None else None)
        # which delta assertions the baseline also passed = still non-discriminating
        nd, flaky = [], []
        if reps and base:
            for i, e in enumerate(reps[0]["expectations"]):
                if e["kind"] != "delta":
                    continue
                w = [r["expectations"][i]["passed"] for r in reps]
                b = base["expectations"][i]["passed"]
                if all(w) and b:
                    nd.append(e["text"])
                if 0 < sum(w) < len(w):
                    flaky.append(f"{e['text']} ({sum(w)}/{len(w)})")
        row["non_discriminating_delta"] = nd
        row["flaky_delta"] = flaky
        out.append(row)

    bench = {"skill_name": "six-stage-pipeline", "evals": out}
    ws = pathlib.Path(args.dirs[0]).parent
    (ws / "benchmark.json").write_text(json.dumps(bench, indent=2))
    scores = {"note": "Written by evals/aggregate.py. skill_hash is the content hash of the skill "
                      "folder the scored runs saw (null: scored before run.py recorded it); "
                      ".github/scripts/check_repo.py reports each skill whose current hash differs.",
              "evals": {r["eval"]: {"skill": r["skill"], "iteration": r["source"], "n": r["n"],
                                    "staging": r["staging"], "skill_hash": r["skill_hash"]}
                        for r in out if r["skill"]}}

    L = ["# Benchmark", "",
         "`delta` = assertions that test what the skill instructs. `cap` = does the skill do its job at all. `n` = with-skill runs; the baseline is one run.", "",
         "| eval | from | n | delta (mean ± sd) | delta base | gain | cap | cap base |",
         "|---|---|---|---|---|---|---|---|"]
    for r in out:
        f = lambda v: "—" if v is None else f"{v:.2f}"
        g = r["delta_gain"]
        gain = "—" if g is None else f"{g:+.2f}"
        L.append(f"| {r['eval'].replace('eval-','')} | {r['source'].replace('iteration-','i')} "
                 f"| {r['n']} | {f(r['delta_mean'])} ± {r['delta_sd']:.2f} | {f(r['delta_base'])} "
                 f"| {gain} "
                 f"| {f(r['cap_mean'])} | {f(r['cap_base'])} |")

    dm = [r["delta_mean"] for r in out if r["delta_mean"] is not None]
    db = [r["delta_base"] for r in out if r["delta_base"] is not None]
    cm = [r["cap_mean"] for r in out if r["cap_mean"] is not None]
    cb = [r["cap_base"] for r in out if r["cap_base"] is not None]
    m = lambda v: f"{st.mean(v):.2f}" if v else "—"
    L += ["", f"**Delta — current {m(dm)} vs baseline {m(db)}**",
          f"**Capability — current {m(cm)} vs baseline {m(cb)}**", ""]

    L += ["## Delta assertions the baseline also passed (still non-discriminating)", ""]
    any_nd = False
    for r in out:
        if r["non_discriminating_delta"]:
            any_nd = True
            L.append(f"**{r['eval']}**")
            L += [f"- {a}" for a in r["non_discriminating_delta"]]
            L.append("")
    if not any_nd:
        L.append("_None — every delta assertion separates current from baseline._\n")

    L += ["## Delta assertions that varied across repetitions", ""]
    any_f = False
    for r in out:
        if r["flaky_delta"]:
            any_f = True
            L.append(f"**{r['eval']}**")
            L += [f"- {a}" for a in r["flaky_delta"]]
            L.append("")
    if not any_f:
        L.append("_None._")

    for dest in [ws] + ([EVALS_DIR] if args.record else []):
        (dest / "benchmark.md").write_text("\n".join(L))
        (dest / "scores.json").write_text(json.dumps(scores, indent=2) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
