#!/usr/bin/env python3
"""A deterministic routing check over every skill description: free, no model.

    python3 .github/scripts/routing.py            # exit 0 clean · 1 a check failed
    python3 .github/scripts/routing.py --report   # the distributions the thresholds come from

It indexes each skill by its frontmatter name and description, routes every
prompt in evals/trigger/cases.json through BM25 over that index, and checks:

  - recall     every should-trigger case ranks its skill within the top K
  - near-miss  no should-not case whose `expected` is a neighbour ranks the skill
               under test first (one needing no skill is reported, not failed)
  - collision  no two descriptions have a TF-IDF cosine above COLLISION

It complements the model-based trigger eval (evals/trigger/run_trigger.py), it
does not replace it: a lexical router misses paraphrase a model gets, and a
model ignores word overlap a lexical router rewards. What it catches for free,
on every push, is a description edit that drops the words its prompts use, or
two descriptions drifting into the same vocabulary.

The index holds the name (split on hyphens) as well as the description, because
the skill listing an agent chooses from shows both; the name parts are topic
words ("incident", "fix", "review", "ticket") and never a skill's literal name,
which the prompts may not contain (evals/tests/test_trigger.py enforces that).

The thresholds were set from the numbers on 2026-11-24 with a little margin;
see evals/trigger/README.md for how to read --report and tighten them.
Standard library only. Pass --root to run it against another tree (the tests do).
"""
import argparse
import collections
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import registry  # noqa: E402  (frontmatter parsing, shared so the two never disagree)

# ------------------------------------------------------------- thresholds

# Set 2026-11-24 on the descriptions as of 36e6515: 69 of 75 should-trigger cases
# ranked 1-5; the most alike pair (dbaudit / netaudit) was at cosine 0.381.
# Tightened the same day after the 500-character rewrite and the 108 new cases:
# 123 of 129 should-trigger cases rank 1-6 (the six others are KNOWN_FAILURES),
# and the most alike pair (dbdesign / dbpropose) is at 0.361.
K = 6             # a should-trigger case's skill must rank within the top K (of 43)
COLLISION = 0.40  # fail on two descriptions whose TF-IDF cosine is above this

# Cases that fail today at any reasonable K, each with why. This list must only
# shrink: an entry that passes is reported as stale, so delete it then. The
# reasons for held-out cases do not quote their prompts (the split rule).
HELD = "held-out, so its prompt is deliberately not read to explain it"
KNOWN_FAILURES = {
    "incident-fix-yes-3": "shares no word with incident-fix's description (it speaks of a ledger that "
                          "won't balance); 'quick patch', 'bug', 'shipped' are hotfix's words",
    "incident-fix-yes-2": f"ranks 29, appsec first; {HELD}",
    "pr-prep-yes-3": f"ranks 38, peer-review first; {HELD}",
    "netaudit-yes-3": f"ranks 27, hardening first; {HELD}",
    "dbpropose-yes-3": "matches only 'database'; 'legacy' and 'redesign' are dbaudit's words, and "
                       "'what should we do, in what order' has no lexical twin in dbpropose's",
    "peer-review-no-1": "a PR-description request; peer-review's description names 'pull request', "
                        "'description' and 'branch', which pr-prep's does less",
    "netblueprint-no-3": "asks for IaC from 'the accepted topology.json', which is netblueprint's own "
                         "artifact; terraform's description has no word for a topology file",
    "appsec-yes-1": f"ranks 13 after the 2026-11-24 description cut; {HELD}",
    "ticket-no-1": f"ranks ticket first, not backlog; {HELD}",
    "devils-advocate-no-3": f"ranks devils-advocate first, not threatmodel; {HELD}",
    "acceptance-tests-no-3": f"ranks acceptance-tests first, not test-review; {HELD}",
    "agent-brief-no-2": "'build plan', 'brief', 'acceptance criteria' are agent-brief's own words, "
                        "used here to ask for the next stage (acceptance-tests)",
}

BM25_K1, BM25_B = 1.2, 0.75
CASES = "evals/trigger/cases.json"

# --------------------------------------------------------------- text

STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing done down during each either else even ever
every few for from further get gets got had has have having he her here hers him his how i if in
into is it its itself just let like make me might more most much must my need needs no nor not now
of off on once one only or other our ours out over own per please put rather really same see she
should so some still such than that the their theirs them then there these they thing things this
those though through to too under until up upon us use used uses using very via want was way we
well were what when where whether which while who whom whose why will with within without would yet
you your yours e g eg ie etc
""".split())

TOKEN = re.compile(r"[a-z0-9]+")


def _cons(w, i):
    if w[i] in "aeiou":
        return False
    if w[i] == "y":
        return i == 0 or not _cons(w, i - 1)
    return True


def _m(stem):
    """Porter's measure: the number of vowel-consonant sequences in stem."""
    form = "".join("c" if _cons(stem, i) else "v" for i in range(len(stem)))
    return len(re.findall(r"v+c+", form))


def _has_vowel(stem):
    return any(not _cons(stem, i) for i in range(len(stem)))


def _cvc(w):
    return (len(w) >= 3 and _cons(w, len(w) - 3) and not _cons(w, len(w) - 2)
            and _cons(w, len(w) - 1) and w[-1] not in "wxy")


_STEP2 = (("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
          ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"),
          ("ization", "ize"), ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
          ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"))
_STEP3 = (("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"),
          ("ful", ""), ("ness", ""))
_STEP4 = ("al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ion",
          "ou", "ism", "ate", "iti", "ous", "ive", "ize")


def stem(w):
    """The Porter (1980) stemmer, compact. Words of two letters or fewer pass through."""
    if len(w) <= 2:
        return w
    # 1a
    if w.endswith("sses") or w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    # 1b
    if w.endswith("eed"):
        if _m(w[:-3]) > 0:
            w = w[:-1]
    else:
        for suf in ("ed", "ing"):
            if w.endswith(suf) and _has_vowel(w[:-len(suf)]):
                w = w[:-len(suf)]
                if w.endswith(("at", "bl", "iz")):
                    w += "e"
                elif len(w) >= 2 and w[-1] == w[-2] and _cons(w, len(w) - 1) and w[-1] not in "lsz":
                    w = w[:-1]
                elif _m(w) == 1 and _cvc(w):
                    w += "e"
                break
    # 1c
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"
    # 2, 3
    for table in (_STEP2, _STEP3):
        for suf, rep in table:
            if w.endswith(suf):
                if _m(w[:-len(suf)]) > 0:
                    w = w[:-len(suf)] + rep
                break
    # 4
    for suf in sorted(_STEP4, key=len, reverse=True):
        if w.endswith(suf):
            base = w[:-len(suf)]
            if _m(base) > 1 and (suf != "ion" or base[-1:] in ("s", "t")):
                w = base
            break
    # 5
    if w.endswith("e"):
        base = w[:-1]
        if _m(base) > 1 or (_m(base) == 1 and not _cvc(base)):
            w = base
    if w.endswith("ll") and _m(w) > 1:
        w = w[:-1]
    return w


def tokens(text):
    """Lowercased, split on anything not a letter or digit (so `peer-review` is two
    words), stopwords and single characters dropped, Porter-stemmed."""
    return [stem(t) for t in TOKEN.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]

# --------------------------------------------------------------- index


class Index:
    """BM25 over a {name: text} corpus, and TF-IDF cosine between its documents."""

    def __init__(self, docs, k1=BM25_K1, b=BM25_B):
        self.names = sorted(docs)
        self.tf = {n: collections.Counter(tokens(docs[n])) for n in self.names}
        self.len = {n: sum(c.values()) for n, c in self.tf.items()}
        self.avg = sum(self.len.values()) / max(len(self.names), 1)
        self.df = collections.Counter(t for c in self.tf.values() for t in c)
        self.k1, self.b = k1, b
        N = len(self.names)
        self.idf = {t: math.log(1 + (N - d + 0.5) / (d + 0.5)) for t, d in self.df.items()}
        self.vec = {}
        for n, c in self.tf.items():
            v = {t: (1 + math.log(f)) * math.log(N / self.df[t]) for t, f in c.items()}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            self.vec[n] = {t: x / norm for t, x in v.items() if x}

    def score(self, query, name):
        tf, dl, s = self.tf[name], self.len[name], 0.0
        for t in set(tokens(query)):
            f = tf.get(t, 0)
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
        return s

    def rank(self, query):
        """[(name, score)] best first; ties broken by name so the order is stable."""
        return sorted(((n, self.score(query, n)) for n in self.names), key=lambda x: (-x[1], x[0]))

    def cosine(self, a, b):
        va, vb = self.vec[a], self.vec[b]
        if len(va) > len(vb):
            va, vb = vb, va
        return sum(x * vb.get(t, 0.0) for t, x in va.items())

    def pairs(self):
        """[(cosine, a, b)] for every pair of documents, most similar first."""
        out = [(self.cosine(a, b), a, b) for i, a in enumerate(self.names) for b in self.names[i + 1:]]
        return sorted(out, key=lambda x: (-x[0], x[1], x[2]))

# --------------------------------------------------------------- inputs


def descriptions(root=ROOT):
    """{name: description} from every skills/<family>/<skill>/SKILL.md, parsed
    the way registry.py (and so check_repo.py) reads frontmatter."""
    out = {}
    for md in sorted((root / "skills").glob("*/*/SKILL.md")):
        m = registry.FRONTMATTER.match(md.read_text())
        if not m:
            continue
        fields = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
        name = registry.scalar(fields.get("name", ""))
        if name:
            out[name] = registry.scalar(fields.get("description", ""))
    return out


def documents(descs):
    """What each skill is indexed by: its name, split on hyphens, then its description."""
    return {n: f"{n.replace('-', ' ')} {d}" for n, d in descs.items()}


def load_cases(root=ROOT):
    return json.loads((root / CASES).read_text())["cases"]

# --------------------------------------------------------------- checks


def evaluate(index, cases):
    """One row per case: its skill's rank (1-based) and the top pick."""
    rows = []
    for c in cases:
        ranked = index.rank(c["prompt"])
        order = [n for n, _ in ranked]
        rows.append({"id": c["id"], "skill": c["skill"], "should_trigger": c["should_trigger"],
                     "expected": c["expected"], "split": c["split"],
                     "rank": order.index(c["skill"]) + 1 if c["skill"] in order else None,
                     "top": order[0] if ranked and ranked[0][1] > 0 else None,
                     "top_score": ranked[0][1] if ranked else 0.0})
    return rows


def failures(index, cases, k=K, collision=COLLISION, known=None):
    """(failure messages, notes). A case in `known` is excused while it still
    fails and reported stale once it passes."""
    known = KNOWN_FAILURES if known is None else known
    msgs, notes = [], []
    seen = set()
    for r in evaluate(index, cases):
        seen.add(r["id"])
        if r["rank"] is None:
            msgs.append(f"{r['id']}: names skill {r['skill']!r}, which no SKILL.md defines")
            continue
        if r["should_trigger"]:
            bad = r["rank"] > k
            why = f"{r['id']}: {r['skill']} ranks {r['rank']} for its own prompt (must be within the top {k})"
        else:
            # A near-miss that needs no skill (expected null) is only reported: a
            # lexical ranker always ranks something first and has no "none".
            bad = r["expected"] is not None and r["top"] == r["skill"]
            why = f"{r['id']}: near-miss ranks {r['skill']} first (expected {r['expected'] or 'no skill'})"
        if r["id"] in known:
            if bad:
                notes.append(f"known failure {r['id']}: {known[r['id']]}")
            else:
                msgs.append(f"{r['id']}: passes now; remove it from KNOWN_FAILURES in routing.py")
        elif bad:
            msgs.append(why)
    for cid in sorted(set(known) - seen):
        msgs.append(f"KNOWN_FAILURES names {cid}, which is not a case in {CASES}; remove it")
    for sim, a, b in index.pairs():
        if sim <= collision:
            break
        msgs.append(f"{a} and {b}: descriptions too alike (cosine {sim:.3f} > {collision}); "
                    f"say what sets each apart in its own words")
    return msgs, notes


def report(index, cases, k=K, collision=COLLISION):
    rows = evaluate(index, cases)
    pos = [r for r in rows if r["should_trigger"]]
    neg = [r for r in rows if not r["should_trigger"]]
    L = [f"{len(index.names)} skills indexed (name + description), {len(cases)} cases "
         f"({len(pos)} should-trigger, {len(neg)} near-miss); K={k}, COLLISION={collision}", ""]

    L.append("Rank of each should-trigger case's own skill (1 = first):")
    hist = collections.Counter(r["rank"] for r in pos)
    for rank in sorted(hist):
        L.append(f"  rank {rank:>2}: {hist[rank]:>3}  " + "#" * hist[rank])
    for r in sorted(pos, key=lambda r: (-r["rank"], r["id"])):
        if r["rank"] > 1:
            L.append(f"  {r['id']:<26} rank {r['rank']:>2}  top {r['top']}"
                     + ("  [known]" if r["id"] in KNOWN_FAILURES else ""))
    top1 = sum(r["rank"] == 1 for r in pos)
    L.append(f"  top-1 {top1}/{len(pos)}, within K {sum(r['rank'] <= k for r in pos)}/{len(pos)}")
    L.append("")

    L.append("Top pick of each near-miss (✗ = the skill under test, a failure):")
    hits = 0
    for r in sorted(neg, key=lambda r: r["id"]):
        wrong = r["top"] == r["skill"]
        hits += wrong
        ok = "✗" if wrong else ("=" if r["top"] == r["expected"] else " ")
        L.append(f"  {ok} {r['id']:<26} top {r['top'] or '-':<20} expected {r['expected'] or 'none':<20} "
                 f"rank of {r['skill']}: {r['rank']}" + ("  [known]" if r["id"] in KNOWN_FAILURES else ""))
    L.append(f"  (= the expected neighbour came first) under-test-first {hits}/{len(neg)}, "
             f"expected-first {sum(r['top'] == r['expected'] for r in neg if r['expected'])}"
             f"/{sum(1 for r in neg if r['expected'])}")
    L.append("")

    pairs = index.pairs()
    L.append("Most similar description pairs (TF-IDF cosine):")
    for sim, a, b in pairs[:15]:
        L.append(f"  {sim:.3f}  {a} / {b}" + ("  ✗" if sim > collision else ""))
    L.append("")

    worst = max((r["rank"] for r in pos if r["id"] not in KNOWN_FAILURES), default=0)
    worst_all = max((r["rank"] for r in pos), default=0)
    new_hits = sum(r["top"] == r["skill"] and r["id"] not in KNOWN_FAILURES for r in neg)
    L.append("Slack (how far each threshold could tighten today):")
    L.append(f"  worst should-trigger rank outside KNOWN_FAILURES {worst}, {worst_all} with them "
             f"(K={k}): K could be {max(worst, 1)}")
    L.append(f"  max pair cosine {pairs[0][0]:.3f} (COLLISION={collision})" if pairs else "  no pairs")
    L.append(f"  near-misses ranking the skill under test first: {hits}, {new_hits} outside KNOWN_FAILURES "
             f"({len(KNOWN_FAILURES)} entries)")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--report", action="store_true", help="print the rank, near-miss and similarity distributions")
    ap.add_argument("--root", type=pathlib.Path, default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    index = Index(documents(descriptions(args.root)))
    cases = load_cases(args.root)
    if args.report:
        print(report(index, cases))
        print()
    msgs, notes = failures(index, cases)
    for n in notes:
        print(f"! {n}")
    for m in msgs:
        print(f"✗ {m}")
    if msgs:
        print(f"routing: {len(msgs)} failure(s) — see evals/trigger/README.md, \"The routing check\"")
        return 1
    excused = {c["id"] for c in cases if c["id"] in KNOWN_FAILURES}
    pos = sum(c["should_trigger"] for c in cases if c["id"] not in excused)
    neg = len(cases) - len(excused) - pos
    print(f"routing: {len(index.names)} skills; {pos} should-trigger cases within the top {K}, "
          f"{neg} near-misses clear, {len(excused)} known failure(s) excused; "
          f"no description pair above cosine {COLLISION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
