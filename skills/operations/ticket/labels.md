# Labels — the canonical set

Labels (tags in Azure DevOps) are the cheapest structured data a tracker has, and the only one that cuts across types. Types are usually overloaded — a "Bug" type holds real outages next to cosmetic defects next to customer requests — so **metrics that need a clean population should select by label, not by type.**

These are the canonical names. The profile maps each to the label the team actually uses; where the team has none, propose the canonical one.

## Production incidents — the DORA labels

| Label | On | Meaning |
|---|---|---|
| `prod-incident` | Any item that represents a **failure in production**, whatever its type | The population for change failure rate and time to restore. Without it the failure is invisible to the metrics. |
| `caused-by-<deploy-id>` | An incident item, when the culprit deploy is **not** the default | Pins the deploy that caused it. The default culprit is the last production deploy before the incident started. |

Rules:

- **Open the item when the failure starts.** An item created after the fix records zero time between creation and closure, and any metric built on it is fiction.
- **Restore time is measured from the culprit deploy (or impact start), not from the item's creation date** — precisely because items are sometimes opened late.
- **Close it when service is restored**, using the date the tool actually populates on closure. Check which one that is before building a metric on it: some processes never set a "resolved" date at all.
- **A bug that never reached production is not a `prod-incident`.** Neither is a customer request filed as a bug.

## Cause, from the post-mortem

`cause:<category>` — one or more per incident, from the post-mortem's contributing factors. Keep the vocabulary small and stable so it can be counted over time:

`cause:deploy` · `cause:config` · `cause:data` · `cause:dependency` · `cause:capacity` · `cause:infrastructure` · `cause:security` · `cause:unknown`

Counting incidents by cause, and alerts per incident, over months is what turns individual post-mortems into a picture of where the system is weak (*Site Reliability Engineering*, ch. 16).

## Follow-ups

| Label | Meaning |
|---|---|
| `follow-up` | Work owed by a hotfix, an incident or a post-mortem |
| `action:mitigate` | Reduces the impact or duration of the next occurrence |
| `action:prevent` | Stops this class of failure from happening |
| `action:process` | Changes how the team detects, responds or reviews |
| `revert-containment` | Undoes a temporary production change made during an incident (a flag left off, a job paused, a limit lowered) — always has a due date |

## Flow

| Label | Meaning |
|---|---|
| `unplanned` | Work that arrived already in progress — an interruption, an emergency, a request that skipped the backlog. Labelling it is how a team shows why planned work slipped (DeGrandis, *Making Work Visible*). |
| `toil` | Manual, repetitive, automatable operational work with no lasting value — a data fix run by hand for the third time. Counting it is the first step to capping it. |
| `expedite` | Jumps the queue under the team's stated priority policy (production down, a hard legal date). If everything is expedite, nothing is. |

## Writing labels safely

- **Know whether the tool appends or replaces.** In some tools writing the label field adds to the existing set; in others it replaces it. A misspelled label written to an appending field can't be fixed by writing it again — the adapter says how to remove one.
- **Read back after every label write** and check the full set, not just that the new label is present.
- **Never invent a near-duplicate** (`prod_incident`, `production-incident`) — a metric that selects one misses the other. Use the profile's mapping.
