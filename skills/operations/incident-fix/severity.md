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

## Severity levels

Use the team's own scale where the repo or tracker shows one. Otherwise:

| Level | What it means | Containment target | Post-mortem |
|---|---|---|---|
| **SEV1** | Down for most users; data loss or corruption spreading; active security exposure; money moving wrongly | Minutes — contain before anything else | Deep |
| **SEV2** | Major feature down or badly degraded; corruption bounded but real; wrong figures reported | Within the hour | Standard |
| **SEV3** | Minor degradation with a workaround; a small, bounded set of wrong records; a systemic cause found behind a hotfix | Same day | Lightweight |

## Re-classify as you learn

Severity is a judgment from the evidence you had at the time. When Phase 2 shows the impact is larger — or smaller — change it, log the change with the reason, and update the stakeholder note. **Never quietly downgrade**: the post-mortem reads the log, and a severity that drifted without a reason looks like the incident was managed to a number.
