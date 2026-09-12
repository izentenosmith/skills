#!/usr/bin/env python3
"""Aggregate grading across iterations.

Usage: python3 aggregate.py <iter-dir> [<iter-dir> ...]

Later directories win: an eval present in iteration-2 supersedes iteration-1.
Reports capability and delta pass rates separately — only the delta column is
evidence that this session's edits helped.
"""
import json
import pathlib
import statistics as st
import sys


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
            reps = [load(p / "grading.json") for p in sorted(ed.glob("with_skill/rep*"))]
            reps = [r for r in reps if r]
            base = load(ed / "old_skill/grading.json")
            if reps or base:
                found[ed.name] = (d.name, reps, base)
    return found


def rate(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return vals


def main():
    found = collect(sys.argv[1:])
    out = []
    for name in sorted(found):
        src, reps, base = found[name]
        row = {"eval": name, "source": src, "n": len(reps)}
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
    ws = pathlib.Path(sys.argv[1]).parent
    (ws / "benchmark.json").write_text(json.dumps(bench, indent=2))

    L = ["# Benchmark — six-stage pipeline", "",
         "`delta` = assertions this session's edits added. `cap` = does the stage work at all.", "",
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
    L += ["", f"**Delta — current {st.mean(dm):.2f} vs baseline {st.mean(db):.2f}**",
          f"**Capability — current {st.mean(cm):.2f} vs baseline {st.mean(cb):.2f}**", ""]

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

    (ws / "benchmark.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
