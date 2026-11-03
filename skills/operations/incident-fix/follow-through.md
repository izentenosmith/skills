# Follow-through — from contributing factors to owned work

The post-mortem **describes**; it does not prescribe, because a record written toward a conclusion gets shaped by it. Follow-through is the separate step that comes **after** the record is finished: for each contributing factor it names, someone decides what happens next, and the decision is written down.

Keeping the two apart is the point. The record stays honest because it isn't arguing for a fix, and the follow-through stays honest because it has to answer every factor — including the inconvenient ones.

## Every factor gets exactly one of two outcomes

| Outcome | Required | Example |
|---|---|---|
| **Follow-up** | An outcome stated as an observable property of the system · an action type · an owner · a due date · where it's tracked | "A batch job that writes fewer rows than it read fails the run" — prevent — owner: platform team — due 2026-11-01 — <tracker id> |
| **Accepted risk** | The reason it's acceptable · who accepted it · when to revisit | "The vendor API's silent truncation stays: two incidents in three years, and the workaround costs more" — accepted by <owner> on <date> — revisit if it recurs |

**"Noted" is not an outcome.** A factor with neither is how the next incident's post-mortem starts with "this was known."

## Rules

- [ ] **Every follow-up has an action type** — **mitigate** (the next occurrence hurts less or ends sooner), **prevent** (this class of failure can't happen), or **process** (detection, response or review changes). A set of follow-ups that is all *process* has usually not engaged with the system; one with no *mitigate* has assumed prevention will work every time.
- [ ] **Check for the knee-jerk item.** Right after an incident, follow-ups tend to be over-scoped — a rewrite, a new platform, an alert for this exact symptom. Prefer the smallest change that would have made the incident impossible or obvious: a test that pins the behavior often beats a bespoke alert (*Site Reliability Engineering*, appendix D).
- [ ] **Owners are people or teams who agreed**, not whoever was in the room. "Unassigned — needs an owner" said plainly beats a name somebody didn't accept.
- [ ] **The outcome is a property of the system**, not an instruction to people. "Engineers will be more careful with migrations" is not a follow-up; "a migration that rewrites more than N rows requires a dry-run artifact in review" is.
- [ ] **Detection gets its own line.** If a user or an engineer noticed before monitoring did, or detection took longer than mitigation, one follow-up adds the alert or monitoring that would have caught it — added directly where the repo owns it (a health check, an assertion, an alert rule in the repo), ticketed where it doesn't.
- [ ] **What went well gets protected.** If a canary, alert or runbook saved the day, a follow-up can be "keep it" — a test or a note that stops someone deleting it in a cleanup.
- [ ] **Alert noise is a factor too.** If responders were flooded — dozens of alerts for one problem, or the real signal buried in noise — a follow-up reduces it toward one alert per incident.
- [ ] **Containment left in place** — everything still on the state block's *Temporary changes* list (a flag still off, a job still paused, a limit still lowered, an alert still silenced) — is either undone now, or a follow-up with a date.
- [ ] **An exhausted error budget changes priorities.** Where the team has an error-budget policy and this incident spent the period's budget, the follow-through says what the policy now requires — typically reliability work ahead of features until the budget recovers — and the backlog is ordered accordingly ([backlog](../backlog/SKILL.md) where installed).
- [ ] **Create tracker items only after the user confirms**, with the team's labels — through [ticket](../ticket/SKILL.md) where installed, which reconciles against existing items first and reads every write back. Without a tracker, the follow-ups live in the incident log's **Contributing factors** section and are committed with it.

## Format, in the incident log

```markdown
## Contributing factors
- **C1** <factor, as in the post-mortem> → follow-up: <outcome> — <mitigate | prevent | process>, owner <who>, due <date>, <tracker id or "this log">
- **C2** <factor> → accepted risk: <reason> — accepted by <who> on <date>, revisit <when>
```
