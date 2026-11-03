# Health checks — the rubric, by domain

> What Health mode grades. Four domains, each with the objects it counts, what good looks like, the
> anti-patterns (with how to detect them and their severity) and the checklist criteria scored in
> [scoring.md](scoring.md). Every finding names its principle from [theory.md](theory.md).
>
> Detection is written against the **snapshot** fields from Step 0 (state category, dates, type,
> labels, priority, parent, links, size), not a tracker's query language. The ticket adapters
> translate: WIQL for Azure DevOps, JQL for Jira, filters or GraphQL for Linear.
> "Incident label", "follow-up label", "unplanned label", "toil label" and "highest priority" mean
> whatever the ticket profile records for this team; where it records none, the check that needs it
> is 🔬.

---

## Domain 1 — structure (is there a whole story?)

**Objects:** open containers — epics, features, initiatives, releases, milestones, projects — plus,
for S1, every open standard item.

🟢 **Well done:** open work hangs off a small number of containers, each with a target user and a
measurable outcome; releases are named for what they achieve; ideas get decided; the backlog shrinks
as well as grows.

| ID | Anti-pattern | Detect | Conf. | Principle | Severity |
|---|---|---|---|---|---|
| BL-STR-01 | Flat backlog | Share of open standard items with no parent and no map placement > 50% | ✅ | B2 | Medium |
| BL-STR-02 | Container with no outcome | Epic/feature/release whose description has no target user and no measurable result | ⚠️ | B3 | Medium |
| BL-STR-03 | Release named by output | Release or milestone titles that are versions, phases or feature lists with no outcome in the description | ⚠️ | B3 | Low |
| BL-STR-04 | Undecided opportunities | Items in the opportunity/triage state or label for > 90 days with no decision recorded | ✅ | B10 | Medium |
| BL-STR-05 | Backlog that only grows | Open item count rising over the window while throughput is flat, and no won't-do closures | ✅ | B4 | Medium |
| BL-STR-06 | Ancient to-do | To-do items untouched for > 180 days | ✅ | B4, B16 | Low |
| BL-STR-07 | Duplicates | Open items with the same or near-same title and parent, or linked as duplicate but both open | ⚠️ | B4 | Low |
| BL-STR-08 | Split far ahead of need | Containers not in the next slice whose children are mostly task-sized | ⚠️ | B6 | Low |

**Checklist:**

| # | Criterion | p is the share of… |
|---|---|---|
| S1 | Open standard work sits under a container or map activity | open standard items with a parent or map placement |
| S2 | Containers state a target user and a measurable outcome | open containers |
| S3 | Opportunities older than 30 days have a decision | items in the opportunity state/label for > 30 days |
| S4 | To-do items have been touched in the last 180 days | to-do items |
| S5 | No open duplicates | open items not flagged in BL-STR-07 |

## Domain 2 — readiness (is the next work ready to build?)

**Objects:** the **ready zone** — items in the current and next sprint or cycle, or the top 20 of the
ordered backlog where there are no sprints. State which you used.

🟢 **Well done:** every item in the ready zone says who, what and why; has acceptance criteria and a
demo line; is small enough to finish in a couple of days or is an explicit, time-boxed spike; and
links whatever it depends on.

| ID | Anti-pattern | Detect | Conf. | Principle | Severity |
|---|---|---|---|---|---|
| BL-RDY-01 | No acceptance criteria | No acceptance-criteria field value and no criteria section in the description | ✅ | B9 | High when > 50% of the zone, else Medium |
| BL-RDY-02 | No who or why | Description empty, or names no user/beneficiary and no reason | ⚠️ | B1, B3 | Medium |
| BL-RDY-03 | Team-perspective story | "As a developer / product owner / the system…" with no end beneficiary | ✅ | B1 | Low |
| BL-RDY-04 | Oversized for delivery | Size above the team's few-days equivalent (from the profile or history), or no size and many children | ✅ / 🔬 | B6 | Medium |
| BL-RDY-05 | Layer or activity split | Siblings titled by layer or activity ("API for…", "UI for…", "test …") under one story | ⚠️ | B7 | Medium |
| BL-RDY-06 | Spike without a decision | Spike-type item with no question, no time box, or no decision it feeds | ⚠️ | B5 | Low |
| BL-RDY-07 | Hidden dependency | Item flagged blocked, or mentioning another team's work, with no link | ✅ / ⚠️ | B15 | Medium |
| BL-RDY-08 | No demo | Nothing says how it will be shown or verified at review | ⚠️ | B9 | Low |

**Checklist:**

| # | Criterion | p is the share of… |
|---|---|---|
| R1 | Acceptance criteria present | ready-zone items |
| R2 | Who / what / why stated | ready-zone items |
| R3 | Within delivery size, or an explicit spike | ready-zone items with a size (🔬 if none have one) |
| R4 | Split by behavior, not by layer | ready-zone stories with children |
| R5 | Spikes carry a question, a time box and the decision they feed | ready-zone spikes |
| R6 | Dependencies linked | ready-zone items that are blocked or depend on others |

## Domain 3 — flow (is the work moving?)

**Objects:** items in progress now, the in-progress states themselves, and items started or finished
in the window ([flow.md](flow.md)).

🟢 **Well done:** WIP is limited and the limits hold; nothing sits in progress far longer than the
team's usual cycle time; unplanned work is visible and measured; there is one top priority; blocked
work is linked to its blocker; plans leave slack.

| ID | Anti-pattern | Detect | Conf. | Principle | Severity |
|---|---|---|---|---|---|
| BL-FLO-01 | WIP overload | In-progress items > 2× the state's limit, or > 2 per active assignee with no limits set | ✅ | B13 | High |
| BL-FLO-02 | Queue pile-up | A waiting state (review, QA, validate, deploy) holding more items than the active states feeding it | ✅ | B13 | Medium |
| BL-FLO-03 | Aged in progress | In progress longer than 2× the median cycle time for its type | ✅ / 🔬 | B16 | Medium |
| BL-FLO-04 | Neglected in progress | In-progress items untouched for 30+ days | ✅ | B16 | Medium |
| BL-FLO-05 | Invisible unplanned work | Incidents exist (log, post-mortem, alerts) but no items are created in progress or carry an unplanned/incident label | ⚠️ | B12 | High |
| BL-FLO-06 | Competing top priorities | > 10% of open items at the highest priority, or more than one item or project claiming first | ✅ | B14 | High |
| BL-FLO-07 | Unlinked blocker | Blocked items with no link to what blocks them | ✅ | B15 | Medium |
| BL-FLO-08 | No slack | Committed sprint or cycle scope > 100% of the median throughput of recent ones | ✅ / 🔬 | B13, B17 | Medium |
| BL-FLO-09 | Unassigned work in progress | In-progress items with no assignee | ✅ | B12 | Low |
| BL-FLO-10 | Cadence work invisible | Known recurring deadlines (from docs or history) with no dated item ahead of them | ⚠️ | B17 | Medium |

**Checklist:**

| # | Criterion | p is the share of… |
|---|---|---|
| F1 | In-progress states within their WIP limit (or ≤ 1.5 per active person where no limits exist) | in-progress states |
| F2 | In-progress items younger than 2× median cycle time | in-progress items (🔬 if no history) |
| F3 | In-progress items touched in the last 30 days | in-progress items |
| F4 | Unplanned work is visible — graded 1.0 labeled and measured, 0.5 inferable from dates only, 0 invisible | the team (one object) |
| F5 | One top priority — graded 1.0 when ≤ 10% of open items sit at the highest priority and one item ranks first, else 0 | the team (one object) |
| F6 | Blocked items linked to their blocker | blocked items |
| F7 | Planned scope ≤ ~80–100% of recent throughput | recent sprints/cycles (🔬 without sprints) |

## Domain 4 — reliability (is operational work getting done?)

**Objects:** post-mortem follow-ups, incident items, reliability and toil items. N/A when the team
has no production system — say so and drop the domain.

🟢 **Well done:** every post-mortem action item is a tracked item with an owner, a type and a date,
linked to its incident, and gets done; incidents carry the team's incident label consistently; when
an error budget is spent, reliability work is ordered first; toil stays well under half the work and
repeated manual work has an automation item.

| ID | Anti-pattern | Detect | Conf. | Principle | Severity |
|---|---|---|---|---|---|
| BL-REL-01 | Abandoned safety follow-up | A prevent or mitigate follow-up from a data-loss, corruption or security incident with no owner, or past due | ✅ | B19 | **Critical** |
| BL-REL-02 | Overdue follow-up | Any other follow-up past its due date, or open > 60 days with no date | ✅ | B19 | High |
| BL-REL-03 | Untracked follow-up | A post-mortem or incident log in the repo lists follow-ups with no matching tracker item | ✅ | B19 | High |
| BL-REL-04 | Untagged incident | Items whose type or title marks a production failure without the team's incident label — invisible to incident and DORA metrics | ⚠️ | B12 | Medium |
| BL-REL-05 | Budget spent, features first | Error budget exhausted (from the SLO source) and feature items ordered above open reliability items | ✅ / 🔬 | B18 | High |
| BL-REL-06 | Toil-heavy | > 50% of items done in the window are manual operational work (toil label, or ⚠️ by type/title) | ✅ / ⚠️ | B20 | Medium |
| BL-REL-07 | Repeated manual fix | The same manual fix or data correction done three or more times with no automation item | ⚠️ | B20 | Medium |
| BL-REL-08 | Containment left in place | A follow-up or revert item for a temporary production change (flag, limit, paused job) that's past its date | ✅ | B19 | High |

**Checklist:**

| # | Criterion | p is the share of… |
|---|---|---|
| L1 | Follow-ups have an owner | open follow-ups |
| L2 | Follow-ups are within their due date | open follow-ups with a date; undated ones count as failing |
| L3 | Follow-ups are linked to their incident and typed (mitigate / prevent / process) | open follow-ups |
| L4 | Production failures carry the incident label | incident-like items in the window |
| L5 | Error-budget policy reflected in order — 1.0 honored or budget healthy, 0 ignored; N/A without an SLO | the team (one object) |
| L6 | Toil under half of completed work | the window (one object): 1.0 below 50%, 0.5 at 50–65%, 0 above |

## Coverage

Large backlogs (thousands of items): grade structure and readiness on the containers and the ready
zone, which are small; grade flow on everything in progress; signal-scan the rest with the snapshot
and state coverage. Never sample the reliability domain — read every follow-up and incident item.
