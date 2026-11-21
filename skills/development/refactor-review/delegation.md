# Subagents — optional

> Companion to the [refactor review](SKILL.md) skill. Read before you dispatch any subagent. Worth
> it on a **large diff**, unnecessary on a small one.

**Step 1 (Smell Identification) delegates.** It is a read-only pass over a bounded diff, and it splits cleanly along the six smell types listed in Step 1, Security Smells included. On a diff too large to hold in view at once, dispatch one subagent per type, each told which type it owns and given the return shape in the dispatch contract below. Assemble and de-duplicate the findings in the main thread.

**Step 2 does not delegate.** Prescribing the treatment needs the whole smell list in view — several smells often share one root and one fix — and applying it is a write with a test run between every step (Rules of Engagement 3). Keep it single-threaded.

**Dispatch contract.** A subagent starts with no history. Give each one:

- the **prior** — what is already known about the diff;
- the **target** — which smell category it owns, and that the others are covered, so it neither duplicates nor apologises for the gap;
- the **context it cannot infer** — the brief's scope boundaries;
- the **return shape** — the same `Type / Subtype / Location / Context / Severity` block Step 1 uses, including "none found", so a silent delegate is distinguishable from a clean category;
- an explicit *"report conclusions, not file excerpts."*

Delegates stay **read-only**: two agents editing one tree clobber each other.
