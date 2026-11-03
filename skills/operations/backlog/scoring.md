# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a backlog health review is graded and written down. **Rubric version: `v1.0`.** Every output
> records the rubric version it was graded against, the tracker and query it read, and the snapshot
> file. Each finding names the principle it violates from [`theory.md`](theory.md) (B-N). A finding
> without a principle is taste.
>
> The formula is the same one the database, networking, Terraform and pipeline skills use, so a 7.4
> means the same thing everywhere.

## Severity taxonomy

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | Work that protects users or data has been lost or abandoned | A prevent/mitigate follow-up from a data-loss, corruption or security incident with no owner or past due (BL-REL-01); an ongoing production incident with no item at all |
| **High** | The backlog or board is actively misleading the team, or flow is broken | WIP over twice its limit; several competing top priorities; most of the ready zone has no acceptance criteria; follow-ups overdue or untracked; error budget spent with features ordered first; incidents happening with no visible unplanned work |
| **Medium** | Debt that slows delivery or hides the big picture | A flat backlog; containers with no outcome; stale or aged work; oversized or layer-split items; unlinked blockers; undecided opportunities; toil over half the work |
| **Low** | Hygiene | Team-perspective stories; duplicates; ancient to-do items; releases named by version; unassigned in-progress items |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches the theory and current practice.
- 🟡 **Acceptable / watch**: works, but carries debt.
- 🔴 **Not well done**: violates the criterion.

## Detection confidence

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the snapshot's fields and dates: a missing acceptance-criteria field, an item in progress for 74 days, 38% of open items at highest priority, a blocked item with no link | Yes. A confirmed defect. |
| ⚠️ **proxy** | A text or pattern signal that approximates a concern: no user named in a description, sibling titles that look like layers, an item that looks like a production failure but has no incident label | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs data the tracker doesn't hold or the snapshot couldn't read: state history for cycle time, sizes, SLO and error-budget state, whether a conversation happened, the outcome a release achieved | **No.** Recorded as a flag, never scored. |

When the user supplies the missing data — an export with history, an SLO report, the team's capacity
— findings from it are ✅.

## Scoring model

### Evaluation units

One evaluation per **domain** per backlog scope (one team, project or board), each graded with its
section of [`health-checks.md`](health-checks.md):

| Domain | In-scope objects (the weight) |
|---|---|
| structure | open containers + open standard items |
| readiness | items in the ready zone |
| flow | in-progress items + in-progress states |
| reliability | open follow-ups + incident items in the window (N/A when there's no production system — say so and drop the domain) |

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   One-object criteria (F4, F5, L5, L6) use the grade the checklist defines for them.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`. Criteria that are 🔬 or N/A are
   left out of both sums and listed.
3. **Severity caps** (lowest wins): any open **Critical** caps at **2.0**; any open **High** caps at
   **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Backlog score

The **backlog score** is the mean of the domain scores, weighted by in-scope object count, caps
re-applied. Several teams or boards make a **portfolio**: mean of backlog scores weighted by
objects, caps re-applied. Report uncapped beside capped.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A backlog is **healthy** — no restructuring is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every item in the ready zone has acceptance criteria (R1 at p = 1.0);
- there is one top priority (F5);
- every post-mortem follow-up has an owner and a date (L1, L2);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately.

## Repeatability

The score must come out the same when re-run on the same snapshot. So: the snapshot is saved
(`.workflow/backlog/snapshot-<YYYY-MM-DD>.csv`) with the query that produced it; "now" is the
snapshot's timestamp, not the time of grading; thresholds are the ones written here; ⚠️ judgments
list the items they were made on.

## Templates

### Health report — `.workflow/backlog/health-<YYYY-MM-DD>.md`

```markdown
# Backlog health — <scope> — <date>
> Rubric v1.0. Tracker: <Linear | Azure DevOps | Jira | markdown>, <team/project/board>.
> Snapshot: .workflow/backlog/snapshot-<date>.csv — <n> items, taken <timestamp UTC>, query: `<query>`.
> Ready zone: <current + next sprint | top 20 of the order>. Window: <90 days>.
> Coverage: <what was read in full; what was signal-scanned>.

## Scores
| structure | readiness | flow | reliability | **Backlog** |
|---:|---:|---:|---:|---:|
| <s> | <s> | <s> | <s or N/A> | **<s>** (uncapped <u>) |

## The board, as text
<the lane × state table from flow.md, with WIP limits proposed in parentheses>

## Flow measures
| Measure | Value | Note |
|---|---|---|
| WIP (in progress / per active person) | | |
| Untouched 30 / 60 / 90+ days | | |
| Unplanned share (window) | | |
| Throughput (per week) · lead time p50/p85 · cycle time p50/p85 | | |
| Items at highest priority | | |

## Findings (worst first)
| ID | Item(s) | Anti-pattern | Conf. | Principle | Severity | Evidence |
|----|---------|--------------|-------|-----------|----------|----------|
| BL-FLO-06 | 41 of 112 open items | Competing top priorities | ✅ | One top priority (B14) | High | priority = highest in snapshot |

## Checklists (per domain)
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

## Needs-data flags (not scored)
## What is working well
## Gate (each condition, pass/fail, with the reason)
## Proposed changes
<a change set for ticket — closures, decisions, links, labels, re-parents — each tied to a finding ID>
```

Finding IDs: `BL-<STR|RDY|FLO|REL>-NN`, as listed in [health-checks.md](health-checks.md).
