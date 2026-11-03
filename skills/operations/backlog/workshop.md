# Story workshop — the refinement conversation, and its brief

Refinement is a conversation among the people who decide what to build, who build it, and who test
it — the "three amigos" (USM ch. 12, ch. 16). The agent can't hold that conversation for the team,
but it can **prepare it** and **record it**: a brief per item that makes the conversation short and
its result durable.

Write the brief to `.workflow/backlog/<initiative>/workshop-<slice>.md`, one section per item.

## What to talk about

Patton's checklist (USM ch. 7), as questions the brief answers or marks open:

- **Who** — exactly which users, and who else is affected.
- **What** — what they will do, step by step; a sketch or a link to one.
- **Why** — why they need it, and why the business wants it now.
- **What happens outside the software** — before and after; manual steps; other systems.
- **What goes wrong** — errors, exceptions, edge cases, bad data.
- **Questions and assumptions** — each with who answers it and by when.
- **Better solutions** — is there a cheaper way to the same goal?
- **How** — technical approach, at the level needed to size it.
- **How long** — a size for this item, and whether it needs splitting.

## The brief, per item

```markdown
### <item key or "new"> — <title as a verb phrase>
**Who / what / why:** <one line each>
**Flow:** <numbered steps, or a link to the sketch>
**Examples:** <concrete data in, concrete result out — one per rule>
**Acceptance criteria:**
- [ ] <observable check>
- [ ] <observable check>
**Demo:** <what will be shown at review, with what data, in which environment>
**Open questions:** <question — owner — by when>
**Split:** <none | the proposed children, by which heuristic in splitting.md>
**Size:** <the team's unit> — <fits a couple of days? yes/no>
```

**Examples beat abstract criteria.** "Order 1042 with two items, one out of stock, shows a partial
delivery date of the 14th" is checkable; "handles partial stock correctly" is not.

**The demo line is mandatory.** Asking how it will be shown regularly surfaces missing test data,
environments or permissions (B9).

## Signs the workshop isn't working

From USM ch. 16; mention any you see in the record:

- One person dictates and others transcribe.
- Only acceptance criteria get discussed, never who or why.
- No alternatives are considered — the first idea is the only idea.
- The group is too large to converse; five people is plenty.

## Ready for delivery

An item leaves refinement **ready** when: who / what / why are stated; it has acceptance criteria and
a demo line; open questions that block building are answered; it fits a couple of days or is
explicitly a spike; its dependencies are linked (B15). The team's own definition of ready, where the
repo or tracker documents one, overrides this list — say which you used.
