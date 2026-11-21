# Delegation — read before you dispatch any subagent

> Companion to [architect-deep-dive](SKILL.md). The design dialogue stays in the main session: in rounds of up to three questions, with the user as the decision-maker. A subagent cannot ask the user anything, so it never runs the conversation.

## What a subagent can run

The **[inferred]** half of rule 4. When a question is answerable from the codebase, dispatching a read-only subagent to answer it keeps the dialogue clean — you get back the finding, not a hundred lines of file excerpts. On a **large** effort the decomposition survey (which existing areas move together, where the current boundaries actually fall) is the same kind of job.

## The dispatch contract

A subagent starts with no history, so every dispatch carries five things:

1. The **stance** — a neutral lookup: report what the code does today, not what it should do.
2. The **target** — what to examine, described behaviorally, not as file paths.
3. The **context it cannot infer** — what the charter already resolved, so it doesn't re-litigate settled ground.
4. The **return shape** you want back.
5. An explicit *"report conclusions, not file excerpts."* A delegate that returns a wall of code has cost you context rather than saved it.

Keep delegates **read-only**, and cap the fan-out — group targets rather than launching one per item.
