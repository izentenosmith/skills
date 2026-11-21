# The ledger grammar

`.workflow/ledger.md` is the closing loop's memory. It is an **event log**: every stage appends a section to the current iteration, nothing above the end of the file is ever edited, and the current state — which findings are open, which slices are closed, which smells are still carried — is *derived* by reading the log from the top.

That resolves a contradiction the prose skills used to carry: the ledger was "append-only", yet slices were "moved to closed" and checkboxes ticked in place. Here a slice is opened by one line and closed by another, later line; neither line is ever rewritten.

`ledger.py`, which ships with this file, is the reference parser: it is in `scripts/` when this file sits beside a skill, and next to this file otherwise. Anything it accepts is a valid ledger; `python3 -I <path to>/ledger.py check .workflow/ledger.md` says so or says why not. `check` and `status` exit with status 2 when the path names no file — a wrong path is not an empty ledger; only `next-id` accepts a ledger nobody has written yet, and answers `F1`, `N1` or `R1`.

## Contents

- [Shape](#shape)
- [Sections](#sections)
- [Rules the checker enforces](#rules-the-checker-enforces)
- [The verdict is computed, not chosen](#the-verdict-is-computed-not-chosen)
- [Error codes](#error-codes)

## Shape

```markdown
# Ledger — <the change>

(anything before the first iteration is preamble: notes, legacy prose from an older
pipeline. It is read by agents, never parsed for state. Ids mentioned here are reserved.)

## Iteration 1

### Smells
- **N1** Dispensables / Duplicate Code at the two constraint validators — noted: the
  architect ruled the duplication accidental
  - **Promote if:** a third instance appears, or a change has to land in both at once

### Findings (unadjudicated)
#### F1
- **Target:** acceptance criterion 3 — the window length reads from account config
- **Claim challenged:** the cutoff window length is read from account config
- **Evidence:** the rule closes over the default constant and never reads `config`
- **Breaking case:** config cutoff 240, slot 180 min out → accepted; expected rejected
- **Confidence:** proven
- **Severity hint:** major

### Surfaces
- **Swept:** security & permissions — no new authorization surface in the diff
- **Unattacked:** performance & scale — delegate timed out

### Verdicts
#### F1 — CONFIRMED major
- **Reason:** reproduced on a scratch copy; the configured window is ignored

### Remediation slices
- [ ] [major] F1 — a booking 180 minutes out is rejected when the account's cutoff is 240

### Verdict: NO-GO
- **Reason:** 1 confirmed major open

## Iteration 2

### Closed slices
- [x] F1 — verified by `test_cutoff_reads_account_config`

### Smells
- **N1** — left: condition not met

### Findings (unadjudicated)
- none

### Surfaces
- **Swept:** acceptance criteria — all five hold against the remediated rule

### Verdicts
- none

### Verdict: GO
- **Reason:** nothing open
```

## Sections

Each stage writes its own section, **even when it has nothing to record** (`- none`). A section's presence is how a resumed harness knows the stage finished.

| Section | Written by | Entries |
|---|---|---|
| `### Closed slices` | tdd (loop-back) | `- [x] F<id> — verified by <test>`; a red run closes the same way, `- [x] R<id> — verified by <test>` |
| `### Smells` | refactor-review | new: `- **N<id>** <Type / Subtype> at <where> — noted: <reason>` + `  - **Promote if:** …`; carried: `- **N<id>** — left \| promoted \| retired: <reason>` |
| `### Findings (unadjudicated)` | devils-advocate | `#### F<id>` + fields; `#### F<id> (re-examined)` for an INCONCLUSIVE finding sent back for evidence |
| `### Surfaces` | devils-advocate | `- **Swept:** <surface> — <note>` / `- **Unattacked:** <surface> — <why>` |
| `### Verdicts` | tyr-verdict | `#### F<id> — CONFIRMED <severity> \| REFUTED \| INCONCLUSIVE` + fields |
| `### Remediation slices` | tyr-verdict | `- [ ] [<severity>] F<id> — <observable behavior>`; and, when its own run before the verdict was red, `- [ ] [blocker] R<id> — red run: <the failing tests, by name>` |
| `### Decisions` | the user's waiver, appended by tyr-verdict (or by the user) — never on a stage's own authority | `- **F<id>** — waived: <the user's words, or the `DEC-n`>` |
| `### Verdict: GO \| NO-GO \| ESCALATED` | tyr-verdict | `- **Reason:** …` |

Within an iteration the order is the order of the loop: closed slices, smells, findings, surfaces, verdicts, slices, verdict. `### Decisions`, when there is one, has no fixed place: the parser accepts it anywhere in the iteration and applies it to that iteration's verdict, so it belongs before the `### Verdict:` line — one appended after it contradicts the verdict already stated (`E50`). A waiver given after the verdict therefore opens the next iteration (`### Decisions`, `### Verdicts` with `- none`, the verdict). After iteration 3 there is no next one (`E02`): the waiver is appended to iteration 3 followed by a restated `### Verdict:` line, and the last verdict line in an iteration is the one that counts.

### Finding fields

| Field | Required |
|---|---|
| `Target`, `Claim challenged`, `Evidence`, `Confidence` (`proven` / `unproven`), `Severity hint` (`blocker` / `major` / `minor`) | always |
| `Breaking case` | when there is one (omit only for a pure missing-branch gap) |
| `Would be settled by` | when `Confidence: unproven` |
| `Reopens` | when re-reporting a REFUTED finding with evidence that meets its *Reopens only if* — names that finding's id; the new report gets a new id |

### Verdict fields

| Verdict | Required |
|---|---|
| any | `Reason` |
| `CONFIRMED` | a severity in the heading, and a remediation slice for it in the same iteration |
| `REFUTED` | `Reopens only if` |
| `INCONCLUSIVE` | `Settled by` — the specific evidence, and who gets it. `Pass` (`1` or `2`) is optional: the parser accepts it and the harness writes it, but the count of passes is taken from the log, not from this field |

### A red run before the verdict

tyr-verdict runs the full suite and the acceptance command before it issues a GO. When that run is red there is no GO, whatever the findings add up to — and no finding to hang the failure on, because only the teardown defines findings. So the red run is recorded as a remediation slice of its own, with an `R` id and no finding behind it:

```markdown
## Iteration 1

### Smells
- none

### Findings (unadjudicated)
- none

### Surfaces
- **Swept:** acceptance criteria — nothing found by reading

### Verdicts
- none

### Remediation slices
- [ ] [blocker] R1 — red run: `test_cutoff_reads_account_config`, `test_accept_window_edge`
  (2 failed, 41 passed at 3f9c2ab)

### Verdict: NO-GO
- **Reason:** the run before the verdict was red (R1)

## Iteration 2

### Closed slices
- [x] R1 — verified by `test_cutoff_reads_account_config`

### Smells
- none

### Findings (unadjudicated)
- none

### Surfaces
- **Swept:** acceptance criteria — all hold

### Verdicts
- none

### Verdict: GO
- **Reason:** nothing open
```

- The line is `- [ ] [blocker] R<id> — red run: <the failing tests, by name>`: the severity is always `blocker`, the text always starts `red run:` and names what failed. Anything after — the counts, the commit — is free text, and a continuation line is fine.
- `R` ids follow the rule for every id: `R1`, `R2`, … defined once, never reused (`ledger.py next-id <ledger> R`).
- An open red run makes the computed verdict **NO-GO**, sends the loop back to tdd like any open slice, and counts as open for the stall and the cap: a red run still open in iteration 3, or after a pass that closed nothing, is **ESCALATED**.
- It is closed in a later iteration under `### Closed slices`, by tdd, naming a test that now passes. Recording one counts as progress in its iteration, like a finding newly confirmed; closing one counts like any slice.
- It cannot be waived under `### Decisions`. A red suite is fixed, not accepted.

## Rules the checker enforces

- Iterations are numbered 1, 2, 3 … with no gaps, and there are at most three.
- Ids are stable and never reused: `F` and `N` ids are defined once (a `(re-examined)` entry re-uses the id of an INCONCLUSIVE finding, which is the point).
- Ids that appear only in the preamble, before the first `## Iteration`, are **reserved and undefined**: `next-id` skips them and nothing in the log may define them again (a finding that takes one is `E10`, a smell `E40`, a red run `E34`), yet no finding stands behind them, so a verdict or a waiver on one is `E20`.
- **REFUTED is sticky.** No later verdict on a refuted finding; a re-report gets a new id and a `Reopens` field.
- Every finding gets exactly one verdict in the iteration that adjudicates it.
- An INCONCLUSIVE finding goes back for evidence **once**. A second INCONCLUSIVE escalates.
- Every CONFIRMED finding has a remediation slice; every slice closes a CONFIRMED finding at the same severity; a slice closes once, naming the test that verifies it.
- A red-run slice is `[blocker] R<id> — red run: <failing tests>` (`E33`), its id is new (`E34`), and it closes like any slice, once, naming a test (`E32`). A GO stated while one is open is `E50`.
- Every carried smell is re-examined — left, promoted or retired — in each later iteration's `### Smells`.
- The stated verdict matches the computed one.
- With `--against <older copy>`, the older ledger must be a prefix of the newer one. That is what append-only means.

## The verdict is computed, not chosen

Given the log up to the end of iteration *n*:

1. **ESCALATED** — a finding came back INCONCLUSIVE a second time; or this is iteration 3 and a confirmed blocker or major, an INCONCLUSIVE, or a red run is still open; or this is iteration 2 or later, nothing was closed this pass, and something is still open (a stall).
2. **NO-GO** — a confirmed blocker or major is open, an INCONCLUSIVE is open, or a red run is open.
3. **GO** — otherwise. Open minors ship as tracked follow-ups.

"Closed something" means a slice closed, a finding newly confirmed, a red run newly recorded, or an INCONCLUSIVE settled either way. "Open" excludes anything the user waived under `### Decisions`; `ledger.py status` names those findings on its `waived:` line (`waived: F3, F7`, or `waived: none`) and under `waived` in its `--json` output.

tyr-verdict still makes every judgment that feeds this — what is confirmed, how severe, what is refuted. It just doesn't get to disagree with arithmetic.

## Error codes

| Code | Means |
|---|---|
| `E01` `E02` | iteration numbers out of sequence; more iterations than the cap |
| `E03` `E04` | an unknown, repeated or misplaced heading; a line that fits no section's shape |
| `E10`–`E14` | findings: id reused or a bad `(re-examined)`; a required field missing; a bad confidence or severity hint; unproven with nothing to settle it; `Reopens` naming a finding that was not refuted |
| `E20`–`E27` | verdicts: on an unknown finding or not one of the three; on a finding already REFUTED or CONFIRMED; no `Reason` or `Reopens only if`; no `Settled by`; CONFIRMED without a severity; a finding never adjudicated; two verdicts in one iteration; INCONCLUSIVE a third time |
| `E30` `E31` | a CONFIRMED finding with no slice; a slice for a finding not CONFIRMED in this iteration, or at another severity |
| `E32` | a closing line for a slice (`F` or `R`) that was never opened, is already closed, or names no test (`verified by`) |
| `E33` | a red-run slice that is not `[blocker] R<id> — red run: <the failing tests>` |
| `E34` | a red-run id already in use |
| `E40`–`E42` | smells: id reused or no `Promote if`; an action on an unknown or settled smell; a carried smell not re-examined |
| `E50` `E51` | the stated verdict is not the computed one; a verdict without `### Verdicts`, or an iteration left without one |
| `E60` | with `--against`: the older copy is not a prefix of this one |
