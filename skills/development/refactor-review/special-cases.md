# Special cases

> Companion to the [refactor review](SKILL.md) skill. Open it when a security smell's fix would
> change behavior, or when you run as one track of a brief with **Parallel tracks**.

## A security smell whose fix changes behavior

A security smell at a trust boundary is `blocking`. A noted smell waits for someone to touch the code, and at a trust boundary the someone is an attacker.

Where the fix changes behavior (a new refusal, a new check), this stage cannot make it. Leave the code, rate the smell `blocking`, record it in the ledger, and say in the handoff that it goes to devils-advocate as a finding and to tdd as a slice. Recorded and handed on, it no longer holds this pass open.

The ledger has one shape for a new entry, so the line is:

```markdown
- **N<id>** Security Smells / <Subtype> at <location> — noted: blocking, the fix changes behavior; handed to devils-advocate
  - **Promote if:** a behavior-preserving fix becomes possible
```

The word `noted` there is the grammar's, not the rating: everywhere else the finding stays `blocking`. Smells never enter the computed verdict, so the handoff names it first, before the handoff line, and tells devils-advocate to raise it as a finding. Later passes re-read it like any carried smell, and retire it when the tdd slice lands.

## Running as one track

As one track of a brief with **Parallel tracks**, your `### Smells` section goes to your stage log for the session that started you, Base is read from that log, and you never write the brief.
