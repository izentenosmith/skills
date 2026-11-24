#!/usr/bin/env python3
"""Aggregate grading across iterations.

Usage: python3 aggregate.py [--record] <iter-dir> [<iter-dir> ...]

Later directories win: an eval present in iteration-2 supersedes iteration-1.
Reports capability and delta pass rates separately. The headline is the
outcome gain, capability with the skill minus capability without it: what the
skill adds to whether the job gets done. Delta (did the run follow the skill's
own instructions) and its gain stay as secondary, instruction-following
columns; a baseline that never read the skill scores near zero on delta by
construction, so the delta gain overstates what a skill adds. An eval whose
baseline already passes every capability assertion is flagged "baseline
already succeeds": on outcome it can only guard against a regression.

Writes benchmark.md, benchmark.json and scores.json next to the iteration
directories. scores.json says, per eval, which iteration its score comes from,
the day its latest scored run ended, its with-skill delta and capability means,
the baseline capability mean and the outcome gain, and the skill_hash and staging run.py recorded for it; check_repo.py compares
that hash with the skill as it is now. --record also writes benchmark.md and
scores.json into evals/, the copies this repo commits.

After the score table comes a health table: for each eval, whether its runs
all finished, how many repetitions passed every delta assertion, whether the
outcome and delta gains are larger than the run-to-run noise, whether the eval still has room to
show an improvement, and what a run costs with and without the skill.
"""
import argparse
import datetime as dt
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
                                   "base": [r for r in (load(p / "run.json") for p in bdirs) if r]},
                                  run_date(graded))
    return found


def run_date(reps):
    """(date, where it came from) of the latest scored with-skill run, as a UTC
    YYYY-MM-DD. run.py records `finished` in run.json since 2026-11-21; older
    runs recorded no date, so their run.json's mtime stands in: run.py writes
    that file once, when the run ends, and grading never rewrites it (it does
    rewrite grading.json, so that file's mtime would date the last re-grade).
    (None, None) when no graded rep has a run.json."""
    stamps = [load(p / "run.json") or {} for p in reps]
    finished = [r["finished"] for r in stamps if r.get("finished")]
    if finished and len(finished) == len(reps):
        return max(finished)[:10], "run.json finished"
    mtimes = [(p / "run.json").stat().st_mtime for p in reps if (p / "run.json").is_file()]
    if not mtimes:
        return None, None
    day = dt.datetime.fromtimestamp(max(mtimes), dt.timezone.utc).date().isoformat()
    return day, "run.json mtime"


def baseline_dirs(ed):
    """One baseline run sits at old_skill/; run.py --baseline-reps N puts N in old_skill/rep*."""
    return sorted(p for p in ed.glob("old_skill/rep[0-9]*") if p.is_dir()) or [ed / "old_skill"]


# A with-skill delta rate at or above this leaves an eval nothing to show: it
# guards against regressions and cannot tell a better skill from this one.
SATURATED = 0.95
# A baseline at or above this passes most of what the eval checks without the skill.
BASE_HIGH = 0.80
# A baseline capability mean at this passed every capability assertion in every
# baseline run: the outcome gain can only be zero or a regression.
BASE_SUCCEEDS = 1.0
BASELINE_SUCCEEDS = "baseline already succeeds"


def baseline_succeeds(row):
    return row.get("cap_base") is not None and row["cap_base"] >= BASE_SUCCEEDS


def gain_noise(reps, base, key):
    """Standard error of the difference between the with-skill and baseline
    means of `key`, or None unless both sides have two or more runs."""
    w = [r[key] for r in reps if r.get(key) is not None]
    b = [g[key] for g in base if g.get(key) is not None]
    if len(w) < 2 or len(b) < 2:
        return None
    return round(math.sqrt(st.variance(w) / len(w) + st.variance(b) / len(b)), 3)


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
         "noise": None, "outcome_noise": None}
    flags = []
    if h["lost_runs"]:
        flags.append(f"{h['lost_runs']} run(s) lost")
    if h["fallback_responses"]:
        flags.append(f"{h['fallback_responses']} fallback response(s)")
    if reps and perfect < len(reps):
        flags.append("inconsistent")
    # Outcome first, with the same noise rule as the delta gain below.
    og = row.get("outcome_gain")
    if og is not None:
        h["outcome_noise"] = gain_noise(reps, base, "capability_rate")
        if baseline_succeeds(row):
            flags.append(BASELINE_SUCCEEDS)
            if og < 0:
                flags.append("outcome below baseline")
        elif h["outcome_noise"] is not None:
            if og <= 0 or abs(og) < 2 * h["outcome_noise"]:
                flags.append("outcome within noise")
        elif og <= 0:
            flags.append("no outcome gain")
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


def overall(out, heldout):
    """The overall lines, outcome first. Each gain is the mean of the per-eval
    gains, over the evals that have a baseline; the current and baseline means
    beside it are over every eval that has that number. A held-out eval is a
    test set, so it gets a line of its own and stays out of the averages of the
    evals the skills were edited against. Last, how many evals' baselines
    already succeed on outcome."""
    vals = lambda rows, key: [r[key] for r in rows if r.get(key) is not None]
    m = lambda rows, key: (lambda v: f"{st.mean(v):.2f}" if v else "—")(vals(rows, key))
    g = lambda rows, key: (lambda v: f"{st.mean(v):+.2f}" if v else "—")(vals(rows, key))
    train = [r for r in out if r["eval"] not in heldout]
    held = [r for r in out if r["eval"] in heldout]
    L = [""]
    if train or not held:
        L += [f"**Outcome gain {g(train, 'outcome_gain')} — capability current "
              f"{m(train, 'cap_mean')} vs baseline {m(train, 'cap_base')}**",
              f"**Instruction-following gain {g(train, 'delta_gain')} — delta current "
              f"{m(train, 'delta_mean')} vs baseline {m(train, 'delta_base')}**"]
    if held:
        ids = ", ".join(r["eval"].split("-")[1] for r in held)
        L.append(f"**Held-out (eval {ids}), not in the two lines above: outcome gain "
                 f"{g(held, 'outcome_gain')} (capability current {m(held, 'cap_mean')} vs baseline "
                 f"{m(held, 'cap_base')}); instruction-following gain {g(held, 'delta_gain')} (delta "
                 f"current {m(held, 'delta_mean')} vs baseline {m(held, 'delta_base')})**")
    with_base = [r for r in out if r.get("cap_base") is not None]
    if with_base:
        ok = [r for r in with_base if baseline_succeeds(r)]
        L.append(f"**{len(ok)} of {len(with_base)} evals: {BASELINE_SUCCEEDS}** (capability "
                 f"baseline {BASE_SUCCEEDS:.2f}). On outcome they can only catch a regression; "
                 "what the skill adds there shows on delta alone.")
    return L + [""]


def health_section(out):
    """The health table and its summary, as benchmark.md lines."""
    usd = lambda v: "—" if v is None else f"${v:.2f}"
    L = ["## Health: plumbing, consistency, noise, headroom and cost", "",
         "`runs` = with-skill runs graded of those dispatched. `all delta` = repetitions that passed "
         "every delta assertion (the consistency of the skill, where the mean above hides a single "
         "miss). `base n` = baseline runs. `outcome noise` and `delta noise` = standard error of that "
         "gain, known only with two or more runs on each side; a gain under twice the noise is not "
         f"evidence. Outcome flags: `{BASELINE_SUCCEEDS}` = every baseline run passed every capability "
         "assertion, so the eval can only catch an outcome regression (`outcome below baseline` = it "
         "did); `outcome within noise` and `no outcome gain` = the skill is not shown to improve the "
         f"outcome. Delta flags: `saturated` = delta {SATURATED:.2f} or more, so the eval guards "
         "regressions and cannot show an improvement; `inconsistent` = some repetition missed a delta "
         "assertion; `noise unknown` = one baseline run; `gain within noise` and `no gain` = the skill "
         "is not shown to change what the run does; `baseline high` = the baseline scores "
         f"{BASE_HIGH:.2f} or more on delta without the skill. "
         "`lost` = a run timed out or left no response and is missing from the score; `fallback` = "
         "the response was taken from the run's final message.", "",
         "| eval | runs | all delta | base n | outcome gain | outcome noise | delta gain | delta noise "
         "| cost with | cost base | flags |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    sign = lambda v: "—" if v is None else f"{v:+.2f}"
    plain = lambda v: "—" if v is None else f"{v:.2f}"
    for r in out:
        h = r["health"]
        L.append(f"| {r['eval'].replace('eval-', '')} | {h['graded']}/{h['dispatched']} "
                 f"| {h['all_delta_passed']}/{h['graded']} | {h['base_n']} "
                 f"| {sign(r.get('outcome_gain'))} | {plain(h['outcome_noise'])} "
                 f"| {sign(r['delta_gain'])} | {plain(h['noise'])} "
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
    heldout = {f"eval-{e['id']}-{e['name']}" for e in evals if e.get("split") == "heldout"}
    found = collect(args.dirs)
    out = []
    for name in sorted(found):
        src, reps, base, runs, dispatched, (date, date_from) = found[name]
        row = {"eval": name, "source": src, "n": len(reps), "date": date, "date_from": date_from,
               **provenance(name, runs, skills)}
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
        # The headline: what the skill adds to whether the job gets done.
        row["outcome_gain"] = (round(row["cap_mean"] - row["cap_base"], 3)
                               if row["cap_mean"] is not None
                               and row["cap_base"] is not None else None)
        row["baseline_succeeds"] = baseline_succeeds(row)
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

    bench = {"skill_name": "six-stage-pipeline", "headline": "outcome_gain", "evals": out}
    ws = pathlib.Path(args.dirs[0]).parent
    (ws / "benchmark.json").write_text(json.dumps(bench, indent=2))
    scores = {"note": "Written by evals/aggregate.py. skill_hash is the content hash of the skill "
                      "folder the scored runs saw (null: scored before run.py recorded it); "
                      ".github/scripts/check_repo.py reports each skill whose current hash differs. "
                      "date is the UTC day the latest scored with-skill run ended, read from "
                      "run.json's `finished` or, for runs from before run.py recorded it, from "
                      "run.json's mtime (date_from says which). delta_mean and cap_mean are the "
                      "with-skill means benchmark.md shows; cap_base is the baseline capability "
                      "mean, and outcome_gain (cap_mean - cap_base, null without a baseline) is "
                      "the headline gain.",
              "evals": {r["eval"]: {"skill": r["skill"], "iteration": r["source"], "n": r["n"],
                                    "staging": r["staging"], "skill_hash": r["skill_hash"],
                                    "date": r["date"], "date_from": r["date_from"],
                                    "delta_mean": r["delta_mean"], "cap_mean": r["cap_mean"],
                                    "cap_base": r["cap_base"], "outcome_gain": r["outcome_gain"]}
                        for r in out if r["skill"]}}

    L = ["# Benchmark", "",
         "**Outcome first.** `outcome gain` = `cap` − `cap base`: how much more often the job gets "
         "done with the skill than without it. `cap` = capability assertions: does the run do the job "
         "at all. Then, as instruction-following: `delta` = assertions that test what the skill "
         "instructs, which a baseline that never read the skill mostly fails by construction, so "
         f"`delta gain` overstates what a skill adds. `{BASELINE_SUCCEEDS}` = `cap base` is "
         f"{BASE_SUCCEEDS:.2f}, so on outcome the eval can only catch a regression. `n` = with-skill "
         "runs; the baseline is one run unless the health table says otherwise.", "",
         "| eval | from | outcome gain | cap | cap base | n | delta gain | delta (mean ± sd) "
         "| delta base | outcome note |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        f = lambda v: "—" if v is None else f"{v:.2f}"
        s = lambda v: "—" if v is None else f"{v:+.2f}"
        L.append(f"| {r['eval'].replace('eval-','')} | {r['source'].replace('iteration-','i')} "
                 f"| {s(r['outcome_gain'])} | {f(r['cap_mean'])} | {f(r['cap_base'])} "
                 f"| {r['n']} | {s(r['delta_gain'])} "
                 f"| {f(r['delta_mean'])} ± {r['delta_sd']:.2f} | {f(r['delta_base'])} "
                 f"| {BASELINE_SUCCEEDS if r['baseline_succeeds'] else '—'} |")

    L += overall(out, heldout)

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
