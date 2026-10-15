---
name: post-mortem
description: Reconstruct a resolved incident into a blameless written record — timeline built from a git history date range plus incident docs, PDFs and logs, quantified impact, and contributing factors rather than a single root cause. Use after an incident is already over and fixed. Documents what happened; it does not plan remediation or propose what to build next.
---

# 🔦 Post-Mortem

## Where this fits

This runs **after the incident is over and already resolved**. It is a reconstruction, not a response and not a plan.

It leans on three reference docs:

- [evidence-sources.md](evidence-sources.md) — reading a git history range, incident docs and PDFs, chat exports and monitoring into a sourced timeline
- [blameless-culture.md](blameless-culture.md) — what blameless actually means, why it is a data-collection strategy rather than a kindness, and the language patterns that break it
- [contributing-factors.md](contributing-factors.md) — why "the root cause" is usually a fiction, and what to look for instead

## What this skill does not do

**It does not propose remediation, assign work, or recommend what to build.** The incident is solved and the fix already shipped; this document's job is to make what happened legible and accurate.

That boundary is what keeps the record trustworthy. A document that reconstructs *and* prescribes has an incentive to shape the reconstruction toward the prescription — factors supporting the proposed fix get written up carefully, factors that don't get a sentence. So the test that replaces "what should we do" is: **is this record complete and honest enough that whoever owns the system can decide well from it?** Every factor carries its evidence and its quantified effect precisely so that judgment can happen downstream.

Two failure modes bracket the work. **The blameful record** finds a person, and teaches everyone watching to volunteer less — removing exactly the information the next reconstruction needs. **The vague record** is written from memory and hedges everything: it neither settles what happened nor supports a decision.

## 📐 Step 0: Scope the reconstruction

**Record why this incident earned a postmortem.** Someone has already decided it did, so this is a line in the document rather than a gate — and it matters because reconstructions that "felt warranted" get selected by how visible or embarrassing an incident was. Writing the reason down is what makes that bias visible over time.

Name which applies: user-visible impact past a threshold · **data loss, corruption or disclosure of any amount** · manual intervention needed to restore service · resolution slower than target · **monitoring didn't catch it — a customer or an engineer did** · a **near miss** caught by luck · someone asked.

Two of those are routinely under-triggered. **"A human noticed first" is a finding about the system** regardless of how small the impact was. And **near misses are the cheapest incidents you will ever learn from** — the lesson without the outage — so a practice that reviews only actual damage discards most of its available information. If none of them fit, say so and write the Lightweight version.

**Then calibrate the depth**, and say which you picked:

| Tier | The incident | Produce |
|---|---|---|
| **Lightweight** | Short, contained, well-understood; near misses | Timeline, impact, factors, what was done. One page, circulated for correction. |
| **Standard** | Real user impact, multiple factors, some uncertainty | The full document, circulated to everyone involved for correction before publishing. |
| **Deep** | Data loss, security, a repeat, or anything that surprised people | The above, plus **what the previous record got wrong or left out**, plus the class rather than the instance. |

**A repeat incident is automatically Deep**, and its first question is about the previous postmortem rather than this outage: a recurrence means the last model was wrong or what it described was never carried out, and establishing which is worth more than re-describing the instance. Where the previous record is missing or inaccessible, that is itself the finding.

## 📥 Step 1: Gather the inputs

A **git history over a date range** and **whatever incident documentation exists**. [evidence-sources.md](evidence-sources.md) covers reading each; the rules that change the outcome:

- [ ] **Confirm the date range out loud** — `2026-08-03 14:00 UTC → 2026-08-04 09:00 UTC` — and **open it wider than the incident window.** The triggering change frequently merged days earlier and a latent condition can be months old. **If the range turns up nothing but the fix, the range is wrong, not the history.**
- [ ] **Read the repository history over that range.** Deploys, config changes, migrations, reverts and the fix all carry machine-generated timestamps nobody reconstructed under stress — the **best-dated source you have**.
- [ ] **Read every incident document in full before writing anything.** A timeline assembled while reading the first document gets anchored to that document's framing.
- [ ] **Note what is missing** — no chat export, no metric retention past 14 days, no logs from the replaced host. Missing evidence bounds what every later claim can assert.
- [ ] **State the timezone convention once** and normalize to it. Mixed timezones produce ordering errors that survive review because nothing looks wrong.

**Treat every input as a source to cite, not a narrative to adopt.** An incident report written during the event is evidence of what people *believed* — valuable, and not the same as what was true. A vendor PDF is that vendor's account. Both enter with a source tag; neither becomes the document's voice.

## 🕰️ Step 2: Build the timeline

The timeline is the spine — everything downstream is a claim about it, so it gets built from **artifacts, not recollection**. Memory reorders under stress with complete confidence, and not randomly: it rearranges into a story that makes sense in hindsight, which is the exact distortion this is resisting.

Source reliability runs roughly: git and deploy logs · monitoring and alerts · application logs · timestamped chat · documents written during the event · **then** recollection, always marked as such.

- [ ] **Absolute timestamps with a timezone**, consistently.
- [ ] **Record these five moments explicitly** — the intervals between them are what Steps 3 and 4 measure:
  - **Change** — when the triggering change was made. Often long before anything is noticed, and usually found in the git history rather than anywhere else
  - **Impact start** — when users were first affected, which is rarely when anyone knew
  - **Detection** — when a human first knew, and **how they found out**
  - **Mitigation** — when user impact stopped, usually before the fix
  - **Resolution** — when the system was fully correct again
- [ ] **Include the dead ends.** The hypothesis pursued for twenty minutes and abandoned is the clearest evidence you have about what the system's signals were telling people; cutting it makes the response look more orderly than it was.
- [ ] **Tag every entry's source** — `[git 3f2a1c]`, `[alert]`, `[#incident 14:22]`, `[incident report p.3]`, `[recollection — unconfirmed]`. That last tag matters: an unconfirmed memory presented flat, alongside sourced facts, will be read as one.
- [ ] **Record contradictions rather than resolving them silently.** When the chat says 14:20 and the alert history says 14:07, both go in with a note. Picking the tidier number discards a real finding — frequently about a delayed or misrouted alert.
- [ ] **Note what people believed at each point, separately from what was true.** The response is only explicable through the information available at the time, and reconstructing a timeline as if everyone knew what you now know is the mechanism by which a blameless intent still produces a blameful document ([blameless-culture.md](blameless-culture.md)).

## 📊 Step 3: Quantify the impact

Numbers, or an explicit statement that a number is unavailable and why. "Significant impact" cannot be compared against the next incident and cannot be checked.

- [ ] **Duration** of user impact — impact start to mitigation, not to resolution
- [ ] **Who and how many** — as a fraction of the whole, not just a count
- [ ] **What they experienced** — errors, slowness, wrong data, silent failure. **Wrong data is the worst case** and the easiest to under-report, because unlike an outage it does not announce itself
- [ ] **Business effect** where it is real and known — failed transactions, missed SLA, error budget consumed
- [ ] **Internal cost** — responder hours, work displaced. Frequently larger than the user-facing cost and almost always omitted
- [ ] **What was still outstanding at resolution** — data corrected late or not at all, customers notified late, a workaround left running. **A record that closes over an unresolved remainder is how the remainder gets forgotten**

## ⏱️ Step 4: Detection and response

Separate from the cause, and frequently the more interesting half.

- [ ] **Time to detect** — impact start → detection. **If a human noticed before monitoring did, that is a finding**, and one of the most generalizable available: it holds for every future failure that looks like this one.
- [ ] **Time to mitigate** — detection → impact stopped.
- [ ] **What slowed it down?** Concrete: an alert into a channel nobody watches, a runbook describing the previous architecture, a dashboard that didn't cover this, an escalation needing someone asleep, a rollback blocked by a forward-only migration.
- [ ] **What sped it up?** Step 6 covers it, and it is the half that gets cut when time is short.

## 🧩 Step 5: Contributing factors — plural, by construction

**Write "contributing factors," never "the root cause."** Not a wording preference: real incidents are conjunctions — a latent bug, plus a config that made it reachable, plus a monitoring gap that let it run, plus a runbook that sent the responder the wrong way. Naming one of those "the" root cause implies the others were fine. It also has a predictable endpoint — the last human action in the chain — which is how a reconstruction that intended to be blameless arrives at a person anyway.

[contributing-factors.md](contributing-factors.md) carries the categories, the limits of "five whys," and the recording format. Working the list:

- [ ] **Sweep every category** — trigger · latent condition · detection · response and tooling · process · organizational. **Record "none found" per category**, because an unexamined category is indistinguishable from a clean one, and the ones people skip are the last two.
- [ ] **Stop descending where the factor names something concrete and checkable about the system.** "Because the engineer didn't know" is not a stopping point — it's a pointer to the system that was supposed to tell them. "The deploy tool has no staged rollout" is.
- [ ] **Every factor carries its evidence** from the timeline, and its confidence. A factor without a timestamp or an artifact behind it is a hypothesis and says so.
- [ ] **Quantify the counterfactual where you can** — "detection at ~13:50 instead of 14:31 would have removed roughly 40 of the 52 minutes." This is the most useful line the document produces for whoever later decides what to change, and it is a **measurement of what happened**, not a recommendation.
- [ ] **Distinguish trigger from condition.** The deploy triggered it; the unbounded query had been latent for eight months. A record naming only the trigger describes the instance, misses the class, and reads as though reverting was sufficient.

## ✅ Step 6: What went well, and where you got lucky

Not a morale section. Two concrete jobs, and skipping it is why review practice erodes:

- [ ] **What worked, and is load-bearing.** A canary that caught it, an alert that fired correctly, a clean rollback, a runbook that was right. These are invisible while they work and routinely deleted during a later cleanup by someone who has never seen them save an outage. **Naming them in a durable document is how they survive.**
- [ ] **Where you got lucky.** Often the most valuable paragraph in the record. *It happened at 14:00 rather than 03:00. The engineer who knew this subsystem happened to be online. It hit the smallest region first. The bad deploy was caught before it reached the second shard.* **Every one of those is a near miss inside the incident** — next time the luck is absent and the outcome is worse. Luck that goes unrecorded gets silently counted as resilience, and that is how an organization comes to believe it is better protected than it is.

---

## 🔧 Step 7: What was actually done

The incident is resolved, so record **what resolved it** — as history, past tense, sourced like everything else. Description, not prescription.

- [ ] **The mitigation** — what stopped user impact, when, and whether it was a fix or a workaround.
- [ ] **The fix** — the change that made the system correct, with its commit or PR from the git history.
- [ ] **Cleanup that followed**, and **anything left in place**: a feature still disabled, a rate limit still lowered, a manual process still running. These loose ends outlive incidents precisely because nobody writes them down.
- [ ] **Anything else that has already changed** — an alert added, a guard introduced. Again as a record of what happened, not a list of what should.

**Then state the open questions plainly.** What the evidence could not settle: a gap with no logs, a timing two sources disagree on, a mechanism that remains a hypothesis. **An honest open question is worth more than a confident guess**, because the guess gets cited later as established fact by someone who wasn't here.

## 🧹 Step 8: The blamelessness pass

Re-read the finished draft **specifically hunting for blame**. It leaks in through grammar, not intent, and the author never sees it. [blameless-culture.md](blameless-culture.md) has the full catalog and the rewrites; the pass itself:

- [ ] **Counterfactuals** — "should have," "could have," "failed to," "didn't notice." Each describes a world that didn't happen and explains nothing about the one that did. Rewrite as what the system presented: *"the dashboard showed aggregate latency, so the per-shard spike was not visible."*
- [ ] **Names attached to errors.** Roles and actions, not people. Names are fine on actions and decisions; not on mistakes.
- [ ] **"Human error" as a factor.** Never a finding — it's the place a finding was supposed to go. A human could cause an outage with one action, with no guard and no confirmation: **that** is the finding, and it is about the system.
- [ ] **Hindsight markers** — "obviously," "clearly," "simply." If it had been obvious at the time it would not have happened.
- [ ] **Prescription that crept in** — "we need to…", "this should be…", "the team must…". Rewrite as the factual finding it came from, or cut it. A reconstruction that starts recommending has stopped being one, and the recommendation is not this document's to make.
- [ ] **Would the person closest to the triggering change read this and call it fair?** The practical test. If not, this will be the last document anyone contributes to candidly.

## 🛑 Stopping rule

Stop when all five hold:

- [ ] **The timeline is sourced**, tagged, and covers change → impact → detection → mitigation → resolution.
- [ ] **Impact is quantified**, or its absence is explained.
- [ ] **Contributing factors are plural**, every category swept including "none found," each with evidence and confidence, each descended to something concrete about the system.
- [ ] **What was done is recorded**, including loose ends still in place, and the open questions are stated as open.
- [ ] **The blamelessness pass is done** on the final text, not on the draft — including the prescription check.

Then publish it, **with the open questions marked as open**. A record circulated in three days with two unknowns is worth far more than a complete one in three weeks: memories decay fast, log retention decays faster, and a reconstruction that arrives after everyone has moved on is an artifact rather than a record. **Do not hold a postmortem for certainty it cannot reach** — mark the gap and ship it.

---

## Subagents — optional

Worth it on a **large incident** — a wide git range, hours of logs, several systems, a long chat export, multiple documents.

**Steps 1–2 delegate.** Read-only, and they split cleanly by source: one subagent on the git range, one on monitoring and alerts, one on the chat export, one per document. Each returns timestamped entries with source tags; you merge and reconcile. **Contradictions between sources are findings, not merge conflicts** — reconcile in the main thread, and record a disagreement nothing explains.

**Steps 5–8 do not delegate.** Contributing factors live in the *relationships* between events from different sources, which is exactly what a per-source split destroys, and the blamelessness pass needs one voice reading one finished document.

**Dispatch contract.** A subagent starts with no history. Give each one the **prior** (what is known), the **target** (which source it owns, and that the others are covered so it neither duplicates nor apologises for the gap), the **context it cannot infer** (date range, systems, timezone convention), the **return shape** — timestamped entries with `[source]` tags, **including an explicit "nothing found in this window"** so a silent delegate is distinguishable from a quiet source — and an explicit *"report conclusions, not file excerpts."* Tell each one to **report what it cannot determine rather than inferring**: a delegate that fills a gap with a plausible guess corrupts the spine of the document, and the guess is unrecoverable once it's in the timeline. Delegates stay **read-only**.

## Rules of Engagement

1. **Describe, don't prescribe.** The incident is solved. This document records what happened; it does not decide what happens next.
2. **Blameless is a data-collection strategy.** People who expect blame report less, and the next reconstruction is worse. That is the mechanism, not the sentiment.
3. **Timeline from artifacts.** The git history and the logs are dated; memory reorders under stress, confidently, toward a tidier story.
4. **Cite every entry.** An unsourced claim in a permanent document becomes a fact by repetition.
5. **Factors are plural.** "The root cause" is a fiction that implies the others were acceptable.
6. **Descend to something concrete about the system**, and stop there. "Because a person didn't know" is a pointer to the system that should have told them.
7. **Record the luck.** Unrecorded luck gets counted as resilience.
8. **Mark the gaps.** What the evidence could not settle is part of the record, not a hole to paper over.

## Handoff

Once the document is complete:

> Postmortem for `<incident>` is ready: `<d>` of user impact, `<n>` contributing factors across `<c>` categories, `<u>` open questions the evidence could not settle. Sources: git `<X>..<Y>` (`<k>` commits), `<m>` incident documents. Blamelessness pass complete, including the prescription check.

Then, in order:

- **Circulate to everyone involved for correction first.** They were there and you were not; the timeline will contain errors only they can catch, and a record corrected before publication is trusted afterwards.
- **Then circulate beyond them.** A postmortem read only by its responders has taught the organization nothing, and the failure modes it describes are rarely unique to one team.

What to do about any of it is a decision for whoever owns the system. **This document exists to make that decision well-informed, not to make it.**
