# The ledger grammar

`.workflow/ledger.md` is the closing loop's memory. It is an **event log**: every stage appends a section to the current iteration, nothing above the end of the file is ever edited, and the current state — which findings are open, which slices are closed, which smells are still carried — is *derived* by reading the log from the top.

That resolves a contradiction the prose skills used to carry: the ledger was "append-only", yet slices were "moved to closed" and checkboxes ticked in place. Here a slice is opened by one line and closed by another, later line; neither line is ever rewritten.

`ledger.py` is the reference parser. Anything it accepts is a valid ledger; `python3 harness/ledger.py check .workflow/ledger.md` says so or says why not.

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
| `### Closed slices` | tdd (loop-back) | `- [x] F<id> — verified by <test>` |
| `### Smells` | refactor-review | new: `- **N<id>** <Type / Subtype> at <where> — noted: <reason>` + `  - **Promote if:** …`; carried: `- **N<id>** — left \| promoted \| retired: <reason>` |
| `### Findings (unadjudicated)` | devils-advocate | `#### F<id>` + fields; `#### F<id> (re-examined)` for an INCONCLUSIVE finding sent back for evidence |
| `### Surfaces` | devils-advocate | `- **Swept:** <surface> — <note>` / `- **Unattacked:** <surface> — <why>` |
| `### Verdicts` | tyr-verdict | `#### F<id> — CONFIRMED <severity> \| REFUTED \| INCONCLUSIVE` + fields |
| `### Remediation slices` | tyr-verdict | `- [ ] [<severity>] F<id> — <observable behavior>` |
| `### Decisions` | the user | `- **F<id>** — waived: <reason>` |
| `### Verdict: GO \| NO-GO \| ESCALATED` | tyr-verdict | `- **Reason:** …` |

Within an iteration the order is the order of the loop: closed slices, smells, findings, surfaces, verdicts, slices, verdict.

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
| `INCONCLUSIVE` | `Settled by` — the specific evidence, and who gets it |

## Rules the checker enforces

- Iterations are numbered 1, 2, 3 … with no gaps, and there are at most three.
- Ids are stable and never reused: `F` and `N` ids are defined once (a `(re-examined)` entry re-uses the id of an INCONCLUSIVE finding, which is the point). Ids mentioned in the preamble are reserved.
- **REFUTED is sticky.** No later verdict on a refuted finding; a re-report gets a new id and a `Reopens` field.
- Every finding gets exactly one verdict in the iteration that adjudicates it.
- An INCONCLUSIVE finding goes back for evidence **once**. A second INCONCLUSIVE escalates.
- Every CONFIRMED finding has a remediation slice; every slice closes a CONFIRMED finding at the same severity; a slice closes once, naming the test that verifies it.
- Every carried smell is re-examined — left, promoted or retired — in each later iteration's `### Smells`.
- The stated verdict matches the computed one.
- With `--against <older copy>`, the older ledger must be a prefix of the newer one. That is what append-only means.

## The verdict is computed, not chosen

Given the log up to the end of iteration *n*:

1. **ESCALATED** — a finding came back INCONCLUSIVE a second time; or this is iteration 3 and a confirmed blocker or major, or an INCONCLUSIVE, is still open; or this is iteration 2 or later, nothing was closed this pass, and something is still open (a stall).
2. **NO-GO** — a confirmed blocker or major is open, or an INCONCLUSIVE is open.
3. **GO** — otherwise. Open minors ship as tracked follow-ups.

"Closed something" means a slice closed, a finding newly confirmed, or an INCONCLUSIVE settled either way. "Open" excludes anything the user waived under `### Decisions`.

tyr-verdict still makes every judgment that feeds this — what is confirmed, how severe, what is refuted. It just doesn't get to disagree with arithmetic.
