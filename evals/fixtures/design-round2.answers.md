# design-round2: answer key (eval 63)

The `base` fixture plus `.workflow/designs/20261117-0940-cancellation-cutoff.md`: `in progress`, the charter, `~7 to resolve … 0 resolved, 0 deferred`, no decisions. Round 1's three questions are answered in the prompt. Kept outside the fixture folder, because runs copy the folder.

| Answer | Goes into Decisions as |
|---|---|
| Q1: account config, `cutoff_minutes`, default 120: venue groups differ, a constant means a deploy per change | the option and that reason |
| Q2: exclusive, a slot exactly at the edge is accepted: "two hours" means what the sign says | the option and that reason |
| Q3: the existing `Rejected` with `CUTOFF_WINDOW` beside any other violation: callers already switch on codes | the option and that reason |

Q1's answer also says two venue groups asked for a per-venue window and the user doesn't know whether it belongs here. That opens a scope question (is a per-venue window in this design?) and, behind it, questions that only exist if the answer is yes: which setting wins, where a venue's setting lives. **The dependent ones must not share a round with the scope question.**

**Expected:** the three decisions recorded and the Questions line at `3 resolved`; a round line `Design: … · Round 2 · 3/<total> resolved …`; one to three questions numbered from 4, each in the four sections; the estimate change stated if the total is no longer ~7; the awaiting line once, after the last question; Status still `in progress`; no second design file, no brief.
