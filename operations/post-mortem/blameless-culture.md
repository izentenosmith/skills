# Blameless culture

The reference behind [SKILL.md](SKILL.md) Step 7 and its Rules of Engagement.

Synthesized from the postmortem-culture material in *Site Reliability Engineering: How Google Runs Production Systems* (Beyer, Jones, Petoff & Murphy, O'Reilly, 2016) and *The Postmortem Playbook: Root Cause, Follow Through, and Reliability*. The examples and phrasing below are original.

---

## What blameless actually means

**Blameless is not "be nice." It is a data-collection strategy.**

The argument is mechanical, not moral. A postmortem's value is entirely a function of how much accurate information reaches it. Most of that information exists only in the heads of the people who were closest to the failure — what they believed, what the dashboard showed them, which hypothesis they chased first, what the runbook said, what they half-noticed and dismissed.

A person who expects to be blamed reports less. Not by lying — by omitting, by hedging, by declining to volunteer the detail that makes them look slow. Each omission is a contributing factor that stays in place.

So the causality runs: **blame → less information → a worse model of the failure → the same failure again.** An organization that punishes the person who typed the command gets safer-sounding reviews and less reliable systems, and the two are the same phenomenon.

**What blameless does not mean:** it doesn't mean nobody is accountable, that performance is never managed, or that a deliberate policy violation is treated as a system property. It means that in *this document*, about *this incident*, the question is what in the system allowed the outcome — not who to hold responsible for it. Accountability for fixing what's found is real and is assigned in Step 6.

---

## The core premise

**People act reasonably given the information they have at the time.**

This is not generosity, it is usually literally true. An engineer who took down a service made a decision that seemed correct against the dashboard in front of them, the runbook they had, the alert that fired, and the pressure they were under. When you know the outcome, the decision looks obviously wrong. That is hindsight bias, and it is not a weakness of careless reviewers — it is what knowing the answer does to everyone.

The productive question is therefore never *why did they do that?* but:

> **What made that the reasonable action at the time?**

Which turns into findings that generalize: the dashboard aggregated away the signal · the runbook described the previous architecture · the alert named a symptom with three unrelated causes · the confirmation prompt for the destructive path looked identical to the safe one.

Those are fixable. "They should have checked" is not.

---

## Hindsight bias, specifically

Three effects, all of which corrupt a postmortem written by people who know the ending:

1. **The outcome looks foreseeable.** Once you know a config change caused an outage, the risk seems obvious. At the time it was one of forty routine changes that week, thirty-nine of which were fine.
2. **The signal looks clear.** In review, the metric that spiked is unmistakable — because you know which of the two hundred metrics to look at. At the time it was one line on one of many dashboards.
3. **The path looks shorter.** A three-hour response reads as a series of steps where two were wrong. At the time it was fog, with several plausible hypotheses and no way to rank them.

**The countermeasure is structural, not attitudinal:** build the timeline so that *what was known* is recorded separately from *what was true* (SKILL.md Step 1). Once those two columns are distinct, most hindsight statements become visibly unsupportable — you can see that the fact was not available.

---

## The language patterns that leak blame

Blame almost never enters as an accusation. It enters through grammar, in documents written by people sincerely trying to be fair. This is the catalog for the Step 7 pass.

### Counterfactuals

The largest category. **A counterfactual describes a world that did not happen and explains nothing about the one that did.**

| Blameful | Blameless |
|---|---|
| "The engineer should have checked replication lag before failing over." | "Replication lag was not on the failover runbook's checklist and was not shown on the failover dashboard." |
| "The team failed to notice the error rate climbing." | "The error-rate alert was configured at 5%; the incident peaked at 4.2% and never fired." |
| "QA didn't catch this." | "The test suite has no case covering a multi-tenant boundary, and no environment where one could run." |
| "He forgot to drain connections first." | "The deploy script does not drain connections, and nothing in the process requires it as a separate step." |

Notice what happens to each rewrite: **it becomes something you can build.** The blameful version supports only the instruction "be more careful," which is not an engineering control and has never prevented anything.

**Scan for:** *should have · could have · failed to · neglected to · forgot to · didn't notice · overlooked · missed.*

### Names attached to errors

Names attached to **actions** are fine and often necessary: "Priya rolled back at 14:22." Names attached to **mistakes** are the problem: "Priya's change broke the index."

Prefer the role when describing anything that went wrong — "the on-call engineer," "the deploying engineer." Not to obscure who it was (everyone knows) but because the document is read by people who weren't there, and it becomes the record. A name next to a failure in a permanent document is a lasting cost to that person and a lesson to every reader about what candor gets you.

### "Human error" as a contributing factor

**Never a finding. Always a signal that the analysis stopped one step early.**

If a human action caused an outage, the questions that follow are the actual findings:

- Why was a single human action sufficient to cause it? (no staged rollout, no canary, no review gate)
- What did the interface show at that moment? (a dangerous action indistinguishable from a safe one)
- What was the guard? (none, or one that was easy to skip)
- Why was the mistake undetectable until impact? (no validation, no dry run, no confirmation of scope)
- How long had this been possible? (usually: a long time, and this was the first time anyone rolled the dice badly)

Every one of those is about the system, and every one is fixable. "Human error" is where those five questions were supposed to go.

### Hindsight markers

*Obviously · clearly · simply · of course · trivially.*

If it had been obvious at the time, it would not have happened. These words are the most reliable tell that a timeline has been reconstructed with knowledge nobody had, and they also quietly insult everyone who was in the fog.

### Passive voice hiding a system

Passive voice is usually fine here and often correct. But watch for the form that hides a missing mechanism: "the change was deployed without review" invites the reader to supply the villain. "The deploy pipeline does not require review for config-only changes" names the mechanism, which is what you can change.

---

## The practical test

> **Would the person closest to the triggering change read this document and recognize it as fair?**

If not, fix the document. The cost of getting this wrong is not that one person feels bad — it's that everyone who reads it learns that the safe strategy is to volunteer less, and every subsequent review is conducted with less information.

A stronger version of the same test, from practice: **would that person be willing to present this postmortem themselves?** In healthy organizations they usually do, and it is a good signal precisely because it is only possible when the document is genuinely about the system.

---

## What sustains it

Blameless culture is a set of habits, and it decays without them:

- **Leaders go first.** The fastest way to establish it is a senior person running a blameless review of their own mistake. The fastest way to destroy it is one blameful review after a visible outage — everyone updates immediately, and trust rebuilds far more slowly than it breaks.
- **Review near misses too.** Only reviewing damage tells people the trigger is consequence, not learning. Near misses are also where candor is cheapest, which makes them good practice for the expensive ones.
- **Publish beyond the responders.** A postmortem read only by the team involved has taught the organization nothing, and the failure modes described are rarely unique to one team.
- **Something has to come of them.** This is the one that actually decides whether the practice survives. People stop contributing to a process whose output is a document that changes nothing — and they are right to. That follow-through is not this skill's job (see [SKILL.md](SKILL.md) — *What this skill does not do*), but the record is what whoever owns it acts on, so it has to be good enough to act on.
- **No postmortem count in performance reviews.** The moment involvement becomes a liability, the incentive inverts completely: people route around declaring incidents.

---

## The honest limits

Blamelessness is not unconditional, and pretending otherwise makes it easy to dismiss:

- **Deliberate policy violation is a different conversation.** Someone who knowingly bypassed a control for convenience is not a system-design finding. Handle it separately, through a different process — and still write the blameless postmortem about why the control was bypassable and why bypassing it was faster.
- **Repeated identical incidents point at a management problem**, not a new technical one. The finding is that what the previous record described was never carried out, and the question is why it lost prioritization every quarter. That is still blameless and still about the system — the system in question is the planning process. Record it as a contributing factor; deciding what to do about it is someone else's call.
- **Blameless does not mean consequence-free for the organization.** Real remediation costs real engineering time, and "we accept this risk" is a legitimate answer only when it is written down and someone with authority owns it. A record that makes the risk legible has done its part of that.

---

## Sources

- Beyer, Jones, Petoff & Murphy, *Site Reliability Engineering: How Google Runs Production Systems* (O'Reilly, 2016) — chapters on postmortem culture and learning from failure. Free to read at [sre.google/books](https://sre.google/books/).
- *The Postmortem Playbook: Root Cause, Follow Through, and Reliability* — on moving past performative reviews to durable change.
- Dekker, *The Field Guide to Understanding 'Human Error'* — the source of the "human error is the start of the investigation, not its conclusion" framing that underlies the section above.
