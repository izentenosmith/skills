# Contributing factors

The reference behind [SKILL.md](SKILL.md) Step 4 — why "the root cause" is usually a fiction, how far to descend, and the categories to sweep.

---

## Why not "root cause"

The phrase carries three assumptions, and in a production system of any size all three are usually false:

1. **That there is one.** Real incidents are conjunctions. A latent bug, *and* a config that made it reachable, *and* a monitoring gap that let it run for forty minutes, *and* a runbook that pointed the responder at the wrong subsystem. Remove any one and the outage is smaller or doesn't happen.
2. **That it's a root.** The chain doesn't terminate; you stop when you run out of patience, access, or organizational comfort. Where you stop is a choice, and calling that stopping point "the root" disguises the choice as a discovery.
3. **That finding it is the job.** Naming one cause implies the others were acceptable — which leaves every one of them armed for the next incident.

There's a fourth, practical problem. **Single-cause analysis has a predictable endpoint: the last human action in the chain.** It's the most legible link, it's where the causal story feels complete, and it is how a review that fully intended to be blameless arrives at a person. Writing "contributing factors," plural, from the start structurally prevents that — you cannot stop at one.

**What to write instead:** a list of factors, each with evidence, each answering *"if this had been different, would the outcome have been better?"* — and, where it can be measured, *by how much*.

---

## The categories to sweep

Work all six. **Record "none found" explicitly** — an unexamined category is indistinguishable from a clean one in the finished document, and the categories people skip are reliably the last two.

### 1. The trigger

What started it. A deploy, a config change, a traffic shift, a dependency failure, a certificate expiry, a clock.

The trigger is the easiest factor to find and usually the least interesting. **Note it and keep going** — a postmortem that stops here produces "we reverted the deploy," which prevents nothing, since the next trigger will be a different one.

### 2. The latent condition

What made the trigger harmful. **This is usually the most valuable factor in the document.**

The unbounded query that had been there for eight months. The retry loop with no backoff. The connection pool sized for the old traffic level. The missing index that didn't matter at a tenth of the data. The assumption that a list would stay short.

Latent conditions are the reason "we reverted the change" isn't a fix: the condition is still there, and something else will meet it. The test: **if the same trigger happened again tomorrow, would it still hurt?** If yes, you've found a condition and not fixed it.

### 3. Detection

How long until a human knew, and how they found out.

**"A customer told us" is a finding every time**, regardless of how small the impact was — because it generalizes to every failure that looks like this one, most of which haven't happened yet. Same for "an engineer happened to be looking at a dashboard."

Sub-factors worth checking specifically: the alert didn't exist · it existed but the threshold was wrong · it fired into a channel nobody watches · it fired and was dismissed because that alert is usually noise · the metric existed but nothing alerted on it · the dashboard aggregated the signal away.

That second-to-last one — **an alert that is routinely ignored because it is usually wrong** — is a factor in a startling proportion of long-detection incidents, and it is a fixable property of the alert, not of the person who ignored it.

### 4. Response and tooling

What slowed down the fix once people knew. This is often where the most user impact actually accumulates, and it is under-examined because it feels like it's about people.

The runbook was missing, wrong, or described the previous architecture · the rollback wasn't possible because of a forward-only migration · the fix needed a permission the responder didn't have · the escalation path needed someone asleep in another timezone · the logs didn't contain the field needed to identify affected records · the dashboard couldn't break the metric down by the dimension that mattered.

Every one of these is a system property with a concrete fix.

### 5. Process

What allowed the state to exist. No staged rollout. No canary. Review not required for this class of change. Load testing that doesn't cover this shape. A test suite with no environment where the failure mode could be reproduced. A dependency upgraded without a compatibility check.

### 6. Organizational

The uncomfortable one, and the one most often skipped — which is exactly why repeat incidents happen.

The team owning this system has no capacity for reliability work. The service has no clear owner since a reorg. A known risk was raised and deprioritized twice. The on-call rotation is one person deep. **What a prior postmortem described was never carried out.**

**If this incident is a repeat, category 6 is where its explanation lives**, and skipping it guarantees a third occurrence. It is legitimate to write "this was raised in the March postmortem and not prioritized" — that is a factual finding about the system, and suppressing it is how the same outage arrives every quarter with a well-written document attached.

---

## How far to descend

"Five whys" is a useful prompt and a bad rule. Two failure modes, both common:

**Stopping too early** leaves you at the trigger. *Why did the service go down? The deploy broke it. Fix: revert.* Nothing learned; the latent condition survives.

**Descending too far** arrives at something nobody could act on. *…because the company prioritized growth over reliability, because the market demanded it.* Possibly true, and it names nothing anyone can check or change.

There's also a structural flaw in the technique: **asking "why" five times traces a single chain**, and real incidents are trees. Use it to explore a branch, not to structure the analysis.

### The stopping test

> **Stop at the first point where the factor names something specific and checkable about the system.**

Then check that point against three questions:

1. **Is it concrete enough to check?** Could someone go and verify whether it is still true today? "The deploy tool has no staged rollout" is checkable. "Communication was poor" is not, and it is where analysis goes to stop.
2. **Does it generalize past this incident?** "This query had no `LIMIT`" is the instance. "There is no `statement_timeout` on the primary, so any unbounded query can take the database down" is the class — and the class statement is the one that describes the failures nobody has imagined yet.
3. **Does it stop at a person?** If the answer is "because the engineer didn't know," you are one level short. **That is a pointer to the system that was supposed to tell them** — the runbook, the alert, the onboarding, the interface. Descend one more and you'll have something buildable.

That third check does most of the work, and it is the one that keeps the analysis honest without requiring anyone to be diplomatic.

---

## Trigger vs. condition

Worth stating explicitly per factor, because conflating them is how postmortems produce fixes that don't hold.

| | Trigger | Condition |
|---|---|---|
| Deploy at 14:02 | ✓ | |
| Query with no `LIMIT`, present since January | | ✓ |
| Traffic spike from a marketing email | ✓ | |
| Connection pool sized in 2023 | | ✓ |
| Certificate expired | ✓ | |
| No alert on certificate expiry | | ✓ |

**Triggers are specific to one incident; conditions outlive them.** A record that names only the trigger describes the instance and misses everything that made it matter — and reads, wrongly, as though reverting the change was sufficient.

The clean framing for the document: *"The deploy triggered it. It was harmful because \<condition\>, and it lasted 40 minutes because \<detection factor\>."* Three factors, independently true, each one separately sufficient to have changed the outcome.

---

## Recording a factor

Evidence, mechanism, counterfactual. In one block:

```markdown
**CF-3: No alert on replication lag** (detection)
- **Evidence:** lag crossed 30s at 13:47 [metrics]; first human
  awareness 14:31 via a customer report [#support 14:31]
- **Mechanism:** lag is graphed on the database dashboard but no
  alert is configured on it; nothing paged.
- **If this had been different:** detection at ~13:50 instead of
  14:31 — roughly 40 of the 52 minutes of impact.
- **Confidence:** high — the metric history and the support ticket
  timestamp both survive.
```

Four things this block does that a prose paragraph doesn't: the evidence is **cited**, the mechanism is **specific**, the counterfactual is **quantified**, and the confidence is **stated**. The quantified counterfactual is the most useful line in the document for whoever later decides what to change — it is the only thing that lets one factor be weighed against another — and it is a measurement of what happened, not a recommendation.

**Mark confidence where it's not certain.** "Probable — the timing matches but we have no direct evidence" is honest and useful. A hypothesis presented flat, alongside sourced facts, gets read as one — and then gets cited as established fact by someone who wasn't there, which can send a quarter of effort at the wrong thing.

---

## Contributing factors that are absences

Roughly half of all factors are things that **weren't there**, and absences are harder to see than events because nothing in the log marks them.

No canary. No alert. No runbook. No rollback path. No rate limit. No timeout. No circuit breaker. No validation on the input. No confirmation on the destructive action. No second person in the rotation.

The prompt that surfaces them: **what would have caught this, and why wasn't it there?**

The second half of that question matters. Often the answer is "nobody thought of it," which is fine and normal. But sometimes it's "it was there and was removed," or "it was proposed and deprioritized," or "it exists for the other three services and not this one" — and each of those is a much more interesting finding, pointing at a process or organizational factor sitting underneath the technical one.
