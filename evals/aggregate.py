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

After the score table comes a health table: for each eval, whether its runs
all finished, how many repetitions passed every delta assertion, whether the
gain is larger than the run-to-run noise, whether the eval still has room to
show an improvement, and what a run costs with and without the skill.
"""
import argparse
import json
import math
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
            bdirs = baseline_dirs(ed)
            base = [g for g in (load(p / "grading.json") for p in bdirs) if g]
            if reps or base:
                dispatched = [load(p / "run.json") for p in sorted(ed.glob("with_skill/rep*"))]
                found[ed.name] = (d.name, reps, base, runs,
                                  {"with": [r for r in dispatched if r],
                                   "base": [r for r in (load(p / "run.json") for p in bdirs) if r]})
    return found


def baseline_dirs(ed):
    """One baseline run sits at old_skill/; run.py --baseline-reps N puts N in old_skill/rep*."""
    return sorted(p for p in ed.glob("old_skill/rep[0-9]*") if p.is_dir()) or [ed / "old_skill"]


# A with-skill delta rate at or above this leaves an eval nothing to show: it
# guards against regressions and cannot tell a better skill from this one.
SATURATED = 0.95
# A baseline at or above this passes most of what the eval checks without the skill.
BASE_HIGH = 0.80


def mean(v):
    v = [x for x in v if x is not None]
    return st.mean(v) if v else None


def health(row, reps, base, runs):
    """What the score table can't show: plumbing, consistency, noise, headroom, cost.

    reps and base are the graded with-skill and baseline runs; runs holds every
    run.json that was dispatched, graded or not."""
    perfect = sum(1 for r in reps if r.get("delta_total") and r["delta_passed"] == r["delta_total"])
    lost = [r for r in runs["with"] + runs["base"] if r.get("response") == "missing" or r.get("timed_out")]
    fallback = [r for r in runs["with"] + runs["base"] if str(r.get("response", "")).startswith("fallback")]
    h = {"dispatched": len(runs["with"]) or len(reps), "graded": len(reps),
         "base_n": len(base), "all_delta_passed": perfect,
         "lost_runs": len(lost), "fallback_responses": len(fallback),
         "cost_with": mean(r.get("cost_usd") for r in runs["with"]),
         "cost_base": mean(r.get("cost_usd") for r in runs["base"]),
         "turns_with": mean(r.get("num_turns") for r in runs["with"]),
         "seconds_with": mean(r.get("seconds") for r in runs["with"]),
         "noise": None}
    flags = []
    if h["lost_runs"]:
        flags.append(f"{h['lost_runs']} run(s) lost")
    if h["fallback_responses"]:
        flags.append(f"{h['fallback_responses']} fallback response(s)")
    if reps and perfect < len(reps):
        flags.append("inconsistent")
    gain, dm, db = row["delta_gain"], row["delta_mean"], row["delta_base"]
    if gain is not None:
        if len(base) > 1 and len(reps) > 1:
            # Standard error of the difference between the two means.
            bsd = st.stdev([b["delta_rate"] for b in base if b.get("delta_rate") is not None] or [0, 0])
            h["noise"] = round(math.sqrt(row["delta_sd"] ** 2 / len(reps) + bsd ** 2 / len(base)), 3)
            if abs(gain) < 2 * h["noise"] or gain <= 0:
                flags.append("gain within noise")
        else:
            flags.append("noise unknown")
            if gain <= 0:
                flags.append("no gain")
        if db >= BASE_HIGH:
            flags.append("baseline high")
    if dm is not None and dm >= SATURATED:
        flags.append("saturated")
    h["flags"] = flags
    return h


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


def health_section(out):
    """The health table and its summary, as benchmark.md lines."""
    usd = lambda v: "—" if v is None else f"${v:.2f}"
    L = ["## Health: plumbing, consistency, noise, headroom and cost", "",
         "`runs` = with-skill runs graded of those dispatched. `all delta` = repetitions that passed "
         "every delta assertion (the consistency of the skill, where the mean above hides a single "
         "miss). `base n` = baseline runs. `noise` = standard error of the gain, known only with two "
         "or more runs on each side; a gain under twice the noise is not evidence. "
         f"Flags: `saturated` = delta {SATURATED:.2f} or more, so the eval guards regressions and cannot "
         "show an improvement; `inconsistent` = some repetition missed a delta assertion; "
         "`noise unknown` = one baseline run; `gain within noise` and `no gain` = the skill is not shown "
         f"to help; `baseline high` = the baseline scores {BASE_HIGH:.2f} or more without the skill; "
         "`lost` = a run timed out or left no response and is missing from the score; `fallback` = "
         "the response was taken from the run's final message.", "",
         "| eval | runs | all delta | base n | gain | noise | cost with | cost base | flags |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        h, g = r["health"], r["delta_gain"]
        L.append(f"| {r['eval'].replace('eval-', '')} | {h['graded']}/{h['dispatched']} "
                 f"| {h['all_delta_passed']}/{h['graded']} | {h['base_n']} "
                 f"| {'—' if g is None else f'{g:+.2f}'} "
                 f"| {'—' if h['noise'] is None else f'{h['noise']:.2f}'} "
                 f"| {usd(h['cost_with'])} | {usd(h['cost_base'])} | {'; '.join(h['flags']) or '—'} |")
    scored = [r for r in out if r["delta_mean"] is not None]
    sat = [r for r in scored if r["delta_mean"] >= SATURATED]
    high = [r for r in scored if r["delta_base"] is not None and r["delta_base"] >= BASE_HIGH]
    lost = sum(r["health"]["lost_runs"] for r in out)
    L += ["", f"**{len(sat)} of {len(scored)} evals are saturated**, so they work as regression "
              "tests. Only the others can show that a skill edit helped."]
    if high:
        L.append(f"**{len(high)} baseline(s) score {BASE_HIGH:.2f} or more on delta** without the skill.")
    if lost:
        L.append(f"**{lost} run(s) timed out or left no response** and are missing from the scores above.")
    return L + [""]


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
        src, reps, base, runs, dispatched = found[name]
        row = {"eval": name, "source": src, "n": len(reps), **provenance(name, runs, skills)}
        for label, key in (("all", "pass_rate"), ("delta", "delta_rate"),
                           ("cap", "capability_rate")):
            v = rate(reps, key)
            row[f"{label}_mean"] = round(st.mean(v), 3) if v else None
            row[f"{label}_sd"] = round(st.stdev(v), 3) if len(v) > 1 else 0.0
            b = rate(base, key)
            row[f"{label}_base"] = round(st.mean(b), 3) if b else None
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
                # Every baseline run passed it: with one baseline run, that run.
                b = all(g["expectations"][i]["passed"] for g in base)
                if all(w) and b:
                    nd.append(e["text"])
                if 0 < sum(w) < len(w):
                    flaky.append(f"{e['text']} ({sum(w)}/{len(w)})")
        row["non_discriminating_delta"] = nd
        row["flaky_delta"] = flaky
        row["health"] = health(row, reps, base, dispatched)
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
         "`delta` = assertions that test what the skill instructs. `cap` = does the skill do its job at all. `n` = with-skill runs; the baseline is one run unless the health table says otherwise.", "",
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

    L += health_section(out)

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
