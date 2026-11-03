# Containment levers — ranked, reversible, and undone in steps

Containment stops the damage without needing to understand it. The levers below are the ones worth checking for; [discovery.md](discovery.md) finds which of them this system actually has. Every one is a production action: proposed with what it stops, what it costs and how it's undone, confirmed, taken, verified, logged — and added to the state block's *Temporary changes* list.

## The general order

1. **Undo the change** — roll back the deploy, revert the config, flip the flag back. Most incidents follow a change, and undoing it is the lever with the best-known outcome. Check first that nothing forward-only (a migration, a data format) shipped since.
2. **Switch the failing part off** — disable the feature, pause the job, stop the consumer — when users can live without it for a while.
3. **Route around it** — drain traffic to healthy instances or a healthy region; fail over.
4. **Degrade on purpose** — serve cached or partial results, turn off expensive features, go read-only.
5. **Add capacity** — only when the system is short of capacity and isn't in a feedback loop (below).
6. **Ship a fix** — last, because it's new, untested code going into a system that's already failing.

**A security exposure** puts revoke and rotate at the top. **Data being corrupted** puts stopping the writer at the top — the job, the endpoint, the consumer — before anything else.

## Overload and cascading failure

When a system is overloaded, failures feed on themselves: slow responses cause client retries, retries add load, overloaded instances fail health checks and get restarted, and their traffic lands on the survivors, which then fail too. Adding capacity into that loop often doesn't help — new instances are overwhelmed as they start (*Site Reliability Engineering*, ch. 22). The levers, roughly in order:

| Lever | What it does | Watch for |
|---|---|---|
| **Shed load hard** | Reject a large share of requests — down to a small fraction if needed — so the remaining ones succeed | Users see errors; prefer shedding the cheapest-to-retry traffic |
| **Stop retries and batch load** | Turn off retry storms, background jobs, report generation, imports | Queues that grow while paused |
| **Block the trigger** | Drop the specific request, tenant or input that is causing the expensive work ("query of death") | Make sure it's the cause, not a symptom |
| **Stop health checks from killing instances** | Relax liveness checks so busy-but-working instances aren't restarted into a cold start | Re-tighten afterwards |
| **Enter degraded mode** | Serve stale cache, disable expensive features | What users see |
| **Restart carefully** | One instance or zone at a time, watching each | A full restart can fail all at once |
| **Then add capacity** | Once the loop is broken | Start-up time; cold caches |

## Undoing containment — a stepped ramp

Containment comes off the way a risky deploy goes on: **in steps, watching each one.** Turning everything back on at once re-creates the conditions of the incident with full traffic and cold caches.

- **Traffic and load:** ramp back up in stages — for example 1% → 10% → 50% → 100% — holding at each step long enough to see the error rate and latency settle.
- **Flags:** re-enable for a fraction of users, an internal group, or one tenant first.
- **Paused jobs:** resume on a slice of the backlog, check the output, then the rest. A queue that grew while the job was paused is itself a load spike.
- **Relaxed limits and silenced alerts:** restore them explicitly. A silenced alert left silenced is a detection gap for the next incident.

Each step is confirmed, logged, and struck from the *Temporary changes* list. Anything not undone by the time the incident is resolved becomes a follow-up with a date ([follow-through.md](follow-through.md)).
