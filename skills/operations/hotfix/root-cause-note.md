# The root-cause note

Three lines, written **before** the fix. Its job is to stop the most common hotfix failure: a fix for the symptom on the reported path, shipped while the cause keeps producing the same bug through another one.

```markdown
## Root cause
- **Symptom:** <what the user saw, observably — the request, input or screen, and the wrong result>
- **Cause:** <the code path and the condition that produces it, described by behavior: "the discount helper
  rounds each line before summing, so totals drift by up to a cent per line">
- **Why no test caught it:** <the specific gap — no test for this input class, a test asserting on a fixture that
  hides it, a mock standing where the bug lives, no tests at all>
```

## What makes each line honest

- **Symptom** is what was observed, not your theory of it. Keep the reporter's input where you have it — it becomes the red test.
- **Cause** comes from evidence: the code you read, a reproduction you ran, the commit that introduced it (`git log -S`, `git blame` on the faulty lines). **If you can't point at the evidence, it's a hypothesis** — write it as one and keep looking, or take the stopping rule's first exit.
- **Why no test caught it** is the line most often skipped, and the one that makes the red test better than "a test for this bug": it names the *class* of input the suite was blind to.

## The caller sweep

Before editing, find every path into the code you're changing:

- [ ] **Direct callers** — every call site of the function, method or component.
- [ ] **Indirect reach** — anything that passes it as a callback, registers it, exports it, or re-exports it; dynamic dispatch the search won't show by name.
- [ ] **Other copies** — the same logic duplicated elsewhere. Search for its distinctive expression, not just its name.

For each, one line: *same bug, fixed by the shared change* / *unaffected, because …* / *needs different behavior* (→ design question, leave the lane). Record the count in the note:

```markdown
- **Callers:** <n> — <m> share the bug and are fixed in <the shared place>; <k> unaffected (<why>)
```
