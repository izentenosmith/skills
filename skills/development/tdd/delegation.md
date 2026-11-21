# Subagents — do not delegate the loop

> Companion to the [tdd](SKILL.md) skill. Read before you dispatch any subagent.

**The red→green cycle stays in the main thread.** This is the one stage in the workflow where delegation actively damages the output. Each cycle is *supposed* to respond to what the previous one taught you — that is the whole argument against horizontal slices. Hand the loop to a subagent working from the brief and you get several tests written in bulk against imagined behavior: horizontal slicing with extra steps.

What you may delegate is **lookup**, never construction:

- A prior-art or convention search when the brief's pointer turns out to be stale or missing.
- A read-only sweep for existing callers of a seam you are about to change, when back-compat is in question.

Take the answer, then write the test yourself.

**Dispatch contract**, if you do delegate a lookup. Give the subagent:

- the **prior** — what you already know or have ruled out;
- the **target** — behavioral, not file paths;
- the **context it cannot infer**;
- the **return shape**;
- an explicit *"report conclusions, not file excerpts."*

Keep it read-only — a delegate must never edit the tree while you are mid-cycle in it.
