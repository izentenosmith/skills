# Flow — how the work is actually moving

The backlog says what the team intends; the board says what it's doing. Flow is read from the
tracker's dates and states, so most of it is decidable (✅) from the snapshot rather than estimated.
Grounded in MWV: make the work visible, limit WIP, and look for the time thieves — too much WIP,
unplanned work, conflicting priorities, unknown dependencies and neglected work.

## Inputs

From the Step 0 snapshot, per item: state, **state category** (to do / in progress / done — mapped
from the tracker's own states by the ticket profile), created, started (first move into an in-progress
state, from history where the adapter can read it), done, last changed, assignee, type, labels,
priority, parent, links (blocks / blocked by / depends on). Where history isn't available, "started"
is 🔬 and cycle time is not computed — say so.

Use a window: **the last 90 days** for throughput and unplanned share unless the user picks another.

## The measures

| Measure | How | Principle |
|---|---|---|
| **WIP per state** | Count of items in each in-progress state now | B13 |
| **WIP per person** | In-progress items per assignee; also unassigned in-progress items | B13 |
| **Age in progress** | Now − started, for every in-progress item; flag the oldest 10% | B16 |
| **Untouched** | Now − last changed, bucketed 30 / 60 / 90+ days, per state category | B16 |
| **Unplanned share** | Items in the window that were created already in progress or done, created and started the same day, or carry the team's incident / interrupt / unplanned label — as a share of all items started | B12, B17 |
| **Throughput** | Items done per week over the window | — |
| **Lead time** | Created → done, median and 85th percentile, by type | — |
| **Cycle time** | Started → done, median and 85th percentile, by type | — |
| **Top priorities** | Count of open items at the tracker's highest priority; count of items or projects claiming to be "first" | B14 |
| **Dependencies** | Blocked items, and how many have a link to their blocker; cross-team links | B15 |
| **Queue pile-ups** | States where items wait (review, QA, validate, deploy) holding more items than the active states before them | B13 |

Lead and cycle time are trailing indicators; WIP is the leading one — it says things will be late
before they are (MWV). Report all, lead with WIP.

**Never reconstruct dates from memory or guess them.** A measure the data can't support is 🔬 with
the reason.

## WIP limits — start from what's there

MWV's method, which avoids arguing about the "right" number:

1. **Put the current count on the board** as the limit for each in-progress state — today's real WIP.
2. **Ask whether that number makes sense.** Usually it doesn't: a validation queue of 98 is not a
   plan.
3. **Lower it a step** — any step; 80 is better than 98 — and run with it for a cycle or two.
4. **Repeat** until work flows smoothly: items leave states at about the rate they arrive.
5. **Revisit** when the team changes. Limits are adjusted, not permanent.

A limit can also be per row — per class of service ([ordering.md](ordering.md)) — rather than per
column. **Expedite** may break the limit by policy; nothing else should.

Plan to around **80% of capacity**: wait time rises steeply as utilization nears 100%, so a plan with
no slack has already planned the next delay (B13, B17).

Proposed limits are a recommendation in the report. Setting them on a board is a tracker
configuration change: the user does it, or `ticket` does it after confirmation where the adapter
supports it.

## Making unplanned work visible

When unplanned work isn't tracked, its share can't be measured — that's a finding in itself (B12).
Propose a two-week experiment: every interruption gets an item with the team's unplanned label,
created directly in progress, however small. At the end, the share is a number instead of a feeling,
and the reserved capacity for unplanned work can be set from it.

## Lanes worth proposing

A text view of the board, in the health report, makes the competing work visible at a glance:

```markdown
| Lane \ State | To do | In progress (limit) | Review (limit) | Done (30 d) |
|---|---:|---:|---:|---:|
| Expedite / incidents | — | 1 | 0 | 4 |
| Fixed date / cadence | 2 | 1 | 0 | 3 |
| Post-mortem follow-ups | 5 | 1 | 1 | 2 |
| Standard | 61 | 9 (6) | 14 (5) | 22 |
| Maintenance / toil | 8 | 0 | 0 | 1 |
```

Read it the way MWV suggests: stand back and ask why the most valuable item isn't moving, and what
it's competing with — unplanned work, conflicting priorities, or a dependency.
