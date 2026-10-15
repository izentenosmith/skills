#!/usr/bin/env python3
"""Deterministic grading for the skills evals.

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

SKIP_NAMES = {".workflow", "build", "out", "node_modules", "__pycache__", ".venv", ".git", ".DS_Store"}
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
