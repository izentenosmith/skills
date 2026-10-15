# Post-mortem — the fallback template

Use this only when the `post-mortem` skill isn't installed; it carries the method this template compresses. Three rules carry over regardless:

- **Blameless.** Roles and system properties, not names attached to errors. "Human error" is never a factor — it's where a factor about the system was supposed to go.
- **Describe, don't prescribe.** No "we should" in the record. What to do next is the follow-through step, written separately ([follow-through.md](follow-through.md)).
- **From artifacts.** The incident log and the git history are the timeline; recollection is marked as such.

```markdown
# Post-mortem: <incident title>

- **Severity:** <level> · **Status:** resolved · **Incident log:** <path or link>
- **Why this got a post-mortem:** <user impact | data | security | a user found it first | near miss | …>

## Summary
<three or four sentences: what users experienced, for how long, what stopped it, what fixed it>

## Timeline (UTC)
| Time | Event | Source |
|---|---|---|
| … | change — <the triggering change> | git <sha> |
| … | impact start | <evidence> |
| … | detected — <how> | <source> |
| … | mitigated — <action> | incident log |
| … | resolved — <fix and repair> | incident log, git <sha> |

**Time to detect:** <impact start → detected> · **Time to mitigate:** <detected → mitigated> · **Time to resolve:** <detected → resolved>

## Impact
- **Who and how many:** <counts and share of the whole, with the query that produced them>
- **What they experienced:** <errors, slowness, wrong data — wrong data stated explicitly>
- **Data:** <records affected, repaired, outstanding>
- **Known vs. assumed:** <which numbers are measured and which are estimates>

## Contributing factors
<one entry per factor, across: trigger · latent condition · detection · response and tooling · process ·
organizational. "None found" recorded per category. Each with its evidence and confidence.>
- **C1 — <category>:** <factor, as a property of the system> — evidence: <…>

## What went well, and where we got lucky
- <load-bearing things that worked>
- <luck that won't be there next time>

## What was done
- **Mitigation:** <…> · **Fix:** <commit> · **Repair:** <artifact> · **Still in place:** <containment not yet undone>

## Open questions
- <what the evidence could not settle>
```

Before circulating: re-read it hunting for blame — "should have", "failed to", names on mistakes, "obviously" — and for any prescription that crept in.
