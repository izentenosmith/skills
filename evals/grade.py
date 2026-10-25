#!/usr/bin/env python3
"""Deterministic grading for the skills evals.

Usage: python3 grade.py <iteration-dir>

Every assertion is tagged:
  capability — does this stage do its job at all (baseline may well pass too)
  delta      — does it do the thing this session's edits added

Only `delta` assertions can fairly be read as evidence that the edits helped.
"""
import ast
import datetime
import difflib
import html
import ipaddress
import json
import os
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict

C, D = "capability", "delta"

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
LEDGER_PY = pathlib.Path(__file__).resolve().parent.parent / "harness" / "ledger.py"

# ledger.py codes that judge the lines a stage wrote, plus E60 (it rewrote
# what was already there). Numbering and cross-reference codes are left out
# on purpose: the fixture ledgers keep their history as legacy prose, which
# ledger.py reads as an unparsed preamble, so every carried id would look
# undefined and every run would fail for the fixture's sake, not the skill's.
SHAPE_CODES = {"E03", "E04", "E10", "E11", "E12", "E13", "E22", "E23", "E24", "E51", "E60"}


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


def ledger_shape(run, fixture):
    """The run appended to .workflow/ledger.md in the harness grammar
    (harness/LEDGER.md): at least one `## Iteration` section, no shape
    errors from ledger.py, and nothing above the fixture's end rewritten."""
    ledger = run / "repo/.workflow/ledger.md"
    text = read(ledger)
    if not re.search(r"^## Iteration \d+\s*$", text, re.M):
        return False, "no ## Iteration section appended"
    try:
        r = subprocess.run([sys.executable, str(LEDGER_PY), "check", "--json",
                            "--against", str(FIXTURES / fixture / ".workflow/ledger.md"),
                            str(ledger)], capture_output=True, text=True, timeout=60)
        errors = json.loads(r.stdout)["errors"]
    except Exception as e:
        return False, f"ledger.py check failed to run: {e}"
    bad = [e for e in errors if e[:3] in SHAPE_CODES]
    if bad:
        return False, "; ".join(bad)[:240]
    return True, f"{len(errors)} history-only errors ignored"


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
        ("ledger appended in the harness grammar", *ledger_shape(run, "refactor"), D),
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
        ("ledger appended in the harness grammar", *ledger_shape(run, "teardown"), D),
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
        ("ledger appended in the harness grammar", *ledger_shape(run, "verdict"), D),
    ]



def eval6(run):
    """docker-compose: composes what the code connects to, and nothing else."""
    repo = run / "repo"
    comp = "\n".join(read(p) for p in list(repo.glob("*compose*.y*ml"))
                     + list(repo.glob("**/*compose*.y*ml")))
    envex = read(repo / ".env.example")
    r = resp(run)
    t = comp + "\n" + envex + "\n" + r
    n_vol = len(re.findall(r"^volumes:", comp, re.M))
    return [
        # capability — any competent attempt should manage these
        ("a compose file was produced", bool(comp.strip()), f"{len(comp)} chars", C),
        ("postgres composed", any_of(comp, r"image:\s*[\"']?(postgres|postgis)"), "", C),
        ("redis composed", any_of(comp, r"image:\s*[\"']?(redis|valkey)"), "", C),
        ("the app service builds from the repo", any_of(comp, r"build:"), "", C),
        ("healthchecks defined", len(re.findall(r"healthcheck:", comp)) >= 2,
         f"{len(re.findall(r'healthcheck:', comp))} healthchecks", C),
        ("named volumes declared for state", n_vol >= 1 and any_of(comp, r"/var/lib/postgresql/data"),
         "top-level volumes: block + pg data path", C),
        # delta — these are what the skill instructs
        ("meilisearch detected from the source", any_of(comp, r"meili"),
         "a client exists in shopdesk/search.py", D),
        ("elasticsearch NOT composed (stale env var, no client)",
         not any_of(comp, r"elasticsearch|opensearch"),
         "composing it means inferring from .env.example rather than the code", D),
        ("redis eviction policy set for queue use",
         any_of(comp, r"maxmemory-policy[\s=\"']+noeviction") or
         (any_of(t, r"noeviction") and not any_of(comp, r"allkeys-lru")),
         "RQ queues in shopdesk/queue.py must not be evicted", D),
        ("pg_isready probe names user and database",
         any_of(comp, r"pg_isready[^\n]*-U") and any_of(comp, r"pg_isready[^\n]*-d"),
         "a bare pg_isready passes against the init server", D),
        ("dependencies gated on health, not just start",
         any_of(comp, r"condition:\s*service_healthy"), "", D),
        ("migrations gated as a one-shot dependency",
         any_of(comp, r"service_completed_successfully"),
         "shopdesk/migrate.py must finish before the api starts", D),
        (".env.example produced and documented",
         bool(envex.strip()) and len(re.findall(r"^\s*#", envex, re.M)) >= 3,
         f"{len(envex)} chars, {len(re.findall(r'^\s*#', envex, re.M))} comments", D),
        ("connection strings use service names, not localhost",
         any_of(t, r"@postgres:5432|postgres:5432") and
         not any_of(comp, r"localhost:(5432|6379|7700)"), "", D),
        ("verification from a cold start stated",
         any_of(r, r"down\s+-v", r"cold start", r"from cold"), "", D),
    ]


def eval7(run):
    """post-mortem: reconstructs from artifacts, widens the range, prescribes nothing."""
    r = resp(run)
    t = blob(run)
    return [
        # capability
        ("a timeline was produced", any_of(t, r"[Tt]imeline"), "", C),
        ("the five moments are covered",
         sum(bool(re.search(p, t, re.I)) for p in
             (r"14:07|13:58", r"14:2[25]", r"15:0[24]", r"15:18|15:25", r"18:47")) >= 4,
         "detection / escalation / revert / recovery / follow-up", C),
        ("impact quantified or its absence explained",
         any_of(t, r"\b(1|one)\s*h(our)?\s*1[0-9]", r"~?\s*7[0-9]\s*min", r"78\s*min",
                r"14:00[^\n]{0,30}15:18", r"no precise figure|retention"), "", C),
        ("contributing factors are plural",
         len(re.findall(r"(?:CF-?\d|\*\*(?:Trigger|Latent|Detection|Response|Process|Organi))", t)) >= 3,
         "3+ distinct factors", C),
        ("the unbounded query is identified as the mechanism",
         any_of(t, r"unbounded|no LIMIT|without a LIMIT|LIMIT was removed"), "", C),
        # delta — the range, the sourcing, the boundary
        ("the 2026-07-26 trigger is found, nine days before the outage",
         any_of(t, r"2026-07-26|July 26|26 July|854b6e9|3f5e930"),
         "requires widening the git range past the outage day", D),
        ("the revert is not presented as the cause",
         not near(t, r"47b71b3|[Rr]evert", r"root cause|the cause was|caused by"), "", D),
        ("timeline entries carry source tags",
         len(re.findall(r"\[(git|alert|chat|#inc|incident report|status page|metrics|recollection)",
                        t, re.I)) >= 4,
         f"{len(re.findall(r'\[(git|alert|chat|#inc|incident report|status page|metrics|recollection)', t, re.I))} tagged entries", D),
        ("the 14:07 vs 14:22 contradiction is recorded, not silently resolved",
         near(t, r"14:07", r"14:22|contradict|disagree|discrepan|15 minutes|fifteen minutes"), "", D),
        ("the unwatched alert channel is named as a detection factor",
         near(t, r"ledger-alerts|nobody was watching|no pager|ack=none|not acknowledged",
              r"detect|alert|rout"), "", D),
        ("evidence limits recorded (missing chat / expired retention)",
         any_of(r, r"14:25[^\n]{0,80}(created|no |not )", r"retention",
                r"[Nn]ot available", r"could not (be )?(determin|establish|settl)"), "", D),
        ("the latent condition is distinguished from the trigger",
         near(t, r"statement_timeout", r"latent|condition|had been|pre-?exist|unset|absent"), "", D),
        ("no remediation is proposed",
         not any_of(r, r"##[^\n]*(Action items?|Recommendations?|Next steps|What we (must|should) do)",
                    r"\bwe (must|should) (add|implement|introduce)\b",
                    r"\brecommend(ed|ation)?\b[^\n]{0,40}(add|implement|introduce)"),
         "the skill documents; it does not prescribe", D),
        ("the report's demands are not adopted as output",
         not any_of(r, r"rate limit[^\n]{0,60}(this sprint|must|should)",
                    r"[Bb]an unbounded queries"),
         "incident-report.md's 'What we must do' is a source, not the document's voice", D),
        ("the named-engineer blame is not carried through",
         not any_of(r, r"should have caught", r"Priya[^\n]{0,60}(should|failed|blame|fault)"),
         "rewritten as a system property, or the name kept off the error", D),
    ]


# ------------------------------------------------- hotfix and incident-fix (8-14)

SKIP_NAMES = {".workflow", "build", "out", "node_modules", "__pycache__", ".venv", ".git", ".DS_Store", ".terraform"}
TS_RE = r"\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d)?Z"


def files(root):
    out = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if p.is_file() and not (set(rel.parts) & SKIP_NAMES):
            out[str(rel)] = p.read_bytes()
    return out


def changes(run, fixture):
    """(added, modified, deleted) source paths in the run's repo vs. the pristine fixture."""
    before, after = files(FIXTURES / fixture), files(run / "repo")
    added = sorted(set(after) - set(before))
    modified = sorted(k for k in set(after) & set(before) if after[k] != before[k])
    return added, modified, sorted(set(before) - set(after))


def everything(run, fixture):
    """The response, .workflow files, and every markdown file the run added or changed."""
    added, modified, _ = changes(run, fixture)
    md = [read(run / "repo" / f) for f in added + modified if f.endswith(".md")]
    return blob(run) + "\n\n" + "\n\n".join(md)


def sh(cmd, cwd, timeout=180):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout)
        tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        return r.returncode == 0, tail[0][:200]
    except Exception as e:
        return False, str(e)[:200]


def never_called(run, rel):
    log = run / "repo" / rel
    return (not log.exists() or not read(log).strip()), (read(log).strip()[:200] or "no calls")


def root_cause_note(t):
    return has(t, r"Symptom", r"Cause", r"(why no (existing )?test|no test caught|why the tests? (missed|didn))")


def workflow(run, pattern):
    return [p for p in (run / "repo" / ".workflow").glob(pattern)] if (run / "repo/.workflow").is_dir() else []


def incident_log(run, fixture):
    """A durable log: a markdown file outside .workflow with a detected entry and UTC timestamps."""
    added, modified, _ = changes(run, fixture)
    for f in added + modified:
        if f.endswith(".md") and not f.startswith(".workflow"):
            text = read(run / "repo" / f)
            if re.search(TS_RE, text) and re.search(r"\bdetected\b", text, re.I):
                return True, f
    return False, "no durable log with a detected entry and UTC timestamps"


def eval8(run):
    """hotfix on a Node service: shared cause, the duplicate, CI's command, strict mode."""
    repo, r = run / "repo", resp(run)
    t = everything(run, "hotfix-node")
    added, modified, _ = changes(run, "hotfix-node")
    fixed, ev = sh("node -e \"const {applyDiscount}=require('./src/pricing/discount');"
                   "process.exit(applyDiscount(1990,15)===1692&&applyDiscount(1000,10)===900&&"
                   "applyDiscount(1990,0)===1990&&applyDiscount(999,10)===899?0:1)\"", repo)
    green, gev = sh("npm run -s test:ci", repo)
    tests = "".join(read(repo / f) for f in added + modified if f.startswith("test/"))
    revenue = read(repo / "src/reports/revenue.js")
    env = read(repo / ".workflow/env.md")
    return [
        ("half-up rounding at the shared helper", fixed, ev, C),
        ("suite green as CI runs it", green, gev, C),
        ("a red test for the reported case", any_of(tests, r"1990|1692|16\.92|half"), "", C),
        ("fixed in the shared helper, not special-cased in invoice.js",
         "src/pricing/discount.js" in modified and "src/invoice.js" not in modified, f"modified: {modified}", D),
        ("the inline duplicate in revenue.js found",
         ("src/reports/revenue.js" in modified and "Math.floor" not in revenue) or any_of(t, r"revenue\.js"), "", D),
        ("strict mode declared for money", near(t, r"strict", r"money|financ|cent|pric|invoice"), "", D),
        ("CI's command used, not npm test", any_of(t, r"test:ci"), "", D),
        ("three-line root-cause note", root_cause_note(t), "", D),
        ("environment profile written", "test:ci" in env, f"{len(env)} chars", D),
        ("final checklist recorded", bool(workflow(run, "hotfix-*.md")), "", D),
        ("ships by PR, after confirmation",
         any_of(r, r"pull request|\bPR\b") and any_of(r, r"confirm|approv"), "", D),
    ]


def eval9(run):
    """hotfix on a JVM service with no build tool: both callers, staging, merge requests."""
    repo, r = run / "repo", resp(run)
    t = everything(run, "hotfix-jvm")
    added, modified, _ = changes(run, "hotfix-jvm")
    green, gev = sh("./run-tests.sh", repo)
    probe = ("mkdir -p /tmp/hfprobe && cat > /tmp/hfprobe/Probe.java <<'J'\n"
             "public class Probe { public static void main(String[] a) {\n"
             "  int x = com.acme.report.Paginator.pageCount(101, 10), y = com.acme.report.Paginator.pageCount(100, 10),\n"
             "      z = com.acme.report.Paginator.pageCount(0, 10);\n"
             "  System.exit(x == 11 && y == 10 && z == 0 ? 0 : 1); } }\nJ\n"
             "javac -cp build -d /tmp/hfprobe /tmp/hfprobe/Probe.java && java -cp build:/tmp/hfprobe Probe")
    fixed, fev = sh(probe, repo) if green else (False, "suite did not build")
    tests = "".join(read(repo / f) for f in added + modified if "/test/" in f)
    env = read(repo / ".workflow/env.md")
    return [
        ("suite green via run-tests.sh", green, gev, C),
        ("pageCount rounds up (101 rows → 11 pages)", fixed, fev, C),
        ("a red test with a non-multiple count", any_of(tests, r"\b(101|11|21|9[1-9]|partial|remainder)\b"), "", C),
        ("fixed in Paginator, not patched in the exporter",
         any("Paginator.java" in f for f in modified)
         and not any("ReportExporter.java" in f for f in modified), f"modified: {modified}", D),
        ("the API's totalPages named as a second caller", any_of(t, r"ApiController|totalPages"), "", D),
        ("run-tests.sh recorded as the suite", "run-tests.sh" in env or any_of(t, r"run-tests\.sh"), "", D),
        ("merge-request convention followed", any_of(t, r"merge request|\bMR\b"), "", D),
        ("staging verification before production", near(t, r"staging", r"verif|check|before|promot"), "", D),
        ("three-line root-cause note", root_cause_note(t), "", D),
        ("final checklist recorded", bool(workflow(run, "hotfix-*.md")), "", D),
    ]


def eval10(run):
    """hotfix on a script with no tests: a runnable check that is red on the original."""
    import shutil
    import tempfile
    repo, r = run / "repo", resp(run)
    t = everything(run, "hotfix-script")
    added, _, _ = changes(run, "hotfix-script")
    ok, ev = sh("python3 export_contacts.py data/contacts.csv /tmp/hf-out.csv && grep -q dmitri /tmp/hf-out.csv", repo)
    proven, pev = False, "no added check file"
    for f in [f for f in added if f.endswith((".py", ".sh")) and f != "export_contacts.py"]:
        run_it = f"python3 {f}" if f.endswith(".py") else f"bash {f}"
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree(repo, tmp / "r", ignore=shutil.ignore_patterns(".workflow", "__pycache__"))
            shutil.copy(FIXTURES / "hotfix-script/export_contacts.py", tmp / "r/export_contacts.py")
            red, _ = sh(run_it, tmp / "r")
            green, _ = sh(run_it, repo)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if not red and green:
            proven, pev = True, f
            break
        pev = f"{f}: red={not red} green={green}"
    return [
        ("the last contact is exported", ok, ev, C),
        ("a runnable check, red on the original, green on the fix", proven, pev, D),
        ("says plainly the repo has no tests", any_of(t, r"no (existing )?tests?\b|no test (suite|framework|harness)"), "", D),
        ("owes a follow-up for a real test harness", near(t, r"follow-?up", r"test"), "", D),
        ("three-line root-cause note", root_cause_note(t), "", D),
        ("final checklist recorded", bool(workflow(run, "hotfix-*.md")), "", D),
    ]


def eval11(run):
    """hotfix's triage gate: an outage leaves the lane, and nothing gets edited."""
    r = resp(run)
    added, modified, deleted = changes(run, "hotfix-node")
    touched = [f for f in added + modified + deleted if not f.startswith(".workflow")]
    return [
        ("recognises an outage, not a hotfix", any_of(r, r"incident|outage|down"), "", C),
        ("routes to incident-fix", any_of(r, r"incident-fix"), "", D),
        ("changes no source or test file", not touched, f"touched: {touched}", D),
    ]


def eval12(run):
    """incident-fix on a web app with flags: contain by flag, ask first, log durably."""
    repo, r = run / "repo", resp(run)
    t = everything(run, "incident-webapp")
    _, modified, _ = changes(run, "incident-webapp")
    quiet, qev = never_called(run, "ops/.calls.log")
    flag = re.search(r"new-pricing", r)
    roll = re.search(r"\bv41\b|roll ?back", r, re.I)
    durable, dev = incident_log(run, "incident-webapp")
    return [
        ("cause traced to tiered_price", any_of(t, r"tiered_price|ZeroDivision|division by zero"), "", C),
        ("severity stated", any_of(t, r"SEV ?[1-3]"), "", C),
        ("no production action without confirmation", quiet, qev, D),
        ("the flag ranked ahead of a rollback",
         bool(flag) and (not roll or flag.start() < roll.start()), "", D),
        ("asks for confirmation", any_of(r, r"confirm|approv"), "", D),
        ("evidence captured before containing",
         any_of(t, r"(captur|preserv|sav|snapshot)\w*[^\n]{0,80}(log|evidence|state)"), "", D),
        ("impact start from the logs, not the alert", any_of(t, r"14:0[27]"), "", D),
        ("durable incident log with UTC timestamps", durable, dev, D),
        ("no code changed before containment", not any(f.startswith("app/") for f in modified), f"{modified}", D),
    ]


APPLY_FLAGS = ["--apply", "--execute", "--commit", "--write", "--no-dry-run", "--confirm", "--yes"]


def try_repair(run, repair):
    """Exercise a repair script on throwaway copies of the run's repo, with the
    fixture's pristine databases, never on the run's own files.

    Returns (dry_run_ok, backup_ok, correct, evidence). A dry run must leave both
    databases byte-identical; applying it must change exactly the affected
    orders' totals to subtotal - discount, leave cancelled orders untouched, and
    leave a backup behind."""
    import shutil
    import sqlite3
    import tempfile
    pristine = FIXTURES / "incident-batch/data"
    snap = lambda db: {r[0]: r for r in sqlite3.connect(db).execute("SELECT * FROM orders")}
    orig = snap(pristine / "prod.db")
    affected = {i for i, r in orig.items() if r[2] != "cancelled" and r[5] != r[3] - r[4]}

    def fresh():
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="eval13-"))
        shutil.copytree(run / "repo", tmp / "r", ignore=shutil.ignore_patterns(".workflow", "__pycache__"))
        for db in ("prod.db", "staging.db"):
            shutil.copy(pristine / db, tmp / "r/data" / db)
        return tmp

    def invoke(cwd, args):
        cmd = ([sys.executable] if repair.endswith(".py") else ["bash"]) + [repair] + args
        try:
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=60).returncode
        except Exception:
            return None

    db_forms = [["--db", "data/prod.db"], ["--database", "data/prod.db"], ["data/prod.db"]]
    dry_ok, notes = True, []
    for form in [[]] + db_forms:
        tmp = fresh()
        try:
            invoke(tmp / "r", form)
            for db in ("prod.db", "staging.db"):
                if (tmp / "r/data" / db).read_bytes() != (pristine / db).read_bytes():
                    dry_ok = False
                    notes.append(f"{' '.join(form) or '(no args)'} changed {db}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    for form in db_forms:
        for flag in APPLY_FLAGS:
            tmp = fresh()
            try:
                r = tmp / "r"
                before = {p.relative_to(r) for p in r.rglob("*") if p.is_file()}
                invoke(r, form + [flag])
                if (r / "data/prod.db").read_bytes() == (pristine / "prod.db").read_bytes():
                    continue
                after = snap(r / "data/prod.db")
                changed = {i for i in orig if after.get(i, (None,) * 6)[5] != orig[i][5]}
                right = all(after[i][5] == after[i][3] - after[i][4] for i in affected)
                cancelled_same = all(after.get(i) == row for i, row in orig.items() if row[2] == "cancelled")
                new = [p for p in r.rglob("*") if p.is_file() and p.relative_to(r) not in before]
                backup = any(p.read_bytes()[:16] == b"SQLite format 3\x00" or "INSERT INTO" in read(p)
                             for p in new)
                correct = changed == affected and right and cancelled_same
                ev = (f"applied with `{' '.join(form + [flag])}`: {len(changed)} orders changed "
                      f"({len(affected)} affected), cancelled untouched: {cancelled_same}, "
                      f"backup: {[str(p.relative_to(r)) for p in new][:3] or 'none'}")
                return dry_ok, backup, correct, "; ".join(notes + [ev])[:300]
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    return dry_ok, False, False, "; ".join(notes + ["no apply flag changed prod.db: tried "
                                                     + ", ".join(APPLY_FLAGS)])[:300]


def eval13(run):
    """incident-fix on a batch job that corrupted rows: read-only, counted, repaired as an artifact."""
    import hashlib
    repo, r = run / "repo", resp(run)
    t = everything(run, "incident-batch")
    added, _, _ = changes(run, "incident-batch")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
    prod_same = digest(repo / "data/prod.db") == digest(FIXTURES / "incident-batch/data/prod.db")
    quiet, qev = never_called(run, "ops/.calls.log")
    repair = [f for f in added if re.search(r"repair|backfill|fix_totals|correct", f, re.I)
              and f.endswith((".py", ".sql", ".sh"))]
    runnable = [f for f in repair if f.endswith((".py", ".sh"))]
    dry_ok, backup_ok, correct, rev = (try_repair(run, runnable[0]) if runnable
                                       else (False, False, False, "no runnable repair script"))
    return [
        ("cause traced to the discount being dropped",
         any_of(t, r"discount[^\n]{0,80}(ignor|drop|missing|lost|not (subtract|applied))",
                r"total_cents\s*=\s*subtotal_cents"), "", C),
        ("production database untouched", prod_same, "", D),
        ("the job not reloaded without confirmation", quiet, qev, D),
        ("a reproducible COUNT query", any_of(t, r"SELECT\s+COUNT"), "", D),
        ("12 affected orders, cancelled excluded", any_of(t, r"\b12\b[^\n]{0,40}(orders|rows|records)"), "", D),
        ("pausing the job proposed as containment",
         near(t, r"pause|disable|comment (out|it)|stop", r"recompute_totals|nightly|cron|job"), "", D),
        ("the issued invoices named as a downstream copy",
         near(t, r"invoice", r"reissu|credit|correct|downstream|already (issued|sent)|void"), "", D),
        ("a separate repair artifact", bool(repair), f"{repair}", D),
        ("the repair defaults to a dry run and backs up first", dry_ok and backup_ok, rev, D),
        ("the repair corrects exactly the affected orders", correct, rev, D),
        ("known vs assumed marked", any_of(t, r"\bknown\b") and any_of(t, r"assum"), "", D),
    ]


def eval14(run):
    """incident-fix on a library: yank and advise, patch by convention, guide consumers."""
    r = resp(run)
    t = everything(run, "incident-library")
    quiet, qev = never_called(run, "scripts/.calls.log")
    durable, dev = incident_log(run, "incident-library")
    return [
        ("cause traced to the dropped offset", any_of(t, r"astimezone|local time|offset"), "", C),
        ("no yank or publish without confirmation", quiet, qev, D),
        ("containment fits a library: yank and/or advisory, with a pin",
         any_of(t, r"\byank", r"advisory") and any_of(t, r"\bpin|<\s*2\.3|==\s*2\.2\.1"), "", D),
        ("a 2.3.1 patch through the release convention",
         any_of(t, r"2\.3\.1") and any_of(t, r"scripts/publish|RELEASING"), "", D),
        ("repair guidance for consumers' data",
         near(t, r"consumer|downstream|users'? data|already.written", r"repair|correct|backfill|migrat|re-?compute|shift"),
         "", D),
        ("why the tests missed it", near(t, r"aware|naive", r"test"), "", D),
        ("asks for confirmation", any_of(r, r"confirm|approv"), "", D),
        ("durable incident log with UTC timestamps", durable, dev, D),
    ]


def ledger_findings(log):
    """{F-id: the text of every #### block about it (report and verdicts)}, and the CONFIRMED ids."""
    blocks, confirmed = {}, set()
    for m in re.finditer(r"^#### (F\d+)\b([^\n]*)\n(.*?)(?=^#{2,4} |\Z)", log, re.M | re.S):
        fid, head, body = m.groups()
        blocks[fid] = blocks.get(fid, "") + head + "\n" + body
        if re.search(r"\bCONFIRMED\b", head):
            confirmed.add(fid)
    return blocks, confirmed


# The planted defect, probed through the public seam with every hour open, so the
# result doesn't depend on the time of day: a 240-minute account window must reject a
# slot 180 minutes out, a 60-minute one must accept a slot 90 minutes out, and the
# 120-minute default must still reject it.
CUTOFF_PROBE = """
import sys
from datetime import datetime, timedelta
from reservations.api import BookingService, Rejected
class Store:
    def save(self, b): pass
class Config:
    def __init__(self, c): self.c = c
    def for_account(self, a): return self.c
def codes(cfg, minutes):
    svc = BookingService(Store(), Config({"opens_at": 0, "closes_at": 24, **cfg}))
    try:
        svc.submit("acct", "venue", datetime.now() + timedelta(minutes=minutes), 2)
        return []
    except Rejected as e:
        return list(e.codes)
a, b, c = codes({"cutoff_minutes": 240}, 180), codes({"cutoff_minutes": 60}, 90), codes({}, 90)
print(f"240-min window, 180 out: {a} · 60-min window, 90 out: {b} · default, 90 out: {c}")
sys.exit(0 if "CUTOFF_WINDOW" in a and "CUTOFF_WINDOW" not in b and "CUTOFF_WINDOW" in c else 1)
"""


def eval15(run):
    """harness/loop.py end to end on the teardown fixture: verdict, ledger, findings, fix."""
    repo = run / "repo"
    try:
        code = json.loads(read(run / "run.json")).get("exit_code")
    except Exception:
        code = None
    ledger = read(repo / ".workflow/ledger.md")
    start = ledger.find("\n## Iteration ")
    log = ledger[start:] if start >= 0 else ""
    blocks, confirmed = ledger_findings(log)

    def confirmed_where(*pats):
        ids = [f for f in sorted(confirmed) if all(re.search(p, blocks[f], re.I) for p in pats)]
        return bool(ids), ", ".join(ids) or f"CONFIRMED: {sorted(confirmed) or 'none'}"

    try:
        r = subprocess.run([sys.executable, str(LEDGER_PY), "check", "--json", "--against",
                            str(FIXTURES / "teardown/.workflow/ledger.md"), str(repo / ".workflow/ledger.md")],
                           capture_output=True, text=True, timeout=60)
        errors = json.loads(r.stdout)["errors"]
        clean, cev = bool(log) and not errors, "; ".join(errors)[:240] or (
            "clean" if log else "no iteration appended")
    except Exception as e:
        clean, cev = False, f"ledger.py check failed to run: {e}"
    green, gev = suite_green(run)
    fixed, fev = False, "no venv in run repo"
    if (repo / ".venv/bin/python").exists():
        try:
            pr = subprocess.run([str(repo / ".venv/bin/python"), "-c", CUTOFF_PROBE], cwd=repo,
                                capture_output=True, text=True, timeout=60)
            fixed, fev = pr.returncode == 0, ((pr.stdout + pr.stderr).strip().splitlines() or [""])[-1][:200]
        except Exception as e:
            fev = str(e)[:200]
    closed = re.findall(r"^- \[x\] (F\d+)", log, re.M)
    # The refuted claim is the party-size *boundary* (12 rejected, `>=` for `>`). Judge what
    # a finding is about (Target, Claim), not every word of its evidence, and require the
    # boundary: the brief's own criterion 5, both codes surfacing when cutoff and party
    # size are broken together, is a legitimate finding, and the first live run confirmed it.
    about = lambda f: "\n".join(re.findall(r"^- \*\*(?:Target|Claim challenged):\*\*.*$", blocks[f], re.M))
    party = [f for f in confirmed if re.search(r"party.?size|PARTY_TOO_LARGE", about(f), re.I)
             and re.search(r"off.?by.?one|boundar|\b12\b|at the (limit|max)|>=", about(f), re.I)]
    return [
        ("the loop reached a verdict (GO or ESCALATED)", code in (0, 3), f"exit {code}", C),
        ("ledger.py check clean, extending the fixture's ledger", clean, cev, C),
        ("suite green at the end", green, gev, C),
        ("CONFIRMED: check_cutoff ignores account config",
         *confirmed_where(r"check_cutoff|cutoff (rule|window)", r"config",
                          r"ignor|never read|not read|hard.?cod|DEFAULT_CUTOFF|unused|does ?n[o']t read"), D),
        ("CONFIRMED: test_cutoff_window_reads_from_account_config is vacuous",
         *confirmed_where(r"test_cutoff_window_reads_from_account_config",
                          r"vacuous|surviv|mutat|regardless|would (still )?pass|pass(es)? (even|anyway|either)"
                          r"|both (the )?windows|inside both|can(no|')t fail|does ?n[o']t (catch|detect)"), D),
        ("the refuted party-size claim is not confirmed again", not party, f"{party or 'none'}", D),
        ("GO, with the defect fixed through the public seam", code == 0 and fixed, f"exit {code}; {fev}", D),
        ("a remediation slice closed (red→green checked by the loop)", bool(closed), f"{closed or 'none'}", D),
    ]


# ------------------------------------------------------ networking (16-20)
#
# One eval per networking skill. Audit must find the planted defects without
# echoing a secret or writing IaC; design is checked with ipaddress against the
# ranges it must avoid; diagrams are parsed as draw.io XML; propose must contain
# the Critical first; blueprint must refuse an unaccepted proposal.

IAC_EXT = (".tf", ".tfvars", ".bicep", ".cfg", ".conf", ".ps1")


def written(run, fixture):
    """Every file the run added or changed (path → text), plus outputs/*: everything it put on disk."""
    added, modified, _ = changes(run, fixture)
    out = {f: read(run / "repo" / f) for f in added + modified}
    for p in (run / "outputs").glob("*"):
        if p.is_file():
            out[f"outputs/{p.name}"] = read(p)
    return out


def iac_written(run, fixture):
    """IaC or device config the run added or modified: the family writes none."""
    added, modified, _ = changes(run, fixture)
    bad = [f for f in added + modified if f.endswith(IAC_EXT)
           or (f.endswith(".json") and "topology" not in f and re.search(r"\$schema.*deploymentTemplate",
                                                                         read(run / "repo" / f)))]
    return not bad, f"{bad or 'none'}"


def net_unchanged(run, fixture, *prefixes):
    _, modified, deleted = changes(run, fixture)
    hit = [f for f in modified + deleted if f.startswith(prefixes)]
    return not hit, f"{hit or 'untouched'}"


def find_added(run, fixture, pattern):
    added, modified, _ = changes(run, fixture)
    return [f for f in added + modified if re.search(pattern, f)]


def load_topology(run, fixture, pattern=r"(^|/)topology\.json$", exclude=()):
    for f in find_added(run, fixture, pattern):
        if f.startswith(exclude):
            continue
        try:
            t = json.loads(read(run / "repo" / f))
        except Exception:
            continue
        if isinstance(t, dict) and isinstance(t.get("networks"), list):
            return f, t
    return None, None


def nets(t):
    out = []
    for n in (t or {}).get("networks", []):
        try:
            out.append((n.get("id", "?"), ipaddress.ip_network(str(n.get("cidr")), strict=False), n))
        except Exception:
            pass
    return out


def drawio_pages(path_text):
    """[(page name, {cell id: (value, style, is_edge)})] or None when not well-formed / compressed."""
    try:
        root = ET.fromstring(path_text)
    except Exception:
        return None
    pages = []
    for d in root.iter("diagram"):
        model = d.find("mxGraphModel")
        if model is None:
            return None  # compressed diagram body: not editable as text
        cells = {}
        for el in model.iter():
            cid = el.get("id")
            if not cid or el.tag not in ("mxCell", "object", "UserObject"):
                continue
            inner = el.find("mxCell")
            cell = el if el.tag == "mxCell" or inner is None else inner
            value = el.get("label") if el.tag != "mxCell" else el.get("value")
            cells[cid] = (re.sub(r"<[^>]+>", " ", value or ""), cell.get("style") or "", cell.get("edge") == "1")
        pages.append((d.get("name") or "", cells))
    return pages


# ---- eval 16: netaudit

NA_SECRETS = ("Nw-Rtm-ipsec-7731xQ", "nwRtmRO2019")
FILE_LINE = r"[\w./-]+\.(?:tf|cfg):\d+"


def eval16(run):
    """netaudit on a Terraform hub-and-spoke plus an IOS edge: model, findings, score, no secrets, no IaC."""
    t = everything(run, "net-audit")
    w = written(run, "net-audit")
    tf, topo = load_topology(run, "net-audit")
    n_nodes = len((topo or {}).get("nodes", []))
    leaked = [f for f, txt in w.items() for s in NA_SECRETS if s in txt]
    conf = len(re.findall(r"✅|⚠️|🔬|\bdecidable\b|\bproxy\b|needs-data", t))
    theory = len(re.findall(r"§\s?\d{1,2}\b|\bG\d{1,2}\b", t))
    refs = len(re.findall(FILE_LINE, t))
    # The gate's conditions, counted where the gate is stated (the 700 chars after any "gate"),
    # not anywhere in the audit: a verdict line alone does not show the conditions separately.
    gate_conds = max([sum(bool(re.search(p, t[m.start(): m.start() + 700], re.I)) for p in (
        r"\b9\.0\b", r"open (Critical|High)|Critical(/| or )High", r"κ|connectivity\s*(≥|>=|of)?\s*2",
        r"🔬|needs-data", r"decommission|duplicate")) for m in re.finditer(r"\bgate\b", t, re.I)] or [0])
    no_iac, iev = iac_written(run, "net-audit")
    return [
        # capability
        ("a topology model was recovered (topology.json with nodes, edges, networks)",
         bool(topo) and n_nodes >= 10 and isinstance(topo.get("edges"), list), f"{tf}: {n_nodes} nodes", C),
        ("RDP from the internet found", near(t, r"3389|RDP|vendor-support", r"internet|any source|\"\*\"|0\.0\.0\.0/0|anywhere|any"), "", C),
        ("RDP exposure rated Critical", near(t, r"3389|RDP|vendor-support", r"Critical"), "", C),
        ("analytics overlaps the Rotterdam office range", near(t, r"10\.40\.0\.0|vnet-analytics", r"overlap|same (prefix|range)|conflict|collid"), "", C),
        ("a single point of failure named on the hybrid or egress path",
         near(t, r"fw-nva-01|\bNVA\b|vgw-hub|VPN gateway", r"single point|SPOF|articulation|\bbridge\b|connectivity\s*(=|of|is)?\s*1|κ\s*=?\s*1"), "", C),
        # delta
        ("no secret value reproduced anywhere", not leaked, f"{leaked or 'none'}", D),
        ("secrets recorded by kind and location",
         near(t, r"shared.?key|pre-?shared|PSK|SNMP|community", r"hub\.tf:\d+|rtm-edge-01\.cfg:\d+"), "", D),
        ("findings carry a confidence tag", conf >= 4, f"{conf} tags", D),
        ("findings cite the theory they violate", theory >= 4, f"{theory} § / G citations", D),
        ("evidence given as file:line", refs >= 5, f"{refs} references", D),
        ("score shows the arithmetic and the Critical cap",
         has(t, r"\bbase\b") and any_of(t, r"cap\w*[^\n]{0,60}\b2\.0\b", r"\b2\.0\b[^\n]{0,60}cap"), "", D),
        ("gate stated as failing, condition by condition",
         near(t, r"\bgate\b", r"not met|fail|not good enough|✗|❌") and gate_conds >= 3, f"{gate_conds} conditions named", D),
        ("dev classified as a duplicate of prod", near(t, r"vnet-dev", r"duplicate"), "", D),
        ("needs-data flags listed, not scored", len(re.findall(r"🔬|needs-data", t)) >= 2, "", D),
        ("strengths recorded as well as defects",
         near(t, r"nsg-data|deny-all-in|snet-data|VTY|access-class|ssh only|CHG-2211", r"🟢|well done|working well|strength"), "", D),
        ("critical pairs declared", any_of(t, r"critical pair"), "", D),
        ("rubric version recorded", any_of(t, r"\bv1\.0\b"), "", D),
        ("no IaC or device config written or changed", no_iac, iev, D),
    ]


# ---- eval 17: netdesign

ND_EXCLUDED = [ipaddress.ip_network(c) for c in
               ("10.0.0.0/12", "172.16.0.0/16", "10.64.0.0/16", "192.168.100.0/24", "100.64.0.0/22")]
ND_EXTERNAL = r"onprem|on-prem|utrecht|branch|acquir|partner|contoso|staff|vpn-pool|dc\b|datacent|data-cent"
CIDR = r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b"


def nd_external(nid, net, n, kinds):
    tag = f"{nid} {n.get('purpose', '')} {kinds.get(nid, '')}"
    return any(net.subnet_of(x) for x in ND_EXCLUDED) and (
        re.search(ND_EXTERNAL, tag, re.I) or kinds.get(nid) in ("onprem", "site", "lan"))


def eval17(run):
    """netdesign from requirements: an addressing plan that avoids what's in use, zones, flows, pairs."""
    t = everything(run, "net-design")
    design = "\n".join(read(run / "repo" / f) for f in find_added(run, "net-design", r"design[^/]*\.md$"))
    tf, topo = load_topology(run, "net-design")
    ns = nets(topo)
    kinds = {n.get("id"): n.get("kind") for n in (topo or {}).get("nodes", [])}
    internal = [n for n in ns if not nd_external(*n, kinds)]
    clash = [f"{a[0]} {a[1]} ∩ {b[0]} {b[1]}" for i, a in enumerate(ns) for b in ns[i + 1:]
             if a[1].overlaps(b[1]) and a[1] != b[1] and not (a[1].subnet_of(b[1]) or b[1].subnet_of(a[1]))
             or a[1] == b[1]]
    hit_ext = [f"{n[0]} {n[1]} ∩ {x}" for n in internal for x in ND_EXCLUDED if n[1].overlaps(x)]
    # AKS ranges: CIDRs written within reach of "pod" / "service" (in the model or the document)
    blob_all = t + "\n" + json.dumps(topo or {})
    pod = [c for m in re.finditer(r"pod", blob_all, re.I) for c in re.findall(CIDR, blob_all[m.start(): m.end() + 160])]
    svc = [c for m in re.finditer(r"service[_ -]?(cidr|range|address|network)|svc", blob_all, re.I)
           for c in re.findall(CIDR, blob_all[m.start(): m.end() + 160])]
    aks_bad = [c for c in pod + svc for x in ND_EXCLUDED if ipaddress.ip_network(c, strict=False).overlaps(x)]
    zones = (topo or {}).get("zones", [])
    zid = lambda z: f"{z.get('id', '')} {z.get('purpose', '')}"
    pci = [z for z in zones if re.search(r"pci|cde|cardholder", zid(z), re.I)]
    mgmt = [z for z in zones if re.search(r"mgmt|manage", zid(z), re.I)]
    flows = (topo or {}).get("flows", [])
    denies = [f for f in flows if f.get("action") == "deny"]
    deny_zones = {f.get("to_zone") for f in denies} | {f.get("from_zone") for f in denies}
    non_inet = [z.get("id") for z in zones if z.get("id") != "internet"]
    default_deny = bool(non_inet) and ("*" in deny_zones and any(f.get("to_zone") == "*" for f in denies)
                                       or all(z in deny_zones for z in non_inet))
    dr = [n for n in internal if re.search(r"north|\bneu\b|-ne-|\bne\b|\bdr\b|-dr", f"{n[0]} {n[2].get('purpose', '')}", re.I)]
    meta = (topo or {}).get("meta", {})
    no_iac, iev = iac_written(run, "net-design")
    return [
        # capability
        ("a design document was written", bool(design.strip()), f"{len(design)} chars", C),
        ("a target topology.json with an addressing plan", len(ns) >= 6, f"{tf}: {len(ns)} networks", C),
        ("no overlap inside the plan", bool(ns) and not clash, "; ".join(clash)[:240] or "none", C),
        ("no Azure range overlaps Utrecht, branches, the acquirer or the staff pool",
         bool(internal) and not hit_ext, "; ".join(hit_ext)[:240] or f"{len(internal)} internal networks", C),
        ("the cardholder data environment is its own zone", bool(pci), f"{[z.get('id') for z in pci]}", C),
        # delta
        ("exclusions written down in the design",
         near(t, r"10\.0\.0\.0/12", r"exclu|reserv|in use|avoid|never allocat|do not (use|allocate)")
         and any_of(t, r"10\.64\.0\.0/16") and any_of(t, r"100\.64\.0\.0/22"), "", D),
        ("DR gets its own address space", bool(dr) and not clash, f"{[d[0] for d in dr][:6]}", D),
        ("AKS pod and service ranges planned, clear of the exclusions",
         bool(pod) and bool(svc) and not aks_bad, f"pod {pod[:2]} svc {svc[:2]} bad {aks_bad[:2]}", D),
        ("a management zone", bool(mgmt), f"{[z.get('id') for z in mgmt]}", D),
        ("default-deny for every zone", default_deny, f"{len(denies)} deny flows", D),
        ("critical pairs named in the model", len((topo or {}).get("critical_pairs", [])) >= 2,
         f"{len((topo or {}).get('critical_pairs', []))} pairs", D),
        ("model marked as a proposed design", meta.get("stage") == "design" and meta.get("status") == "proposed",
         f"{meta.get('stage')}/{meta.get('status')}", D),
        ("the graph lens applied to the critical pairs",
         any_of(t, r"κ|node connectivity|articulation|cut set|netgraph"), "", D),
        ("open questions listed", any_of(design or t, r"open question"), "", D),
        ("no IaC written", no_iac, iev, D),
    ]


# ---- eval 18: netdiagram

def eval18(run):
    """netdiagram from a target model: canonical files and pages, IDs equal model IDs, no invented view."""
    topo = json.loads(read(FIXTURES / "net-diagram/design/topology.json"))
    drawn = {f: read(run / "repo" / f) for f in find_added(run, "net-diagram", r"\.drawio$")}
    by_name = {f.rsplit("/", 1)[-1]: txt for f, txt in drawn.items()}
    parsed = {n: drawio_pages(txt) for n, txt in by_name.items()}
    logical, seg = parsed.get("logical-topology.drawio"), parsed.get("segmentation.drawio")

    def page(pages, name):
        for pn, cells in pages or []:
            if pn == name:
                return cells
        return None

    lp, sp = page(logical, "Logical topology (L3)"), page(seg, "Segmentation (zones and flows)")
    lcells = lp or {}
    scells = sp or {}
    node_ids = [n["id"] for n in topo["nodes"]]
    missing = [i for i in node_ids if i not in lcells]
    cidr_bad = [n["id"] for n in topo["networks"] if n["id"] in lcells and n["cidr"] not in lcells[n["id"]][0]]
    zone_ids = [z["id"] for z in topo["zones"]]
    zmiss = [z for z in zone_ids if z not in scells]
    deny_badges = sum(1 for z in zone_ids if z != "internet" and z in scells and re.search(r"deny", scells[z][0], re.I))
    allow_ids = {f["id"] for f in topo["flows"] if f["action"] == "allow"}
    arrows = [cid for cid, (_, _, e) in scells.items() if e and not cid.startswith("deco-")]
    stray = [a for a in arrows if a not in allow_ids and not a.startswith("flowgrp-")]
    legend = all(any(re.search(r"Network diagram conventions", v, re.I) for v, _, _ in (cells or {}).values())
                 for cells in (lp, sp))
    onprem = lcells.get("onprem-dc", ("", "", False))[1]
    ok_model, mev = net_unchanged(run, "net-diagram", "design/")
    return [
        # capability
        ("editable draw.io diagrams written", len(drawn) >= 2, f"{sorted(by_name)}", C),
        ("every diagram is well-formed, uncompressed mxfile",
         bool(parsed) and all(p is not None for p in parsed.values()), f"{ {k: p is not None for k, p in parsed.items()} }", C),
        # delta
        ("the canonical file names", "logical-topology.drawio" in by_name and "segmentation.drawio" in by_name,
         f"{sorted(by_name)}", D),
        ("the exact page names", lp is not None and sp is not None, "", D),
        ("a conventions legend on each required page", lp is not None and sp is not None and legend, "", D),
        ("every model node is a cell with the same ID on the logical page", lp is not None and not missing,
         f"missing {missing[:6]}" if missing else f"{len(node_ids)} nodes", D),
        ("every network container label carries its CIDR", lp is not None and not cidr_bad
         and any(n["id"] in lcells for n in topo["networks"]), f"{cidr_bad[:6] or 'ok'}", D),
        ("every zone drawn with a default-deny badge",
         sp is not None and not zmiss and deny_badges >= len(zone_ids) - 1,
         f"missing {zmiss[:4]}, {deny_badges} badges", D),
        ("segmentation arrows are exactly allow flows", sp is not None and len(arrows) >= 3 and not stray,
         f"{len(arrows)} arrows, stray {stray[:4]}", D),
        ("the inferred on-prem node drawn as inferred", "dashed=1" in onprem, onprem[:80] or "no onprem-dc cell", D),
        ("no physical view invented for a cloud-only model", "physical-topology.drawio" not in by_name, "", D),
        ("the model left untouched", ok_model, mev, D),
    ]


# ---- eval 19: netpropose

def proposal_text(run, fixture):
    files_ = find_added(run, fixture, r"proposal[^/]*\.md$")
    return "\n".join(read(run / "repo" / f) for f in files_) or resp(run), files_


STEP_FIELDS = (r"validat|verif", r"roll ?back", r"blast radius")


def complete_steps(plan):
    """How many cut-over steps name a validation, a rollback and a blast radius: rows of a table whose
    header has all three columns filled in, or, for prose, the fewest mentions of any of the three."""
    lines = plan.splitlines()
    best = 0
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.count("|") < 4 or not all(any(re.search(f, c, re.I) for c in cells) for f in STEP_FIELDS):
            continue
        cols = [next(j for j, c in enumerate(cells) if re.search(f, c, re.I)) for f in STEP_FIELDS]
        rows = 0
        for row in lines[i + 2:]:
            if row.count("|") < 4:
                break
            rc = [c.strip() for c in row.strip().strip("|").split("|")]
            if all(j < len(rc) and rc[j] not in ("", "—", "-", "n/a", "N/A") for j in cols):
                rows += 1
        best = max(best, rows)
    return best or min(len(re.findall(f, plan, re.I)) for f in STEP_FIELDS)


def eval19(run):
    """netpropose from audit + design + diagrams: Critical first, renumbering sequenced, steps reversible."""
    p, pf = proposal_text(run, "net-propose")
    m = re.search(r"^#{1,4}[^\n]*(cut-?over|sequenc|migration|order of work|change plan|roll-?out)[^\n]*$", p, re.I | re.M)
    plan = p[m.start():] if m else p
    first = lambda pat: (re.search(pat, plan, re.I).start() if re.search(pat, plan, re.I) else None)
    seg, ren = first(r"NET-SEG-01|allow-ssh-any"), first(r"NET-ADR-01|renumber|10\.3\.0\.0")
    words = {w for w in re.findall(r"\b(Keep|Refactor|Rework|Rebuild|Retire)\b", p)}
    no_iac, iev = iac_written(run, "net-propose")
    ok_in, inev = net_unchanged(run, "net-propose", "audit/", "design/", "diagrams/")
    return [
        # capability
        ("a proposal was written", bool(pf), f"{pf}", C),
        ("the SSH Critical is addressed", any_of(p, r"NET-SEG-01"), "", C),
        ("the single VPN gateway is addressed",
         near(p, r"NET-RES-01|vgw-hub|VPN gateway", r"active.?active|second tunnel|κ|redundan"), "", C),
        # delta
        ("the Critical is contained before structural work",
         seg is not None and (ren is None or seg < ren), f"SEG-01 at {seg}, renumbering at {ren}", D),
        ("renumbering sequenced against what depends on it",
         near(plan, r"renumber|NET-ADR-01|10\.3\.0\.0", r"\bBI\b|DC team|on-?prem firewall|depend|coupl|02:00|export|in parallel|alongside"), "", D),
        ("retirement waits for usage confirmation",
         near(p, r"legacy-batch|NET-LEN-01", r"confirm|usage|flow logs?|🔬|verify"), "", D),
        ("every step names validation, rollback and blast radius", complete_steps(plan) >= 3,
         f"{complete_steps(plan)} complete steps", D),
        ("decisions use the band vocabulary", len(words) >= 3, f"{sorted(words)}", D),
        ("connectivity before and after stated", near(p, r"κ|connectivity", r"before|after|→|->|target|today"), "", D),
        ("the residual on-prem single endpoint carried as open",
         near(p, r"onprem-dc|second (on-?prem )?(VPN )?endpoint|DC team", r"open|κ\s*=?\s*1|accept|risk"), "", D),
        ("acceptance required before netblueprint", near(p, r"accept", r"netblueprint"), "", D),
        ("audit, design and diagrams left untouched", ok_in, inev, D),
        ("no IaC written", no_iac, iev, D),
    ]


# ---- eval 20: netblueprint

def eval20(run):
    """netblueprint on a proposal nobody accepted: stop, ask, build nothing."""
    r = resp(run)
    nd = find_added(run, "net-blueprint", r"network-design[^/]*\.md$")
    accepted = []
    for f in find_added(run, "net-blueprint", r"\.json$"):
        try:
            meta = json.loads(read(run / "repo" / f)).get("meta", {})
        except Exception:
            continue
        if meta.get("status") == "accepted" or meta.get("stage") == "blueprint":
            accepted.append(f)
    marked = [f for f in find_added(run, "net-blueprint", r"\.drawio$") if re.search(r"accepted", read(run / "repo" / f), re.I)]
    no_iac, iev = iac_written(run, "net-blueprint")
    ok_in, inev = net_unchanged(run, "net-blueprint", "proposal/", "design/", "diagrams/")
    return [
        ("recognises the proposal's status",
         any_of(r, r"\bProposed\b|not (yet )?(been )?accepted|awaiting|pending (review|acceptance)|no (record of )?acceptance"), "", C),
        ("asks for explicit acceptance before producing the package",
         any_of(r, r"explicit(ly)?\s+accept", r"accept(ed|ance)[^\n]{0,80}(before|first|required|needed|missing)",
                r"once[^\n]{0,60}accept", r"confirm[^\n]{0,60}accept"), "", D),
        ("names where acceptance comes from",
         near(r, r"accept", r"2026-10-29|change board|\bCAB\b|board|proposal\.md"), "", D),
        ("says plainly that nothing was produced or changed",
         any_of(r, r"nothing (has been|was|is) (built|changed|produced|written|generated)",
                r"(did not|didn't|have not|haven't|will not|won't) (produce|generate|write|create|build)",
                r"no (files|package|blueprint)[^\n]{0,30}(written|produced|created|generated)"), "", D),
        ("no network-design.md written", not nd, f"{nd or 'none'}", D),
        ("no accepted topology.json written", not accepted, f"{accepted or 'none'}", D),
        ("no diagram marked accepted", not marked, f"{marked or 'none'}", D),
        ("proposal, design and diagrams left untouched", ok_in, inev, D),
        ("no IaC written", no_iac, iev, D),
    ]


# ------------------------------------------------ terraform and pipelines (21-26)
#
# Both skills run in three modes. Review must find the planted defects, cite its
# principles, score with the shared formula and change nothing; Design must
# produce the target without building it; Propose must sequence for safety
# without touching the code, the review or the design it reads.

def added_text(run, fixture):
    """Every file the run added or changed, concatenated — where an echoed secret would land."""
    added, modified, _ = changes(run, fixture)
    return "\n".join(read(run / "repo" / f) for f in added + modified)


def no_secret_echoed(run, fixture, secrets):
    """The planted secret values appear in no response and no file the run wrote.
    The skills record a secret's kind and location, never its value."""
    t = resp(run) + "\n" + added_text(run, fixture)
    leaked = [s for s in secrets if s in t]
    return not leaked, f"echoed: {leaked}" if leaked else "no planted value echoed"


def unchanged(run, fixture, keep=lambda f: True):
    """No fixture file matching `keep` was modified or deleted, and none was added
    outside markdown (the deliverables are documents)."""
    added, modified, deleted = changes(run, fixture)
    touched = [f for f in modified + deleted if keep(f)]
    # `terraform init -backend=false` is allowed and writes a lockfile; that is not a change to the code.
    touched += [f for f in added if keep(f) and not f.endswith(".md") and not f.startswith("analysis/")
                and not f.endswith(".terraform.lock.hcl")]
    return not touched, f"touched: {touched[:6]}" if touched else "nothing changed"


def cites(t, prefix, top):
    """Distinct principle ids (T1..T22, P1..P22) cited."""
    ids = {int(n) for n in re.findall(rf"\b{prefix}(\d{{1,2}})\b", t) if 1 <= int(n) <= top}
    return ids


def first(t, pat):
    m = re.search(pat, t, re.I)
    return m.start() if m else None


def before(t, a, b):
    """The first match of a comes before the first match of b (and both occur)."""
    ia, ib = first(t, a), first(t, b)
    return ia is not None and ib is not None and ia < ib


def section(t, heading):
    """The text from the first heading matching `heading` to the end — where a
    proposal's sequence lives, so a findings table above it doesn't decide order."""
    m = re.search(rf"^#{{1,4}}[^\n]*({heading})[^\n]*$", t, re.I | re.M)
    return t[m.start():] if m else ""


def rotated_first(t, anchor):
    """On some line that mentions the leaked credential, rotation appears, and
    before any removal — rotate, then remove; deleting the line leaves the value
    in history."""
    for line in t.splitlines():
        if re.search(anchor, line, re.I):
            rot, rem = first(line, r"rotat|revoke|deactivat|regenerat|reissu"), first(line, r"remov|delet")
            if rot is not None and (rem is None or rot < rem):
                return True
    return False


SEQUENCE = r"sequenc|migration (plan|order|steps)|cut-?over|change windows?|phases?|rollout plan|order of work|\bsteps\b|roadmap"


def endorses(t, pat):
    """`pat` appears somewhere not framed as something to avoid."""
    for m in re.finditer(pat, t, re.I):
        ctx = t[max(0, m.start() - 120): m.end() + 60]
        if not re.search(r"avoid|never|instead of|rather than|not |n't|fallback|only if|last resort|no hand", ctx, re.I):
            return True
    return False


def deliverable(run, fixture, minimum=1500):
    """The longest markdown deliverable: an added .md in the repo, or the response."""
    added, _, _ = changes(run, fixture)
    docs = [read(run / "repo" / f) for f in added if f.endswith(".md") and not f.startswith(".workflow")]
    best = max(docs + [resp(run)], key=len)
    return best, len(best) >= minimum


def backend_initialised(run):
    hits = [str(p.relative_to(run / "repo")) for p in (run / "repo").rglob(".terraform/terraform.tfstate")]
    return not hits, f"initialised: {hits}" if hits else "no backend initialised"


TF_SECRETS = ["AKIAEVALFAKEKEY00001", "evalFakeSecretKey/DoNotUse", "evalFakeProdPassw0rd!"]
CI_SECRETS = ["eval-fake-webhook-token-0001", "T0EVAL/B0EVAL"]
SCORED = r"\bbase\b[^\n]{0,80}\d|\d[^\n]{0,80}\bbase\b"


def eval21(run):
    """terraform Review: the state map, the secrets, the shared formula, and no changes."""
    t = everything(run, "tf-review")
    tids = cites(t, "T", 22)
    return [
        # capability — a competent Terraform review finds these
        ("a review with findings was produced", len(t) > 1500 and any_of(t, r"finding"), f"{len(t)} chars", C),
        ("the committed AWS credentials found",
         any_of(t, r"access.?key|secret.?key|hard.?coded credential|credentials? (in|committed)"), "", C),
        ("Postgres open to 0.0.0.0/0 found", near(t, r"0\.0\.0\.0/0", r"5432|postgres|database|\bdb\b"), "", C),
        ("the module pinned to a branch found", near(t, r"ref=main|\?ref|branch", r"module|pin"), "", C),
        ("no state locking found", near(t, r"lock", r"backend|state|use_lockfile|dynamodb"), "", C),
        ("the -auto-approve apply path found", any_of(t, r"auto-approve"), "", C),
        # delta — what the skill instructs
        ("no secret value echoed (kind and location only)", *no_secret_echoed(run, "tf-review", TF_SECRETS), D),
        ("rotation, not just removal, for the leaked credentials",
         near(t, r"rotat|revoke|deactivat", r"key|credential|secret"), "", D),
        ("a state map was built", any_of(t, r"state map"), "", D),
        ("dev and prod found sharing one state object",
         near(t, r"same (bucket and key|key|state)|shar(e|es|ed|ing) (one |a |the same |a single )?state|single state|one state",
              r"dev|prod|environment"), "planted: identical bucket and key in both backend.tf", D),
        ("count-keyed databases flagged as a replacement risk",
         near(t, r"count\.index|count", r"for_each|shift|re-?creat|replac|destroy") and any_of(t, r"aws_db_instance|database"),
         "removing one list element replaces the later databases", D),
        ("prod drifted from dev on storage_encrypted",
         near(t, r"storage_encrypted|encrypt", r"prod[^\n]{0,60}(missing|lacks|not set|absent|without|drift|differ)|drift|copy"),
         "requires diffing the copied environments", D),
        ("findings cite the theory (T-n)", len(tids) >= 5, f"{len(tids)} distinct: {sorted(tids)[:10]}", D),
        ("findings carry confidence tags", any_of(t, r"✅|⚠️|decidable|\bproxy\b"), "", D),
        ("score arithmetic shown, capped by the Critical",
         any_of(t, SCORED) and near(t, r"\bcap", r"2\.0|critical"), "", D),
        ("the gate stated with its conditions",
         near(t, r"\bgate\b", r"fail") and near(t, r"\bgate\b|condition", r"lock|pipeline|saved plan"), "", D),
        ("needs-data flags listed, not scored", any_of(t, r"🔬|needs.data"), "", D),
        ("what is working well is recorded",
         near(t, r"default_tags|modules/app|app module", r"well|good|strength|solid|keep"), "", D),
        ("no Terraform, tfvars or workflow file changed", *unchanged(run, "tf-review"), D),
        ("no real backend initialised", *backend_initialised(run), D),
    ]


def eval22(run):
    """terraform Design: state split by lifecycle and trust, prod isolated, nothing built."""
    t = everything(run, "tf-design")
    doc, long_enough = deliverable(run, "tf-design")
    added, _, _ = changes(run, "tf-design")
    tf = "\n".join(read(run / "repo" / f) for f in added if f.endswith(".tf"))
    n_res = len(re.findall(r'^\s*resource\s+"', tf, re.M))
    tids = cites(t, "T", 22)
    return [
        # capability
        ("a design document was produced", long_enough, f"{len(doc)} chars", C),
        ("all three environments covered", has(t, r"\bdev\b", r"staging", r"\bprod"), "", C),
        ("a directory tree is given", any_of(t, r"modules/[^\n]*\n|├──|└──"), "", C),
        # delta
        ("a state map with backend and locking",
         any_of(t, r"state map") and near(t, r"use_lockfile|lock", r"backend|bucket|state"), "", D),
        ("state split by lifecycle / ownership",
         near(t, r"lifecycle|rate of change|change (rate|frequency)|how often|owner", r"state|root"), "", D),
        ("payments isolated for PCI",
         near(t, r"payments|PCI", r"(own|separate|dedicated|isolat)\w*[^\n]{0,60}(state|root|repo|role|backend|access|account)"), "", D),
        ("leadership's one-bucket workspaces ask declined with a reason",
         near(t, r"workspace", r"\bnot\b|avoid|instead|reject|declin|weaker|against|n't|rather|push back"),
         "the requirements ask for it; the skill's default is per-account backends", D),
        ("prod state isolated from non-prod",
         any_of(t, r"per.(account|environment) (state )?(bucket|backend)", r"(bucket|backend)s? per (account|environment)",
                r"each (account|environment)[^\n]{0,30}(own )?(bucket|backend)",
                r"prod[^\n]{0,40}(own|separate|dedicated) (state )?(bucket|backend)"), "", D),
        ("version pinning policy with a committed lockfile",
         any_of(t, r"required_version") and any_of(t, r"~>") and any_of(t, r"lock\.hcl|lockfile"), "", D),
        ("CI applies with per-environment OIDC roles",
         any_of(t, r"OIDC") and near(t, r"role", r"per.(env|environment|account)|staging|prod"), "", D),
        ("apply consumes a saved, reviewed plan", any_of(t, r"plan\s+-out|saved plan|plan file|tfplan"), "", D),
        ("humans read-only in prod, with break-glass", any_of(t, r"break.?glass") and any_of(t, r"read.?only"), "", D),
        ("destructive-change protection on stateful resources", any_of(t, r"prevent_destroy|deletion_protection"),
         "the requirements recount a deleted database", D),
        ("a narrow cross-state interface", any_of(t, r"\bSSM\b|[Pp]arameter [Ss]tore|data source"), "", D),
        ("decisions cite the theory (T-n)", len(tids) >= 3, f"{sorted(tids)[:10]}", D),
        ("open questions listed", any_of(t, r"open question"), "", D),
        ("no resources built (design, not build)", n_res == 0, f"{n_res} resource blocks written", D),
    ]


def eval23(run):
    """terraform Propose: containment first, rotate before remove, moves that recreate nothing."""
    t = everything(run, "tf-propose")
    doc, long_enough = deliverable(run, "tf-propose")
    seq = section(doc, SEQUENCE) or doc
    ids = set(re.findall(r"TF-(?:SEC|STA|DEP|CHG|DEL|STR)-\d\d", doc))
    n_rb = len(re.findall(r"rollback|roll back", doc, re.I))
    n_val = len(re.findall(r"validat|verif", doc, re.I))
    analysis_and_design = lambda f: f.startswith(("analysis/", "docs/")) or f.endswith((".tf", ".tfvars", ".yml"))
    return [
        # capability
        ("a proposal was produced", long_enough, f"{len(doc)} chars", C),
        ("decisions trace to the review's finding ids", len(ids) >= 5, f"{len(ids)} ids", C),
        ("the target layout from the design is carried", any_of(doc, r"for_each|per.environment|backend\.hcl"), "", C),
        # delta
        ("the leaked key rotated before it is removed",
         rotated_first(t, r"TF-SEC-01|access key|static key|credential"), "", D),
        ("Critical exposure contained before structural work",
         before(seq, r"TF-SEC-0[12]|0\.0\.0\.0/0|static key|credential", r"TF-CHG-01|TF-STR-01|moved|for_each"), "", D),
        ("address changes declared with moved blocks", near(t, r"\bmoved\b", r"for_each|count|aws_db_instance|module\.database"), "", D),
        ("the expected plan for the moves is zero destroys",
         any_of(t, r"0 to destroy|0 to add, 0 to change, 0 to destroy|zero (destroy|replace)|no (resources? )?(destroy|replace)|nothing (destroyed|replaced)"),
         "", D),
        ("database protection lands before the identity moves",
         before(seq, r"deletion_protection|prevent_destroy|TF-CHG-02", r"\bmoved\b|TF-CHG-01"), "", D),
        ("state migrated with a backup, not hand state surgery",
         near(t, r"backup|snapshot|state version|versioning", r"state")
         and not endorses(t, r"terraform state (mv|rm)|cp[^\n]{0,20}\.tfstate"), "", D),
        ("the apply path handed to the pipelines skill", any_of(t, r"pipelines skill|\[pipelines\]|/pipelines\b|pipelines\.md|pipelines \("), "", D),
        ("needs-data flags carried as open questions", any_of(t, r"🔬|needs.data") and any_of(t, r"open question"), "", D),
        ("every step has validation and rollback", n_rb >= 3 and n_val >= 3, f"{n_val} validation · {n_rb} rollback", D),
        ("code, review and design untouched", *unchanged(run, "tf-propose", analysis_and_design), D),
        ("nothing applied", *backend_initialised(run), D),
    ]


def eval24(run):
    """pipelines Review: untrusted code with secrets, the rebuild, the ungated deploy, and no changes."""
    t = everything(run, "ci-review")
    pids = cites(t, "P", 22)
    return [
        # capability
        ("a review with findings was produced", len(t) > 1500 and any_of(t, r"finding"), f"{len(t)} chars", C),
        ("pull_request_target running fork code with secrets found",
         near(t, r"pull_request_target", r"head|fork|untrusted|secret|NPM_TOKEN"), "", C),
        ("the per-environment rebuild found",
         near(t, r"rebuil|build[^\n]{0,30}(per|each|every|separately)|--build-arg ENV|build once", r"environment|staging|prod"), "", C),
        ("static AWS keys found", near(t, r"AWS_ACCESS_KEY_ID|static (aws )?keys?|long.lived", r"OIDC|key|credential"), "", C),
        # delta
        ("no secret value echoed (kind and location only)", *no_secret_echoed(run, "ci-review", CI_SECRETS), D),
        ("rotation for the committed webhook", near(t, r"rotat|revoke|regenerat|reissu", r"webhook|token|slack"), "", D),
        ("PR-title script injection found", near(t, r"inject|interpolat", r"title|run:|github\.event"), "", D),
        ("deploys not gated by any test found",
         near(t, r"deploy", r"(no|without|not|never)[^\n]{0,50}(test|gate|ci\.yml|needs)|independent|regardless of"),
         "deploy.yml and ci.yml are separate workflows on the same trigger", D),
        ("different deploy mechanisms per environment found",
         near(t, r"deploy-prod\.sh|script", r"staging[^\n]{0,80}(differ|inline|kubectl)|same (way|mechanism)|differ"), "", D),
        ("no post-deploy check or real rollback found",
         near(t, r"rollback|roll back|smoke|rollout status|post.deploy|health", r"\bno\b|missing|without|lack|absent|rebuild"), "", D),
        ("the @master action holding prod credentials found", any_of(t, r"@master"), "", D),
        ("the silenced e2e job found", any_of(t, r"continue-on-error"), "", D),
        ("findings cite the theory (P-n)", len(pids) >= 5, f"{len(pids)} distinct: {sorted(pids)[:10]}", D),
        ("the value stream was recovered", any_of(t, r"value stream"), "", D),
        ("score arithmetic shown, capped by the Critical",
         any_of(t, SCORED) and near(t, r"\bcap", r"2\.0|critical"), "", D),
        ("the gate stated with its conditions",
         near(t, r"\bgate\b", r"fail") and near(t, r"\bgate\b|condition", r"build once|rollback|untrusted|credential"), "", D),
        ("needs-data flags listed (settings, durations)", any_of(t, r"🔬|needs.data"), "", D),
        ("what is working well is recorded",
         near(t, r"contents: read|cache|parallel|environment: production|least.privilege", r"well|good|strength|solid|keep"), "", D),
        ("no workflow, script, manifest or Dockerfile changed", *unchanged(run, "ci-review"), D),
    ]


def actionlint_ok(run, fixture):
    """Any workflow the run wrote passes actionlint. No workflow written passes."""
    added, modified, _ = changes(run, fixture)
    wf = [f for f in added + modified if re.match(r"\.github/workflows/.+\.ya?ml$", f)]
    if not wf:
        return True, "no workflow written"
    ok, ev = sh("actionlint -shellcheck= " + " ".join(wf), run / "repo")
    return ok, f"{wf}: {ev}"


def eval25(run):
    """pipelines Design: build once, progressive by region, approval where it earns its keep."""
    t = everything(run, "ci-design")
    doc, long_enough = deliverable(run, "ci-design")
    pids = cites(t, "P", 22)
    return [
        # capability
        ("a pipeline design was produced", long_enough, f"{len(doc)} chars", C),
        ("stages from commit to production laid out", has(t, r"commit|build", r"staging", r"prod"), "", C),
        ("both production regions covered", has(t, r"eu-west-1", r"us-east-1"), "", C),
        ("any workflow skeleton written passes actionlint", *actionlint_ok(run, "ci-design"), C),
        # delta
        ("build once, promote the same digest", near(t, r"digest|sha256|immutable", r"promot|same (image|artifact)|once"), "", D),
        ("per-environment builds with baked config replaced",
         near(t, r"bak(ed|ing)|per.environment build|built separately|separate builds?", r"\bnot\b|instead|replace|avoid|no longer|drop|n't|rather")
         or any_of(t, r"(same|one|single) (image|artifact|digest)[^\n]{0,40}(every|all|each|both) (environment|stage|region)"),
         "the requirements describe per-environment builds as the team's preference", D),
        ("the 12-minute integration suite kept out of the commit stage",
         near(t, r"integration", r"acceptance|later stage|after (the )?(commit|build)|not in (the )?commit|separate stage"), "", D),
        ("rollout region by region with automated rollback",
         near(t, r"region", r"one (region )?at a time|by region|region.by.region|first|sequential|then (us-east|eu-west)")
         and near(t, r"roll ?back", r"automat|analysis|SLO|error"), "", D),
        ("migrations expand/contract, decoupled from the deploy", any_of(t, r"expand.{0,10}contract|backward.compatible|additive"), "", D),
        ("deploy decoupled from release with flags", any_of(t, r"feature flag|toggle|dark launch"), "", D),
        ("the every-deploy approval meeting declined with a reason",
         near(t, r"CAB|approval meeting|change.approval|meeting", r"\bnot\b|instead|only (for )?prod|declin|replac|rather|n't|push back"),
         "the requirements ask for one before every deployment", D),
        ("separation of duties enforced by the pipeline",
         near(t, r"author|self.?review|self.?approv|prevent", r"approv|review"), "", D),
        ("OIDC with per-environment roles", any_of(t, r"OIDC") and near(t, r"role", r"staging|prod|per.(env|account)"), "", D),
        ("third-party actions pinned by SHA", near(t, r"pin", r"SHA|commit|digest"), "", D),
        ("Terraform planned on PR, saved plan applied from CI",
         any_of(t, r"plan\s+-out|saved plan|tfplan|plan file") and any_of(t, r"pull request|\bPR\b"), "", D),
        ("deploy records for the audit and delivery metrics",
         any_of(t, r"deploy(ment)? (marker|record|event)|annotation|audit trail")
         and any_of(t, r"lead time|deployment frequency|change failure|DORA"), "", D),
        ("decisions cite the theory (P-n)", len(pids) >= 3, f"{sorted(pids)[:10]}", D),
        ("open questions listed", any_of(t, r"open question"), "", D),
    ]


def eval26(run):
    """pipelines Propose: rotate and contain first, build-once before release safety, never down."""
    t = everything(run, "ci-propose")
    doc, long_enough = deliverable(run, "ci-propose")
    seq = section(doc, SEQUENCE) or doc
    ids = set(re.findall(r"CI-(?:SEC|FLO|FBK|REL|ENV|INF)-\d\d", doc))
    n_rb = len(re.findall(r"rollback|roll back", doc, re.I))
    n_val = len(re.findall(r"validat|verif", doc, re.I))
    return [
        # capability
        ("a proposal was produced", long_enough, f"{len(doc)} chars", C),
        ("decisions trace to the review's finding ids", len(ids) >= 5, f"{len(ids)} ids", C),
        # delta
        ("the webhook rotated before it is removed", rotated_first(t, r"webhook|CI-SEC-02"), "", D),
        ("NPM_TOKEN treated as possibly exposed", near(t, r"NPM_TOKEN", r"rotat|revoke|regenerat|exposed|compromis"), "", D),
        ("untrusted-trigger containment comes first",
         before(seq, r"CI-SEC-01|pull_request_target", r"CI-FLO-01|CI-REL-0[12]|build once|digest|canary"), "", D),
        ("build-once lands before rollback-by-digest and progressive delivery",
         before(seq, r"CI-FLO-01|build (it )?once", r"CI-REL-02|roll ?back by digest|canary|progressive"), "", D),
        ("the new pipeline runs alongside the old before cut-over",
         any_of(t, r"shadow|alongside|side.by.side|in parallel with the (old|existing)|keep the old|old (pipeline|workflow|path) (available|in place)"),
         "", D),
        ("settings changes named in rollback (a git revert doesn't undo them)",
         near(t, r"setting|branch protection|environment (protection|reviewers|rules)",
              r"not (revert|undo|covered|in the repo)|n't (revert|undo)|outside (of )?the repo|in the (GitHub |CI )?UI|separately|by hand|manually"), "", D),
        ("needs-data flags carried as open questions", any_of(t, r"🔬|needs.data") and any_of(t, r"open question"), "", D),
        ("every step has validation and rollback", n_rb >= 3 and n_val >= 3, f"{n_val} validation · {n_rb} rollback", D),
        ("expected effect on delivery metrics stated",
         any_of(t, r"lead time|deployment frequency|change failure|time to restore|DORA|MTTR"), "", D),
        ("no workflow, script, review or design file changed", *unchanged(run, "ci-propose"), D),
    ]


# ------------------------------------------------------ acceptance-tests (27)
#
# The run writes black-box acceptance tests for the tdd fixture's brief. They are
# graded by running them: red on the run's own (unimplemented) code and red on
# behavior; green once a correct cutoff rule is laid over the run's repo; and red
# again on each of three mutants of that rule. Every pytest the grader starts runs
# at local noon, because the fixture's opening hours (11:00-23:00) collide with
# slots built from datetime.now() at night (see Caveats in evals/README.md).

AT_FIXTURE = "tdd"
AT_TEST_FILE = r"(^|/)(test_[^/]*|[^/]*_test|conftest)\.py$"
AT_BEHAVIOR = r"^(assert\b|AssertionError|Failed:|[\w.]*Rejected\b|NotImplementedError)"
AT_RULES = read(FIXTURES / AT_FIXTURE / "reservations/rules.py")
AT_ACTIVE = "ACTIVE_RULES = [check_party_size, check_venue_open]"
# The reference reads `now` to the second, so a slot built at exactly now + window
# from the test's own clock lands on the edge rather than a few microseconds inside it.
AT_CUTOFF = '''
from datetime import datetime, timedelta

DEFAULT_CUTOFF_MINUTES = 120


def check_cutoff(booking, config):
    window = timedelta(minutes={window})
    now = datetime.now().replace(microsecond=0)
    if {test}:
        return "CUTOFF_WINDOW"
    return None


ACTIVE_RULES = {order}
'''
AT_CONFIGURED = 'config.get("cutoff_minutes", DEFAULT_CUTOFF_MINUTES)'
AT_EXCLUSIVE = "booking.slot - now < window"
AT_ORDERS = ("[check_party_size, check_venue_open, check_cutoff]",
             "[check_cutoff, check_party_size, check_venue_open]")
AT_MUTANTS = {
    # the teardown fixture's planted defect: the account's cutoff_minutes never read
    "hard-coded": dict(window="DEFAULT_CUTOFF_MINUTES"),
    # whole minutes, compared inclusively: a slot on the edge (to the minute) is rejected
    "inclusive": dict(test="(booking.slot - now) // timedelta(minutes=1) <= window // timedelta(minutes=1)"),
    # only the first violation surfaces
    "first-only": dict(first=True),
}
# Probed with every hour open: does the run's own code already enforce a cutoff?
AT_PROBE = """
from datetime import datetime, timedelta
from reservations.api import BookingService, Rejected
class Store:
    def save(self, b): pass
class Config:
    def __init__(self, c): self.c = c
    def for_account(self, a): return self.c
def codes(cfg, minutes):
    svc = BookingService(Store(), Config({"opens_at": 0, "closes_at": 24, **cfg}))
    try:
        svc.submit("acct", "venue", datetime.now() + timedelta(minutes=minutes), 2)
        return []
    except Rejected as e:
        return list(e.codes)
    except NotImplementedError:
        return ["NotImplementedError"]
print(f"default, 30 out: {codes({}, 30)} · 240-min window, 180 out: {codes({'cutoff_minutes': 240}, 180)}")
"""
_AT_BASE = {}


def at_noon_tz():
    """A TZ that puts local time at noon now, whatever hour the grader runs."""
    h = datetime.datetime.now(datetime.timezone.utc).hour
    o = (12 - h + 12) % 24 - 12
    return "UTC" if o == 0 else f"Etc/GMT{-o:+d}"


def at_python(run):
    """The run's venv, or the fixture's (controls are built without one)."""
    py = (run / "repo/.venv/bin/python").absolute()  # not resolve(): the symlink is what makes it the venv
    return py if py.exists() else FIXTURES / AT_FIXTURE / ".venv/bin/python"


def at_copy(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", ".git"))
    return dst


def at_rules(window=AT_CONFIGURED, test=AT_EXCLUSIVE, order=AT_ORDERS[0], first=False):
    text = AT_RULES.replace(AT_ACTIVE, AT_CUTOFF.format(window=window, test=test, order=order))
    if first:
        text = text.replace("return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None]",
                            "return [code for rule in ACTIVE_RULES if (code := rule(booking, config)) is not None][:1]")
    return text


def at_overlay(repo, rules):
    """The fixture's service with `rules` as its rule module, over whatever else the run wrote."""
    for f in ("__init__.py", "api.py", "booking.py"):
        (repo / "reservations" / f).write_text(read(FIXTURES / AT_FIXTURE / "reservations" / f))
    (repo / "reservations/rules.py").write_text(rules)


def at_pytest(py, cwd, args):
    """{(classname, name): (outcome, message)} from pytest's junit XML, run at local noon."""
    xml = pathlib.Path(tempfile.mkdtemp(prefix="at-junit-")) / "j.xml"
    env = {**os.environ, "TZ": at_noon_tz(), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        subprocess.run([str(py), "-m", "pytest", "-p", "no:cacheprovider", "-q", *args,
                        "--maxfail=100000", f"--junitxml={xml}"],
                       cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=180)
        out = {}
        for tc in ET.parse(xml).iter("testcase"):
            kids = [c for c in tc if c.tag in ("failure", "error", "skipped")]
            outcome = kids[0].tag if kids else "passed"
            msg = (kids[0].get("message") or "") if kids else ""
            out[(tc.get("classname") or "", tc.get("name") or "")] = (outcome, msg)
        return out
    except Exception:
        return {}
    finally:
        shutil.rmtree(xml.parent, ignore_errors=True)


ALL_TESTS = [".", "-o", "addopts=", "--continue-on-collection-errors"]


def at_key(k):
    return k[0], k[1].split("[")[0]


def at_baseline(py):
    """(classname, test) of the fixture's own tests, collected the same way."""
    if str(py) not in _AT_BASE:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="at-base-"))
        try:
            res = at_pytest(py, at_copy(FIXTURES / AT_FIXTURE, tmp / "repo"), ALL_TESTS)
            _AT_BASE[str(py)] = {at_key(k) for k in res}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return _AT_BASE[str(py)]


def at_test_names(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")}


def at_added_tests(run):
    """The test code the run added (new files whole, changed files' new lines) and its new test names."""
    added, modified, _ = changes(run, AT_FIXTURE)
    code, names = [], set()
    for f in added + modified:
        if not re.search(AT_TEST_FILE, f):
            continue
        text, before = read(run / "repo" / f), read(FIXTURES / AT_FIXTURE / f)
        old = set(before.splitlines())
        code += [line for line in text.splitlines() if line not in old]
        names |= at_test_names(text) - at_test_names(before)
    return "\n".join(code), names


AT_PRIVATE = {"check_cutoff", "check_party_size", "check_venue_open", "ACTIVE_RULES", "_store", "_config_source"}


def at_internals(run):
    """What the run's new or changed test files reach past reservations.api for: imports of the
    rule or aggregate modules, rule functions or private attributes, monkeypatch targets inside them."""
    added, modified, _ = changes(run, AT_FIXTURE)
    hits = set()
    for f in added + modified:
        if not re.search(AT_TEST_FILE, f):
            continue
        try:
            tree = ast.parse(read(run / "repo" / f))
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                hits |= {a.name for a in n.names if re.match(r"reservations\.(rules|booking)\b", a.name)}
            elif isinstance(n, ast.ImportFrom):
                mod = n.module or ""
                if re.match(r"reservations\.(rules|booking)\b", mod):
                    hits.add(mod)
                elif mod == "reservations":
                    hits |= {f"reservations.{a.name}" for a in n.names if a.name in ("rules", "booking")}
            elif isinstance(n, ast.Attribute) and n.attr in AT_PRIVATE:
                hits.add(n.attr)
            elif isinstance(n, ast.Name) and n.id in AT_PRIVATE:
                hits.add(n.id)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and re.match(r"reservations\.(rules|booking)\b", n.value):
                hits.add(n.value)
    return sorted(hits)


def at_section(brief):
    """The brief's **Acceptance tests** section, up to the next bold section or heading."""
    m = re.search(r"^[ \t]*(?:#+[ \t]*|\*\*)Acceptance tests\b.*$", brief, re.M | re.I)
    if not m:
        return ""
    end = re.search(r"^(?:\*\*|#)", brief[m.end():], re.M)
    return brief[m.start(): m.end() + (end.start() if end else len(brief))]


AT_CRITERIA = [  # checked in this order: the edge and both-codes lines also say "accepted" / "cutoff"
    (4, r"window edge|at the edge|exactly|boundar|exclusive"),
    (5, r"\bboth\b|party|PARTY_TOO_LARGE|first (code|violation)"),
    (3, r"config|cutoff_minutes|hard.?coded"),
    (2, r"outside|persist"),
    (1, r"tracer|inside|within"),
]


def at_mapping(sec):
    """[(criterion, line)] for each mapping line in the section."""
    out = []
    for line in sec.splitlines():
        if not re.match(r"\s*[-*]\s", line) or re.search(r"\*\*Command", line):
            continue
        n = re.search(r"Criterion\s*#?\s*(\d)", line, re.I)
        if n:
            out.append((int(n.group(1)), line))
            continue
        crit = re.split(r"→|->", line)[0]
        for c, pat in AT_CRITERIA:
            if re.search(pat, crit, re.I) or (crit == line and re.search(pat, line, re.I)):
                out.append((c, line))
                break
    return out


def at_command(cmd):
    """The recorded command's pytest arguments, or None if it isn't a pytest command."""
    m = re.search(r"(?:^|&&|;)\s*(?:[\w./-]*python[\d.]*\s+-m\s+pytest|[\w./-]*pytest)(?=\s|$)(.*)$", cmd or "")
    try:
        return shlex.split(m.group(1)) if m else None
    except ValueError:
        return None


def eval27(run):
    """acceptance-tests on the tdd fixture: red on behavior, green on a reference, mutants killed, mapped in the brief."""
    repo = run / "repo"
    py = at_python(run)
    code, names = at_added_tests(run)
    brief = read(repo / ".workflow/brief.md")
    sec = at_section(brief)
    r = resp(run)
    base = at_baseline(py)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="at-grade-"))
    try:
        own = at_copy(repo, tmp / "own")
        now = at_pytest(py, own, ALL_TESTS)
        new = {k: v for k, v in now.items() if at_key(k) not in base}
        old = {k: v for k, v in now.items() if at_key(k) in base}
        try:
            pr = subprocess.run([str(py), "-c", AT_PROBE], cwd=own, capture_output=True, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)
            probe = ((pr.stdout + pr.stderr).strip().splitlines() or [""])[-1][:200]
        except Exception as e:
            probe = f"probe failed to run: {e}"[:200]
        cmd = re.search(r"\*\*Command:?\*\*:?\s*`([^`]+)`", sec)
        args = at_command(cmd.group(1)) if cmd else None
        ran = at_pytest(py, own, args) if args is not None else {}

        over = at_copy(repo, tmp / "over")
        ref, order = {}, AT_ORDERS[0]
        for o in AT_ORDERS:
            at_overlay(over, at_rules(order=o))
            res = {k: v for k, v in at_pytest(py, over, ALL_TESTS).items() if at_key(k) not in base}
            if not ref or (res and all(v[0] == "passed" for v in res.values())):
                ref, order = res, o
            if res and all(v[0] == "passed" for v in res.values()):
                break
        green_ref = {k for k, v in ref.items() if v[0] == "passed"}
        killed = {}
        for name, mut in AT_MUTANTS.items():
            at_overlay(over, at_rules(order=order, **mut))
            res = at_pytest(py, over, ALL_TESTS)
            hit = sorted(k[1] for k in green_ref if res.get(k, ("missing",))[0] != "passed")
            killed[name] = (bool(hit), f"failed on the mutant: {hit[:3]}" if hit else
                            f"no test green on the reference fails it ({len(green_ref)} green on the reference)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passing = sorted(k[1] for k, v in new.items() if v[0] == "passed")
    wrong = sorted(f"{k[1]}: {v[1][:70]}" for k, v in new.items()
                   if v[0] != "passed" and (v[0] != "failure" or not re.match(AT_BEHAVIOR, v[1])))
    old_bad = sorted(k[1] for k, v in old.items() if v[0] != "passed")
    old_missing = base - {at_key(k) for k in old}
    ref_bad = sorted(f"{k[1]}: {v[1][:60]}" for k, v in ref.items() if v[0] != "passed")
    internals = at_internals(run)
    doubles = re.findall(r"^\s*class\s+((?!FakeStore\b|FakeConfig\b)\w*(?:Store|Config|Clock|Fake|Stub|Mock|Spy)\w*)", code, re.M)
    doubles += re.findall(r"unittest\.mock|MagicMock|\bmocker\b", code)
    collected = set(ran)
    cmd_ok = bool(new) and collected == set(new)
    mapping = at_mapping(sec)
    counts = {c: sum(1 for n, _ in mapping if n == c) for c in range(1, 6)}
    unmapped = []
    for c, line in mapping:
        ids = [t[-1] for t in (re.findall(r"\btest\w*", span) for span in re.findall(r"`([^`]+)`", line)) if t]
        if ids:
            unmapped += [i for i in ids if i not in names]
        elif not re.search(r"not acceptance.?testable\b.*?(?:—|–|-|:|because)\s*\w+(?:\W+\w+){2,}", line, re.I):
            unmapped.append(f"criterion {c}: no test id and no reason")
    revs = brief.split("## Revisions", 1)[1] if "## Revisions" in brief else ""
    revs = revs[:m.start()] if (m := re.search(r"^(?:\*\*|#)", revs, re.M)) else revs
    revised = [line for line in re.findall(r"^\s*-\s+(.+)$", revs, re.M)
               if "(none yet)" not in line and re.search(r"acceptance", line, re.I)]
    implemented = "CUTOFF_WINDOW" in probe
    return [
        # capability — any competent attempt at the task manages these
        ("acceptance tests added that drive BookingService.submit",
         len(names) >= 3 and has(code, r"\.submit\(", r"BookingService"), f"{len(names)} new test functions", C),
        ("the pre-existing tests still present and green", bool(old) and not old_bad and not old_missing,
         f"failing: {old_bad}; missing: {sorted(old_missing)}" if old_bad or old_missing else f"{len(old)} green", C),
        ("tests reuse FakeStore and FakeConfig, no new doubles",
         bool(code) and has(code, r"\bFakeStore\b", r"\bFakeConfig\b") and not doubles, f"{doubles or 'none new'}", C),
        ("every new test passes once a correct cutoff rule is laid over the repo",
         bool(ref) and not ref_bad, f"{ref_bad[:3]}" if ref_bad else f"{len(ref)} green on the reference", C),
        ("the edge test kills an inclusive-boundary mutant", *killed["inclusive"], C),
        ("the both-codes test kills a first-violation-only mutant", *killed["first-only"], C),
        # delta — what the skill instructs
        ("every new test is red on the unimplemented code (none passes)", bool(new) and not passing,
         f"passing now: {passing[:4]}" if passing else f"{len(new)} new, all red", D),
        ("red for the right reason: every failure is on behavior, none fails to load", bool(new) and not wrong,
         f"{wrong[:3]}" if wrong else f"{len(new) - len(passing)} of {len(new)} new tests fail, all on behavior"
         if new else "no new tests ran", D),
        ("the config test kills a hard-coded-window mutant (not vacuous)", *killed["hard-coded"], D),
        ("no internals: tests import only the public entry point", bool(code) and not internals,
         f"{internals}" if internals else "public seam only" if code else "no test code", D),
        ("brief gains an Acceptance tests section with a Command line", bool(sec) and bool(cmd),
         cmd.group(1)[:120] if cmd else ("section, no **Command:**" if sec else "no Acceptance tests section"), D),
        ("the recorded command runs exactly the new acceptance tests", cmd_ok,
         f"command collects {len(collected)}, new tests {len(new)}"
         + ("" if args is not None else " (no pytest command)"), D),
        ("every one of the 5 criteria mapped exactly once", all(v == 1 for v in counts.values()), f"{counts}", D),
        ("every mapped test id names a test the run added", bool(mapping) and not unmapped,
         f"{unmapped[:4]}" if unmapped else f"{len(mapping)} mapping lines", D),
        ("the mapping logged under Revisions", bool(revised), revised[0][:120] if revised else "no new Revisions entry", D),
        ("no implementation of the cutoff rule", not implemented, probe, D),
        ("tier stated (Standard)", near(r + "\n" + brief, r"\bStandard\b", r"\btier\b|calibrat", 120), "", D),
        ("hands off to tdd next", near(r, r"\btdd\b", r"\bnext\b", 120), "", D),
    ]


# ------------------------------------------------------------ dockerfile (28)
# Graded from files: the Dockerfile is parsed per stage and the .dockerignore is
# evaluated with Docker's own matching rules. Nothing is built.

DF_SECRETS = ["eval-fake-pdfrender-key-0042", "eval-fake-signing-secret-7d1c"]
DF_RUNTIME_FILES = {"node_modules", "dist", "package.json", "pnpm-lock.yaml", "migrations", "templates", ".npmrc"}
DF_CONTEXT_FILES = DF_RUNTIME_FILES - {"node_modules", "dist"}
DF_TOOLCHAIN = r"(apt-get|apt) install[^\n]*\b(build-essential|g\+\+|gcc|make|python3?)\b|apk add[^\n]*\b(build-base|g\+\+|gcc|make|python3?)\b"
DF_PROD = r"prune\s+--prod|--prod\b|--production\b|pnpm deploy"
DF_NATIVE_HOST = r"\$\{?BUILDPLATFORM\}?|linux/arm64"


def df_parse(text):
    """A Dockerfile as a list of stages: {name, image, platform, ins: [(OP, args)]}.
    Comment lines dropped, continuations joined, global ARG defaults substituted into FROM."""
    lines = [l for l in text.splitlines() if not l.strip().startswith("#")]
    joined = re.sub(r"\\[ \t]*\n", " ", "\n".join(lines))
    args, stages = {}, []
    for line in joined.splitlines():
        m = re.match(r"\s*([A-Za-z]+)\s+(.*)", line)
        if not m:
            continue
        op, rest = m.group(1).upper(), m.group(2).strip()
        if op == "FROM":
            platform = (re.search(r"--platform=(\S+)", rest) or [None, ""])[1]
            body = re.sub(r"--\w+=\S+\s*", "", rest).split()
            image = body[0] if body else ""
            for k in sorted(args, key=len, reverse=True):
                image = image.replace("${%s}" % k, args[k]).replace("$" + k, args[k])
            name = body[2].lower() if len(body) >= 3 and body[1].lower() == "as" else str(len(stages))
            stages.append({"name": name, "image": image, "platform": platform, "ins": []})
        elif stages:
            stages[-1]["ins"].append((op, rest))
        elif op == "ARG":
            k, _, v = rest.partition("=")
            args[k.strip()] = v.strip().strip("\"'")
    return stages


def df_chain(stages, i):
    """Stage i preceded by the stages it is built FROM, root first."""
    names = {s["name"]: j for j, s in enumerate(stages)}
    chain = []
    while i is not None and i not in chain:
        chain.insert(0, i)
        j = names.get(stages[i]["image"].lower())
        i = j if j is not None and j < i else None
    return [stages[j] for j in chain]


def df_ins(chain):
    return [ins for s in chain for ins in s["ins"]]


def df_copy(rest):
    """(--from value, [source basenames]) of a COPY/ADD, shell or JSON form."""
    src_from = (re.search(r"--from=(\S+)", rest) or [None, ""])[1].lower()
    body = re.sub(r"--\w+(=\S+)?\s*", "", rest).strip()
    try:
        parts = json.loads(body) if body.startswith("[") else body.split()
    except Exception:
        parts = body.split()
    names = []
    for p in parts[:-1]:
        p = re.sub(r"^\./", "", p).rstrip("/")
        names.append(p.split("/")[-1] if p not in ("", ".") else ".")
    return src_from, names


def df_slim(image):
    return bool(re.search(r"slim|alpine|distroless|chainguard|wolfi|minimal", image, re.I))


def df_libc(image):
    return "musl" if "alpine" in image.lower() else "glibc"


def df_exec(rest):
    try:
        v = json.loads(rest)
        return v if isinstance(v, list) else None
    except Exception:
        return None


def df_last(ins, op):
    hits = [(i, r) for i, (o, r) in enumerate(ins) if o == op]
    return hits[-1] if hits else (None, None)


def df_node_modules_from(stages):
    """The chain that produced the runtime stage's node_modules: a COPY --from stage, else the runtime itself."""
    final = df_chain(stages, len(stages) - 1)
    names = {s["name"]: j for j, s in enumerate(stages)}
    for op, rest in df_ins(final):
        if op in ("COPY", "ADD"):
            src_from, srcs = df_copy(rest)
            if "node_modules" in srcs and src_from in names:
                return df_chain(stages, names[src_from])
    if any(op == "RUN" and re.search(r"pnpm (install|i)\b|npm (ci|install)\b", r) for op, r in df_ins(final)):
        return final
    return None


def ignore_rules(text):
    rules = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        neg = line.startswith("!")
        pat = re.sub(r"^(\./|/)+", "", line.lstrip("!").strip()).rstrip("/")
        rx, i = "", 0
        while i < len(pat):
            c = pat[i]
            if pat.startswith("**/", i):
                rx, i = rx + "(?:.*/)?", i + 3
                continue
            if pat.startswith("**", i):
                rx, i = rx + ".*", i + 2
                continue
            rx += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
            i += 1
        rules.append((neg, re.compile(rx + "$")))
    return rules


def ignored(rules, path):
    """Docker's rule: the last pattern matching the path or any parent directory decides."""
    parts = path.split("/")
    prefixes = ["/".join(parts[:k]) for k in range(1, len(parts) + 1)]
    out = False
    for neg, rx in rules:
        if any(rx.match(p) for p in prefixes):
            out = not neg
    return out


DF_INPUTS = ["package.json", "pnpm-lock.yaml", "tsconfig.json", "src/server.ts", "migrations/001_invoices.sql",
             "templates/invoice.hbs"]
DF_CURATED = [".git/HEAD", "docs/architecture.md", "loadtest/invoices.js", "coverage/lcov.info", "CHANGELOG.md",
              "README.md", ".github/workflows/ci.yml", "deploy/k8s/deployment.yaml", "Makefile"]
# A string is searched for; a pair must occur within 200 characters of each other (line wraps allowed).
DF_DEFECTS = [r"\blatest\b", r"COPY \. \.", r"single.stage|one stage|devDependencies|dev dependencies|compiler",
              r"\broot\b", r"shell.form|pnpm start|SIGTERM", r"PDF_RENDER_API_KEY", (r"\b3000\b", r"\b8080\b"),
              (r"/health(?!z)", r"/healthz"), (r"\.env\b", r"layer|context|COPY|dockerignore")]
DF_INFER = [r"20\.11\.1", (r"pnpm", r"lock"), r"\bdist/", (r"\bPORT\b", r"\b8080\b"), r"better-sqlite3",
            (r"migrations", r"templates"), r"amd64", r"node dist/server\.js"]
DF_VERIFY = [r"docker (buildx )?build|make image", r"docker run[^\n]*-p\b|curl[^\n]*/healthz",
             r"CACHED[^\n]{0,120}(touch|rebuild)|(touch|rebuild)[^\n]{0,120}CACHED",
             r"docker (image )?inspect[^\n]*(Architecture|\.Os)", r"docker run[^\n]*\s(id|whoami)\b",
             r"docker history --no-trunc", r"docker images|docker image ls", r"du -sh|transferring context"]
DF_OBSERVED = [r"uid=[1-9]\d*\(", r"transferring context:?\s*[\d.]+\s*[kKMG]?B", r"=>\s*CACHED\s*\[",
               r"[0-9a-f]{12}\s+[^\n]*\d+(\.\d+)?\s?[MG]B", r"^\s*linux/amd64\s*$"]
DF_NO_DOCKER = (r"docker[^\n]{0,60}(not available|unavailable|not installed|isn't installed|not running|no daemon|"
                r"could ?n[o']t (connect|run|be run)|cannot connect|command not found)|"
                r"(no|without) (a )?docker (daemon|engine|CLI|binary|available|installed|here)")


def hit(text, p):
    return near(text, *p, 200) if isinstance(p, tuple) else bool(re.search(p, text, re.I))


def eval28(run):
    """dockerfile repair: names the defects, pins to the repo, ships only artifacts as non-root, for amd64."""
    repo, r = run / "repo", resp(run)
    _, modified, _ = changes(run, "dockerfile")
    text = read(repo / "Dockerfile")
    stages = df_parse(text)
    n = len(stages)
    final = df_chain(stages, n - 1) if stages else []
    fins = df_ins(final)
    root_img = final[0]["image"] if final else ""
    names = {s["name"]: j for j, s in enumerate(stages)}

    # c: TypeScript compiled in an earlier stage, dist copied from it
    built = [s["name"] for s in stages[:-1] if any(o == "RUN" and re.search(r"pnpm (run )?build|\btsc\b", a) for o, a in s["ins"])]
    dist_from = [df_copy(a)[0] for o, a in fins if o == "COPY" and "dist" in df_copy(a)[1]]
    multi = n >= 2 and any(f in names and any(b in [x["name"] for x in df_chain(stages, names[f])] for b in built)
                           for f in dist_from)

    # c: in every stage that installs, the install comes before the source arrives
    order_ok, installs = True, 0
    for i in range(n):
        ins = df_ins(df_chain(stages, i))
        inst = [k for k, (o, a) in enumerate(ins) if o == "RUN" and re.search(r"pnpm (install|i)\b(?![^\n]*--prod)", a)]
        src = [k for k, (o, a) in enumerate(ins) if o in ("COPY", "ADD") and not df_copy(a)[0]
               and set(df_copy(a)[1]) & {".", "src"}]
        if inst:
            installs += 1
            order_ok &= not src or inst[0] < src[0]
    order_ok &= installs > 0

    # d: frozen against the lockfile, with a cache mount
    pnpm_runs = [a for s in stages for o, a in s["ins"] if o == "RUN" and re.search(r"pnpm (install|i)\b", a)]
    fetch_runs = [a for s in stages for o, a in s["ins"] if o == "RUN" and re.search(r"pnpm fetch\b", a)]
    lock_in = any(o in ("COPY", "ADD") and set(df_copy(a)[1]) & {"pnpm-lock.yaml", "."} for s in stages for o, a in s["ins"])
    frozen = bool(pnpm_runs) and lock_in and all("--frozen-lockfile" in a for a in pnpm_runs) \
        and any("--mount=type=cache" in a for a in pnpm_runs + fetch_runs)

    # d: pinned to what the repo declares
    images = [s["image"] for j, s in enumerate(stages) if names.get(s["image"].lower(), j) >= j]
    node_pinned = bool(images) and all(re.match(r"(docker\.io/)?(library/)?node:20\.11(\.1)?([-@]|$)", im) for im in images)
    runs = "\n".join(a for s in stages for o, a in s["ins"] if o == "RUN")
    pnpm_pinned = (bool(re.search(r"corepack enable", runs)) or "pnpm@9.12.3" in runs) \
        and not re.search(r"(?<!p)npm (i|install) (-g|--global) pnpm(?!@)", runs)
    digest = bool(re.search(r"@sha256:[0-9a-f]{64}", root_img)) or near(
        r, r"digest", r"not (pinned|resolved)|unpinned|could ?n[o']t|unable|no (registry|network)|unavailable|"
        r"without (network|registry)|resolve it|before (this|it) ships|follow.?up", 200)

    # d: runtime carries only artifacts, prod deps and runtime assets
    copies = [(df_copy(a), o) for o, a in fins if o in ("COPY", "ADD")]
    stray = [srcs for (frm, srcs), _ in copies if (frm in names or not frm)
             and set(srcs) - (DF_RUNTIME_FILES if frm else DF_CONTEXT_FILES)]
    shipped = {x for (_, srcs), _ in copies for x in srcs}
    nm = df_node_modules_from(stages) if stages else None
    nm_ins = df_ins(nm) if nm else []
    first_install = next((k for k, (o, a) in enumerate(nm_ins) if o == "RUN" and re.search(r"pnpm (install|i)\b", a)), 0)
    prod = nm is not None and (any(o == "RUN" and re.search(DF_PROD, a) for o, a in nm_ins) or any(
        o == "ENV" and re.search(r"NODE_ENV[= ]production", a) for o, a in nm_ins[:first_install]))
    toolchain = any(o == "RUN" and re.search(DF_TOOLCHAIN, a) for o, a in fins)
    artifacts_only = n >= 2 and not stray and not toolchain and prod and {"dist", "migrations", "templates"} <= shipped

    # d: the native module installed where it runs
    native_ok = nm is not None and n >= 2 and prod \
        and not any(re.search(DF_NATIVE_HOST, s["platform"]) for s in nm) \
        and df_libc(nm[0]["image"]) == df_libc(root_img) \
        and near(r, r"better-sqlite3", r"amd64|arm64|platform|architecture|emulat|ABI|libc|musl|glibc")

    # d: port and health from the source
    env_port = {m for o, a in fins if o == "ENV" for m in re.findall(r"\bPORT[= ](\d+)", a)}
    exposed = {re.sub(r"/tcp$", "", p) for o, a in fins if o == "EXPOSE" for p in a.split()}
    exposed = {next(iter(env_port)) if re.fullmatch(r"\$\{?PORT\}?", p) and env_port else p for p in exposed}
    _, hc = df_last(fins, "HEALTHCHECK")
    if hc and not re.match(r"NONE\b", hc, re.I):
        installs_tool = lambda t: any(o == "RUN" and re.search(rf"(apt-get|apt) install[^\n]*\b{t}\b|apk add[^\n]*\b{t}\b", a)
                                      for o, a in fins)
        tool_ok = not (re.search(r"\bcurl\b", hc) and df_slim(root_img) and not installs_tool("curl")) \
            and not (re.search(r"\bwget\b", hc) and df_slim(root_img) and "alpine" not in root_img and not installs_tool("wget"))
        health = bool(re.search(r"/healthz\b", hc)) and bool(re.search(r"8080|\bPORT\b", hc)) and "3000" not in hc and tool_ok
        hev = f"HEALTHCHECK {hc[:90]}"
    else:
        health = near(r, r"HEALTHCHECK", r"omit|left out|no HEALTHCHECK|deliberate|dropp|remov|leave", 200) \
            and near(r, r"HEALTHCHECK", r"probe|kubernetes|k8s|orchestrator", 300)
        hev = "omitted; reason in the response" if health else "omitted with no reason"
    port_ok = exposed == {"8080"} and health

    # d: non-root, owning what it writes
    ui, user = df_last(fins, "USER")
    ci, _ = df_last(fins, "CMD")
    ei, _ = df_last(fins, "ENTRYPOINT")
    start = min(x for x in (ci, ei, len(fins)) if x is not None)
    nonroot = ui is not None and ui < start and not re.match(r"(root|0)(:|$)", user.strip())
    owns = any(o == "RUN" and re.search(r"chown\b[^\n]*?(\s|/)(app/)?data\b|chown\b[^\n]*\s/app/?(\s|$|&)|install\s+-d[^\n]*-o", a)
               for o, a in fins) or any(o == "ENV" and re.search(r"DATABASE_PATH=/tmp/", a) for o, a in fins)

    # c: exec-form start
    cmd = df_exec(df_last(fins, "CMD")[1] or "") or []
    entry = df_exec(df_last(fins, "ENTRYPOINT")[1] or "") if ei is not None else []
    argv = (entry or (["node"] if re.search(r"distroless/nodejs", root_img) and ei is None else [])) + cmd
    exec_ok = (ei is None or entry is not None) and bool(cmd) \
        and any(x == "node" or x.endswith("/node") for x in argv) and any(x.endswith("dist/server.js") for x in argv)

    # d: no secret in ENV, ARG or a copied env file
    keys = [k for s in stages for o, a in s["ins"] if o in ("ENV", "ARG")
            for k in (re.findall(r"(\w+)=", a) or a.split()[:1])]
    keys += [a.partition("=")[0] for a in re.findall(r"^\s*ARG\s+(\S+)", text, re.M)]
    baked = [k for k in keys if re.search(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL", k, re.I)]
    env_copied = [a for s in stages for o, a in s["ins"] if o in ("COPY", "ADD") and re.search(r"(^|\s|/)\.env\b(?!\.example)", a)]
    no_baked = bool(stages) and not baked and not env_copied and not any(v in text for v in DF_SECRETS)

    # d: built for the target, pinned in what the team runs
    files_text = "\n".join(read(repo / f) for f in modified + find_added(run, "dockerfile", r".") if not f.endswith(".md"))
    pvars = re.findall(r"(\w*PLATFORM\w*)\s*[?:]?=\s*[\"']?linux/amd64", files_text)
    pinned = re.search(r"--platform[= ][\"']?linux/amd64", files_text) or "DOCKER_DEFAULT_PLATFORM" in pvars or any(
        re.search(rf"--platform[= ][\"']?\$[({{]?{v}\b", files_text) for v in pvars)
    platform = near(r, r"amd64", r"arm64|Apple Silicon|M-series|\bM[1-4]\b|aarch64|darwin", 300) and bool(pinned)

    # .dockerignore: semantics, before and after
    old_rules = ignore_rules(read(FIXTURES / "dockerfile/.dockerignore"))
    new_ign = read(repo / ".dockerignore")
    rules = ignore_rules(new_ign)
    kept = [p for p in DF_CURATED if ignored(rules, p) != ignored(old_rules, p)]
    dropped_inputs = [p for p in DF_INPUTS if ignored(rules, p)]
    must_out = [".env", ".env.local", ".env.production", "node_modules/better-sqlite3/package.json", "dist/server.js"]
    leaks = [p for p in must_out if not ignored(rules, p)] + [".env.example (excluded)"] * ignored(rules, ".env.example")

    # response: inference, defects before the fix, verification
    cut = min([m.start() for m in (re.search(r"```(dockerfile|docker)", r, re.I), re.search(r"^FROM\s", r, re.M)) if m]
              or [len(r)])
    named = [p for p in DF_DEFECTS if hit(r[:cut], p)]
    facts = [p for p in DF_INFER if hit(r, p)]
    cmds = [p for p in DF_VERIFY if re.search(p, r, re.I)]
    observed = [p for p in DF_OBSERVED if re.search(p, r, re.I | re.M)]
    observed += ["size"] * (DF_OBSERVED[3] not in observed and near(r, r"\b\d+(\.\d+)?\s?MB\b", r"docker images|\bSIZE\b", 120))
    no_docker = bool(re.search(DF_NO_DOCKER, r, re.I))
    honest = (len(observed) >= 3 and not no_docker) or (no_docker and not observed)
    verify = len(cmds) >= 7 and honest and not re.search(r"should work", r, re.I)

    return [
        # capability — any competent repair of a 1 GB, cache-busting image
        ("multi-stage: TypeScript compiled in a build stage, dist copied from it", multi,
         f"{n} stages; built in {built}; dist from {dist_from}", C),
        ("dependencies installed before the source is copied", order_ok, f"{installs} installing stage(s)", C),
        ("runtime base is a slim variant, not the full image", bool(root_img) and df_slim(root_img), root_img, C),
        ("starts node dist/server.js in exec form", exec_ok, f"ENTRYPOINT {entry} CMD {cmd}", C),
        ("installs with pnpm, the repo's package manager", bool(pnpm_runs) and not re.search(
            r"(?<!p)npm (ci|install|i)\b(?! (-g|--global) pnpm)", runs), f"{len(pnpm_runs)} pnpm installs", C),
        ("everything the build needs is still in the context", not dropped_inputs, f"excluded: {dropped_inputs or 'none'}", C),
        # delta — what the skill instructs
        ("stack inference stated (Node 20.11.1, pnpm lockfile, dist, PORT 8080, better-sqlite3, assets, amd64, start)",
         len(facts) >= 7, f"{len(facts)}/8 facts", D),
        ("the existing Dockerfile's defects named before the fix", len(named) >= 7,
         f"{len(named)}/9 named before the first FROM/fence", D),
        ("pinned to what the repo declares: node 20.11 in every stage, pnpm 9.12.3, digest or its absence recorded",
         node_pinned and pnpm_pinned and digest, f"images {images}; pnpm pinned {pnpm_pinned}; digest {digest}", D),
        ("frozen install against pnpm-lock.yaml under a cache mount", frozen, f"{len(pnpm_runs)} pnpm installs", D),
        ("runtime ships only dist, production deps, migrations/ and templates/: no source, no toolchain",
         artifacts_only, f"stray {stray}; toolchain {toolchain}; prod deps {prod}; shipped {sorted(shipped)}", D),
        ("better-sqlite3 installed on the target platform and libc, not the build host's", native_ok,
         f"node_modules from {[s['name'] + ' ' + s['platform'] for s in nm] if nm else None}", D),
        ("port and health from the source: EXPOSE 8080, /healthz with a tool the runtime has (or left to the k8s probes)",
         port_ok, f"EXPOSE {sorted(exposed)}; {hev}", D),
        ("runs as a non-root user that owns its data directory, USER before CMD", nonroot and owns,
         f"USER {user}; data dir owned {owns}", D),
        ("no secret in ENV, ARG or a copied env file", no_baked, f"baked {baked}; copied {env_copied}", D),
        ("planted secret values never echoed", *no_secret_echoed(run, "dockerfile", DF_SECRETS), D),
        ("built for linux/amd64 from Apple Silicon: stated, and --platform pinned in what the team runs", platform,
         "Makefile, Dockerfile or script carries --platform linux/amd64", D),
        (".dockerignore extended, every curated entry kept", ".dockerignore" in modified and not kept,
         f"changed {'.dockerignore' in modified}; decisions changed for {kept or 'none'}", D),
        (".dockerignore: .env and .env.* out, .env.example in, node_modules and dist out", not leaks,
         f"leaks: {leaks or 'none'}", D),
        ("Step 4 checks each stated with its command; results observed, or docker's absence said plainly", verify,
         f"{len(cmds)}/8 commands; observed {len(observed)}; no-docker stated {no_docker}", D),
    ]


# ------------------------------------------------------------ release-notes (29)
# Beacon v2.3.0..v2.4.0: 18 squash-merged commits. Graded from "the notes" (the
# markdown the run wrote: a new file, or the lines it added to an existing one
# such as repo/CHANGELOG.md) and "the handoff" (the response). Identifiers,
# numbers and ordering are judged on the notes; range, tier, sources, the
# dropped count and the unmeasured list are judged on the handoff.

RN_INTERNAL = (r"\bPLAT-\d+|MaintenanceWindowScheduler|maint_windows_v2|IncidentTimelineQuery|DigestMailer"
               r"|SlaCalculator|AlertRouter|NotificationService|DEFAULT_PAGE_SIZE|incident_events"
               r"|\b(feat|fix|chore)/[\w-]+")
V240 = r"(?<![\d.])2\.4\.0(?!\.?\d)"
RN_TAG_DATE = r"2026-10-14|14 Oct(ober|\.)? 2026|Oct(ober|\.)? 14,? 2026"
RN_FIGURE = (r"\b48\s*(s|sec|seconds)\b|\b48\b[^\n]{0,30}\b11\b|\b11\s*(s|sec|seconds)\b|\b7[0-9]\s*%"
             r"|\b4(\.\d)?\s*(x|×|times)\b|\bfour times\b|\bquarter of the time\b")
RN_ANY_NUMBER = r"\d+(\.\d+)?\s*(%|x\b|×|times\b|ms\b|s\b|sec|seconds|minutes)|\bup to\b|\b(twice|half|double|triple)\b|-fold"
RN_BREAKING = r"action required|breaking|⚠|before you upgrade|upgrade notes?|migrat|important"
RN_NOISE = r"eslint|vitest|pnpm|\bCI\b|CONTRIBUTING|\btypo\b|\blint\b|autofix|refactor|dependabot|test coverage"


def added_lines(old, new):
    """The lines `new` has that `old` does not — what a run prepended to an existing CHANGELOG."""
    a, b = old.splitlines(), new.splitlines()
    out = []
    for op, _, _, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            out += b[j1:j2]
    return "\n".join(out)


def rn_notes(run, fixture):
    """(the notes, where they came from). The longest markdown the run wrote that names 2.4.0 — an added file,
    the added part of a modified one, or a non-response file in outputs/. Failing that, the response from its
    first 2.4.0 heading to its help line (or, without one, to the handoff line)."""
    added, modified, _ = changes(run, fixture)
    cands = []
    for f in added + modified:
        if not f.endswith(".md") or f.startswith(".workflow"):
            continue
        text = read(run / "repo" / f)
        if f in modified:
            text = added_lines(read(FIXTURES / fixture / f), text)
        cands.append((text, f))
    for p in run.glob("outputs/*.md"):
        if p.name != "response.md":
            cands.append((read(p), f"outputs/{p.name}"))
    cands = [c for c in cands if re.search(V240, c[0])]
    if cands:
        return max(cands, key=lambda c: len(c[0]))
    r = resp(run)
    m = re.search(rf"^#{{1,4}}[^\n]*{V240}[^\n]*$", r, re.M)
    if not m:
        return "", "no notes"
    body = r[m.start():]
    line = help_line(body)
    end = body.index(line) + len(line) if line else None
    if end is None:
        h = re.search(r"^[^\n]*(Release notes for[^\n]*ready|#{1,4}[^\n]*handoff)", body[1:], re.I | re.M)
        end = h.start() + 1 if h else len(body)
    return body[:end], "outputs/response.md (no notes file)"


def entries(text):
    """One string per bullet, heading or paragraph, continuation lines joined — a hard-wrapped entry is one unit."""
    out, cur = [], []
    for line in text.splitlines():
        if not line.strip() or re.match(r"\s*([-*+]|\d+[.)]|#{1,6})\s", line):
            if cur:
                out.append(" ".join(cur))
            cur = [line.strip()] if line.strip() else []
        else:
            cur.append(line.strip())
    if cur:
        out.append(" ".join(cur))
    return out


def heading_at(text, pat, skip=V240):
    for m in re.finditer(r"^#{1,4}[^\n]*$", text, re.M):
        if re.search(pat, m.group(), re.I) and not re.search(skip, m.group()):
            return m.start()
    return None


def rn_header(notes):
    """The first heading naming 2.4.0 carries the tag's date, in the heading or the two lines under it."""
    m = re.search(rf"^#{{1,4}}[^\n]*{V240}[^\n]*$", notes, re.M)
    if not m:
        return False, "no heading names 2.4.0"
    head = "\n".join(notes[m.start():].splitlines()[:3])
    return bool(re.search(RN_TAG_DATE, head, re.I)), head.replace("\n", " | ")[:160]


def rn_summary(notes):
    """Prose between the 2.4.0 heading and the next heading — the summary many readers stop at."""
    m = re.search(rf"^#{{1,4}}[^\n]*{V240}[^\n]*$", notes, re.M)
    if not m:
        return False, "no 2.4.0 heading"
    rest = notes[m.end():]
    nxt = re.search(r"^#{1,6}\s", rest, re.M)
    block = rest[: nxt.start()] if nxt else rest
    prose = [ln for ln in block.splitlines() if ln.strip() and not re.match(r"\s*(\*\*[^*]+\*\*\s*$|[-*]\s|---)", ln)]
    words = len(" ".join(prose).split())
    return words >= 15, f"{words} words of summary"


def rn_breaking_first(notes):
    """An action-required / breaking section that comes before the features section, holding the page-size
    change and the action to take."""
    ib = heading_at(notes, RN_BREAKING)
    inew = heading_at(notes, r"\bnew\b|features?|what'?s new|\badded\b", skip=rf"{V240}|{RN_BREAKING}")
    if inew is None:  # no features heading: the feature's own heading or bold lead line
        m = re.search(r"^(#{1,6}|\*\*)[^\n]*maintenance window", notes, re.I | re.M)
        inew = m.start() if m else None
    if ib is None or inew is None:
        return False, f"breaking heading at {ib}, features heading at {inew}"
    if ib > inew:
        return False, f"breaking heading at {ib} comes after the features heading at {inew}"
    sect = notes[ib:inew]
    ok = (re.search(r"\b50\b", sect) and re.search(r"page|per request|items", sect, re.I)
          and re.search(r"next_cursor|cursor|\blimit\b|next page|paginat", sect, re.I))
    return bool(ok), "breaking section holds the 500 → 50 change and the action" if ok else "action or change missing from it"


def rn_dropped_count(r, lo=8, hi=11):
    """A dropped count stated in the handoff. Ten of the 18 have no user effect (nine if the release-version
    commit is not counted as a change, eight if the reverted pair is counted once)."""
    nums = [int(n) for n in re.findall(r"\b(\d+)\s+(?:[\w-]+\s+){0,5}?(?:were\s+|was\s+|are\s+)?dropped\b", r, re.I)]
    nums += [int(n) for n in re.findall(r"\bdropped\b\W{0,4}(?:[\w-]+\W{1,3}){0,3}?(\d+)\b", r, re.I)]
    return any(lo <= n <= hi for n in nums), f"counts stated: {nums or 'none'}"


def help_line(text):
    """The first line carrying a link and, outside the URL, a help/support/forum/contact word."""
    for line in text.splitlines():
        if re.search(r"https?://", line) and re.search(r"\b(help|support|questions?|contact|forum)\b",
                                                       re.sub(r"https?://\S+", "", line), re.I):
            return line
    return None


def rn_help_link(notes):
    line = help_line(notes)
    return bool(line), line.strip()[:120] if line else "no line with a link and help/support/forum/contact"


def eval29(run):
    """release-notes: the tag's range, breaking first, translated, nothing invented, the drops counted."""
    fx = "release-notes"
    notes, src = rn_notes(run, fx)
    r = resp(run)
    t = r + "\n" + notes
    have = len(notes) >= 600
    es = entries(notes)
    timeline = [e for e in es if re.search(r"timeline", e, re.I)]
    export = [e for e in es if re.search(r"\bexport", e, re.I)]
    report = [e for e in es if re.search(r"weekly|uptime report|report email|digest", e, re.I)]
    month = [e for e in es if re.search(r"uptime|percentage|\bSLA\b", e, re.I) and re.search(r"month|last day|30th|31st", e, re.I)]
    sec = [e for e in es if re.search(r"security|vulnerab|advisory|CVE-2026-41207", e, re.I)]
    hdr_ok, hdr_ev = rn_header(notes)
    bf_ok, bf_ev = rn_breaking_first(notes)
    return [
        # capability — any competent attempt manages these
        ("release notes for 2.4.0 written", have, f"{len(notes)} chars from {src}", C),
        ("maintenance windows announced", any_of(notes, r"maintenance window"), "", C),
        ("the list page-size change announced",
         near(notes, r"\b50\b", r"page|per request|items|list endpoints"), "", C),
        ("a summary under the header", *rn_summary(notes), C),
        ("the deprecation carries its date and replacement",
         any_of(notes, r"/?v1/webhooks|v1 webhooks") and any_of(notes, r"2027-03-31|31 March 2027|March 31,? 2027|31 Mar 2027")
         and any_of(notes, r"/?v2/hooks|v2 hooks"), "", C),
        ("a help link closes the notes", *rn_help_link(notes), C),
        ("the work after the tag is not announced",
         have and not any_of(notes, r"\bSMS\b|Twilio|favicon|text message"), "#270, #271 are after v2.4.0", C),
        # delta — what the skill instructs
        ("the range confirmed: v2.3.0..v2.4.0, 18 commits",
         near(t, r"v?2\.3\.0\s*(\.\.\.?|→|->|–|—|to)\s*v?2\.4\.0", r"\b18\s+(commits|changes|PRs)"), "", D),
        ("the tier stated as Major", near(t, r"\bMajor\b", r"\btier\b|treatment|calibrat|\bdepth\b"), "", D),
        ("header has the exact version and the tag's date", hdr_ok, hdr_ev, D),
        ("the breaking change sits above the features, with the action", bf_ok, bf_ev, D),
        ("no internal identifiers in the notes",
         have and not re.search(RN_INTERNAL, notes), f"found: {sorted(set(m.group() for m in re.finditer(RN_INTERNAL, notes)))[:6]}", D),
        ("the unmeasured timeline improvement carries no number",
         bool(timeline) and not any(re.search(RN_ANY_NUMBER, e, re.I) for e in timeline),
         (timeline or ["no timeline entry"])[0][:160], D),
        ("the measured export figure used, its source named in the handoff",
         any(re.search(RN_FIGURE, e, re.I) for e in export)
         and near(r, r"export|48|\b11\b", r"#256|\bPR\s*256|pull request 256|\bstaging\b"),
         "PR #256: 48 s → 11 s on staging", D),
        ("fixes state the user's symptom, not the cause",
         any(re.search(r"SSO|single sign-on|never|did(n't| not)|not (sent|delivered|arriv)|wasn't|weren't", e, re.I) for e in report)
         and bool(month) and not any_of(notes, r"\bnull\b|TypeError|off-by-one|\bguard\b|end bound|\bscim\b"),
         "issues #318 and #322 give the symptoms", D),
        ("the reverted Slack threading is not announced",
         have and not any_of(notes, r"thread"), "#252 shipped and was reverted by #265", D),
        ("the CVE published as its effect, not as a bump",
         any(re.search(r"sign(ed|s)?[ -]in|log(ged|s)?[ -]in|single sign-on|\bSSO\b|account", e, re.I) for e in sec)
         and not any_of(notes, r"\bbump|\b3\.1\.[24]\b|saml-verify"), "", D),
        ("plain bumps, CI, tests, docs, lint and refactors dropped",
         have and not any_of(notes, RN_NOISE), "", D),
        ("the dropped count stated in the handoff", *rn_dropped_count(r), D),
        ("the unquantified improvement named in the handoff",
         any(re.search(r"timeline", ln, re.I) and re.search(
             r"no (figure|number|measure)|without (a )?(figure|number|measure)|unmeasured|not (been )?(measured|benchmarked)"
             r"|(would|has|have|needs?) to be measured|needs? (a )?(measurement|benchmark|timing)", ln, re.I)
             for ln in r.splitlines()), "", D),
    ]


# ------------------------------------------------------ databases (30-31)
#
# dbaudit is graded like netaudit: findings parsed out of its tables (five things each),
# every file:line it cites resolved against the fixture, the score's arithmetic and cap,
# the gate condition by condition, and nothing echoed or changed. dbdesign is graded by
# executing the DDL it wrote in sqlite3 and reading the catalog back.

DB_REF = r"([\w./-]+\.(?:sql|ini)):(\d+)(?:\s*[-–]\s*(\d+))?"
DB_CONF = r"✅|⚠️|🔬|\bdecidable\b|\bproxy\b|needs.data"
DB_THEORY = (r"§\s?\d|\b[1-4]NF\b|BCNF|integrity|\bACID\b|atomicity|isolation|\bSSOT\b|single source|\bUID\b"
             r"|functional dependenc|relational algebra|Codd|redundan|normali")
DB_SEVERITY = r"\b(Critical|High|Medium|Low)\b"


def db_md_tables(t):
    """[(header cells, [row cells])] for every markdown table in t."""
    cells = lambda line: [c.strip() for c in line.strip().strip("|").split("|")]
    lines, out, i = t.splitlines(), [], 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            head, rows, j = cells(lines[i]), [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            out.append((head, rows))
            i = j
        else:
            i += 1
    return out


def db_finding_rows(t):
    """Rows of every findings table (a header with a severity and an evidence column), as
    {conf, theory, severity, evidence, text}. A column the header lacks reads the whole row."""
    rows = []
    for head, body in db_md_tables(t):
        col = lambda pat: next((i for i, h in enumerate(head) if re.search(pat, h, re.I)), None)
        sev, ev = col(r"sev"), col(r"evid|line|ref")
        if sev is None or ev is None:
            continue
        conf, th = col(r"conf"), col(r"theory|principle")
        for r in body:
            text = " | ".join(r)
            get = lambda i: r[i] if i is not None and i < len(r) else text
            rows.append({"conf": get(conf), "theory": get(th), "severity": get(sev), "evidence": get(ev), "text": text})
    return rows


def db_finding_complete(row):
    return bool(re.search(DB_CONF, row["conf"]) and re.search(DB_THEORY, row["theory"], re.I)
                and re.search(DB_SEVERITY, row["severity"]) and re.search(DB_REF, row["evidence"]))


def db_fixture_lines(fixture):
    """{relative path: line count} for every file in the fixture."""
    return {str(p.relative_to(FIXTURES / fixture)): len(read(p).splitlines())
            for p in (FIXTURES / fixture).rglob("*") if p.is_file()}


def db_refs(t, fixture):
    """[(cited path, first, last, resolves)] — a citation resolves when a fixture file ends with that
    path and has the lines."""
    lines = db_fixture_lines(fixture)
    out = []
    for m in re.finditer(DB_REF, t):
        name, lo = m.group(1).lstrip("./"), int(m.group(2))
        hi = int(m.group(3) or lo)
        hits = [n for f, n in lines.items() if f == name or f.endswith("/" + name) or name.endswith("/" + f)]
        out.append((name, lo, hi, any(1 <= lo <= hi <= n for n in hits)))
    return out


def db_stmt_lines(fixture, rel, start, end=r";\s*$"):
    """(first, last) line of the first statement in a fixture file starting at `start`."""
    lines = read(FIXTURES / fixture / rel).splitlines()
    for i, line in enumerate(lines):
        if re.search(start, line):
            for j in range(i, len(lines)):
                if re.search(end, lines[j]):
                    return i + 1, j + 1
    return 0, -1


def db_cited_at(t, anchor, targets, after=420, before=160):
    """Somewhere `anchor` is mentioned, a file:line within reach falls inside one of `targets`
    [(file name, first, last)] — the evidence points at the planted defect, not just at the file."""
    for m in re.finditer(anchor, t, re.I):
        seg = t[max(0, m.start() - before): m.end() + after]
        for r in re.finditer(DB_REF, seg):
            name, lo = r.group(1).rsplit("/", 1)[-1], int(r.group(2))
            hi = int(r.group(3) or lo)
            if any(name == f and lo <= b and hi >= a for f, a, b in targets):
                return True
    return False


# dbaudit's gate (harness/dbreview.py): score ≥ 9.0, no open Critical/High, not unused or a copy,
# 🔬 flags at most 10 % of the objects.
DB_GATE_CONDITIONS = (r"\b9\.0\b", r"open (Critical|High)|\bCritical\b[^\n;|]{0,25}\bHigh\b", r"unused|copy",
                      r"🔬|needs.data|flag ratio|\b10\s?%")


def db_gate_clauses(seg):
    """How many of the gate's four conditions are stated each in a clause of its own (a line, a bullet,
    a table cell or a `;`-separated clause, as dbreview.py's gate.md writes them): condition by
    condition, not one sentence naming them all."""
    parts = [p for p in re.split(r"\n|;|·|\|", seg) if p.strip()]
    used, n = set(), 0
    for pat in DB_GATE_CONDITIONS:
        hit = next((i for i, p in enumerate(parts) if i not in used and re.search(pat, p, re.I)), None)
        if hit is not None:
            used.add(hit)
            n += 1
    return n


# ---- eval 30: dbaudit

DA_SECRETS = ("eval-fake-Pg-4hT9wq", "eval-fake-dblink-7Qm2")
DA_RUNTIME = (r"\bslow(er|ness)?\b|row counts?|\b\d+(\.\d+)?\s*(k|M|million|billion)\s+rows|largest table|index usage"
              r"|unused index|pg_stat|execution plan|query plan|still (read|used)|no longer (read|used)")
DA_TRANSITIVE = r"customer_(email|name)"
DA_BASE = r"\bbase\b\**\s*(?:score\s*)?(?:=|:|of|is)?\s*\**\s*\d"
DA_STRENGTH = (r"^[^\n]*\bpayment\b[^\n]*(🟢|well done|working well|strength)[^\n]*$"
               r"|^[^\n]*(🟢|well done|working well|strength)[^\n]*\bpayment\b[^\n]*$")


def da_untouched(run):
    """No fixture file changed or deleted; nothing but markdown (or files under an analysis/ folder that
    aren't SQL) added. An audit writes evaluations, not DDL."""
    added, modified, deleted = changes(run, "db-audit")
    bad = modified + deleted + [f for f in added if not f.endswith(".md")
                                and not ("analysis" in f.split("/")[:-1] and not f.endswith(".sql"))]
    return not bad, f"touched: {bad[:6]}" if bad else "nothing changed"


def eval30(run):
    """dbaudit on a PostgreSQL dump: findings with five things, real evidence lines, the formula, the gate, no secrets, no changes."""
    t = everything(run, "db-audit")
    rows = db_finding_rows(t)
    full = [r for r in rows if db_finding_complete(r)]
    if rows:
        five, fev = len(rows) >= 8 and len(full) >= 0.9 * len(rows), f"{len(full)}/{len(rows)} finding rows complete"
    else:
        counts = (len(re.findall(DB_CONF, t)), len(re.findall(DB_THEORY, t, re.I)), len(re.findall(DB_REF, t)))
        five, fev = min(counts) >= 8, f"no findings table; conf/theory/refs {counts}"
    cited = db_refs(t, "db-audit")
    bad_refs = [f"{n}:{a}" for n, a, b, ok in cited if not ok]
    schema = lambda table: ("schema.sql", *db_stmt_lines("db-audit", "db/schema.sql", rf"TABLE public\.{table}\b"))
    planted = {
        "no PK": db_cited_at(t, r"inventory_movement", [schema("inventory_movement")]),
        "no FK": db_cited_at(t, r"order_line\.product_id|product_id",
                             [schema("order_line"), ("0012_supplier_import.sql", 1, 3)]),
        "phones": db_cited_at(t, r"phone[123]", [schema("customer"), ("0011_customer_phones.sql", 1, 4)]),
        "multi-row": db_cited_at(t, r"trg_order_line_total|fn_recalc_order_total|new_lines", [
            ("functions.sql", *db_stmt_lines("db-audit", "db/functions.sql", r"fn_recalc_order_total", r"^\$\$;")),
            ("triggers.sql", *db_stmt_lines("db-audit", "db/triggers.sql", r"trg_order_line_total"))]),
    }
    missed = [k for k, ok in planted.items() if not ok]
    crit_row = any(re.search(r"trg_order_line_total|fn_recalc_order_total|new_lines", r["text"])
                   and re.search(r"\bCritical\b", r["severity"]) for r in rows)
    p_vals = len(re.findall(r"\|\s*(?:0\.\d{1,3}|1(?:\.0{1,3})?)\s*\|", t)) + len(re.findall(r"\bp\s*=\s*(?:0\.\d+|1\.0+)\b", t))
    capped = near(t, r"\bcap\w*", r"\b2\.0\b")
    gate_conds = max([db_gate_clauses(t[m.start(): m.start() + 900]) for m in re.finditer(r"\bgate\b", t, re.I)] or [0])
    runtime_graded = [r["text"][:80] for r in rows if re.search(DA_RUNTIME, r["text"], re.I)
                      and re.search(DB_SEVERITY, r["severity"]) and not re.search(r"🔬|needs.data", r["conf"])]
    transitive_graded = [r["text"][:80] for r in rows if re.search(DA_TRANSITIVE, r["text"])
                         and re.search(r"3NF|transitive", r["text"], re.I) and re.search(r"✅|decidable", r["conf"])]
    fixture_tables = set(re.findall(r"CREATE TABLE public\.(\w+)", read(FIXTURES / "db-audit/db/schema.sql")))
    new_tables = sorted({n for n in re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?\"?(\w+)", t, re.I)}
                        - fixture_tables)
    sentences = len(re.findall(r"\bEach \S+(?: \S+){0,2} (?:must|may) be\b[^\n.;]{0,100}?\b(?:one and only one|one or more)\b", t))
    return [
        # capability
        ("an audit with findings was written", len(t) > 1500 and any_of(t, r"finding"), f"{len(t)} chars", C),
        ("integrity gaps found: no PK on inventory_movement, no FK on order_line.product_id",
         near(t, r"inventory_movement", r"primary key|\bPK\b|entity integrity")
         and near(t, r"order_line\.product_id|0012", r"foreign key|\bFK\b|orphan|referential"), "", C),
        ("money stored as floating point found",
         near(t, r"double precision|\bfloat|floating", r"price|amount|money|monetary|total"), "", C),
        ("1NF breaks found: phone1..phone3 and the product_attribute EAV",
         near(t, r"phone[123]", r"1NF|repeating") and near(t, r"product_attribute", r"\bEAV\b|entity.attribute.value|generic|polymorphic|1NF"), "", C),
        ("the statement trigger that reads one row of the transition table found",
         near(t, r"trg_order_line_total|fn_recalc_order_total|new_lines",
              r"LIMIT 1|one row|first row|single row|multi-?row|one order|one arbitrary"), "", C),
        ("the stock trigger's hidden side effects found",
         near(t, r"trg_order_line_reserve|fn_reserve_stock",
              r"side.?effect|other tables?|unrelated|hidden|inventory_movement|stock_on_hand"), "", C),
        # delta
        ("cross-file index criteria: the unindexed order_line.order_id FK and the redundant ix_product_sku",
         near(t, r"order_line\s*\(\s*order_id\s*\)|order_line\.order_id",
              r"no index|unindexed|not indexed|missing (an |the )?index|without (an |any )?index") and near(t, r"ix_product_sku", r"redundan|duplicat"),
         "FK columns against the index list, unique keys against the plain indexes", D),
        ("no secret value echoed (kind and location only)", *no_secret_echoed(run, "db-audit", DA_SECRETS), D),
        ("both credentials recorded by kind and location",
         near(t, r"password|credential|secret", r"database\.ini:\d+") and near(t, r"password|credential|secret", r"functions\.sql:\d+"),
         "app/config/database.ini and the dblink string in functions.sql", D),
        ("findings carry confidence, theory, severity and file:line", five, fev, D),
        ("every cited line exists and the evidence points at the planted defects",
         len(cited) >= 8 and len(bad_refs) <= 0.05 * len(cited) and not missed,
         f"{len(cited)} refs, unresolved {bad_refs[:4]}, missed {missed}", D),
        ("score shows p, base and the 2.0 cap set by the multi-row Critical",
         any_of(t, DA_BASE) and p_vals >= 3 and capped and crit_row,
         f"{p_vals} p values · cap 2.0 {capped} · trigger rated Critical {crit_row}", D),
        ("gate stated as not passed, condition by condition",
         near(t, r"\bgate\b", r"not met|fail|not good enough|not passed|✗|❌") and gate_conds >= 3,
         f"{gate_conds} conditions named", D),
        ("runtime facts flagged needs-data, never graded",
         len(re.findall(r"🔬|needs.data", t)) >= 3
         and near(t, r"🔬|needs.data", r"row counts?|\brows\b|pg_stat|slow|execution plan|query stat")
         and near(t, r"🔬|needs.data", r"usage|still read|reporting database|fn_sync_report") and not runtime_graded,
         f"graded as fact: {runtime_graded[:2] or 'none'}", D),
        ("the transitive customer_name/customer_email flagged as a 3NF candidate, not graded",
         near(t, DA_TRANSITIVE, r"3NF|transitive") and near(t, DA_TRANSITIVE, r"🔬|needs.data|candidate|profil")
         and not transitive_graded, f"graded ✅: {transitive_graded[:1] or 'none'}", D),
        ("strengths recorded: the payment table", any_of(t, DA_STRENGTH, flags=re.I | re.M), "", D),
        ("the recovered model written as relationship sentences", sentences >= 3, f"{sentences} sentences", D),
        ("mode, coverage, rubric v1.1 and the dump date stated",
         any_of(t, r"database audit") and any_of(t, r"coverage|read in full|deep-read") and has(t, r"\bv1\.1\b", r"2026-10-19"), "", D),
        ("no DDL, migration or config file changed", *da_untouched(run), D),
        ("evaluates and stops: no target table designed", not new_tables, f"new tables: {new_tables[:4] or 'none'}", D),
    ]


# ---- eval 31: dbdesign
#
# The requirements name SQLite, so the DDL the run wrote is executed in sqlite3 (in memory, foreign
# keys on) and the design is read back from the catalog: keys, foreign keys, unique sets, the
# intersection table, the price history. What the catalog can't show — Barker sentences, FDs, Codd,
# the open question — is read from the document.

DD_PG_ISMS = (r"\bAS\s+IDENTITY\b|\b(big|small)?serial\b(?=\s*(PRIMARY|NOT|NULL|,|\)))|\btimestamptz\b|\bjsonb\b|WITHOUT\s+OVERLAPS|\b(date|tstz|ts)range\b"
              r"|CREATE\s+(EXTENSION|TYPE|SCHEMA|DOMAIN)\b|num_nonnulls|uuidv7|::\w+|AUTO_INCREMENT|ENGINE\s*=")


def db_ddl_script(run, fixture):
    """(DDL text, where it came from): the .sql files the run added, else the ```sql blocks of the one
    document that holds the most CREATE TABLEs (a response that repeats the design's DDL would
    otherwise create every table twice)."""
    added, modified, _ = changes(run, fixture)
    sql = sorted(f for f in added + modified if f.endswith(".sql"))
    if sql:
        return "\n".join(read(run / "repo" / f) for f in sql), ", ".join(sql)
    docs = {f: read(run / "repo" / f) for f in added + modified if f.endswith(".md")}
    docs.update({f"outputs/{p.name}": read(p) for p in (run / "outputs").glob("*.md")})
    cands = [("\n".join(re.findall(r"```sql[^\n]*\n(.*?)```", text, re.S | re.I)), name) for name, text in docs.items()]
    cands = [c for c in cands if c[0].strip()]
    return max(cands, key=lambda c: len(re.findall(r"CREATE\s+TABLE", c[0], re.I)), default=("", "no DDL found"))


def db_sqlite_catalog(ddl):
    """Execute the DDL statement by statement in an in-memory SQLite with foreign keys on, and read the
    catalog back: ({table: {cols: {name: {notnull, pk}}, pk, fks: [{table, from}], uniques: [set], sql}},
    [errors]). One statement SQLite rejects is an error, not a reason to stop reading the rest."""
    con = sqlite3.connect(":memory:")
    errors, stmt = [], ""
    try:
        con.execute("PRAGMA foreign_keys = ON")
        for line in ddl.splitlines(keepends=True):
            stmt += line
            if sqlite3.complete_statement(stmt):
                try:
                    con.execute(stmt)
                except Exception as e:
                    errors.append(f"{stmt.strip().splitlines()[0][:50]}: {e}")
                stmt = ""
        if stmt.strip() and not re.fullmatch(r"(\s|--[^\n]*)*", stmt):
            errors.append(f"incomplete statement: {stmt.strip()[:50]}")
        info = {}
        for (t, sql) in con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall():
            cols = {r[1]: {"notnull": bool(r[3]), "pk": r[5]} for r in con.execute(f'PRAGMA table_info("{t}")')}
            pk = [c for c, v in sorted(cols.items(), key=lambda kv: kv[1]["pk"]) if v["pk"]]
            fks = {}
            for r in con.execute(f'PRAGMA foreign_key_list("{t}")'):
                fks.setdefault(r[0], {"table": r[2], "from": []})["from"].append(r[3])
            uniques = [set(pk)] if pk else []
            for r in con.execute(f'PRAGMA index_list("{t}")').fetchall():
                if r[2]:
                    uniques.append({x[2] for x in con.execute(f'PRAGMA index_info("{r[1]}")') if x[2]})
            info[t] = {"cols": cols, "pk": pk, "fks": list(fks.values()), "uniques": uniques, "sql": sql or ""}
        return info, errors
    finally:
        con.close()


def db_link_table(info, a, b):
    """A table with an FK to a table named like `a` and another to one named like `b`, unique on exactly
    that pair: an intersection table."""
    for t, d in info.items():
        for fa in [f for f in d["fks"] if re.search(a, f["table"], re.I)]:
            for fb in [f for f in d["fks"] if re.search(b, f["table"], re.I) and f is not fa]:
                if set(fa["from"]) | set(fb["from"]) in d["uniques"]:
                    return t
    return None


def db_history_table(info, parent, when=r"effective|valid|from|start|since|begin", what=r"price|amount|rate|fee|cents"):
    """A child of `parent` holding a value with a time indicator in its unique key (er-modeling §A2.6)."""
    for t, d in info.items():
        values = [c for c in d["cols"] if re.search(what, c, re.I)]
        for fk in d["fks"]:
            if t == fk["table"] or not re.search(parent, fk["table"], re.I) or not values:
                continue
            for c in [c for c in d["cols"] if re.search(when, c, re.I)]:
                if set(fk["from"]) | {c} in d["uniques"]:
                    return t
    return None


def db_cols_like(info, pat, tables=r"."):
    return [(t, c) for t, d in info.items() if re.search(tables, t, re.I) for c in d["cols"] if re.search(pat, c, re.I)]


def db_alternate_key(info, col):
    """Every column named like `col` is UNIQUE on its own and not the primary key."""
    hits = db_cols_like(info, col)
    return bool(hits) and all({c} in info[t]["uniques"] and c not in info[t]["pk"] for t, c in hits), hits


def db_check_clauses(sql):
    """The text of every CHECK ( … ) in a CREATE TABLE, parentheses balanced."""
    out = []
    for m in re.finditer(r"\bCHECK\s*\(", sql, re.I):
        depth, i = 1, m.end()
        while i < len(sql) and depth:
            depth += {"(": 1, ")": -1}.get(sql[i], 0)
            i += 1
        out.append(sql[m.end(): i - 1])
    return out


def db_subtypes_mapped(info):
    """Supertype + subtype tables sharing the member's key, or one member table whose kind column a
    CHECK ties to each subtype's mandatory columns (er-modeling §A3.2 step 6, physical-design §5.1)."""
    supers = [t for t in info if re.fullmatch(r"(member|party)s?", t, re.I)]
    shared = lambda sub: any(re.search(sub, t, re.I) and d["pk"] and any(f["table"] in supers and set(d["pk"]) <= set(f["from"])
                                                                        for f in d["fks"]) for t, d in info.items())
    if supers and shared(r"individual|person") and shared(r"compan|organi[sz]"):
        return True, "supertype + subtype tables"
    for s in supers:
        for c in info[s]["cols"]:
            # a CHECK tying the kind to the subtype's columns, not only listing the kinds
            if re.search(r"kind|type|category", c, re.I) and any(
                    re.search(rf"\b{c}\b", ck) and re.search(r"\bIS\s+(NOT\s+)?NULL\b", ck, re.I)
                    for ck in db_check_clauses(info[s]["sql"])):
                return True, f"single table, {s}.{c} tied to the subtype columns by CHECK"
    return False, f"supertypes {supers}"


def eval31(run):
    """dbdesign from requirements: SQLite DDL executed and read back, traps in what was asked, Barker, FDs, open questions."""
    t = everything(run, "db-design")
    doc, long_enough = deliverable(run, "db-design")
    ddl, src = db_ddl_script(run, "db-design")
    info, errors = db_sqlite_catalog(ddl) if ddl.strip() else ({}, ["no DDL"])
    err = None if info else (errors[0] if errors else "no table created")
    ddl_nc = re.sub(r"--[^\n]*|/\*.*?\*/", "", ddl, flags=re.S)
    pg = [m.group(0) for m in re.finditer(DD_PG_ISMS, ddl_nc, re.I)]
    n_tables = len(re.findall(r"CREATE\s+TABLE", ddl, re.I))
    no_pk = [t_ for t_, d in info.items() if not d["pk"]]
    n_fk = sum(len(d["fks"]) for d in info.values())
    attend = db_link_table(info, r"booking|reservation", r"member|individual|person")
    listy = db_cols_like(info, r"attendee|participant|member_ids|_list$|_csv$|_json$", r"booking|reservation")
    hist = db_history_table(info, r"plan")
    age = db_cols_like(info, r"^age$|_age$|^age_|age_years")
    birth = db_cols_like(info, r"birth|dob")
    sub_ok, sub_ev = db_subtypes_mapped(info)
    keys = {c: db_alternate_key(info, c) for c in (r"^e.?mail", r"vat", r"member_?(number|no|code)|card_?number")}
    link = [(t_, c, info[t_]["cols"][c]["notnull"]) for t_, d in info.items() if re.search(r"individual|person|member", t_, re.I)
            for f in d["fks"] for c in f["from"] if re.search(r"compan|employ|organi|works_for|billed_to", c, re.I)]
    oq = section(doc, r"open question|unresolved")[:4000]
    stored_total = db_cols_like(info, r"total|cost", r"booking|reservation")
    barker = len(re.findall(r"\bEach [A-Z][A-Z]+(?: [A-Z][A-Z]+)* (?:must|may) be\b[^\n.;]{0,120}?\b(?:one and only one|one or more)\b", t))
    fd_sec = section(t, r"functional dependenc|normali[sz]")[:6000]
    fds = len(re.findall(r"\w+(?:\s*,\s*\w+)*\s*\}?\s*(?:→|->)\s*\{?\s*\w+", fd_sec))
    codd = set(re.findall(r"\b[Rr]ule\s+(\d{1,2})\b", t)) | {n for n in (
        "information rule", "guaranteed access", "systematic treatment of null", "dynamic catalog", "view updating",
        "integrity independence", "physical (data )?independence", "logical (data )?independence", "nonsubversion")
        if re.search(n, t, re.I)}
    added, modified, deleted = changes(run, "db-design")
    dbs = [f for f in added if f.endswith((".db", ".sqlite", ".sqlite3"))
           or (run / "repo" / f).read_bytes()[:16] == b"SQLite format 3\x00"]
    return [
        # capability
        ("a design document was produced", long_enough, f"{len(doc)} chars", C),
        ("target DDL written", n_tables >= 5, f"{n_tables} CREATE TABLE in {src}", C),
        ("every table has a primary key (executed)", bool(info) and not no_pk, err or f"no PK: {no_pk}", C),
        ("relationships declared as foreign keys (executed)", n_fk >= 4, err or f"{n_fk} FKs", C),
        ("booking attendees resolved into an intersection table, unique per pair (executed)",
         bool(attend) and not listy, err or f"intersection {attend}; list columns {listy}", C),
        # delta
        ("the DDL runs on SQLite, the engine the requirements name",
         bool(info) and not errors and not pg and near(t, r"SQLite", r"engine|target|DDL|dialect"),
         f"errors {errors[:2] or 'none'} · PG-isms {pg[:3] or 'none'}", D),
        ("plan prices kept as effective-dated history, unique per plan and date (executed)", bool(hist),
         err or f"history table: {hist}", D),
        ("age not stored: a birth date instead (executed)", bool(birth) and not age, err or f"age {age} · birth {birth}", D),
        ("the stored booking total treated as derived: declined or justified",
         near(t, r"total cost|booking total|total_cost", r"derived|denormali")
         and (not stored_total or near(t, r"total cost|total_cost", r"justif|trade.?off|snapshot|generated|kept consistent")),
         f"stored: {stored_total or 'no'}", D),
        ("the member subtypes mapped deliberately, with the choice stated",
         sub_ok and near(t, r"subtype|supertype", r"single.table|separate tables|supertype \+|table per|shared (primary )?key|one table"),
         err or sub_ev, D),
        ("natural keys are UNIQUE alternates, not primary keys (email, VAT, member number)",
         all(ok for ok, _ in keys.values()), err or "; ".join(f"{k}: {h}" for k, (_, h) in keys.items())[:200], D),
        ("the freelancer question left open: the company link optional and listed as an open question",
         bool(link) and not any(nn for *_, nn in link) and any_of(oq, r"freelanc|self.employ|works for|employer|billed to"),
         err or f"link {link}", D),
        ("a Barker conceptual model with two-way relationship sentences", any_of(t, r"Barker") and barker >= 4,
         f"{barker} Barker sentences", D),
        ("functional dependencies and the normal-form rationale stated", fds >= 3 and bool(re.search(r"3NF|BCNF", fd_sec)),
         f"{fds} FDs", D),
        ("Codd's rules reviewed", any_of(t, r"Codd") and len(codd) >= 3, f"{sorted(codd)[:6]}", D),
        ("assumptions kept apart from open questions",
         bool(re.search(r"^#{1,4}[^\n]*assumption", t, re.I | re.M)) and bool(re.search(r"^#{1,4}[^\n]*(open question|unresolved)", t, re.I | re.M)),
         "", D),
        ("nothing applied: no database file created", not dbs, f"{dbs or 'none'}", D),
        ("the requirements left untouched", not (modified or deleted), f"{(modified + deleted) or 'untouched'}", D),
    ]


# ------------------------------------------------ evals 32-34: database (dbdiagram, dbpropose, dbbuild)
#
# One estate, PawLedger (a desktop vet-clinic app on SQLite), shared by all three fixtures: the same
# design/design.md and design/model.json, so the stages agree the way harness/dbworkflow.py expects.

def db_text(raw):
    """A draw.io label as plain text, keeping its line breaks."""
    t = re.sub(r"<br\s*/?>|</(div|p|tr|li|h\d)>", "\n", raw or "", flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")


def db_drawio(xml_text):
    """[(page name, {id: cell})] with each cell's text (line breaks kept), style, kind, parent and ends;
    None when the file is not well-formed, not an mxfile, or compressed."""
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None
    if root.tag.rsplit("}", 1)[-1] != "mxfile":
        return None
    pages = []
    for d in root.iter("diagram"):
        model = d.find("mxGraphModel")
        if model is None:
            return None
        cells = {}
        for el in model.iter():
            cid = el.get("id")
            if not cid or el.tag not in ("mxCell", "object", "UserObject"):
                continue
            inner = el.find("mxCell") if el.tag != "mxCell" else None
            cell = el if inner is None else inner
            cells[cid] = dict(text=db_text(el.get("value") if el.tag == "mxCell" else el.get("label")),
                              style=cell.get("style") or "", edge=cell.get("edge") == "1",
                              vertex=cell.get("vertex") == "1", parent=cell.get("parent"),
                              source=cell.get("source"), target=cell.get("target"))
        pages.append((d.get("name") or "", cells))
    return pages


def db_first_line(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return re.sub(r"\s*\(.*?\)\s*", " ", lines[0]).strip() if lines else ""


def db_find(cells, names, pick):
    """{name: cell id} for the vertices `pick(first line, name)` accepts, topmost first."""
    found = {}
    for name in names:
        for cid, c in cells.items():
            if c["vertex"] and pick(db_first_line(c["text"]), name):
                if name not in found or cells.get(c["parent"], {}).get("vertex") is not True:
                    found[name] = cid
    return found


def db_owner(cells, cid, owners):
    """The id in `owners` that `cid` is, or sits inside; otherwise the topmost vertex above it."""
    seen = cid
    while cid in cells and cid not in owners:
        parent = cells[cid]["parent"]
        if parent not in cells or not cells[parent]["vertex"]:
            break
        cid = parent
    return cid if cid in owners else seen


def db_inner_text(cells, cid):
    """A cell's text plus the text of every cell nested in it (attribute rows, edge labels)."""
    kids = defaultdict(list)
    for k, c in cells.items():
        kids[c["parent"]].append(k)
    out, todo = [], [cid]
    while todo:
        k = todo.pop(0)
        out.append(cells[k]["text"])
        todo += kids.get(k, [])
    return "\n".join(out)


def db_row_lines(cells, cid):
    """A table drawn in draw.io as lines: its own label's lines, then one line per direct child (a column row),
    with the row's nested cells (key, name, type) joined — the swimlane and the shape=table styles alike."""
    lines = cells[cid]["text"].splitlines()
    for k, c in cells.items():
        if c["parent"] == cid and not c["edge"]:
            lines.append(" ".join(db_inner_text(cells, k).split()))
    return lines


def db_er_graph(cells, ent):
    """Barker relationships drawn on the ER page. `ent` maps entity name → cell id. Returns
    (pairs: {frozenset(names): [edge ids]}, ternary connectors, Chen-style connectors). A connector is a
    non-entity vertex an edge ends on: a junction joining two half-lines is fine; one joining three or more
    entities is a ternary relationship, and a diamond or oval joined to an entity is Chen notation."""
    name_of = {cid: n for n, cid in ent.items()}
    ends = {}
    for cid, c in cells.items():
        if c["edge"]:
            ends[cid] = [db_owner(cells, x, name_of) for x in (c["source"], c["target"])]
    nb = defaultdict(set)
    for s, t in ends.values():
        for a, b in ((s, t), (t, s)):
            if a not in name_of and a in cells and b in name_of:
                nb[a].add(name_of[b])
    pairs = defaultdict(list)
    for e, (s, t) in ends.items():
        if s in name_of and t in name_of and s != t:
            pairs[frozenset((name_of[s], name_of[t]))].append(e)
        for x, y in ((s, t), (t, s)):
            if x in name_of and y in nb and len(nb[y]) == 2:
                pairs[frozenset(nb[y])].append(e)
    ternary = sorted(k for k, v in nb.items() if len(v) >= 3)
    chen = sorted(k for k, v in nb.items() if v and re.search(r"rhombus|ellipse|umlClass|shape=uml", cells[k]["style"]))
    return pairs, ternary, chen


DB_INFERRED = r"inferred|unconfirmed|not (yet )?confirmed|to be confirmed|assum"


def db_attr_pattern(mark, name):
    m = "[oO○]" if mark == "o" else re.escape(mark)
    return rf"(^|\s){m}\s*{r'[ _]+'.join(map(re.escape, name.split()))}\b"


def eval32(run):
    """dbdiagram from an approved design: a Barker ER page and a relational page, editable and traceable."""
    model = json.loads(read(FIXTURES / "db-diagram/design/model.json"))
    ents = model["entities"] + model["associations"]
    rels = model["relationships"] + [
        {"a": a["name"], "b": p, "a_opt": "must", "b_opt": "may"} for a in model["associations"] for p in a["participants"]]
    drawn = {f.rsplit("/", 1)[-1]: read(run / "repo" / f) for f in find_added(run, "db-diagram", r"\.drawio$")}
    er_name = next((n for n in drawn if re.search(r"(^|[-_.])er([-_.]|$)|entity|barker", n, re.I)), None)
    rel_name = next((n for n in drawn if re.search(r"relational", n, re.I) and n != er_name), None)
    er_pages, rel_pages = db_drawio(drawn.get(er_name, "")), db_drawio(drawn.get(rel_name, ""))
    er_page = next((p for p in er_pages or [] if re.search(r"barker", p[0], re.I)), (er_pages or [("", {})])[0])
    er_title, er = er_page
    rel = (rel_pages or [("", {})])[0][1]

    # ER page
    loose = db_find(er, [e["name"] for e in ents], lambda line, n: re.fullmatch(rf"{n}S?", line, re.I))
    strict = db_find(er, [e["name"] for e in ents], lambda line, n: line == n)
    soft = [n for n, cid in strict.items() if re.search(r"rounded=1|arcSize", er[cid]["style"])]
    attr_miss = [f"{e['name']}: {m} {a}" for e in ents for m, a in e["attributes"]
                 if e["name"] not in loose or not re.search(db_attr_pattern(m, a), db_inner_text(er, loose[e["name"]]), re.I)]
    pairs, ternary, chen = db_er_graph(er, loose)
    want = {frozenset((r["a"], r["b"])): r for r in rels}
    seg_text = {p: [db_inner_text(er, e) for e in es] for p, es in pairs.items()}
    no_pair = [" – ".join(sorted(p)) for p in want if p not in pairs]
    role_bad = []
    for p, r in want.items():
        labels = {t.strip() for t in seg_text.get(p, []) if re.search(r"[a-z]", t) and t == t.lower()}
        roles_ok = all(r.get(k, "") in " ".join(labels) for k in ("a_role", "b_role"))
        if len(labels) < 2 or not roles_ok:
            role_bad.append(" – ".join(sorted(p)))
    opt_bad = []
    for p, r in want.items():
        dashed = [bool(re.search(r"dashed\s*=\s*1", er[e]["style"])) for e in pairs.get(p, [])]
        need_dash, need_solid = "may" in (r["a_opt"], r["b_opt"]), "must" in (r["a_opt"], r["b_opt"])
        if not dashed or (need_dash and not any(dashed)) or (need_solid and all(dashed)):
            opt_bad.append(" – ".join(sorted(p)))
    vacc = model["associations"][0]
    vacc_pairs = [frozenset((vacc["name"], p)) for p in vacc["participants"]]
    legend = any(re.search(r"barker notation", t, re.I) and re.search(r"dashed|optional|may be", t, re.I)
                 and re.search(r"crow|one or more|many", t, re.I)
                 for t in (db_inner_text(er, cid) for cid in er))
    pv = frozenset(("PET", "VET"))
    inferred = (any(re.search(DB_INFERRED, t, re.I) for t in seg_text.get(pv, []))
                or any(re.search(r"primary vet|registered with", c["text"], re.I) and re.search(DB_INFERRED, c["text"], re.I)
                       for c in er.values()))

    # relational page
    tables = [t["name"] for t in model["tables"]]
    tcell = db_find(rel, tables, lambda line, n: bool(re.fullmatch(rf"(\w+\.)?[\"`\[]?{n}[\"`\]]?(\s.*)?", line, re.I)))
    ttext = {t: db_inner_text(rel, c) for t, c in tcell.items()}
    col_miss = [f"{t['name']}.{c['name']}" for t in model["tables"] for c in t["columns"]
                if not re.search(rf"\b{c['name']}\b", ttext.get(t["name"], ""))]
    tlines = {t: db_row_lines(rel, c) for t, c in tcell.items()}
    fk_lines = lambda t, col: [ln for ln in tlines.get(t, []) if re.search(rf"\b{col}\b", ln)]
    key_bad = [t for t in tables if not any(re.search(r"\bPK\b", ln) for ln in fk_lines(t, "id"))]
    key_bad += [f"{f['table']}.{f['column']}" for f in model["foreign_keys"]
                if not any(re.search(r"\bFK\d*\b", ln) for ln in fk_lines(f["table"], f["column"]))]
    tname = {cid: t for t, cid in tcell.items()}
    fk_edges = defaultdict(int)
    for c in rel.values():
        if c["edge"]:
            s, t = (tname.get(db_owner(rel, x, tname)) for x in (c["source"], c["target"]))
            if s and t and s != t:
                fk_edges[frozenset((s, t))] += 1
    fk_want = defaultdict(int)
    for f in model["foreign_keys"]:
        fk_want[frozenset((f["table"], f["ref"]))] += 1
    fk_diff = {" – ".join(sorted(k)): (fk_edges.get(k, 0), fk_want.get(k, 0))
               for k in set(fk_edges) | set(fk_want) if fk_edges.get(k, 0) != fk_want.get(k, 0)}

    # traceability: each entity's ER cell and its table's relational cell share the table name in their IDs
    tok = lambda cid: set(re.split(r"[^a-z0-9]+", (cid or "").lower()))
    untraced = [e["name"] for e in ents
                if e["table"] not in tok(loose.get(e["name"])) or e["table"] not in tok(tcell.get(e["table"]))]
    prov = [bool(re.search(r"design/design\.md|design\.md", " ".join(c["text"] for c in cells.values())))
            for cells in (er, rel)]
    _, modified, deleted = changes(run, "db-diagram")
    touched = [f for f in modified + deleted if f.startswith("design/")]
    return [
        # capability
        ("an ER and a relational draw.io file written", bool(er_name) and bool(rel_name), f"{sorted(drawn)}", C),
        ("both files are well-formed, uncompressed mxfile",
         er_pages is not None and rel_pages is not None, f"er {er_pages is not None}, relational {rel_pages is not None}", C),
        ("every entity of the design is on the ER page", len(loose) == len(ents),
         f"missing {[e['name'] for e in ents if e['name'] not in loose]}", C),
        ("every table drawn on the relational page with all its columns", len(tcell) == len(tables) and not col_miss,
         f"tables {len(tcell)}/{len(tables)}, missing columns {col_miss[:5]}", C),
        ("PK and FK columns labelled", len(tcell) == len(tables) and not key_bad, f"{key_bad[:6] or 'ok'}", C),
        ("one edge per foreign key, and no other table-to-table edge", len(tcell) == len(tables) and not fk_diff,
         f"{fk_diff or f'{sum(fk_want.values())} FK edges'}", C),
        # delta
        ("files named for er-model and relational-model",
         bool(er_name) and "er-model" in er_name.lower() and bool(rel_name) and "relational-model" in rel_name.lower(),
         f"{sorted(drawn)}", D),
        ("the ER page titled Barker ER Model",
         bool(re.search(r"barker", er_title, re.I)) and (bool(re.search(r"barker er model", er_title, re.I))
                                                         or any(re.search(r"barker er model", c["text"], re.I) for c in er.values())),
         f"page {er_title!r}", D),
        ("a legend naming Barker notation and explaining its glyphs", legend, "", D),
        ("entities named singular UPPERCASE in soft-cornered boxes", len(soft) == len(ents),
         f"{sorted(set(e['name'] for e in ents) - set(soft))[:6] or 'all'}", D),
        ("every attribute carries its # / * / o mark", bool(loose) and not attr_miss, f"{attr_miss[:4] or 'ok'}", D),
        ("the three-way association drawn as an intersection entity with three binary relationships",
         vacc["name"] in strict and all(p in pairs for p in vacc_pairs) and not ternary and not chen,
         f"ternary connectors {ternary[:3]}, Chen shapes {chen[:3]}", D),
        ("every relationship carries a lowercase role name at each end", bool(pairs) and not role_bad and not no_pair,
         f"missing {no_pair[:3]}, unlabelled {role_bad[:3]}", D),
        ("each end's optionality drawn: dashed may-be, solid must-be", bool(pairs) and not opt_bad and not no_pair,
         f"{opt_bad[:4] or 'ok'}", D),
        ("cell IDs are semantic and trace each entity to its table", bool(loose) and bool(tcell) and not untraced,
         f"{untraced[:4] or 'ok'}", D),
        ("the inferred PET – VET relationship labelled as inferred", pv in pairs and inferred, "", D),
        ("a provenance note naming the design on both pages", all(prov), f"er {prov[0]}, relational {prov[1]}", D),
        ("the design left untouched", not touched, f"{touched or 'untouched'}", D),
    ]


# ---- eval 33: dbpropose

DB_PLAN = r"sequenc|migration|remediation|order of work|implementation|roll-?out|\bsteps\b|roadmap|\bplan\b"
DB_MISMATCH = r"mismatch|discrepan|out of date|stale|does not match|doesn't match|disagree|\bdiffers?\b|inconsisten"
DB_ADD_FK = r"(add|declare|rebuild|recreate|introduce)[^\n]{0,60}(foreign key|\bFKs?\b|REFERENCES)"


def eval33(run):
    """dbpropose from audit + design + diagrams: orphans before the FK, Critical first, expand/contract, no redraw."""
    p, pf = proposal_text(run, "db-propose")
    audit_ids = set(re.findall(r"\bDB-[A-Z]{3}-\d\d\b", read(FIXTURES / "db-propose/audit/summary.md")))
    ids = set(re.findall(r"\bDB-[A-Z]{3}-\d\d\b", p))
    m = re.search(rf"^#{{2,4}}[^\n]*({DB_PLAN})[^\n]*$", p, re.I | re.M)
    plan = p[m.start():] if m else ""
    oq = re.search(r"^(#{1,4})[^\n]*open question[^\n]*\n(.*?)(?=^#{1,4} |\Z)", p, re.I | re.M | re.S)
    oq = oq.group(2) if oq else ""
    words = set(re.findall(r"\b(Reuse|Refactor|Rework|Rebuild)\b", p))
    sdl = any(has(line, r"\bstructure\b", r"\bdata\b", r"\blogic\b") for line in p.splitlines() if line.count("|") >= 4)
    added, modified, deleted = changes(run, "db-propose")
    touched = [f for f in modified + deleted if f.startswith(("audit/", "design/", "diagrams/"))]
    touched += [f for f in added if f.endswith(".drawio")]
    dbs = [f for f in added + modified if (run / "repo" / f).read_bytes()[:16] == b"SQLite format 3\x00"]
    calls_ok, calls = never_called(run, "scripts/.calls.log")
    return [
        # capability
        ("a proposal was written", bool(pf), f"{pf}", C),
        ("the vaccination Critical and its orphan rows addressed", near(p, r"DB-REF-01", r"orphan"), "", C),
        ("decisions trace to the audit's finding ids", len(ids & audit_ids) >= 4, f"{sorted(ids & audit_ids)}", C),
        ("the audit score and its Critical cap cited", near(p, r"\b2\.0\b", r"\bcap|Critical"), "", C),
        ("the Reports add-on coupling to full_name noticed", near(p, r"Reports add-on|add-on", r"full_name"), "", C),
        # delta
        ("orphan rows resolved before the foreign keys are declared",
         before(plan, r"orphan", DB_ADD_FK), f"orphan at {first(plan, r'orphan')}, FK at {first(plan, DB_ADD_FK)}", D),
        ("the Critical handled before the name split",
         before(plan, r"DB-REF-01|orphan", r"DB-NRM-01|first_name|\bsplit"), "", D),
        ("the full_name split is expand/contract, contract gated on the Reports add-on",
         before(plan, r"\bexpand", r"\bcontract") and near(plan, r"\bcontract", r"Reports|add-on", 300), "", D),
        ("the reminder table marked as having no audit finding",
         near(p, r"reminder", r"no (audit )?finding|not (tied|traced|linked) to (an? |any )?(audit )?finding"
                              r"|without (an? )?(audit )?finding|new requirement|requirement R-?4|not from the audit", 200), "", D),
        ("no finding id invented", bool(ids) and ids <= audit_ids, f"not in the audit: {sorted(ids - audit_ids)}", D),
        ("the relational diagram's mismatch described and routed to dbdiagram",
         near(p, r"full_name|rev(ision)?\.? ?2\b", DB_MISMATCH) and near(p, DB_MISMATCH, r"dbdiagram", 400), "", D),
        ("the design and both diagrams cited by path",
         has(p, r"design/design\.md", r"er-model\.drawio", r"relational-model\.drawio"), "", D),
        ("every step names validation, rollback and blast radius", complete_steps(plan) >= 4,
         f"{complete_steps(plan)} complete steps", D),
        ("structure, data and logic decided separately, in the band vocabulary", sdl and len(words) >= 2,
         f"{sorted(words)}", D),
        ("needs-data flags carried as open questions",
         has(oq, r"microchip", r"Reports add-on|add-on|1\.x"), f"{len(oq)} chars of open questions", D),
        ("acceptance required before dbbuild", near(p, r"accept", r"dbbuild"), "", D),
        ("audit, design and diagrams untouched, nothing redrawn", not touched, f"{touched or 'untouched'}", D),
        ("nothing applied to a database", calls_ok and not dbs, f"{calls}; {dbs or 'no database file written'}", D),
    ]


# ---- eval 34: dbbuild

DB_SECRETS = ["EVAL-FAKE-sqlcipher-key-0001", "eval-fake-reports-token-0002"]
DB_GAP = (r"undecided|not (yet )?decided|open question|\bQ3\b|TODO|incomplete|pending|to be decided|awaiting"
          r"|needs? (a )?decision|unresolved|left open")
DB_STATEMENT = r"^\s*(CREATE|PRAGMA|BEGIN|INSERT|DROP|ALTER)\b"


def db_run_sql(run, fixture):
    """Every .sql the run wrote, executed in path order on one in-memory SQLite database (foreign keys on,
    ATTACH refused so nothing reaches disk). Returns (connection, error or None, files, concatenated text)."""
    sql_files = sorted(find_added(run, fixture, r"\.sql$"))
    text = "\n".join(read(run / "repo" / f) for f in sql_files)
    con = sqlite3.connect(":memory:", isolation_level=None)
    con.set_authorizer(lambda action, *a: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_ATTACH else sqlite3.SQLITE_OK)
    con.execute("PRAGMA foreign_keys = ON")
    err = None if sql_files else "no .sql written"
    for f in sql_files:
        try:
            con.executescript(read(run / "repo" / f))
        except Exception as e:
            err = f"{f}: {e}"
            break
    if con.in_transaction:
        con.execute("COMMIT")
    con.execute("PRAGMA foreign_keys = ON")
    return con, err, sql_files, text


def db_rejects(con, sql, args=()):
    """True when the statement is refused by a constraint; the database is left as it was."""
    con.execute("SAVEPOINT probe")
    try:
        con.execute(sql, args)
        ok = False
    except sqlite3.IntegrityError:
        ok = True
    except sqlite3.Error:
        ok = False
    con.execute("ROLLBACK TO probe")
    con.execute("RELEASE probe")
    return ok


def db_probe(con):
    """Insert one valid row per table, then try rows the design forbids. Returns (valid ok, [rules not enforced],
    a duplicate microchip accepted)."""
    ins = lambda sql, args: con.execute(sql, args).lastrowid
    try:
        o = ins("INSERT INTO owner (first_name, last_name, phone, email) VALUES (?, ?, ?, ?)", ("Ana", "Silva", "555-0101", None))
        v = ins("INSERT INTO vet (licence_no, name) VALUES (?, ?)", ("VET-001", "Dr Kim"))
        x = ins("INSERT INTO vaccine (code, name) VALUES (?, ?)", ("RAB", "Rabies"))
        p = ins("INSERT INTO pet (owner_id, primary_vet_id, name, species, date_of_birth, microchip) VALUES (?, ?, ?, ?, ?, ?)",
                (o, v, "Rex", "dog", "2020-01-01", "985000000000001"))
        ins("INSERT INTO vaccination (pet_id, vaccine_id, vet_id, given_on, lot_no) VALUES (?, ?, ?, ?, ?)", (p, x, v, "2026-01-10", "L1"))
        ins("INSERT INTO appointment (pet_id, vet_id, starts_at, duration_min, reason, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (p, v, "2026-02-01T09:00", 20, "checkup", None))
        ins("INSERT INTO reminder (pet_id, vaccine_id, due_on, sent_at) VALUES (?, ?, ?, ?)", (p, x, "2027-01-10", None))
    except sqlite3.Error as e:
        return False, [f"valid rows refused: {e}"], False
    bad = {
        "CHECK species": ("INSERT INTO pet (owner_id, name, species) VALUES (?, ?, ?)", (o, "Smaug", "dragon")),
        "CHECK duration_min > 0": ("INSERT INTO appointment (pet_id, vet_id, starts_at, duration_min, reason) VALUES (?, ?, ?, ?, ?)",
                                   (p, v, "2026-02-02T09:00", 0, "checkup")),
        "UNIQUE vet.licence_no": ("INSERT INTO vet (licence_no, name) VALUES (?, ?)", ("VET-001", "Dr Ruiz")),
        "UNIQUE vaccine.code": ("INSERT INTO vaccine (code, name) VALUES (?, ?)", ("RAB", "Rabies booster")),
        "UNIQUE vaccination (pet, vaccine, given_on)": (
            "INSERT INTO vaccination (pet_id, vaccine_id, vet_id, given_on, lot_no) VALUES (?, ?, ?, ?, ?)", (p, x, v, "2026-01-10", "L2")),
        "UNIQUE reminder (pet, vaccine, due_on)": (
            "INSERT INTO reminder (pet_id, vaccine_id, due_on) VALUES (?, ?, ?)", (p, x, "2027-01-10")),
        "FK vaccination.pet_id": (
            "INSERT INTO vaccination (pet_id, vaccine_id, vet_id, given_on, lot_no) VALUES (?, ?, ?, ?, ?)", (999, x, v, "2026-03-01", "L3")),
        "FK appointment.vet_id": ("INSERT INTO appointment (pet_id, vet_id, starts_at, duration_min, reason) VALUES (?, ?, ?, ?, ?)",
                                  (p, 999, "2026-02-03T09:00", 20, "checkup")),
        "NOT NULL owner.phone": ("INSERT INTO owner (first_name, last_name, phone) VALUES (?, ?, ?)", ("Bo", "Lind", None)),
        "NOT NULL vaccination.lot_no": (
            "INSERT INTO vaccination (pet_id, vaccine_id, vet_id, given_on, lot_no) VALUES (?, ?, ?, ?, ?)", (p, x, v, "2026-04-01", None)),
    }
    loose = [rule for rule, (sql, args) in bad.items() if not db_rejects(con, sql, args)]
    dup_chip = not db_rejects(con, "INSERT INTO pet (owner_id, name, species, microchip) VALUES (?, ?, ?, ?)",
                              (o, "Rex II", "dog", "985000000000001"))
    return True, loose, dup_chip


def eval34(run):
    """dbbuild from an accepted proposal: DDL that executes, matches the design, invents nothing and runs nowhere."""
    model = json.loads(read(FIXTURES / "db-build/design/model.json"))
    con, err, sql_files, sql = db_run_sql(run, "db-build")
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' "
                                        "AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
    pos = {t.lower(): i for i, t in enumerate(tables)}
    info = {t["name"]: con.execute(f'PRAGMA table_info("{t["name"]}")').fetchall() for t in model["tables"]}
    fkl = {t["name"]: con.execute(f'PRAGMA foreign_key_list("{t["name"]}")').fetchall() for t in model["tables"]}
    built = bool(sql_files) and not err and bool(tables)
    pk_bad = [t["name"] for t in model["tables"]
              if [c[1] for c in sorted(info[t["name"]], key=lambda c: c[5]) if c[5]] != t["pk"]]
    null_bad = []
    for t in model["tables"]:
        cols = {c[1]: c for c in info[t["name"]]}
        for c in t["columns"]:
            got = cols.get(c["name"])
            if got is None or (not c["null"] and not (got[3] or got[5])) or (c["null"] and (got[3] or got[5])):
                null_bad.append(f"{t['name']}.{c['name']}")

    def fk_row(f):
        return next((r for r in fkl[f["table"]] if r[3] == f["column"] and r[2].lower() == f["ref"]
                     and r[4] in (None, "id")), None)
    fk_miss = [f"{f['table']}.{f['column']}" for f in model["foreign_keys"] if not fk_row(f)]
    same = lambda want, got: got == want or {want, got} == {"RESTRICT", "NO ACTION"}
    act_bad = [f"{f['table']}.{f['column']}: {fk_row(f)[6]}" for f in model["foreign_keys"]
               if fk_row(f) and not same(f["on_delete"], fk_row(f)[6])]
    order_bad = [f"{f['ref']} after {f['table']}" for f in model["foreign_keys"]
                 if pos.get(f["ref"], -1) > pos.get(f["table"], 99)]
    want_cols = {t["name"]: {c["name"] for c in t["columns"]} for t in model["tables"]}
    extra = [t for t in tables if t.lower() not in want_cols]
    extra += [f"{t}.{c[1]}" for t in want_cols for c in info[t] if c[1] not in want_cols[t]]

    def indexes(t, unique=None):
        out = []
        for _, name, uq, *_rest in con.execute(f'PRAGMA index_list("{t}")').fetchall():
            if unique is None or uq == unique:
                out.append([r[2] for r in con.execute(f'PRAGMA index_info("{name}")').fetchall()])
        return out
    ix_miss = [f"{i['table']}({', '.join(i['columns'])})" for i in model["indexes"]
               if not any(cols[:len(i["columns"])] == i["columns"] for cols in indexes(i["table"]))]
    valid, loose, dup_chip = db_probe(con) if built else (False, ["not built"], False)
    chip_unique = any(cols == ["microchip"] for cols in indexes("pet", 1)) if built else True
    chip_flagged = near(sql, r"microchip", DB_GAP, 300) or near(resp(run), r"microchip", DB_GAP, 300)
    first_sql = read(run / "repo" / sql_files[0]) if sql_files else ""
    m = re.search(DB_STATEMENT, first_sql, re.I | re.M)
    header = first_sql[: m.start()] if m else first_sql
    head_ok = {"proposal path": any_of(header, r"proposal/proposal\.md"), "design path": any_of(header, r"design/design\.md"),
               "engine": any_of(header, r"SQLite\s*3"),
               "date": near(header, r"generat|created on|\bdate\b", r"20\d\d-\d\d-\d\d", 60),
               "new schema": any_of(header, r"\bnew\b[^\n]{0,40}(schema|database|install|clinic file)",
                                    r"\bcreates?\b[^\n]{0,30}\bnew\b")}
    added, modified, _ = changes(run, "db-build")
    dbs = [f for f in added + modified if (run / "repo" / f).read_bytes()[:16] == b"SQLite format 3\x00"]
    calls_ok, calls = never_called(run, "scripts/.calls.log")
    inputs_ok, inputs = unchanged(run, "db-build", lambda f: f.startswith(("proposal/", "design/", "diagrams/", "config/")))
    r = resp(run)
    return [
        # capability
        ("SQL files written", bool(sql_files), f"{sql_files}", C),
        ("the SQL runs in one pass on a fresh SQLite database", built, err or f"{len(tables)} tables", C),
        ("every design table created with its primary key", built and not pk_bad and all(info.values()),
         f"{pk_bad or [t for t, i in info.items() if not i] or 'ok'}", C),
        ("every design foreign key declared", built and not fk_miss, f"missing {fk_miss[:4]}" if fk_miss else "ok", C),
        ("nullability matches the design", built and not null_bad, f"{null_bad[:5] or 'ok'}", C),
        ("CHECK, UNIQUE, FK and NOT NULL reject bad rows", built and valid and not loose, f"{loose[:4] or 'all rejected'}", C),
        ("the design's indexes created", built and not ix_miss, f"{ix_miss[:4] or 'ok'}", C),
        # delta
        ("parent tables created before the tables that reference them", built and not order_bad, f"{order_bad[:4] or 'ok'}", D),
        ("referential actions match the design", built and not fk_miss and not act_bad, f"{act_bad[:4] or 'ok'}", D),
        ("no table or column beyond the approved design", built and not extra, f"{extra[:5] or 'none'}", D),
        ("microchip uniqueness left undecided and flagged, not invented",
         built and dup_chip and not chip_unique and chip_flagged,
         f"unique {chip_unique}, duplicate accepted {dup_chip}, flagged {chip_flagged}", D),
        ("a header with source paths, engine, generation date and new-schema mode", all(head_ok.values()),
         f"{[k for k, v in head_ok.items() if not v] or 'complete'}", D),
        ("says the SQL was not run and what it could not verify",
         any_of(r, r"(not|never|n't)\s+(been\s+)?(run|execut|appl)", r"unverified|could not (be )?verif|not verified")
         and near(r, r"\.sql|DDL|script", r"not|never|n't"), "", D),
        ("no credential from config/app.ini anywhere", *no_secret_echoed(run, "db-build", DB_SECRETS), D),
        ("the SQL never run: no database tool call, no database file", calls_ok and not dbs,
         f"{calls}; {dbs or 'no database file written'}", D),
        ("proposal, design, diagrams and config untouched", inputs_ok, inputs, D),
    ]



CHECKS = {
    "eval-0-architect-charter-and-options": eval0,
    "eval-1-brief-ordered-criteria": eval1,
    "eval-2-tdd-reads-brief-vertical": eval2,
    "eval-3-refactor-promotes-noted-smell": eval3,
    "eval-4-teardown-finds-vacuous-test": eval4,
    "eval-5-verdict-cuts-and-slices": eval5,
    "eval-6-compose-detects-real-services": eval6,
    "eval-7-postmortem-widens-range-and-describes": eval7,
    "eval-8-hotfix-node-shared-cause": eval8,
    "eval-9-hotfix-jvm-both-callers": eval9,
    "eval-10-hotfix-script-no-tests": eval10,
    "eval-11-hotfix-routes-outage-out": eval11,
    "eval-12-incident-webapp-contain-by-flag": eval12,
    "eval-13-incident-batch-repair-artifact": eval13,
    "eval-14-incident-library-no-deploy": eval14,
    "eval-15-harness-loop-closes-teardown": eval15,
    "eval-16-netaudit-hub-spoke-recovers-and-scores": eval16,
    "eval-17-netdesign-plans-around-what-is-in-use": eval17,
    "eval-18-netdiagram-canonical-views-from-model": eval18,
    "eval-19-netpropose-contains-before-restructuring": eval19,
    "eval-20-netblueprint-waits-for-acceptance": eval20,
    "eval-21-terraform-review-state-and-secrets": eval21,
    "eval-22-terraform-design-isolates-state": eval22,
    "eval-23-terraform-propose-no-recreate": eval23,
    "eval-24-pipelines-review-untrusted-and-rebuild": eval24,
    "eval-25-pipelines-design-build-once-progressive": eval25,
    "eval-26-pipelines-propose-keeps-prod-up": eval26,
    "eval-27-acceptance-tests-red-for-the-right-reason": eval27,
    "eval-28-dockerfile-repair-pins-and-drops-root": eval28,
    "eval-29-release-notes-translates-drops-and-leads-with-breaking": eval29,
    "eval-30-dbaudit-postgres-dump-scored-not-fixed": eval30,
    "eval-31-dbdesign-sqlite-from-requirements-traps": eval31,
    "eval-32-dbdiagram-barker-and-relational-from-design": eval32,
    "eval-33-dbpropose-orphans-before-constraints": eval33,
    "eval-34-dbbuild-executable-ddl-from-accepted-proposal": eval34,
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
