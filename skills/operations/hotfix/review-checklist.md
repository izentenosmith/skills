# The review pass — when no review skill is installed

One pass, over **the diff only**, adopting the prior that the fix is wrong. Re-read the diff as though someone else wrote it under time pressure — because someone did.

For each item: **found nothing** (say what you checked), or a **finding** with evidence — the input, the path, what happens vs. what should. A finding without evidence is a suspicion; record it as one, it becomes a follow-up rather than a blocker.

## The checklist

- [ ] **The red test** — would it still pass if the fix were reverted? If yes, it tests nothing. Does it assert on the behavior the user saw, or on an internal detail?
- [ ] **Edge cases of the fix itself** — empty, null or missing input; zero, one, many; the boundary value the fix compares against (`<` vs `<=`); very large values; unexpected types.
- [ ] **Every other caller** — from the caller sweep: does each one still get correct behavior after the shared change, including the ones you marked unaffected?
- [ ] **Error paths** — what happens when the fixed code fails? Is an error now swallowed, raised at a different layer, or shaped differently than callers expect?
- [ ] **Concurrency and ordering** — shared state, caches, retries, two requests at once. Did the fix assume an order that isn't guaranteed?
- [ ] **Data written** — anything persisted, sent, or deleted: is it correct for records created *before* the fix? Is the write idempotent if retried? **Strict mode lives here.**
- [ ] **Permissions and isolation** — can the changed path now be reached by someone who couldn't before, or see data across a boundary?
- [ ] **Backward compatibility** — interfaces, outputs, config or stored formats that a caller depends on.
- [ ] **What the fix hides** — a clamp, default or catch that makes the symptom disappear while the cause stays. If so, it's a band-aid: Step 5 applies.

## Turning findings into actions

| Finding | Action |
|---|---|
| Proven, and it would hurt a user on a supported path | **Blocker** — fix now, red→green |
| Proven, narrow or low-impact | Follow-up item |
| Unproven | Follow-up item, with what would settle it |
| Strict mode, proven, blocker *or* major | **Ship blocks** until fixed — or the change leaves the lane |

Record the pass in the final checklist: which items found something, which found nothing.
