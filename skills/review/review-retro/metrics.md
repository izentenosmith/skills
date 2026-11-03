# Metrics — What to Compute From Reviews, and What Each Number Can't Tell You

> Every metric here is about the **review process and the code**, never about a person (RR6). Each
> one gives a **definition**, a **formula**, **what it tells you**, **how it gets gamed**, and the
> **minimum sample** before it means anything. Principles are in [theory.md](theory.md).
>
> Under the PR harness, the harness computes these in code and hands you a table. **Don't recompute
> it, round it, or edit it.** Paste it as given. If a number looks wrong, say so in a note under the
> table. Without the harness, compute them yourself from the rows below, and show every numerator
> and denominator.

---

## 0. The rows everything is computed from

Normalise the input into two tables first. Every metric is a count or a ratio over these rows.

**A finding row**, one per posted finding:

| Field | From | Notes |
|---|---|---|
| `pr` | the PR number | |
| `id` | the finding id (`PR-3`) | stable across rounds; never reused |
| `file`, `line` | the anchor | |
| `area` | the code area: the path's first one or two meaningful directories (`src/billing/`), or the project's own module map | **never** the owner from CODEOWNERS; that's a person or team |
| `change_type` | the PR's kind: `feature`, `fix`, `refactor`, `deps`, `config`, `docs`, `test`, `migration` | from labels, the claim, or the diff; say which |
| `type` | `bug` · `security` · `test` · `evolvability` · `process` · `conventions` | peer-review's vocabulary |
| `severity` | `blocker` · `major` · `minor` · `nit` | |
| `lens` | the lens or check that produced it (`J`, `L`, `test-review:T4`…) | |
| `principle` | the principle or heuristic it cited | |
| `class` | the **defect class**: a short, reusable name for the kind of defect, not this instance ("optional config read without a default", not "`timeout` in `client.py`") | you assign it; see [proposals.md](proposals.md#1-from-findings-to-defect-classes) |
| `outcome` | `fixed` · `partly fixed` · `not fixed` · `withdrawn` · `deferred` · `open` | see §0.1 |
| `verified` | `yes` when a re-review checked the outcome, `no` otherwise | |
| `issue` | the tracked issue id for a deferral, or `none` | |
| `source` | `report`, `harness`, or `thread` (a human comment the retro classified) | thread rows carry lower confidence; say how many there are |

**A review row**, one per PR: `pr`, `areas`, `change_type`, `meaningful_lines` (production and test
code; lockfiles, generated, vendored and snapshot files left out), `rounds` (review iterations),
`created`, `first_review`, `merged` or `closed`, `state`, `has_rereview`, `findings` (count).

**No person fields.** `gh` JSON carries `author`, `login` and reviewer names. Drop them when you
ingest, before any row exists. A table without them can't be sliced by person by accident.

### 0.1 Outcomes

| Outcome | Means | Evidence it needs |
|---|---|---|
| **fixed** | The defect was real and is resolved | `verified: yes`: a re-review marked it fixed. `verified: no`: the final diff changes that location in a way that addresses the claim, with no re-review |
| **partly fixed** | Some of it is resolved; the rest is named | as for fixed |
| **not fixed** | The PR merged (or closed) with the defect in place, including "won't fix" | the final diff doesn't address it, and there's no withdrawal |
| **withdrawn** | It was never a defect: the reviewer, or the re-review, agreed it was wrong | a re-review `withdrawn`, or a thread reply where the reviewing side concedes it |
| **deferred** | Real, and left for later on purpose | a thread or report saying so; `issue` holds the tracked issue, or `none` |
| **open** | The PR is still open, or there isn't enough evidence to say | name what's missing |

A **resolved thread is not evidence of a fix**. A disagreement is **not fixed**, not withdrawn
(RR4). When the evidence is ambiguous, use `open` and say why, rather than guess.

**Defects** are the findings whose outcome is not `withdrawn`. A defect is a change the reviewing
side decided must be made (BKS p.78), so "not fixed" still counts as one.

---

## 1. Defects per review

- **Definition:** how many defects a review turns up on average.
- **Formula:** defects ÷ reviews. Report it with nits and without (`above nit`).
- **Tells you:** whether reviews are finding things at all (BKS p.117). Read it per area and per
  change type, never as one number (RR8).
- **Gamed by:** splitting one defect into several nits; posting findings nobody would act on. Read
  it next to the usefulness rate (§8) and the withdrawn rate (§9).
- **Minimum sample:** 10 reviews in the group (BKS p.108). Below that, give the raw counts.

## 2. Defect density

- **Definition:** defects per thousand meaningful lines reviewed.
- **Formula:** defects ÷ (Σ meaningful_lines ÷ 1000), per group. Above-nit and all.
- **Tells you:** review effectiveness. A high density usually means a thorough review, not bad
  code (BKS p.118, RR9). It varies hugely with code maturity and module (BKS p.63, p.118), so only
  compare like with like (BKS p.108).
- **Gamed by:** inflating the line count (reformatting, generated code left in); trivial findings.
  Never set a target density.
- **Minimum sample:** 10 reviews and about 2,000 meaningful lines in the group (the line floor is not
  from the sources). Don't compare groups whose size mix differs widely. Small changes show high
  density on their own (BKS p.80–81).

## 3. Distribution: type, severity, lens, area, change type

- **Definition:** how the defects split across each dimension.
- **Formula:** count and share per value: `type` (bug, security, test, evolvability, process,
  conventions), `severity`, `lens`, `area`, `change_type`. Cross-tabulate area × type when there's
  enough data.
- **Tells you:** where defects cluster and what kind they are. Expect evolvability to dominate.
  That's review working, not failing (BKS p.117; ECR). A type that never appears in an area where
  it should (no `security` findings on an auth module) is a coverage question (RR9).
- **Gamed by:** relabelling types to look better. Read it next to the raw findings.
- **Minimum sample:** 30 findings before quoting shares (not from the sources). Below that, counts
  only.

## 4. Review size

- **Definition:** the distribution of meaningful lines per reviewed PR.
- **Formula:** median, p90 and max of `meaningful_lines`; count and share of reviews over 400 and
  over 1,000 lines; defects per review for the ≤ 400 and > 400 groups.
- **Tells you:** whether reviews happen in units a reader can hold. Past about 400 lines, the yield
  of a review collapses (BKS p.80–81, p.87). In the Cisco data no review over 250 lines exceeded
  37 defects/kLOC (BKS p.80–81). That's a human result, used here as an analogy.
- **Gamed by:** splitting a change into stacked PRs that can't be understood one at a time. A split
  only counts if each part is reviewable alone.
- **Minimum sample:** 10 reviews.

## 5. Zero-finding reviews

- **Definition:** reviews that posted no findings above `nit`.
- **Formula:** count and share, split by the area's risk (the peer-review Deep triggers: money,
  auth, personal data, migrations, concurrency, public API, hotspots).
- **Tells you:** in the Cisco study 61% of reviews found no defects (BKS p.79). On low-risk code
  that's fine. On risky or complex code it's a depth question (BKS p.97, RR9).
- **Gamed by:** reviewing less. That's the point of reading it by risk.
- **Minimum sample:** 10 reviews in the risk group.

## 6. Inspection rate and defect rate (timed human reviews only)

- **Definition:** inspection rate is meaningful lines per hour of review; defect rate is defects
  found per hour (BKS p.117–118).
- **Formula:** Σ meaningful_lines ÷ hours; defects ÷ hours.
- **Tells you:** for human review, whether the reading was too fast to be real. About 100–200
  lines/hour is meticulous, 200–500 normal, and above 800–1,000 the review was probably perfunctory
  (BKS p.117). Typical defect rates run 5–20 per hour (BKS p.117–118).
- **Gamed by:** under-reporting time. Stopwatch time is wildly inaccurate, and people fake it (BKS
  p.109–110). Use only time a tool recorded, never self-reports.
- **For agent reviews, don't compute them.** An agent's wall-clock time is not reading attention,
  and the human thresholds don't transfer. Say "not computed: agent review" in the table.
- **Minimum sample:** 10 timed reviews.

## 7. Time to first review, time to merge, iterations

- **Definition:** how long a PR waited for its first review, how long until it merged, and how
  many review rounds it took.
- **Formula:** median and p90 of `first_review − created` and `merged − created`; median of
  `rounds`. Use medians, not means. One stale PR drags a mean for months. If a PR started as a
  draft, the data may not show when it became ready. Say so.
- **Tells you:** where PRs queue, and whether rework loops are long (ACR p.23).
- **Gamed by:** approving fast. Speed metrics alone mislead (ACR p.31, RR7). Never report time
  without the depth metrics beside it (§1, §5, §8).
- **Minimum sample:** 10 PRs.

## 8. Fix verification rate

- **Definition:** of the findings marked fixed, the share a re-review actually checked.
- **Formula:** (fixed + partly fixed with `verified: yes`) ÷ (all fixed + partly fixed).
- **Tells you:** whether "fixed" means fixed (RR11). An unverified fix is a claim. Fixes are where
  new defects hide (BKS p.154–156).
- **Gamed by:** a rubber-stamp re-review. Read it next to the count of new findings that re-reviews
  raised. A re-review that never finds anything in the fix delta may not be reading it.
- **Minimum sample:** 10 fixed findings.

## 9. Usefulness rate and withdrawn rate

- **Usefulness rate:** of the posted findings with a known outcome, the share that someone acted on.
  - **Formula:** (fixed + partly fixed + deferred with an issue) ÷ (all findings − open).
  - Report it above `nit` and for nits alone. Nits are optional by definition, so a low nit rate is
    expected.
- **Withdrawn rate:** the false-positive signal.
  - **Formula:** withdrawn ÷ (all findings − open), overall and **per lens**.
- **Tells you:** whether review comments earn the attention they cost. 34.5–44.5% of human review
  comments were judged not useful in industrial studies (ACR p.11). Measure usefulness from
  outcomes. Don't ask a model to grade it (ACR p.25, RR12). A lens whose findings keep getting
  withdrawn is noisy, and that's a tuning proposal ([proposals.md](proposals.md#7-reviewer-lens-tuning)).
- **Gamed by:** not posting borderline findings, which lowers recall to raise the rate; marking
  things fixed without fixing them (read §8); calling disagreements "withdrawn" (RR4). Never set a
  target for either rate.
- **Minimum sample:** 30 findings overall, 10 per lens (neither floor is from the sources).

## 10. Deferral tracking rate

- **Definition:** of the deferred findings, the share with a tracked issue.
- **Formula:** deferred with `issue ≠ none` ÷ all deferred. List every untracked one by `pr:id`.
- **Tells you:** whether deferrals are decisions or promises (RR3). The target is all of them,
  and every untracked one is listed whatever the sample size.
- **Gamed by:** opening empty issues nobody reads. Check that each one is open and names the
  finding.

## 11. Recurrence of defect classes

- **Definition:** how often each defect class appears, and across how many PRs and areas.
- **Formula:** per `class`: finding count, distinct PRs, distinct areas, first and last seen, and
  whether a checklist item or a tool already covers it.
- **Tells you:** which classes are candidates for a checklist item, a rule or a lint rule
  ([proposals.md](proposals.md#2-thresholds)). A class at 3 or more findings across 2 or more PRs is
  a candidate (not from the sources).
- **Gamed by:** naming classes so narrowly that nothing recurs, or so broadly that everything does.
  A class names one kind of defect a single true/false checklist item could catch (BKS p.133).

## 12. Checklist hit rate

- **Definition:** how many findings each existing checklist item matched in the window.
- **Formula:** per item: matched findings, PRs where the item applied, months since its last
  match.
- **Tells you:** which items still earn their place. An item with no catches for about 3–6 months
  of reviews where it applied is a retirement candidate (BKS p.136–137). Zero catches can mean the
  item worked, because authors now check it before submitting. Retiring it is a success, not a
  failure.
- **Minimum sample:** 3 months of reviews where the item applied. An item can't be judged on code
  it never saw.

---

## What is never computed

- **Anything per person.** No per-author or per-reviewer counts, rates, rankings or comparisons. No
  "who introduced this", no "most findings by". No retro scoped to one person's PRs, which is
  the same table filtered (RR6). If an area has only one contributor in the window, its row is a
  person's row: merge it into its parent area, or say the area is too small to show.
- **A quality score for a PR, an area or a team.** Metrics here describe the review process. They
  don't grade the code or the people who wrote it.
- **Lines of code as output.** Size is a denominator, never a measure of productivity (XR p.198–201).

## How to present a metric

Every metric line carries its numerator, its denominator, its sample size, and a flag when the
sample is below the floor:

```
| Metric | Group | Value | n | Note |
|---|---|---|---|---|
| Defects per review (above nit) | src/billing/ | 2.4 (31 ÷ 13) | 13 reviews | |
| Withdrawn rate | lens G | 40% (4 ÷ 10) | 10 findings | at floor; read with care |
| Usefulness rate | src/ui/ | 3 ÷ 4 | 4 findings | below floor: counts only |
| Inspection rate | all | not computed | | agent reviews |
```

Say what the data can't tell you: missing outcomes, PRs without re-review, rows classified from
threads, a window too short for retirement.
