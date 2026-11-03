# History Signals — What `git log` Says About Where to Look

> The code shows what a change does. The history shows how risky it is to change *there*, and what
> usually changes alongside it. These signals decide **where attention goes** in Phase 1 and feed
> the **omissions** lens (J). Every one is a heuristic that points attention. None is a verdict
> (XR p.84, p.193). Page numbers are XR's (*Software Design X-Rays*, Tornhill). See
> [theory.md](theory.md) for the source list.
>
> **When to run them.** Standard: the coupling check on the changed files, and the hotspot rank
> when it's cheap. Deep: all of section 1. Skip them all, and say so, when the history is too thin.
> Under about 150–200 commits or a few weeks of activity, none of these numbers means much
> (XR p.191).
>
> **A script computes all of this.** [code-xray](../code-xray/SKILL.md) bundles `scripts/xray.py`, a
> read-only stdlib tool: `python3 -I <path>/xray.py pr --repo . --base <base>` prints these signals in
> the §2 format, with the same thresholds. The commands below are what it does, for when it isn't
> installed.

---

## 0. Clean the input first

Every signal below is relative. One generated file at the top of the ranking distorts everything
under it (XR p.191).

- **Exclude non-code and generated paths** from every count: lockfiles, `*.min.*`, `vendor/`,
  `node_modules/`, generated clients and migrations snapshots, changelogs, `README`/docs, version
  files, IDE and project files, JSON fixtures (XR p.31, p.82, p.172–173).
- **Ignore merge commits** (`--no-merges`), and leave out mass commits that touch more than ~50
  files. A reformat, a rename sweep or a vendor bump co-changes everything with everything. (XR
  doesn't treat large commits. This threshold is a practical guard.)
- **Watch the social data.** Aliases need a `.mailmap`. A "build master" at the top of the author
  list means migrated or merged history. Squash merges erase both authorship and coupling. Pairing
  hides co-authors. When in doubt, drop the social signals and keep the technical ones (XR p.124,
  p.191).
- **Windows.** Hotspots and coupling: the last 12 months (`--after`). Social signals: about 3
  months, or since the last reorganisation. Complexity trend: since the branch point, or one
  month (XR p.100–101, p.121, p.180).

The shared extraction, one pass over the log, reused by everything below:

```bash
git log --no-merges --after="12 months ago" --date=short \
  --numstat --format='--%h--%ad--%aN' -- . ':(exclude)*.lock' ':(exclude)vendor/*'
```

Each commit block is a `--hash--date--author` line followed by `added<TAB>deleted<TAB>path` rows.
Binary files show `-`. Skip them.

---

## 1. The signals

### 1.1 Hotspot: change frequency × size

**Measures.** How often a file changes (the interest rate on its debt) times how complex it is.
Change frequency predicts faults as well as elaborate static metrics, and lines of code are as good
a complexity proxy as most (XR p.30–31, p.33).

```bash
# commits per file, last 12 months
git log --no-merges --after="12 months ago" --format=format: --name-only \
  | grep -v '^$' | sort | uniq -c | sort -rn | head -50
# size: non-blank lines at HEAD (or `cloc --by-file`)
grep -cv '^\s*$' <file>
```

Rank by commits, then by size. A file in the top ~10 of its subsystem, or among the files that get
10–15% of all commits, is a hotspot (XR p.108, p.112).

**Changes the review.** Read a hotspot's hunks slowest, and run lenses N and M on them even at
Standard. New complexity in a hotspot is worth a finding even when it is correct. That code
changes most, so it has to stay simple (XR p.104). Narrow a large hotspot to the functions that
change with `git log -L:<function>:<file> --after="12 months ago" | grep -c '^commit '`
(XR p.106). Don't raise ugly code in a cold file. Interest is only paid on code that changes
(XR p.20, p.35).

### 1.2 Change coupling and the missing co-change

**Measures.** Files that change in the same commits. The coupling is invisible in the code and only
the history shows it (XR p.48). The book's defaults: at least **20 shared commits** and a
**degree of 50%** or more, where degree = shared commits ÷ the average of the two files' commit
counts. Use **80%** when the result is a warning (XR p.49, p.185, p.204).

**The check that matters most for review: catch the absence of change** (XR p.184–186).

1. For each file changed in the diff, find its partners with degree ≥ 80% and ≥ 20 shared commits.
2. Every partner **missing from the diff** is an omission candidate.
3. Report it as a question with the evidence, not as a block: *"`billing/tax.py` changed with
   `billing/tax_rules.yaml` in 23 of 26 commits over the last year, but not here. Does this change
   need the rules file too?"*
4. If nothing is missing, say nothing.

A short script does it. Run it from a scratch directory, not the work tree:

```python
# python3 -I cochange.py <base> ; reads git log in the cwd repo
import collections, subprocess, sys
base = sys.argv[1]
changed = set(subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                             capture_output=True, text=True).stdout.splitlines())
log = subprocess.run(["git", "log", "--no-merges", "--after=12 months ago",
                      "--format=tformat:@@commit", "--name-only"], capture_output=True, text=True).stdout
revs, shared = collections.Counter(), collections.Counter()
for block in log.split("@@commit\n"):
    files = sorted({f for f in block.splitlines() if f})
    revs.update(files)
    if not 2 <= len(files) <= 50:   # one-file commits and mass sweeps carry no coupling
        continue
    for i, a in enumerate(files):
        for b in files[i + 1:]:
            shared[a, b] += 1
for (a, b), n in shared.items():
    for f, g in ((a, b), (b, a)):
        if f in changed and g not in changed and n >= 20:
            degree = n / ((revs[a] + revs[b]) / 2)
            if degree >= 0.8:
                print(f"{f} usually changes with {g}: {n} shared commits, {degree:.0%}")
```

**Expected and surprising coupling** (XR p.50–52).

- **Expected, and worrying when absent.** A test that usually changes with its code under test but
  didn't this time. Ask whether the tests went stale.
- **Surprising, and worth a finding.** Two files in different layers, modules, services or
  languages that change together, or two unrelated tests that change together. These point to
  copy-paste, a missing abstraction, or a leaky protocol. Raise this under lens N.

**Limits.** Same-commit coupling misses work split across commits, such as code in one commit and
its tests in the next. Where commit messages carry ticket IDs, group commits by ticket into logical
change sets (XR p.54, p.164–165). Always allow an override. A coupling someone is deliberately
refactoring away has to be ignorable (XR p.186).

### 1.3 Clone twins: the forgotten update

**Measures.** Near-identical functions that keep receiving the same changes. Duplication only
costs when the copies have to change together (XR p.57).

**In the review.** When the diff edits a function that has a near-duplicate, open the twin and diff
the two. A guard, condition or type check present in one and missing in the other is a candidate
latent bug. XR's example is a type check in one TensorFlow layer that was missing from its sibling
(XR p.107–108, p.219). Ask the author to fix the twin, or to name the difference so the next reader
knows it is deliberate. Find twins by grepping for the function's distinctive lines, or by looking
for functions that co-change with this one (`git log -L`).

### 1.4 Complexity growth on the branch

**Measures.** How much more nested, conditional code the branch added, relative to its own past
(XR p.179–181).

1. Take the revisions from `git merge-base <base> HEAD` to HEAD.
2. For each changed file above a size floor (skip small files), compute indentation complexity at
   each revision. That is the sum of logical indentation levels over non-blank lines, with a tab
   or 4 spaces as one level.
3. Take the **minimum** across those revisions as the baseline, and warn if HEAD is more than
   **10%** above it.

Use a relative threshold, never an absolute one. Absolute thresholds fire on every touch in legacy
code, and then everyone ignores them (XR p.180). Name the likely cause: misplaced behaviour
(extract a class), conditional logic squeezed in for a feature (a missing abstraction), or "the code
is fine" (XR p.181). Most smells are introduced when the code is created, which is exactly when
review sees it (XR p.179).

### 1.5 Code age: ignorant surgery

**Measures.** Time since a file was last changed:
`git log -1 --format=%ad --date=short -- <file>` (XR p.81–82, p.212). Code should be recent (a fresh
mental model) or old (a stable black box). Mid-aged code is the costly kind (XR p.83).

**In the review.** A change to code that has been stable for a year or more, whose authors are gone,
is surgery without the original surgeon (XR p.83). Ask for a test that pins the old behaviour
before it changes, and for the rationale in the PR. The first such change invites others to follow.

### 1.6 Knowledge: who knows this code

**Measures.** The **main developer** of a file is whoever added the most lines in the window, from
`git log --numstat`. Added lines are used rather than blame because design knowledge survives a
rewrite (XR p.151). **Fragmentation** is `1 − Σ(cᵢ/C)²` over per-author commit counts: 0 means one
author, and near 1 means many with diffused effort (XR p.122–123).

```bash
git log --no-merges --after="12 months ago" --numstat --format='--%aN' -- <file> \
  | awk '/^--/{a=substr($0,3);next} NF==3{add[a]+=$1} END{for(k in add) print add[k], k}' | sort -rn
```

**In the review.**

- **Suggested reviewer.** The main developer of the touched files, if it isn't the author. Bring
  in someone from a consuming team to widen knowledge boundaries (XR p.127, p.187). Present this as
  a suggestion. The person who knows the code is often a better second reader than the agent.
- **Raise depth when the author is a minor contributor in fragmented code.** Defect risk rises with
  the number of minor contributors (XR p.121, p.124).
- **Knowledge loss.** If the main developer has left, the change is riskier, so ask for tests and
  explanation (XR p.189).
- **Never** present authorship data as a judgement of a person, or as a ranking. People game what
  is measured, and the data stops meaning anything (XR p.134, p.198–201).

### 1.7 Rising hotspot

A file that climbed 10 or more places in the hotspot ranking compared with two months ago (run 1.1
with `--before="2 months ago"` and compare). It isn't necessarily a problem. It means effort is
flowing into new code. Say so in the risk map, and make sure the new code is up to par while it is
still cheap to change (XR p.181–183).

---

## 2. What goes in the report

Put the history signals in the **risk map** section as one line per changed file that has any:

```
billing/invoice.py   hotspot #3 (41 commits/12m, 1.9k lines) · complexity +14% vs branch min
                     · usually changes with billing/tax_rules.yaml (23/26, 88%) — absent
                     · main developer: <name>; author is a minor contributor here
```

Only signals that change a decision go into findings: a missing co-change becomes a lens-J
question, a stale-test co-change becomes a lens-K question, a clone twin becomes a lens-J or A
candidate, and complexity growth in a hotspot becomes a lens-N finding. Everything else stays in the
risk map. Start the section with a data-quality line: window, commit count, exclusions, and any
squash or alias caveat.
