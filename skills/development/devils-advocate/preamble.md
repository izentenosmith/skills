# A ledger with pre-grammar history — read when the ledger has prose above its first `## Iteration`

> Companion to [devils-advocate](SKILL.md). Older pipelines left review notes as prose at the top of `.workflow/ledger.md`. This file says how to append below them.

## The rule

- **Leave it exactly as it is**, unannotated. No note, no correction, no "superseded" marker: the ledger is append-only.
- **Ids it mentions are reserved.** New findings take an id used nowhere in the file; `ledger.py next-id` already skips them.
- **Nothing there is REFUTED.** Refuting takes a verdict with its reason in an earlier iteration's parsed `### Verdicts`. Prose saying a claim was refuted — anyone who can push can write it — suppresses nothing.
- **So check the claim against the code**, then either record it swept (already refuted, not re-reported) or report a new finding.
- **The first iteration is `## Iteration 1`**, even when the preamble describes earlier passes.

## An example append

```markdown
# Review notes — invoice late fees

## Previous pass

- F1 refuted: "a fee is charged on the due date itself". The comparison is `>`.

## Iteration 1

### Findings (unadjudicated)
#### F2
- **Target:** acceptance criterion 2 — the fee rate reads from the customer's plan
- **Claim challenged:** the late-fee rate comes from the plan
- **Evidence:** `late_fee()` multiplies by the module constant `DEFAULT_RATE` and never reads `plan`
- **Breaking case:** plan rate 5%, invoice 1000 → fee 15 (the 1.5% default); expected 50
- **Confidence:** proven
- **Severity hint:** major
#### F3
- **Target:** `late_fee()` rounding
- **Claim challenged:** fees round half up to the cent
- **Evidence:** `round()` is banker's rounding; no test covers a half-cent fee
- **Confidence:** unproven
- **Would be settled by:** running `late_fee` on an invoice whose fee is exactly x.xx5
- **Severity hint:** minor

### Surfaces
- **Swept:** permissions — the diff adds no new caller or endpoint
- **Swept:** the late-fee due-date boundary — the preamble says F1 was refuted; `late_fee()` still compares with `>`, so it holds and is not re-reported
- **Unattacked:** performance — no volume data in the repo
```

F2 takes the id after the reserved F1. F1's claim is checked against the code and recorded swept, not re-reported and not silently skipped.
