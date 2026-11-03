# Report — The PR-Signals Block, the Codebase Report, the Target Table

> Two outputs. In **PR mode**, a block of history signals that goes into peer-review's risk map
> and feeds its omissions lens. In **codebase mode**, a debt report that ends in a ranked list of
> refactoring targets and a list of code to leave alone. Both start with the **data-quality line**,
> because every number after it is only as good as the log it came from (X19, X20). Every target
> and every "leave alone" cites its principle from [theory.md](theory.md).

---

## The data-quality line

Always first, always one line, in this order: window, commits, what was dropped and excluded, and
any caveat.

```
Data: 412 commits in 12 months before a1b2c3d4 (1,980 in all), 3 mass commits dropped, merges excluded,
      excluded: lockfiles, vendor/, src/generated/*. Caveats: none.
```

```
Data: 38 commits in 12 months before 1c02cc50, 1 mass commit dropped, merges excluded.
      Caveats: thin history (under 150) — every signal is weak; one author — social analyses dropped.
```

When a caveat applies, it also changes what follows:

- **Thin history.** Every signal is read as weak. No history signal becomes a finding on its own.
  In codebase mode, the target table is titled "candidates" and has no `now` rows.
- **One author, squash merges, or migrated history.** Leave out the knowledge, reviewer and
  coordination sections, and say why in one line.

---

## PR mode: the signals block

This is history-signals.md §2's format: one line per changed file that has any signal, the strongest
signals first, with the data-quality line above it. Files with no signal are counted, not listed.

```
History signals — base a1b2c3d4 (merge-base), head 9f8e7d6c
Data: 412 commits in 12 months before the merge-base, 3 mass commits dropped, merges excluded. Caveats: none.

billing/invoice.py   hotspot #3 (41 commits/12m, 1.9k lines) · complexity +14% vs branch min (612 → 698)
                     · usually changes with billing/tax_rules.yaml (23 shared, 88%) — absent
                     · main developer: <name or dev-n>; author has not changed this file before
api/handler.py       main developer (dev-2, 67% of added lines) inactive 90+ days · unchanged for 412 days
                     → ask for a test that pins today's behaviour
12 of 14 changed files carry no history signal.
Suggested reviewers (they know the touched code): <name> (billing/invoice.py, billing/tax.py)
```

`xray.py pr` prints a markdown table with the same content. Either shape is fine. Keep the
data-quality line and the caveats at the top.

### What each signal becomes

Only a signal that changes a decision becomes a finding candidate. Everything else stays in the risk
map and changes **where** the reviewer reads, and how slowly. That follows history-signals.md §2.

| Signal | Weight | Goes to | As |
|---|---|---|---|
| `missing-cochange` | high | lens J (omissions) | a **question** with the evidence: "A changed with B in 23 of 26 commits (88%), not here. Does this change need B?" The verifier answers it from the code. If B needs the edit, it's a `major` finding (peer-review's report.md anchor for a ≥ 80% co-change). If not, drop it |
| `missing-cochange` where the partner is the file's test | high | lens K (tests) | "Did the tests go stale?" (XR p.50) |
| `clone-twin`, twin absent | high | lens J or A | diff the two files. A guard in one and not the other is a candidate bug. Otherwise a question: does the twin need the same edit? |
| `clone-twin`, both changed | low | lens J | check they got the same edit. Usually nothing |
| `complexity-growth` on a hotspot | high | lens N | an evolvability finding, `major` per peer-review's anchor "new complexity in a hotspot", with the likely cause named ([analyses.md](analyses.md) §5) |
| `complexity-growth` elsewhere | medium | risk map | read that file's new branches slowly. A finding only if lens N finds a concrete cost in the code |
| `hotspot` | high | risk map | read slowest. Run lenses N and M even at Standard. A touched hotspot makes peer-review Deep |
| `hot-function` | medium | risk map | the touched function takes most of the file's changes. Read it first |
| `rising` | medium | risk map | new code taking effort. Check it is up to par now |
| `stable-code` | medium | risk map, plus a question when `knowledge-loss` is also present | ignorant surgery. Ask for a test that pins the old behaviour, and for the rationale |
| `knowledge-loss` | high | risk map and reviewers | a riskier change. Ask for tests and explanation. Never phrase it about the author |
| `unfamiliar` | medium | risk map | raise depth on that file. Suggest a reviewer who knows it |
| reviewers | — | the risk map | a suggestion for the human who assigns reviewers, never a ranking |

**Under a thin-history caveat**, treat every row as one weight lower. Ask the missing co-change and
clone-twin questions only when the code alone makes the question worth asking.

---

## Codebase mode: the report template

```markdown
# Code X-ray — <repo> @ <short sha>

**Tier:** <Standard | Deep> — <why>. **Window:** <n> months to <sha>.
**Data:** <the data-quality line>

## Summary
<Three sentences at most: where the effort goes (the share of commits in the top hotspots), the one
or two places paying the most interest, and the main structural or knowledge risk.>

## Hotspots
| # | File | Commits | Lines | Complexity | Age (days) | Note |
|---|---|---|---|---|---|---|
| 1 | `src/billing/invoice.py` | 141 | 2,310 | 4,870 | 2 | hotspot · rising |
<Top 10, with excluded noise named. The share of all window commits the top 10 take: <p>%.>

## Inside the top hotspots (Deep)
### `src/billing/invoice.py`
| Function | Commits (12 m) | Note |
|---|---|---|
| `calculate_totals` | 58 | 41% of the file's commits; 180 lines; nesting depth 7 |
**Trend:** <lines and complexity over the file's history in one sentence, e.g. "1,400 → 2,310 lines
since <date>; mean indentation 1.6 → 2.1. Being patched with conditionals, not just growing.">

## Change coupling
| A | B | Shared | Degree | Reading |
|---|---|---|---|---|
| `src/orders/api.ts` | `db/migrations/orders.sql` | 31 | 84% | surprising: crosses layers; leaky protocol? |
<Surprising pairs first. Expected pairs only when they say something, e.g. a test that stopped
co-changing.>
<Deep: the component table and component-pair coupling, from analyses.md §9.>

## Knowledge (Deep, and not under a social-data caveat)
- **Knowledge loss:** <files or components whose main developer is inactive, hotspots first>.
- **Fragmentation:** <hotspots with many minor contributors and no clear owner>.
- **Coordination:** <components many teams change; coupled components owned by different teams>.
<Pseudonyms or team names when this report leaves the team. No per-person table, ever.>

## Refactoring targets
<The ranked target table below.>

## Leave alone
<The cold-code list below.>

## Not covered
<What wasn't analysed and why: social analyses dropped (caveat), component map guessed from folders,
renames inside the window, a subsystem excluded, functions not resolved (no diff driver).>

<Handoff line — see SKILL.md.>
```

At **Standard**, leave out "Inside the top hotspots" and the knowledge section, except for a
knowledge-loss note on a top hotspot. Name the X-ray candidates in the target table, marked
"X-ray not run".

---

## The ranked target table

One row per target. A target is the smallest unit you can act on: a function from the X-ray, a file
when no X-ray ran, a component pair for a coupling problem.

```markdown
| # | Target | Interest paid | Why | First step | Principle | Priority | Hand to |
|---|---|---|---|---|---|---|---|
| T1 | `invoice.py` · `calculate_totals` | 58 of 141 file commits; the file takes 9% of all commits | hot function in hotspot #1; complexity rising faster than size; main developer inactive | pin behaviour with tests, then splinter the tax branch into its own module | X6, X7, X16, X21 | now | refactor-review, per step |
| T2 | `orders/api.ts` ↔ `orders.sql` | 31 shared commits, 84% | cross-layer coupling; every order change touches both | decide where the order schema is owned | X9, X13 | next | architect-deep-dive |
| T3 | `pricing/rules_v1.py` ≈ `rules_v2.py` | co-changed 14 times, 81% similar | clone twins in a hotspot; one lacks the currency guard | proximity refactor: move the twins together, then name the difference | X11, X21 | now | peer-review on that change |
```

**Columns.**

- **Interest paid.** The evidence, in counts: commits in the window, the share of all commits, and
  the shared commits for a coupling. Never a made-up score.
- **Why.** The signals that put it here, in words.
- **First step.** The smallest safe move: a pinning test, a proximity refactoring, one splinter, a
  boundary decision. Not "rewrite".
- **Priority.**
  - `now`: a top hotspot whose trend is rising, or a hotspot with knowledge loss.
  - `next`: a hotspot with a stable trend, or strong surprising coupling.
  - `watch`: rising hotspots and young code. Look again in a few months.

**Ranking rule** (practical guidance, not from the sources: the book gives the ingredients, not a
formula):

1. Start from the hotspots, ordered by commits in the window (X1, X5).
2. Move a target up when its complexity trend is rising, when its changes concentrate in a few
   functions, when it has knowledge loss, or when it has co-changing clones (X6, X7, X11, X16).
3. Move a target down when it hasn't changed recently (XR p.218), or when its trend has been flat
   or falling since a refactoring (X22).
4. Coupling targets go in at the rank of their hotter file.

At most 10 targets. A list longer than a team can act on in a quarter is noise (not from the
sources).

## The "leave alone" list

Name the code that looks bad and isn't worth touching, so nobody spends a sprint on it (X1, X21).

```markdown
| Path | Why it's here | Why leave it |
|---|---|---|
| `legacy/report.py` | complexity 1,900, 1,200 lines | 1 commit in 12 months, last change 410 days ago: no interest paid (X1). Stable, so a library candidate if it's still used (X12) |
```

A cold file belongs here when it has few or no commits in the window and either high complexity or
a bad reputation. A cold file with knowledge loss stays here too, because old abandoned code is the
less critical kind (XR p.189). Note it for whoever next has to touch it.

---

## Rules for both outputs

- **The data-quality line comes first**, with every caveat.
- **Counts, not scores.** Every number in the report is a count or a ratio the script printed.
- **No names outside the team.** Use `--no-names` when the report goes anywhere beyond the people
  who write the code. Coordination sections show team names, never a person's.
- **No per-person tables.** No contributor rankings, no "top authors", no commits per person (X18).
- **Attention, not verdicts.** A hotspot is a reason to look. A target is a recommendation, and the
  team decides what to refactor (X4).
