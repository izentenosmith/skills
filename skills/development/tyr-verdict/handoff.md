# Handoff — the closing prompt on a GO or an ESCALATED

> Companion to [tyr-verdict](SKILL.md). The NO-GO prompt is in the skill itself. Fill every placeholder; a GO with no commit and no counts is not a GO anyone can merge on.

- On **GO**, prompt the user:
  > Verdict: **GO** at `<head sha>` — suite <passed>/<failed>/<skipped>, acceptance tests <passed>/<failed>/<skipped>. All confirmed defects are closed (or accepted as tracked minors) and no findings are open. Shipping with <n> noted smell(s) and <m> tracked minor(s), listed above. <k> ship-checklist item(s) are still open: <each, in a few words> — the code is done; the change is done when those are. Unconfirmed in the brief's Revisions: <each entry, or none> — yours to confirm before it merges. Next: prepare it for review (pr-prep, where installed) and work the open items before it merges.
- On **ESCALATED**, prompt the user:
  > Verdict: **ESCALATED** — the loop is not converging after <i> iterations. <what is unresolved> Your call: accept the risk and ship, treat it as confirmed and fix it, or send it back to **`agent-brief`** / **`architect-deep-dive`** because the plan itself doesn't hold. (A brief revised after being sent back starts a fresh loop: agent-brief archives this ledger with the old brief.)
