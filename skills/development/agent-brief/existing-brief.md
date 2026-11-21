# An existing brief — revising, a loop send-back, an increment

> Read this when `.workflow/brief.md` already holds a brief for this same work: the user asked to revise
> or extend it, the loop sent it back, or it is one increment of a larger effort. A brief for other work,
> finished or not, is handled in SKILL.md.

## A brief for this same work

The user asked to revise or extend it → revise it in place and log the change under **Revisions**. Changing the criteria, scope or interfaces of an `approved` brief sets Status back to `draft — awaiting approval` and reopens the approval gate — the approval was of the old text. A wording-only correction does not.

## A brief the loop sent back

Its ledger ends in `### Verdict: ESCALATED` (tyr-verdict stopped a loop that was not converging) and the answer was to send the plan back here → revise it in place, and archive the old ledger first:

- Move `ledger.md` to `.workflow/archive/<short-slug-of-this-brief>-loop/`, suffixed `-2`, `-3` if that folder exists, so a second send-back never overwrites the first.
- Put a copy of the brief as it stood before your revision beside it.
- Say that you did.

Left in place, the ledger would start the revised brief at the old iteration count; archived, the next loop starts at 1 and the superseded text stays readable.

## One increment of a large effort

When architect-deep-dive split a large effort into increments, the brief holds **one increment at a time**. List the remaining increments, in order, under **Out of scope** as *"next increment: …"*, and write the next brief only once this one has reached GO and been archived.
