# The final checklist — `.workflow/hotfix-<slug>.md`

The record that closes the lane. Every box is ticked or carries **skipped: <why>** — no box is left blank. Its summary goes into the commit or PR body; the file stays in `.workflow/`.

```markdown
# Hotfix: <slug> — <one-line symptom>

- **Date:** <UTC>
- **Triage:** hotfix lane · <standard | strict: data / money / permissions / tenancy> · <revert: yes/no>

## Root cause
- **Symptom:** …
- **Cause:** …
- **Why no test caught it:** …
- **Callers:** <n> — <m> fixed in <shared place>; <k> unaffected (<why>)

## Checklist
- [ ] **Root-cause note** written before the fix, from evidence
- [ ] **Red → green:** `<test name>` — failed before the fix (<how shown: checker output, or the run kept>), passes after
- [ ] **Suite:** `<command>` → <result>
- [ ] **Lint / type-check:** `<commands>` → <results, or "none in this repo">
- [ ] **Review pass:** <skill used, or "fallback checklist"> — <blockers fixed: n> · <follow-ups: n>
- [ ] **Follow-up item:** <id or link> — <or "not a band-aid">
- [ ] **Shipped by:** <PR link | merge commit | …> — confirmed by the user at <time>
- [ ] **Pre-production verification:** `<request or command>` → <result> at <sha> — <or "no pre-production environment">
- [ ] **Production verification:** `<request or command>` → <result> at <sha> — <or why not reachable>

## Skipped
- <item — why> (or "nothing skipped")
```

## What counts as evidence

- **A command and its output**, or the exact request and the response that came back — not "verified it works."
- **The commit SHA** the verification ran against. Without it, nobody can tell whether the evidence describes what shipped.
- **For the red test**, either a checker that ran the new test against the pre-fix code, or the failing run itself captured before the fix was written. "It would have failed" is reasoning, not evidence.
