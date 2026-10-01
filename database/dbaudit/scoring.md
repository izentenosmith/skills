# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How an evaluation is graded and written down. **Rubric version: `v1.1`** — every output records the
> version it was graded against and the source version (commit or dump date) it read. Each finding
> must be backed by the relevant theory in [`theory.md`](theory.md): an evaluation that asserts a
> defect without naming the principle it violates is incomplete.

## Severity taxonomy

| Severity | Meaning | Calibration anchor |
|---|---|---|
| **Critical** | Silent data loss or corruption | Multi-row trigger defect (`SELECT @x = col FROM DELETED`) processing 1 of N rows |
| **High** | Severe, broad performance degradation or integrity gap | Index-suppressing collation mismatch; missing PK; generic arc; missing FK index |
| **Medium** | Maintainability cost / controlled redundancy | Redundant index; nested-view pyramid; RBAR where set-based works; stored derived total |
| **Low** | Style / naming / cosmetic | Inconsistent constraint naming; `SELECT *` in a small view |

## Quality scale (per criterion)

- 🟢 **Well done** — meets the criterion; matches relational theory and engine best practice.
- 🟡 **Acceptable / watch** — works but carries maintainability or performance debt.
- 🔴 **Not well done** — violates the criterion; a defect, anti-pattern, or theory failure.

## Detection confidence — how trustworthy is a signal?

Not everything can be *proven* from static DDL. Every anti-pattern carries one of three tags; they
change how a finding is treated and whether it counts toward the score.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the DDL text alone (no PK, `char(n)`, scalar-from-`DELETED`, heap, deprecated type, mandatory self-FK) | Yes — a confirmed defect |
| ⚠️ **proxy** | A static signal that *approximates* a concern; needs judgement ("God table" by column count, redundant-by-prefix index, generic arc by column naming) | Yes, at reduced weight (see below) |
| 🔬 **needs-data** | Cannot be confirmed without runtime/data (true cardinality, plan-cache behaviour, INT-near-ceiling, hot-path-ness, schema usage) | **No** — recorded as a flag for data review, never scored |

## Scoring model

A defect tally is not a grade. Convert each evaluation to a **0–10 score** with one repeatable formula
so two evaluators reach the same number.

### Per-DDL-file score

1. **Grade each criterion across all objects (proportional rule).** Let `p` = fraction of in-scope
   objects that satisfy the criterion:
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   This stops large files from collapsing to all-🔴 because one of 463 objects trips a rule, and stops
   small files from looking perfect by luck. "In-scope" excludes objects a criterion can't apply to.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`. Normalized — independent of object
   count.
3. **Severity caps** (applied after the base, lowest wins):
   - any open **Critical** finding → score capped at **2.0**;
   - any open **High** finding → score capped at **6.0**;
   - Medium/Low do not cap (they already pull the checklist base down).
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the checklist grade; ⚠️ findings may grade a
   criterion 🟡 but never 🔴 on their own. 🔬 needs-data items never move the score.

`file_score = min(base, caps)`, floored at 0, one decimal.

### Per-database score

Weighted mean of its per-DDL scores, weighted by object count per type (a procedure-heavy database
weights `procedures.md` more), then the same Critical/High caps applied at database level.
Dead/near-dead status is reported alongside but does not alter the number — a tidy dead schema can
still score well structurally; its problem is that it exists at all.

### Estate score

Weighted mean of per-database scores, weighted by total object count, with caps re-applied. Report the
un-capped mean beside the capped one so the reader can see how much the cap is doing.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

## Triage for large files

Files above **~50 objects or ~5k lines** are not read object-by-object cold:

1. **Signal-scan** the whole file with [`detection-signals.md`](detection-signals.md); record
   per-anti-pattern counts (full-file breadth).
2. **Rank** objects by signal density and **deep-read the worst N** (≥ top 10% or 20 objects,
   whichever is larger) plus a **random sample of ~10** for false-negative control.
3. **State coverage explicitly** — "deep-read 32 of 463; signal counts cover all 463." A partial read
   must never read as full coverage.

Files below the threshold are read in full.

## Theory → object-type mapping

| Object type | Primary theory to invoke |
|---|---|
| tables | Entity/referential/domain integrity (§7); normalization 1NF–4NF (§3); functional dependencies (§2); SSOT (§6); ER modelling — UIDs, arcs, subtypes, recursion, derived attributes (§9) |
| indexes | Performance & physical design (§7); relational-algebra plan cost (§4); Winand B-tree mechanics |
| procedures | Relational algebra: set vs row-based (§4); ACID Atomicity/Isolation (§5) |
| views | Relational algebra & query cost (§4); controlled redundancy / materialization (§7) |
| triggers | ACID Isolation & transaction scheduling (§5) |

## Ordering & efficiency notes

- **Cross-file criteria** (collation across catalogs; FK-column-vs-index gap between `tables.sql` and
  `indexes.sql`; trigger→table→trigger chains) can't be judged from one file — read both inputs while
  writing the evaluation where the defect lives.
- **Dead schemas** may be evaluated more lightly: note the dead/SSOT status in the summary and flag for
  archival rather than producing exhaustive per-object findings — but still inventory their triggers
  and shadow tables.
- Only generate an evaluation file when the DDL file exists and is non-empty. Per-database summaries
  come after that database's per-DDL files; the estate synthesis after all summaries.

## Templates

### Per-DDL evaluation — `<db>/analysis/<objecttype>.md`

```markdown
# <DB> — <Object type> evaluation
> Evaluated against dbaudit/<objecttype>.md (rubric v1.1).
> Source: `<db>/<objecttype>.sql` — dump as of <date / git commit>.
> Coverage: <N of M objects deep-read; signal-scan covers all M>.

## Findings
| Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence (line) |
|--------|--------------|-------|-----------------|----------|-----------------|
| …      | …            | ✅/⚠️/🔬 | 1NF (§3)      | High     | tables.sql:NN   |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)
<🔬 items to confirm against a live instance>

## Checklist score
| # | Criterion | p | Result |
|---|-----------|--:|--------|
| 1 | …         |   | 🟢/🟡/🔴 |

**File score: <0–10>** (base <b>, cap <c> — reason)

## Notes
<patterns specific to this DDL file; reverse-engineered model notes for tables>
```

### Per-database summary — `<db>/analysis/summary.md`

```markdown
# <DB> (<CATALOG>) — Database analysis summary
> Status: 🟢 used / 🟡 barely used / 🔴 unused / copy of <X>. Object counts: T/I/V/P/Tr.
> Source dump as of <date / git commit>; rubric v1.1.

## Scores
| tables | indexes | views | procedures | triggers | **Database** |
|-------:|--------:|------:|-----------:|---------:|-------------:|
|   x.x  |   x.x   |  x.x  |    x.x     |   x.x    |   **x.x**    |

## Severity tally
| Critical | High | Medium | Low |
|---------:|-----:|-------:|----:|

## Needs-data flags (unscored, but tracked)
> A high score with many flags is **not** a clean bill of health.
| tables | indexes | views | procedures | triggers | Total |
|-------:|--------:|------:|-----------:|---------:|------:|

## Top findings (worst first)
1. …  (link to the per-DDL evaluation + theory section)

## Systemic issues for this database
<collation, cross-DB coupling, dead/copy status, index starvation, unmodelled constructs>

## Overall grade & recommendation
<one-paragraph verdict>
```

### Estate synthesis — `estate-analysis.md`

```markdown
# Estate-wide database analysis
> Synthesis across <N> databases. Rubric v1.1; source <commit/date>.

## Estate score
<capped and un-capped weighted means; the cap and the finding that sets it>

## Severity heatmap (database × object type)
## Systemic / cross-database findings
  - Collation split, cross-DB coupling (edge counts by source → target), dead/copy schemas,
    RBAR prevalence, missing-FK-index pattern, error-handling absence, sniffing-mitigation count, …
## Worst offenders (top objects estate-wide)
## Needs-data tally
## Prioritized themes (Critical → Low), each tied to its theory and affected databases
```
