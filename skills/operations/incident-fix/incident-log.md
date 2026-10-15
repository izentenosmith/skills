# The incident log

The one record every phase writes to, and the spine the post-mortem's timeline is built from. It is **append-only**: a mistaken entry is corrected by a later entry, never by editing. It is **durable**: committed (or in the tracker) at every phase gate.

## Timestamps come from the clock

Every entry's time is **read from the system clock at the moment of writing** — `date -u +%Y-%m-%dT%H:%M:%SZ`, or an incident log tool if one is available. Never type a time from memory, and never let the model estimate one. Under stress, times written afterwards drift toward a tidier story, and the post-mortem will measure detection and mitigation from these numbers.

**Events that happened before anyone was logging** — when impact actually started, when the triggering change merged — are recorded as `impact-start` or `change` entries stamped with **the time the evidence shows**, naming the evidence and when it was backfilled. Those two kinds are the only ones whose time may be earlier than the entry above them, and the only ones whose time isn't read from the clock.

## Format

```markdown
# Incident: <short title, in the system's own vocabulary>
- **Severity:** <SEV1 | SEV2 | SEV3> — <why>
- **Detected by:** <alert | monitoring | user report | engineer> — <the specific source>
- **Tracker:** <item id or link, or "none — this log is the record">
- **Status:** open

## Log
- 2026-10-15T14:07:00Z · detected · alert "orders 5xx > 5%" fired in <source>
- 2026-10-15T14:08:30Z · phase · contain
- 2026-10-15T14:09:12Z · evidence · saved worker logs 13:50–14:09 to <path> (secrets redacted)
- 2026-10-15T14:11:40Z · proposed · disable flag `new-checkout` — stops new orders on the faulty path; undo in ~1 min
- 2026-10-15T14:12:05Z · confirmed · user approved: disable flag `new-checkout`
- 2026-10-15T14:12:30Z · action[prod] · set `new-checkout=false` in production
- 2026-10-15T14:14:00Z · result · 5xx back to baseline (0.2%) within 90 s
- 2026-10-15T14:14:10Z · mitigated · user impact stopped
- 2026-10-15T14:20:00Z · phase · diagnose
- 2026-10-15T13:41:00Z · impact-start · first 5xx in the saved worker logs (backfilled 14:32)
- 2026-10-15T14:40:00Z · finding · 2,318 orders since 13:41 have a NULL tax total (query in <path>) — known
- …
- 2026-10-15T17:05:00Z · resolved · fix <sha> and repair <artifact> verified in production
- 2026-10-17T10:00:00Z · closed · tracker item closed; post-mortem at <link>

## Contributing factors
- **C1** <factor, as a property of the system> → follow-up: <id or link>, owner <who>, due <date>
- **C2** <factor> → accepted risk: <reason>, accepted by <who> on <date>
```

## Entry kinds

| Kind | When |
|---|---|
| `detected` | First entry: when and how someone knew |
| `impact-start`, `change` | Backfilled from evidence: when users were first affected; when the triggering change landed |
| `phase` | Entering `contain`, `diagnose`, `fix` or `learn`, in that order |
| `evidence` | Something captured or read — logs saved, a query run, a dashboard read |
| `finding` | A conclusion, marked **known** or **assumed** |
| `proposed` | A production action offered to the user: what it does, how it's undone |
| `confirmed` | The user's explicit approval of **one** proposed action |
| `action[prod]` | A production-affecting action taken. **Must follow its own `confirmed` entry** |
| `action` | Anything else done — a branch, a test, a staging deploy |
| `result` | What an action did, observed |
| `comms` | A stakeholder update drafted or sent |
| `severity` | A re-classification, with the reason |
| `mitigated`, `resolved`, `closed` | The three milestones, in that order |
| `note` | Anything else worth the timeline |

## Rules a reviewer — or a checker — can verify

- Times are UTC with a `Z`, and never decrease except on `impact-start` and `change` entries.
- `detected` comes first; phases run contain → diagnose → fix → learn.
- **Every `action[prod]` has a `confirmed` entry after the previous `action[prod]`.** One approval, one action.
- `mitigated` before `resolved` before `closed`.
- At `closed`, every contributing factor has either a follow-up (owner and due date) or an accepted risk (reason and who accepted it).
- Where **Detected by** is a user report, one follow-up or accepted risk addresses the missing alert or monitoring.
