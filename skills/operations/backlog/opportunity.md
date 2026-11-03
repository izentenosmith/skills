# Opportunities — before anything is on the map

An opportunity is an idea that hasn't been decided yet: a feature request, a customer complaint, a
stakeholder's wish, an idea from the team. The opportunity backlog is where these wait for a
decision (USM ch. 13). Treating them as committed work is how backlogs grow without bound (B4).

## Every opportunity gets a decision

Discuss it, then pick one (B10):

| Decision | Means | Record |
|---|---|---|
| **Dig deeper** | Worth discovery: frame it, map it, test its assumptions | Move it to discovery; it gets a map ([story-map.md](story-map.md)) |
| **Throw it away** | Not worth pursuing now | Close it as won't-do, with the reason |
| **Think about it** | Not now, for a stated reason | Park it with the reason and a revisit date |

"Think about it" without a reason and a date is not a decision.

## Gut-size before you spend time

Compare it to past work — "about the size of the invoicing rework" — rather than estimating it. The
point is to know whether it's a week or a quarter before deciding to dig deeper.

## The opportunity canvas — for anything bigger than a few weeks

USM ch. 13 adapts a nine-box canvas. Fill what you know; mark what you don't as an assumption. Write
it to `.workflow/backlog/<initiative>/opportunity.md`:

```markdown
# Opportunity — <name>
1. **Problems or solutions** — the problem users have; the solution idea, if any.
2. **Users and customers** — who has the problem; who pays; who decides.
3. **Solutions today** — what they do now, and what's wrong with it.
4. **User value** — what's better for them if this exists.
5. **User metrics** — what they'll do differently that we can measure.
6. **Adoption strategy** — how they'll find out about it and start using it.
7. **Business problem** — what it does for the business: revenue, cost, risk, retention.
8. **Business metrics** — the measurable business result.
9. **Budget** — what it's worth spending to find out, and to build.

**Assumptions to test first:** <the riskiest, each with the smallest test — slicing.md, learning slices>
**Decision:** <dig deeper | throw away | think about it — reason — revisit date>
```

## In the tracker

Opportunities are usually items in an early state ("new", "triage", "proposed") or with a label —
the ticket profile records which ([../ticket/profile.md](../ticket/profile.md)). Health mode reports
how many sit there with no decision and for how long; the decisions themselves are proposed changes,
applied through `ticket` after confirmation.
