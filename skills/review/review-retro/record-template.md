# Templates — The PR Record and the Retro Report

> Two documents. The **PR record** is one PR's review, written to be found later (RR1). The **retro
> report** is many reviews turned into numbers and proposals. Both describe; proposals sit in their
> own section with their evidence (RR5). Neither names a person as the source of a defect (RR6).
> Principles are in [theory.md](theory.md), formulas in [metrics.md](metrics.md), the proposal format
> in [proposals.md](proposals.md#9-proposal-format).

---

## Writing to be found

A record is read months later by someone who searched for a file path, an issue id or an error
message. Write for that search.

- **Stable headings.** Use the headings below exactly, in this order, even when a section is empty
  (write `None.`). Then one search for `## Deferred without an issue` across the records finds
  every open promise.
- **Full paths, in backticks.** `src/billing/invoice.py`, not "the invoice module". Add the
  function or class name where it matters: `src/billing/invoice.py:apply_discount`.
- **Ids as written elsewhere.** `#482`, `PR-3`, `ENG-1931`, the full merge SHA. A reader pastes them
  into search.
- **A keywords line** at the top: the areas, the main symbols, the issue ids, and the error strings
  the change was about.
- **Links to the thread,** for each decision and answer, so the record never has to quote much.
- **No secrets,** even ones that appear in the thread. Name the kind and the place, as peer-review
  does.
- **No names as blame.** Decisions link to the comment where they were made, and the link carries
  who said it. Findings describe code.
- **The file.** Without the harness, print the record and offer to save it as
  `docs/reviews/pr-<n>.md`, or wherever the user keeps them. Under the harness, it goes in
  `.review/pr-<n>/`.

---

## The PR record

```markdown
# PR record — #<n> <title>

<!-- keywords: <areas>, <main symbols>, <issue ids>, <error strings> -->
**State:** <merged <date> into `<base>` @ `<full sha>` | closed unmerged <date> | open (provisional record)>
**Issues:** <#n, ENG-n | none linked>   **Areas:** `<path/>`, `<path/>`   **Change type:** <feature | fix | …>
**Size:** <m> meaningful lines in <f> files (<excluded: lockfiles, generated…>)
**Review:** <tier>, <r> rounds, re-review: <yes @ <sha> | no>. **Sources:** <report.md, findings.json, rereview-<sha>.md, thread, …>

## Claim
<One or two sentences: what the change does and why, with its source (PR body / issue / derived from
code). The final alignment from the review: Exact | Missing: <what> | Tangling: <what> — and whether it
changed between rounds.>

## What changed
- `<path>` — <what changed there, one line>
- <…group small files: "`tests/billing/` — 4 new tests for the zero-percent path">

## Decisions
| Decision | Reason | Rejected alternative | Where |
|---|---|---|---|
| <Keep rounding in `Money`, not in the caller> | <every caller needs it; one place to test> | <round in `apply_discount`> | <thread link / report §Questions / `file:line`> |

## Findings and outcomes
| Id | Severity | Type | Where | Claim | Outcome | Verified | Issue |
|---|---|---|---|---|---|---|---|
| PR-1 | blocker | bug | `src/pricing.ts:42` | 0% discount skips rounding | fixed | yes | — |
| PR-2 | major | test | `tests/pricing.test.ts` | no test for percent = 0 | fixed | no | — |
| PR-3 | minor | evolvability | `src/pricing.ts:60` | duplicates `roundMoney` | deferred | — | #491 |
| PR-4 | major | bug | `jobs/refund.ts:18` | old shape still passed | not fixed (merged) | — | — |
| PR-5 | minor | bug | `src/mw.ts:12` | missing auth check | withdrawn: guard is in middleware | yes | — |
<Outcomes per metrics.md §0.1. "fixed, not verified" means the final diff addresses it but no
re-review checked. Nits: one grouped line.>

## Deferred without an issue
- **PR-<n>** `<file:line>` — <claim>. Needs an issue because <what breaks or who trips on it if it's
  forgotten>.
<or: None.>

## Knowledge that belongs in the code
| Answer (from the thread) | Belongs in | Landed? | Where asked |
|---|---|---|---|
| <`retry=0` is deliberate: the upstream API double-charges on retry> | `src/payments/client.py:send` (comment) | <yes, in the final diff | no> | <thread link> |

## For the next person touching this code
- <An invariant this change established, and the test that guards it: `tests/…::test_…`>
- <A fragile spot or hotspot (from the xray, if it ran), and what makes it fragile>
- <Files that change with these: `<a>` usually changes with `<b>`>
- <What was deliberately not done, and where that decision lives>
- <Open deferrals with their issue ids>

## Metrics
<Under the harness: its table, pasted unchanged, with any note below it. Without it: findings by
severity and outcome, usefulness and fix-verification counts for this PR, size, rounds, time to first
review and to merge, each with its numerator and denominator. One PR is below every rate's floor, so
show counts, not percentages.>

## Sources
<Report and re-review files with their SHAs, the PR URL, the issue URLs, the commands that fetched the
thread. Anything that couldn't be read, and why.>
```

**What the record leaves out:** proposals (they go to the retro or `proposals.md`), praise or blame,
and the full review report (link it).

---

## The retro report

```markdown
# Review retro — <scope> (<from> → <to>)

**Data:** <n> reviews, <m> findings (<k> classified from threads), <r> with re-review. Sources:
<.review/pr-*/, peer-review reports, gh, git log>. **Gaps:** <PRs with no outcomes, missing sizes,
missing timestamps>.
**Grouped by** code area and change type. No per-person data was collected or computed.
**Tier:** <Retro (light) | Retro (full)> — <why>.

## Headline
- <3–5 bullets. Each names a number, its n, and what it means. Lead with what should change.>

## Metrics
### Volume and density
<table: defects per review and density, by area and by change type, above nit and all>
### Distribution
<table: type × area; severity; lens>
### Size
<median, p90, max meaningful lines; reviews over 400 and over 1,000; defects per review ≤ 400 vs > 400>
### Zero-finding reviews
<by risk group; any risky area with several, named>
### Time
<median and p90 to first review and to merge; median rounds — always next to the depth metrics>
### Outcomes
<fix verification rate; usefulness rate above nit and for nits; withdrawn rate overall and per lens;
deferral tracking rate with every untracked `pr:id` listed>

## Recurring defect classes
| Class | Defects | PRs | Areas | Covered by | → |
|---|---|---|---|---|---|
| <new env var missing from manifests> | 4 | 3 | `services/api/`, `services/worker/` | §J item, too vague | P-1 checklist-add |
| <SQL built by string concatenation> | 3 | 3 | `services/api/` | nothing | P-2 lint |
**Watching** (below threshold): <class (count, PRs)>, …

## Checklist health
<items with their hit counts; retirement candidates with months since last catch; list size per area>

## Proposals
<Each in the proposals.md §9 format, numbered P-1…, with its patch. Or: "None met the thresholds.">

## Last retro's proposals
<For each: accepted (PR link) or rejected (reason), and whether its predicted effect showed up.>

## What the data can't say
<Samples below floor, a window too short for retirement, thread-classified rows, areas merged to avoid
a one-person row, and anything else a reader might over-read.>

## Handoff
<See SKILL.md.>
```

**Light retro.** Keep Data, Headline, Metrics as counts (no rates below the floors), Recurring defect
classes, Proposals, and What the data can't say. Leave out Checklist health unless the window is
three months or more.
