# Theory — The Principles Every Backlog Finding Cites (B1–B20)

> Every finding in a health review, and every reason given in a map, a split or an ordering, names
> one of these. Each principle states **what it says**, **why it matters** for a backlog, and **what
> violating it looks like** in a tracker. Sources:
>
> | Short name | Source |
> |---|---|
> | **USM** | Jeff Patton, *User Story Mapping* (2014) |
> | **MWV** | Dominica DeGrandis, *Making Work Visible: How to Unmask Capacity Killing WIP* (DevOps Enterprise Summit talk, 2017) |
> | **SRE** | Beyer, Jones, Petoff & Murphy (eds.), *Site Reliability Engineering* (2016) |
>
> USM cites chapters; SRE cites chapters and appendices. The books predate most of today's trackers;
> where a principle is old and the mechanism is new (a saved query, a label, a board column), the
> principle comes from the book and the mechanism is named as current practice.

---

## Part A — What a backlog is for

### B1 — Stories exist to build shared understanding
**Says:** A story is a card, a conversation and a confirmation. The card is a reminder that points to
a conversation; the conversation is where understanding is built; the confirmation is how everyone
will know it is done (USM ch. 6). Documents support that conversation — they don't replace it (USM
ch. 1, ch. 8).
**Why:** A ticket written as a one-way specification gets built exactly as written and still misses
what was needed, because the people building it never heard why.
**Violation:** long descriptions nobody discussed; acceptance criteria with no story about who does
what and why (USM ch. 16); items that only their author can explain.

### B2 — Keep the whole story visible
**Says:** A flat, ordered list loses the big picture — the user's journey that gives each item its
meaning. A map arranges work along that journey so gaps and priorities can be seen (USM ch. 1, "the
tragedy of the flat backlog").
**Why:** Ordering items one at a time against each other produces a pile of features that don't add
up to anything a user can finish.
**Violation:** hundreds of open items in one list with no grouping by user activity, epic or outcome;
releases assembled by picking the top N items.

### B3 — Prioritize outcomes, not features
**Says:** Decide what change in users' behavior or in the business you want, then pick the smallest
set of work that produces it. Name release slices by their outcome (USM ch. 2).
**Why:** Output is easy to count and says nothing about whether anything got better.
**Violation:** releases named "Phase 2" or "v3 features"; epics with no target user or metric; items
with no who or why.

### B4 — There is always too much
**Says:** More ideas than time is the normal state. Minimizing is the work — discovery that keeps
more ideas than it cuts is not being done right (USM ch. 2, ch. 14).
**Why:** A backlog that only grows becomes a list nobody reads, and its genuine top items hide among
the rest.
**Violation:** nothing ever closed as "won't do"; the backlog grows every month while throughput is
flat; opportunities that never get a decision.

### B5 — Build to learn before building to earn
**Says:** Name the riskiest assumptions and test them with the smallest experiment — a prototype, a
spike, a minimum viable product experiment — before committing to the full solution (USM ch. 3, ch. 15).
**Why:** Most ideas are wrong in some way; finding out cheaply is the only defense.
**Violation:** large bets with no learning slice; spikes with no question, no time box and no decision
they feed.

### B6 — Size depends on the conversation
**Says:** Stories are like rocks: big ones get broken into smaller ones as they get closer to being
built. The right size is need-sized for users, outcome-sized for the business, and a few days for the
people building it. Split progressively, just in time (USM ch. 11, ch. 17).
**Why:** Splitting too early wastes effort on work that will change; splitting too late puts
unknowns into a sprint.
**Violation:** an epic broken into sixty tasks months before anyone works on it; items entering
delivery that are weeks of work; hundreds of tiny items nobody can prioritize.

### B7 — Slice thin and whole
**Says:** Each piece should be a small, complete, usable thing — a cupcake, not a layer of a cake.
Half a baked cake, not a half-baked cake (USM ch. 10, ch. 16).
**Why:** A layer — "the API for X", "the UI for X" — can't be evaluated by anyone until every layer
is done, so feedback arrives last.
**Violation:** items titled by technical layer or component; a feature that only works once five
items all finish.

### B8 — Opening, midgame, endgame
**Says:** Build a thin end-to-end path through the riskiest part first, then fill in optional steps and
hard rules, then polish (USM ch. 4).
**Why:** Risk retires early, and there is always something working to evaluate and to ship if time
runs out.
**Violation:** polish and edge cases scheduled before the core path works; the risky integration
saved for last.

### B9 — Know how you'll confirm it
**Says:** Before building, agree what you'll check to confirm it is done and how you'll demonstrate it
at review (USM ch. 6, ch. 7).
**Why:** The demo question surfaces gaps — test data, environments, permissions — while they are
still cheap.
**Violation:** items ready for delivery with no acceptance criteria; criteria that restate the title;
no idea how it will be shown.

### B10 — Every opportunity gets a decision
**Says:** An opportunity is discussed and then dug into, thrown away, or deliberately parked for a
reason (USM ch. 13). A parked idea is a decision with a revisit date, not a resting place.
**Why:** Undecided ideas accumulate and make the backlog look like a commitment it isn't.
**Violation:** items in a "new" state for months with no decision; "someday" items nobody owns.

### B11 — Learn from what you build; change is a new card
**Says:** Review what was built against what was agreed, and separately ask whether, now that you see
it, it should change. A change is a new item, not a reopened one (USM ch. 9, ch. 18).
**Why:** Reopening hides both the original delivery and the learning, and corrupts every cycle-time
number.
**Violation:** items reopened repeatedly; releases with no outcome check afterwards.

## Part B — How work flows

### B12 — Make all the work visible
**Says:** Put the work where everyone can see it — including unplanned work, which never enters the
to-do column and appears straight in doing (MWV).
**Why:** Invisible work is still consumed capacity. Without it on the board, the delay it causes has
no evidence and gets blamed on the people.
**Violation:** incidents, interruptions and support requests handled with no item; items created
already in progress or already done; a board that shows only planned work.

### B13 — Limit work in progress
**Says:** Too much work in progress is the biggest enemy of flow. Wait time grows sharply as
utilization approaches 100% (Kingman's formula), so plan for around 80% of capacity. WIP is a
leading indicator — it tells you things will be late before they are (MWV).
**Why:** Context switching and queues turn a week of work into a month of elapsed time.
**Violation:** no WIP limits; more items in progress than people, often several per person; a review
or validation column holding dozens of items.

### B14 — One top priority, and a stated policy
**Says:** There can be many priorities but only one top priority. Make the prioritization policy
explicit — cost of delay, hard dates, whatever it is — so conflicts are settled by the policy rather
than by whoever is loudest (MWV).
**Why:** Competing "top" items split the same people and stall all of them.
**Violation:** most open items marked highest priority; several projects each claiming to be first;
no written policy.

### B15 — Make dependencies visible
**Says:** Each dependency on another person or team multiplies the chance of being late — with three
independent arrivals, only one of eight combinations is on time (MWV). Link dependent work across
teams and warn downstream teams early.
**Why:** Teams that don't know about each other's critical work collide late and expensively.
**Violation:** blocked items with no link to what blocks them; cross-team work tracked on one side
only.

### B16 — Neglected work is expensive
**Says:** Partially completed work is costly and stuck work is invisible until someone looks. Query
everything that hasn't moved in 30 days — 60 or 90 if needed — and ask why each item is stuck (MWV).
**Why:** Stale items hold capacity, mislead planning, and often hide a blocker nobody escalated.
**Violation:** items in progress for months; long tails of untouched items in every state.

### B17 — Plan for unplanned and cadence work
**Says:** Unplanned work never reaches zero, so reserve capacity for it, keep a steady flow of
maintenance to reduce it, and make hard-dated recurring work (month-end, audits, renewals) big, bold
and dated on the board (MWV).
**Why:** A plan that assumes no interruptions is late on day one.
**Violation:** sprints planned to 100% of capacity; recurring deadlines missing from the board until
they are urgent; no maintenance lane.

## Part C — Reliability work in the backlog

### B18 — The error budget decides between features and reliability
**Says:** An SLO sets how unreliable a service may be; the remaining error budget is spent on change.
When the budget is exhausted, releases other than urgent fixes stop and reliability work comes first
(SRE ch. 3, App. B).
**Why:** Without an agreed rule, the trade-off is argued from opinion every time, and features win
until an outage.
**Violation:** an exhausted budget with feature work still ordered above reliability items; no
policy at all where SLOs exist.

### B19 — Post-mortem follow-ups are tracked, owned work
**Says:** Every action item from a post-mortem is a tracked item with a type, an owner and a status,
reviewed regularly until it is done (SRE ch. 15, App. D, App. F).
**Why:** An unfinished follow-up is how the next post-mortem starts with "this was known."
**Violation:** follow-ups with no owner, past their date, or ordered below routine features.

### B20 — Keep toil capped
**Says:** Toil — manual, repetitive, automatable work that scales with the service and leaves nothing
behind — should stay well under half of the team's time (SRE ch. 5).
**Why:** Toil crowds out the engineering that would reduce it, so it grows on its own.
**Violation:** most completed items are manual operational requests; the same data fix or manual
step repeated across many items with no automation item.
