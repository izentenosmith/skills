# The document — shape and metadata

One incident's record is a story; fifty records are data. The prose sections make this incident legible, and the **metadata block** makes it countable: incidents per month by cause, time to detect trending up or down, how many were found by a person before an alert (*Site Reliability Engineering*, ch. 15–16). Keep the block's fields and vocabulary identical across records — a field that's named differently in every document can't be aggregated.

## Metadata block

```markdown
# Postmortem: <short title, in the system's own vocabulary>

| Field | Value |
|---|---|
| **Incident** | <id — tracker item or incident log path> |
| **Status** | draft · reviewed · published |
| **Severity** | <SEV1 / SEV2 / SEV3, or the team's scale> |
| **Depth** | Lightweight · Standard · Deep — <why it earned a postmortem> |
| **Services affected** | <names, as the system calls them> |
| **Timezone** | UTC |
| **Change** | <timestamp> — <the triggering change, with its commit or deploy id> |
| **Impact start** | <timestamp> |
| **Detected** | <timestamp> — <alert · monitoring · user report · engineer> |
| **Mitigated** | <timestamp> |
| **Resolved** | <timestamp> |
| **Time to detect** | <impact start → detected> |
| **Time to mitigate** | <detected → mitigated> |
| **Time to resolve** | <impact start → resolved> |
| **Impact** | <who and how many, as a fraction; failed requests or records> |
| **Error budget** | <share of the period's budget consumed, or "no SLO defined"> |
| **Cause labels** | <cause:deploy, cause:data, … — the same vocabulary as the tracker> |
| **Related incidents** | <links to earlier records, or "none found"> |
| **Authors / reviewers** | <roles or names> |
```

Times are absolute, with the timezone stated once. A duration that can't be computed because a timestamp is unknown says so — `unknown (no logs before 14:00)` — rather than being left blank.

## Sections

In this order, matching the skill's steps:

1. **Summary** — three or four sentences a stakeholder can read alone: what happened, to whom, for how long, and that it's resolved.
2. **Timeline** — sourced entries, dead ends included, contradictions recorded (Step 2).
3. **Impact** — the numbers, and what was still outstanding at resolution (Step 3).
4. **Detection and response** — time to detect and mitigate, what slowed it, what sped it up (Step 4).
5. **Contributing factors** — plural, every category swept, each with evidence and confidence (Step 5).
6. **What went well · where we got lucky** (Step 6).
7. **What was done** — mitigation, fix, cleanup, anything left in place (Step 7).
8. **Open questions** — what the evidence couldn't settle.

There is deliberately **no action-items section.** Follow-ups are decided after the record, by whoever owns the system, and tracked in the tracker or the incident log — incident-fix's follow-through step does exactly that. A link from the record to where the follow-ups live is fine; the follow-ups themselves are not part of the reconstruction.
