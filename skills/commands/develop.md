---
description: Build a feature or fix through the seven-stage development pipeline, starting at architect-deep-dive.
argument-hint: "[what to build or fix]"
disable-model-invocation: true
---

Build this through the development pipeline: $ARGUMENTS

Start with the `architect-deep-dive` skill and follow each skill's hand-off to the next:
`architect-deep-dive` → `agent-brief` → `acceptance-tests` → `tdd` → `refactor-review` →
`devils-advocate` → `tyr-verdict`. Each skill says what it needs, what it writes and when it stops;
follow those instructions, not this summary.

If the arguments point at work already done (an approved brief, a branch with passing acceptance
tests), start at the stage that work leads to. Decide once, up front, which stages the change needs
and say so: a localized fix behind an existing seam needs only `tdd` and `refactor-review`, but
anything touching data, money, permissions or tenancy keeps `devils-advocate` and `tyr-verdict`.
With no arguments, ask what to build.
