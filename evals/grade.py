#!/usr/bin/env python3
"""Deterministic grading for the six-stage pipeline evals.

Usage: python3 grade.py <iteration-dir>

Every assertion is tagged:
  capability — does this stage do its job at all (baseline may well pass too)
  delta      — does it do the thing this session's edits added

Only `delta` assertions can fairly be read as evidence that the edits helped.
"""
import json
import pathlib
import re
import subprocess
import sys

C, D = "capability", "delta"

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def read(p):
    try:
        return p.read_text(errors="replace")
    except Exception:
        return ""


def blob(run):
    parts = [read(p) for p in run.glob("outputs/*.md")]
    wf = run / "repo" / ".workflow"
    if wf.is_dir():
        parts += [read(p) for p in wf.glob("*.md")]
    return "\n\n".join(parts)


def resp(run):
    """Only what the stage said — excludes files it may merely have copied."""
    return "\n\n".join(read(p) for p in run.glob("outputs/*.md"))


def has(text, *pats, flags=re.I):
    return all(re.search(p, text, flags) for p in pats)


def any_of(text, *pats, flags=re.I):
    return any(re.search(p, text, flags) for p in pats)


def near(text, a, b, window=220):
    """a and b within `window` chars of each other, either order."""
    for m in re.finditer(a, text, re.I):
        seg = text[max(0, m.start() - window): m.end() + window]
        if re.search(b, seg, re.I):
            return True
    return False


def suite_green(run):
    repo = run / "repo"
    py = repo / ".venv/bin/python"
    if not py.exists():
        return False, "no venv in run repo"
    try:
        r = subprocess.run([str(py), "-m", "pytest", "tests/", "-q"],
                           cwd=repo, capture_output=True, text=True, timeout=120)
        tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        return r.returncode == 0, tail[0][:200]
    except Exception as e:
        return False, f"pytest failed to run: {e}"


# ---------------------------------------------------------------- eval checks

def eval0(run):
    t = blob(run)
    return [
        ("charter names what we're solving", has(t, r"Solving:?"), "Solving line", D),
        ("charter states why now", has(t, r"Why now"), "Why now line", D),
        ("charter states what done looks like", has(t, r"Done looks like"), "", D),
        ("charter states a calibration", has(t, r"Calibration"), "", D),
        ("charter estimates a question count",
         any_of(t, r"Questions:?\s*~?\s*\*?\*?\d+", r"~\d+\s+(questions|to resolve)"), "", D),
        ("progress line shows current question of total",
         any_of(t, r"Question\s+\d+\s+of\s+~?\s*\d+"), "'Question N of ~M'", D),
        ("options are presented", any_of(t, r"\[Options\]", r"\*\*Options"), "", D),
        ("each option carries a benefit and a cost",
         any_of(t, r"Buys you", r"Pros") and any_of(t, r"Costs you", r"Cons"), "", D),
        ("reversal cost given per option",
         any_of(t, r"reverse later", r"Cost to reverse", r"reversal cost"), "", D),
        ("recommendation names its own cost",
         any_of(t, r"What this costs us", r"costs us:"), "", D),
        ("recommendation names what would change its mind",
         any_of(t, r"change my mind"), "", D),
        ("closes with the awaiting-decision line",
         has(t, r"Awaiting your decision or input to proceed"), "", C),
    ]


def eval1(run):
    t = blob(run)
    brief = read(run / "repo/.workflow/brief.md")
    src = brief or t
    n_crit = len(re.findall(r"^\s*-\s*\[ \]", src, re.M))
    return [
        ("brief written to .workflow/brief.md", bool(brief.strip()),
         f"{len(brief)} chars", D),
        ("acceptance criteria present as a checklist", n_crit >= 4,
         f"{n_crit} criteria", C),
        ("first criterion is the tracer bullet",
         any_of(src, r"\[ \]\s*\*?\*?Tracer bullet"), "", C),
        ("edge cases separately marked",
         len(re.findall(r"Edge case", src, re.I)) >= 2, "", C),
        ("key interfaces name the public seam",
         any_of(src, r"BookingService\.submit|`submit`"), "", C),
        ("prior art points at the existing test suite",
         any_of(src, r"test_booking|test_party_size_rule|existing (pytest )?suite"), "", C),
        ("deferred decisions carried as explicit constraints",
         any_of(src, r"Deferred by design"), "named section, not prose", D),
        ("out of scope names the excluded adjacent work",
         any_of(src, r"[Oo]ut of scope") and any_of(src, r"override")
         and any_of(src, r"notif"), "", C),
        ("no line-number instructions", not any_of(src, r"line\s+\d+"), "", C),
    ]


def eval2(run):
    rules = read(run / "repo/reservations/rules.py")
    tests = read(run / "repo/tests/test_booking.py")
    brief = read(run / "repo/.workflow/brief.md")
    log = read(run / "outputs/cycle-log.md")
    green, eviz = suite_green(run)
    steps = len(re.findall(r"^\s*(?:\d+[.)]|[-*|])", log, re.M))
    ticked = len(re.findall(r"^\s*-\s*\[x\]", brief, re.M | re.I))
    return [
        ("suite is green", green, eviz, C),
        ("cutoff rule implemented", any_of(rules, r"cutoff"), "", C),
        ("window read from account config, not hard-coded",
         any_of(rules, r"config\.get\(\s*[\"']cutoff_minutes"), "", C),
        ("tests exist for the cutoff behavior", any_of(tests, r"cutoff|CUTOFF"), "", C),
        ("boundary case covered", any_of(tests, r"exact|boundary|edge"), "", C),
        ("cycle log shows discrete test-then-implementation steps", steps >= 3,
         f"{steps} logged steps", C),
        ("acceptance criteria checked off in the brief file", ticked >= 3,
         f"{ticked} ticked", D),
        ("brief revised in place when reality contradicted it",
         any_of(brief, r"##\s*Revisions") and len(re.findall(
             r"^\s*-\s+\S", brief.split("## Revisions")[-1], re.M)) >= 1
         if "## Revisions" in brief else False,
         "a logged revision entry", D),
    ]


def eval3(run):
    t = blob(run)
    r = resp(run)
    rules = read(run / "repo/reservations/rules.py")
    green, eviz = suite_green(run)
    dup = r"duplicat|config-default|_int_setting|int_setting|helper"
    ven = r"venue_id|primitive obsession"
    return [
        # capability — both versions should manage these
        ("smells named by type/subtype", any_of(t, r"Dispensables|Bloaters|Couplers|Change Preventers|Object-Orientation"), "", C),
        ("suite green after the refactor", green, eviz, C),
        ("behavior preserved: all three violation codes still returned",
         has(rules, r"PARTY_TOO_LARGE") and has(rules, r"VENUE_CLOSED")
         and has(rules, r"CUTOFF_WINDOW"), "", C),
        ("duplication actually removed",
         len(re.findall(r"if not isinstance\(", rules)) <= 1,
         f"{len(re.findall(r'if not isinstance.', rules))} coerce blocks left (3 in input)", C),
        # delta — only the current skill instructs these
        ("severity vocabulary applied to findings",
         any_of(r, r"blocking") and any_of(r, r"worthwhile") and any_of(r, r"\bnoted\b"),
         "blocking/worthwhile/noted", D),
        ("pass calibrated to diff size", any_of(r, r"[Cc]alibrat|small diff|large diff"), "", D),
        ("prior duplication smell explicitly re-rated (promoted)",
         near(r, dup, r"promot"), "promotion of the carried duplication smell", D),
        ("prior venue_id smell explicitly left, not silently dropped",
         near(r, ven, r"left|still noted|not met|remains|unchanged|untouched|carr"),
         "an explicit leave decision", D),
        ("carried smells recorded with a promotion condition",
         any_of(r, r"[Pp]romote if"), "a forward-looking trigger the input did not supply", D),
        ("stopping rule stated", any_of(r, r"[Ss]topping rule|clean enough"), "", D),
        ("carried count reported in the handoff",
         any_of(r, r"\d+\s+noted|noted and carried|carried.{0,20}\d+"), "", D),
    ]


def eval4(run):
    t = blob(run)
    r = resp(run)
    rules = read(run / "repo/reservations/rules.py")
    ledger = read(run / "repo/.workflow/ledger.md")
    return [
        # capability
        ("finds that the cutoff rule ignores account config",
         any_of(t, r"ignor[^\n]{0,80}config", r"config[^\n]{0,80}(ignor|never read|not read)",
                r"hard-?cod[^\n]{0,80}(120|cutoff)", r"DEFAULT_CUTOFF_MINUTES"), "", C),
        ("finds the vacuous config test",
         any_of(t, r"test_cutoff_window_reads_from_account_config"), "", C),
        ("argues the vacuity (mutation-surviving)",
         any_of(t, r"vacuous", r"passes? (even )?(if|when)[^\n]{0,60}(delet|remov|ignor)",
                r"surviv[^\n]{0,40}mutat"), "", C),
        ("findings carry evidence", len(re.findall(r"Evidence", t, re.I)) >= 2, "", C),
        ("findings carry a confidence rating", any_of(t, r"proven|unproven"), "", C),
        ("negative results recorded", any_of(t, r"found nothing|nothing found|swept|attacked[^\n]{0,40}nothing"), "", C),
        ("implementation left untouched (read-only mandate)",
         "DEFAULT_CUTOFF_MINUTES" in rules
         and 'config.get("cutoff_minutes"' not in rules, "planted defect still present", C),
        # delta
        ("does not re-report the refuted party-size finding",
         not near(t, r"party.?size|PARTY_TOO_LARGE", r"\bfinding\b.{0,60}(off-by-one|boundary)"),
         "prior refusal respected without a written reopen condition", D),
        ("unproven findings name what would settle them",
         any_of(r, r"settled by|would settle"), "", D),
        ("findings written into .workflow/ledger.md",
         len(ledger) > len(read(FIXTURES / "teardown/.workflow/ledger.md")) + 200,
         f"{len(ledger)} chars in ledger", D),
        ("states what it carries from the prior pass",
         any_of(r, r"[Ii]teration \d", r"carr(y|ies|ying)", r"prior pass|previous pass"), "", D),
    ]


def eval5(run):
    t = blob(run)
    r = resp(run)
    ledger = read(run / "repo/.workflow/ledger.md")
    return [
        # capability
        ("F2 adjudicated CONFIRMED",
         bool(re.search(r"F2\b[^\n]{0,140}CONFIRMED", t, re.I)), "", C),
        ("F3 adjudicated CONFIRMED",
         bool(re.search(r"F3\b[^\n]{0,140}CONFIRMED", t, re.I)), "", C),
        ("F5 adjudicated either way with a reason",
         bool(re.search(r"F5\b[^\n]{0,160}(INCONCLUSIVE|REFUTED|CONFIRMED)", t, re.I)), "", C),
        ("remediation slices produced", any_of(t, r"[Rr]emediation slice"), "", C),
        ("explicit NO-GO verdict", any_of(t, r"NO-?GO"), "", C),
        ("slices carry severity and finding id",
         bool(re.search(r"\[(blocker|major|minor)\][^\n]{0,40}F\d", t, re.I)), "", C),
        # delta
        ("F4 struck as an already-refuted repeat, citing the prior verdict",
         bool(re.search(r"F4\b[^\n]{0,200}(REFUTED|struck|cut)", t, re.I))
         and near(t, r"F4", r"F1|prior verdict|already refuted|sticky|re-?report"),
         "stickiness applied without a written reopen condition", D),
        ("iteration count stated up front",
         any_of(r, r"[Ii]teration \d"), "", D),
        ("carried noted smells enumerated in the verdict",
         near(r, r"duplicat|config-default", r"ship|carr|noted|debt")
         or near(r, r"venue_id|primitive obsession", r"ship|carr|noted|debt"),
         "prior smells surfaced into the ship decision", D),
        ("verdicts written back to the ledger",
         any_of(ledger, r"CONFIRMED|REFUTED"), "", D),
        ("loop-health stated (monotonic progress / iteration cap)",
         any_of(r, r"monotonic|iteration \d of|at most 3|stall|converg"), "", D),
    ]


CHECKS = {
    "eval-0-architect-charter-and-options": eval0,
    "eval-1-brief-ordered-criteria": eval1,
    "eval-2-tdd-reads-brief-vertical": eval2,
    "eval-3-refactor-promotes-noted-smell": eval3,
    "eval-4-teardown-finds-vacuous-test": eval4,
    "eval-5-verdict-cuts-and-slices": eval5,
}


def main():
    ws = pathlib.Path(sys.argv[1])
    summary = []
    for ed in sorted(ws.iterdir()):
        if not ed.is_dir() or ed.name not in CHECKS:
            continue
        fn = CHECKS[ed.name]
        runs = [p for p in sorted(ed.glob("with_skill/rep*")) if p.is_dir()]
        if (ed / "old_skill").is_dir():
            runs.append(ed / "old_skill")
        for run in runs:
            if not (run / "outputs/response.md").exists():
                continue
            exp = [{"text": n, "passed": bool(ok), "evidence": ev, "kind": k}
                   for n, ok, ev, k in fn(run)]
            p_all = sum(e["passed"] for e in exp)
            d = [e for e in exp if e["kind"] == D]
            c = [e for e in exp if e["kind"] == C]
            (run / "grading.json").write_text(json.dumps({
                "eval_name": ed.name, "run": str(run.relative_to(ws)),
                "expectations": exp,
                "passed": p_all, "total": len(exp),
                "pass_rate": round(p_all / len(exp), 3),
                "delta_passed": sum(e["passed"] for e in d), "delta_total": len(d),
                "delta_rate": round(sum(e["passed"] for e in d) / len(d), 3) if d else None,
                "capability_passed": sum(e["passed"] for e in c), "capability_total": len(c),
                "capability_rate": round(sum(e["passed"] for e in c) / len(c), 3) if c else None,
            }, indent=2))
            summary.append((ed.name, str(run.relative_to(ed)), p_all, len(exp),
                            sum(e["passed"] for e in d), len(d)))

    print(f"{'eval':42} {'run':16} {'all':>7}  {'delta':>7}")
    for n, rn, p, tot, dp, dt in summary:
        print(f"{n:42} {rn:16} {p:>3}/{tot:<3}  {dp:>3}/{dt:<3}")


if __name__ == "__main__":
    main()
