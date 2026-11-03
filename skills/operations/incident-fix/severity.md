# Severity — is this an incident, and how bad

Classify once, in Step 0, and say why in one line. **When torn between two levels, pick the higher one**: downgrading later costs a sentence, while under-reacting costs the minutes containment was supposed to save.

## Incident or hotfix?

| Signal | incident-fix | hotfix |
|---|---|---|
| Availability | Down, or degraded for a meaningful share of users | Up; one feature misbehaves |
| Data | Being corrupted, lost or exposed **now**, or already corrupted at scale | Displayed wrong but stored right; or a write bug not yet triggered in production |
| Money and business figures | Wrong amounts charged, paid, invoiced or reported | A cosmetic or rounding display issue with no stored effect |
| Security | Any exposure — leaked credential, data visible across a boundary, an auth bypass reachable from outside | A hardening gap with no known exposure (still: strict mode) |
| Trend | Getting worse while you watch | Stable |
| Cause | A hotfix revealed a systemic cause — the same defect in many places, a missing guard, a design flaw | Local and understood |

**Any one row in the left column makes it an incident.** If none applies, hand it to [hotfix](../hotfix/SKILL.md), and say so.

## Declare early

Three more signals make it an incident even when the table above is borderline (*Site Reliability Engineering*, ch. 14):

- **A second team is needed** to fix it, or to contain it.
- **Customers can see a degradation** that's broader than one misbehaving feature — slowness, errors or missing data across a flow they depend on.
- **It's still unsolved after an hour** of focused work.

Declaring is cheap — a log, a commander, an update cadence — and it can be undone in a sentence. Not declaring is what turns a contained problem into a long, uncoordinated one.

## Severity levels

Use the team's own scale where the repo or tracker shows one. Otherwise:

| Level | What it means | Error budget, where there's an SLO | Containment target | Post-mortem |
|---|---|---|---|---|
| **SEV1** | Down for most users; data loss or corruption spreading; active security exposure; money moving wrongly | Burning a month's budget in hours | Minutes — contain before anything else | Deep |
| **SEV2** | Major feature down or badly degraded; corruption bounded but real; wrong figures reported | Likely to spend a large share of the month's budget | Within the hour | Standard |
| **SEV3** | Minor degradation with a workaround; a small, bounded set of wrong records; a systemic cause found behind a hotfix | A small, bounded share | Same day | Lightweight |

## When the service has an SLO

If the repo or its monitoring defines a service level objective, **state the impact as a share of the error budget** as well as in users and records — it's the one unit that's comparable across incidents and that the team has already agreed on. The budget is what the objective allows to fail: at 99.9% availability over 30 days that's 43.2 minutes of full outage, or the equivalent share of failed requests. For a partial outage, count failed requests against total requests rather than minutes — a 10% error rate for an hour spends the same budget as a full outage for six minutes.

If the incident has spent the period's budget, say so in the log: the team's error-budget policy — where one exists — usually changes what gets worked on next, and the follow-through will need it.

## Re-classify as you learn

Severity is a judgment from the evidence you had at the time. When Phase 2 shows the impact is larger — or smaller — change it, log the change with the reason, and update the stakeholder note. **Never quietly downgrade**: the post-mortem reads the log, and a severity that drifted without a reason looks like the incident was managed to a number.
