# Ordering — one top priority, by a stated policy

Ordering answers one question: **what should the team pull next?** It does so by an explicit policy
(B14), so the answer survives the next loud request. There is exactly one item at the top.

## 1. Classes of service first

Work doesn't all compete on value; some of it has rules. Sort into classes, then order within each:

| Class | What | Rule |
|---|---|---|
| **Expedite** | An open production incident or security exposure — items the ticket profile marks with the team's incident label | Goes first, may break WIP limits; there should rarely be more than one |
| **Error-budget freeze** | Reliability work, when an SLO's error budget is exhausted and the team has a freeze policy (B18) | Goes above all standard feature work until the budget recovers; feature work waits except urgent fixes |
| **Fixed date** | Hard-dated work: regulatory deadlines, contract dates, recurring cadence work (month-end, audits, certificate renewals) | Ordered by date minus the time it needs; made visible well before it's urgent (B17) |
| **Post-mortem follow-up** | Action items from incidents (B19) | Past-due items rank above standard work of similar value; a *prevent* item from a data-loss or security incident ranks near the top |
| **Standard** | Features, improvements, ordinary bugs | Ordered by outcome and cost of delay, below |
| **Maintenance and toil reduction** | Upkeep, upgrades, automation of repeated manual work (B20) | Not ordered against features — given a reserved share of capacity ([flow.md](flow.md)) |

Read the error-budget state and the team's incident and follow-up labels from the ticket profile and
from whatever the repo documents (an SLO doc, an error-budget policy). If there's no SLO, say so —
the freeze class is then empty, not guessed.

## 2. Standard work: outcomes, then users, then features

Following USM ch. 2 and ch. 14, decide in this order:

1. **Which business outcome matters most now?** Order the outcomes first. Items inherit their
   slice's outcome ([slicing.md](slicing.md)).
2. **Which users matter most for that outcome?**
3. **Which of their goals or activities matter most?** Activities that critical users do often come
   first.
4. **Only then, which items** serve those goals best, smallest first.

Tags that help the conversation (USM ch. 14): **table stakes** (must exist to compete at all),
**differentiator** (sets you apart), **spoiler** (neutralizes a competitor's differentiator),
**cost reducer** (saves money or time). A release that's all table stakes and no differentiator is a
finding worth mentioning.

## 3. Cost of delay, when value is close

When two items serve similar outcomes, ask what waiting costs — current practice, beyond the three
books:

- **Value** — what users or the business gain once it's done.
- **Time criticality** — does the value decay or disappear if it's late (a season, a contract, a
  competitor)?
- **Risk reduction or opportunity enablement** — does it retire a risk, or unlock other work?

Where sizes exist, divide cost of delay by size and pull the highest ratio first. Where they don't,
rank by cost of delay and say sizes were unavailable. **Never invent numbers for either** — a
qualitative high / medium / low with the reason is better than a fabricated score.

## 4. Adjustments

- **Bundle** low-priority bugs with higher-priority work in the same area (USM ch. 17).
- **Dependencies** (B15): an item blocked by another team ranks no higher than its blocker's
  expected date allows; raise it with that team instead of ranking it first.
- **Learning before earning** (B5): a spike that decides a large bet ranks above the bet.
- **Neglected items** (B16) surfaced by Health mode get a decision, not a quiet re-rank.

## 5. The output

Write `.workflow/backlog/order-<YYYY-MM-DD>.md`:

```markdown
# Backlog order — <scope> — <date>
> Policy: classes of service → outcomes → users → goals → items; cost of delay for ties.
> Source: <tracker, project/team, query> — snapshot <path>. Error budget: <state, or "no SLO">.

| Rank | Item | Class | Outcome / reason | Was |
|---:|---|---|---|---:|
| 1 | PRJ-311 Restore nightly export | Expedite | open incident | 14 |
| 2 | PRJ-298 Alert on failed export | Follow-up (prevent) | due 2026-11-10 | 40 |
| 3 | PRJ-205 Reorder by code | Standard | Slice 1 outcome | 3 |

## Proposed changes
<the rank/priority field updates, as a change set for ticket>

## Not ordered
<items with no outcome, no decision, or no information — each with what's missing>
```

The proposed rank or priority changes are applied through `ticket`, after confirmation. Trackers
store order differently — a rank field, a manual board order, a priority field, a sprint — and the
adapters say how ([../ticket/adapters/azure-devops.md](../ticket/adapters/azure-devops.md),
[../ticket/adapters/jira.md](../ticket/adapters/jira.md),
[../ticket/adapters/linear.md](../ticket/adapters/linear.md)). Where the tracker can only hold a
coarse priority, say so and keep the full order in the file.
