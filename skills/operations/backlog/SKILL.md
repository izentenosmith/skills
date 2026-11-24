---
name: backlog
description: Shapes and health-checks a backlog in Linear, Azure DevOps, Jira or a markdown file. Map mode builds a story map with release slices and a walking skeleton; refine mode splits an epic into thin stories with acceptance criteria; health mode audits the board (stale work, WIP, dependencies) with a 0–10 score; order mode ranks by cost of delay. Use for story mapping, splitting an epic, prioritizing, backlog health or why work is stuck. Not for creating or updating a single item — that is ticket.
---

# 🗺️ Backlog

A backlog is not a list of things to build; it's the team's current best guess at **which outcomes
matter, for whom, and what to try next** — kept small enough to read and honest enough to plan from.
This skill builds one (a story map and outcome slices), gets the next slice ready to build, orders
it by a stated policy, and audits an existing backlog and board for the patterns that make teams
late: no big picture, oversized or unready items, too much work in progress, invisible unplanned
work, competing top priorities, hidden dependencies, and operational follow-ups nobody finishes.

## Where this fits

- [ticket](../ticket/SKILL.md) — **one item at a time**: create, update, close, link, label, against
  the team's tracker profile. It is the **only writer**: everything this skill proposes to change in
  a tracker is applied by ticket.
- **backlog** (this skill) — **many items at once**: their shape, readiness, order and flow. Reads
  the tracker; never writes to it.
- [incident-fix](../incident-fix/SKILL.md) and [post-mortem](../post-mortem/SKILL.md) produce the
  follow-ups that Health mode checks are owned and done, and the incident items it checks are
  labeled. [hotfix](../hotfix/SKILL.md) produces the follow-ups a band-aid owes.

Reference docs, all in this folder:

- [theory.md](theory.md) — the principles every finding and every recommendation cites (B1–B20)
- [story-map.md](story-map.md) — framing, the five mapping steps, the markdown map, mapping an existing flat backlog
- [slicing.md](slicing.md) — release slices by outcome, learning slices, opening/midgame/endgame
- [splitting.md](splitting.md) — splitting heuristics, splits to avoid, reassembling
- [workshop.md](workshop.md) — the refinement conversation and the per-item brief; ready for delivery
- [opportunity.md](opportunity.md) — the opportunity canvas and the decision every idea gets
- [ordering.md](ordering.md) — classes of service, outcomes before features, cost of delay
- [flow.md](flow.md) — WIP, aging, unplanned work, dependencies, WIP limits from today's count
- [health-checks.md](health-checks.md) — the rubric: four domains, anti-patterns, criteria
- [scoring.md](scoring.md) — severity, confidence, the 0–10 formula, the gate, the report template

**Never create, update, close, re-rank, re-parent or label anything in a tracker yourself, and never
change board configuration (columns, WIP limits).** Every change is a line in a change set the user
confirms, applied through ticket (see Apply).

---

## 📐 Pick the mode

| Mode | Input | Output |
|---|---|---|
| **Map** | An idea, initiative or opportunity — or an existing flat backlog to restructure | `.workflow/backlog/<initiative>/map.md` (frame, map, slices), `opportunity.md` when the idea is undecided |
| **Refine** | The next slice of a map, a sprint's candidates, or an epic to split | `.workflow/backlog/<initiative>/workshop-<slice>.md`: one brief per item, splits, ready/not-ready |
| **Health** | An existing backlog or board | `.workflow/backlog/health-<YYYY-MM-DD>.md`: findings, flow measures, per-domain scores, the gate |
| **Order** | An existing backlog, or a refined slice | `.workflow/backlog/order-<YYYY-MM-DD>.md`: the ranked list, each item's class and reason |

Requests often span two — "groom the backlog" is usually Health then Order; "plan the next release"
is Map then Refine. Say which modes you're running and in what order. Every mode that changes
something in the tracker ends with **Apply**.

---

## 🔎 Step 0: Find the backlog, take a snapshot

- [ ] **Read the ticket profile**, `.workflow/tracker.md` — the tracker (Linear, Azure DevOps, Jira),
  its project or team, the type, state and field mappings, and the labels the team uses for
  incidents, follow-ups, unplanned work and toil ([../ticket/profile.md](../ticket/profile.md)). If
  it's missing and ticket is installed, run ticket's profile discovery — read-only. If there's no
  tracker at all, the backlog is `.workflow/backlog.md` (create it in Map mode, with the user's
  agreement), read and written the way ticket's [local adapter](../ticket/adapters/local.md) does.
- [ ] **Agree the scope in one line**: which team, project, board or area; which states count as to
  do, in progress and done; for Health, the ready zone and the window (default: current + next sprint,
  last 90 days). Ask once, in a single question, for whatever can't be read from the profile.
- [ ] **Read through the adapter** for that tracker —
  [Azure DevOps](../ticket/adapters/azure-devops.md), [Jira](../ticket/adapters/jira.md),
  [Linear](../ticket/adapters/linear.md) — using its read-only queries. Credentials stay where the
  adapter says (an existing CLI login or an environment variable); never ask for a token in chat.
- [ ] **Save a snapshot**, `.workflow/backlog/snapshot-<YYYY-MM-DD>.csv`, with the query that produced
  it and the time it was taken: key, type, title, state, state category, created, started, done, last
  changed, assignee, priority, rank, size, sprint or cycle, parent, labels, links, due date, and
  whether it has acceptance criteria. **Metadata only** — no description or comment bodies, which can
  carry customer data; read those in place when a check needs them.
- [ ] **Read the operational context**: incident logs and post-mortems in the repo (`docs/incidents/`,
  `postmortems/`, `.workflow/`), `.workflow/follow-ups.md`, and any SLO or error-budget doc. Health's
  reliability domain and Order's classes of service need them.

If the snapshot can't be taken — no access, no CLI, an expired login — stop and say what's needed;
the user fixes access themselves. Don't grade from memory or from a description of the backlog.

---

## 🗺️ Map

For a new initiative, or to give a flat backlog its big picture. Work [story-map.md](story-map.md),
then [slicing.md](slicing.md).

- [ ] **Undecided idea?** Start with [opportunity.md](opportunity.md): the canvas, the riskiest
  assumptions, and a decision — dig deeper, throw away, or park with a reason and a date. Only "dig
  deeper" continues to mapping.
- [ ] **Frame** — what, why, who, the outcome and how it'll be measured, constraints. A map with no
  frame becomes a feature list (B3).
- [ ] **Map** — the user's steps left to right, alternatives and what goes wrong below, a backbone of
  activities across the top. From an existing backlog, cluster items by what the user is trying to do,
  merge duplicates, and **list the holes** — steps no item covers.
- [ ] **Slice** — release slices named by outcome, each with its measure; learning slices first when
  the frame rests on an untested assumption; the walking skeleton through the riskiest path as the
  opening game.
- [ ] **Questions, risks, out of scope** — written under the map, each question with an owner.

Map produces a picture and a plan. The new items, merges and re-parents it implies go into the change
set.

## ✂️ Refine

For the **next** slice only — later slices stay coarse (B6). Work [splitting.md](splitting.md) and
[workshop.md](workshop.md).

- [ ] **Too big?** First look for a cheaper solution to the same goal; then split by journey step,
  opening/midgame/endgame, good/better/best, alternative path, business rule, what goes wrong —
  never by layer or by team activity.
- [ ] **A brief per item**: who / what / why, flow, concrete examples, acceptance criteria, **a demo
  line**, open questions with owners, size.
- [ ] **Unknowns become spikes** with a question, a time box and the decision they feed.
- [ ] **Mark each item ready or not ready**, using the team's definition of ready where one exists,
  and say what's missing for the rest.
- [ ] **Write the pieces to ticket's templates** — [../ticket/writing.md](../ticket/writing.md) — so
  the change set is ready to apply.

The brief prepares the team's conversation; it doesn't replace it (B1). Say which answers came from
the team or the tracker and which are your proposals.

## 🩺 Health

An audit. **It does not change anything** — findings, measures, a score. Work
[health-checks.md](health-checks.md), [flow.md](flow.md) and [scoring.md](scoring.md).

- [ ] **H1 — Flow measures** from the snapshot: WIP per state and per person, age in progress,
  untouched 30/60/90, unplanned share, throughput, lead and cycle time, items at highest priority,
  blocked items and their links. A measure the data can't support is 🔬 with the reason.
- [ ] **H2 — The board as text**: lanes by class of service × states, with today's counts and the
  WIP limits you'd propose (starting from the current count, lowered a step).
- [ ] **H3 — Findings per domain** — structure, readiness, flow, reliability — each with its six
  fields: ID, items, anti-pattern, confidence, principle, severity, plus the evidence (the field
  values or the query).
- [ ] **H4 — Score** per domain and overall, caps applied and stated, uncapped beside capped; the
  gate, condition by condition; what's working well.
- [ ] **H5 — Proposed changes**, each tied to a finding: close or decide stale items, link blockers,
  add the incident label, give follow-ups owners and dates, merge duplicates. These go to Apply.

The review **describes and proposes; it does not reassign people or set limits.** Owners and WIP
limits are the team's decisions, presented as recommendations.

## 🔢 Order

Work [ordering.md](ordering.md).

- [ ] **Classes of service first**: expedite (open incidents), error-budget freeze (when the budget is
  spent and a policy exists), fixed date and cadence, post-mortem follow-ups, standard, and
  maintenance/toil as reserved capacity.
- [ ] **Standard work by outcome**, then users, then their goals, then items — cost of delay to break
  ties, divided by size where sizes exist. **Never invent sizes or values.**
- [ ] **Exactly one item at the top.** Adjust for dependencies, bundled bugs, and spikes that decide a
  larger bet.
- [ ] **Write the order with a reason per item**, the previous position beside it, and the items that
  couldn't be ordered and why.

## 📤 Apply — through ticket, after confirmation

Every mode that implies tracker changes ends here.

- [ ] **Write the change set** at the end of the mode's output file: one line per operation —
  create, update field, close with reason, link, label, re-parent, re-rank — with the item, the exact
  new value, and the finding or decision it comes from.
- [ ] **Show it and wait.** The user confirms the set as listed; anything not on the list needs its
  own confirmation. A broad "go ahead" earlier doesn't cover a later set.
- [ ] **Hand it to [ticket](../ticket/SKILL.md)**, which reconciles against what exists, applies each
  operation, reports OK or FAIL per item without aborting the batch, and reads the results back.
- [ ] **Without ticket installed**, the change set *is* the deliverable — formatted for the user to
  apply, with the adapter's commands where they help. Without a tracker, apply it to
  `.workflow/backlog.md` after confirmation.
- [ ] **Report** what was applied, what failed, and what was skipped as already done.

## 🛑 Stopping rule

**Map** stops when the frame names an outcome and its measure, the backbone covers the journey, every
slice is named by an outcome, the holes and open questions are listed with owners, and the change set
is written.

**Refine** stops when every item in the next slice has a brief, is marked ready or says what it's
missing, and the split pieces are written to ticket's templates.

**Health** stops when every in-scope domain has an evaluation with coverage stated, every finding has
its fields and evidence, every score shows `p`, base and cap, every 🔬 flag is listed, and the gate is
stated condition by condition.

**Order** stops when there is one top item, every ordered item has a class and a reason, and the
unorderable items are listed with what's missing.

Then stop. A backlog can always be tidier. **A change that doesn't make the next decision easier, the
next slice readier, or the work flow faster by an amount the team would notice is grooming for its
own sake** — and every hour spent on items that won't be built for months is spent on plans that will
change (B6).

## Subagents — optional

Snapshot extraction and the per-domain checks delegate well: read-only, bounded, and they flood
context with item lists. One delegate per domain in Health, or per cluster when mapping a large flat
backlog. **The change set, the confirmation and the hand-off to ticket never delegate.** **Dispatch
contract:** the prior, the target, the snapshot path and profile, the return shape, and *"report
conclusions with item keys, not item dumps."* Delegates stay read-only.

## Handoff

> Backlog `<scope>` — `<modes run>`. Snapshot `<path>` (`<n>` items, `<timestamp>`).
> Map: `<initiative>` — `<k>` activities, `<s>` slices; first slice: `<outcome>`.
> Refine: `<r>` of `<n>` items ready; `<k>` split; `<p>` spikes.
> Health: `<score>` (`<band>`), gate `<pass/fail>` — top findings `<IDs>`; WIP `<n>` (`<per person>`), unplanned `<x>%`, `<k>` follow-ups overdue.
> Order: top item `<key — title>` (`<class>`).
> Changes: `<a>` applied, `<f>` failed, `<s>` skipped — or "change set awaiting confirmation" — `<file>`.

Name anything left 🔬 and what data would settle it.
