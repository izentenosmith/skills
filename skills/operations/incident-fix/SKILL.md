---
name: incident-fix
description: Responds to a production incident — contains first, then diagnoses and sizes the impact, fixes through a capped review loop with data repair as its own audited artifact, and closes with a blameless post-mortem. For a system down or degraded, data corrupted, wrong financial figures, a security exposure, or a hotfix with a systemic cause; every production-affecting action waits for confirmation. Use for "incident", "outage", "prod down", "SEV1", "on-call page", and when hotfix escalates.
---

# 🚨 Incident Fix

## Where this fits

An incident is a bug with a clock running. **Containment comes first and never waits for a diagnosis** — a ranked, reversible action that stops the damage now beats a correct fix in two hours. Then the slower, careful work: evidence, impact, a fix that gets the full review, a repair for whatever data the bug touched, and a record the next incident can learn from.

[hotfix](../hotfix/SKILL.md) routes here when the system is down, data is being corrupted or exposed, or a "quick fix" turned out to have a systemic cause. **The opposite route exists too:** if Step 0 shows nothing is degraded and nothing is getting worse, say so and hand it to hotfix.

Reference docs, all in this folder:

- [severity.md](severity.md) — what qualifies as an incident, when to declare, and how severe
- [roles.md](roles.md) — incident commander, operations, communications and planning, scaled down to a small team, and how command is handed off
- [discovery.md](discovery.md) — the repo's conventions, plus rollback levers, observability and data access
- [containment-levers.md](containment-levers.md) — the ranked levers, including overload and cascading-failure responses, and the stepped ramp that undoes them
- [diagnosis.md](diagnosis.md) — when Phase 2's evidence runs out: a reproduction off production, minimise, ranked hypotheses, one probe at a time
- [incident-log.md](incident-log.md) — the durable, UTC-stamped log every phase writes to
- [data-repair.md](data-repair.md) — the checklist for repairing what the bug wrote
- [follow-through.md](follow-through.md) — turning contributing factors into follow-ups or accepted risks
- [postmortem-fallback.md](postmortem-fallback.md) — the record, when the post-mortem skill isn't installed
- [phase-gates.md](phase-gates.md) — the exit condition of each phase, and the fix-review fallback

## ⛔ Hard gates — check them before every action

These are not judgment calls. Before any edit, command or write, check the one that applies; if it doesn't hold, the action doesn't happen.

1. **No code before containment.** Until Phase 1's gate holds and `mitigated` is logged, don't create, edit or delete any file the running system is built from or executes — source, tests, config, job definitions, migrations — not even locally, not even as an undeployed draft. Containment waiting on a confirmation that hasn't come (the user is away, or hasn't answered) means the gate does **not** hold: keep going read-only through Phase 2, and Phase 3's code fix becomes a proposed diff in the incident log and your response, not a change to the tree. Before `mitigated`, only two things may be written: the incident log with its captured evidence, and a data repair artifact (with its fixture test) under gate 3 — a new, standalone file that changes nothing until someone runs it with `--apply`.
2. **Every impact number comes with its query, written out.** A count goes into the log next to the exact read-only query or command that produced it — the text itself (`SELECT COUNT(*) FROM … WHERE …` → 12), not a description of it and not a pointer to a file holding it. That same query is the repair's selection and its verification.
3. **A data repair is a dry run by default and backs up before it writes.** Run with no flags, it opens the data read-only, prints what it would change with the count from gate 2, and changes nothing. With `--apply`, it writes its own backup of exactly the rows it will change and reads it back *before* its first write, every time — never a separate step someone can skip. `--apply` is the only switch between the two; it may refuse without the expected count, but a precondition such as pausing a downstream job is its own confirmed step, not another flag. Nothing touches production data until the user confirms that exact command.

## The rules that hold in every phase

1. **Every production-affecting action needs explicit confirmation, every time** — rollback, scale-down, disabling a job, a flag or config flip, rotating a secret, a deploy, a publish, a data write. A broad "go ahead" earlier does not cover the next action. Propose it, say what it changes and how it's undone, and wait.
2. **Read-only first.** Diagnosis reads logs, metrics, history and data; it never writes to production to learn something.
3. **Log as you go**, in [incident-log.md](incident-log.md)'s format, with **timestamps from the system clock** (`date -u`, or the incident log tool where available) — never written from memory or estimated by the model. Commit the log at every phase gate: an incident record that lives only in an uncommitted worktree is one cleanup away from gone.
4. **Known vs. assumed, always marked.** Under pressure a plausible guess hardens into fact within the hour.
5. **One commander, no freelancing** ([roles.md](roles.md)). Only the operations role changes production, and every change goes through it. On a small team the user is the commander, the agent keeps the log and the plan, and the person with production access is operations.
6. **Check in every 30–60 minutes** while the incident is open, and log a `checkpoint`: is the current approach still the right one, is the severity still right, and does this need more people? An incident run on its first plan for three hours is usually an incident whose plan stopped working two hours ago (*Site Reliability Engineering*, ch. 14).

## 🔎 Step 0: Discover, and confirm it's an incident

Work [discovery.md](discovery.md) — reuse `.workflow/env.md` if it's current. Beyond the repo's conventions, find the **rollback levers** (previous deployable version, flags and config, scaling and scheduled-job controls, revertable commits, secret rotation), the **observability** reachable from here (CLIs, connected tools, dashboards the repo references — if none, ask the user for logs or screenshots), and the **data access mode** (read-only by default).

Then classify with [severity.md](severity.md), say the severity and why in one line, and **start the incident log** — detection time and source first. **Declare early**: an incident declared and later downgraded costs a sentence; one declared an hour late costs the hour ([severity.md](severity.md) says when).

In the log's state block ([incident-log.md](incident-log.md)), record at declaration:

- **Roles** — who is commander, who is operations, who writes the stakeholder updates ([roles.md](roles.md)).
- **Exit criteria** — the observable condition that will mean *resolved*, such as "error rate under 0.5% and checkout success back to baseline for 30 minutes". Without it, "resolved" is whenever people get tired.
- **Where coordination happens** — a channel or call that does **not** depend on the system that's down. If the chat, the wiki or the tracker runs on the affected infrastructure, name the fallback now.

## 🧯 Phase 1: Contain — minutes, no new logic

- [ ] **Capture what containment would destroy.** A rollback, restart or scale-down can wipe the logs, state and in-flight data diagnosis needs. Take them first when it's quick; when it isn't, say what will be lost and let the user weigh it. Redact secrets and personal data from anything saved.
- [ ] **Ask what changed last.** Most incidents follow a change — a deploy, a config push, a flag flip, a job, a dependency update, a data or traffic shift. Whoever made the most recent change usually knows the fastest way to undo it, so ask them first.
- [ ] **List the containment options** found in Step 0 and in [containment-levers.md](containment-levers.md), ranked by **risk** and **reversibility**: what each stops, what it costs users, how long to undo. Prefer switching something *off* (flag, job, traffic) over shipping something new. A security exposure adds **revoke and rotate** to the top of the list; an overload adds **shed load** ahead of adding capacity.
- [ ] **Recommend one, get confirmation, act, verify the effect** — is the error rate down, the job stopped, the exposure closed? Log the action and its result. If it didn't work, log that too and take the next option.
- [ ] **Register every temporary change** — a flag left off, a job paused, a limit lowered, an alert silenced — in the state block's *Temporary changes* list as you make it. That list is what Phase 3 undoes and what follow-through dates; a temporary change nobody listed becomes permanent by accident.
- [ ] **Open the incident item** — with [ticket](../ticket/SKILL.md) where installed, otherwise directly in the tracker — carrying the team's production-incident label, **now, while the incident is open**, after confirmation. Restore-time metrics are built from it. No tracker: the log is the record.
- [ ] **Draft the stakeholder update** — what's affected, what's been done, and **the time of the next update**, which is kept even when there's nothing new. The user sends it.

**Gate:** user impact has stopped, or is bounded and the user has accepted that. Log `mitigated`. Containment that holds is the goal of this phase — not a fix. A recommendation still awaiting confirmation is not containment: hard gate 1 keeps every code file closed until this gate holds.

## 🔬 Phase 2: Diagnose and size the impact

- [ ] **Root cause from evidence** — logs, metrics, read-only queries, and the git history of the affected code (the triggering change often merged days earlier: widen the range). Find **every caller** of the faulty code — the impact is the union of their paths, not just the one in the alert.
- [ ] **Impact assessment**: which users, records or documents; **from when to when**; with a **reproducible query or command** and its counts, the query's text in the log (hard gate 2). Wrong data is the worst case and the easiest to under-count, because it doesn't announce itself.
- [ ] **Known vs. assumed** for every number. "~2,300 orders (query in log at 15:02); whether refunds were affected is assumed not — no refund path calls this code" is an assessment. "Some orders" is not.

**Gate:** a stated cause with its evidence, and an impact with a reproducible count, both logged.

## 🛠️ Phase 3: Fix — through review, at most two loops

- [ ] **Design, only if there are real options.** Use `architect-deep-dive` where installed; otherwise lay out the options with trade-offs and a recommendation, and let the user pick.
- [ ] **Build it the full way**: test-first (`tdd`), `refactor-review`, `devils-advocate`, `tyr-verdict` — delegating to each where installed, and working [phase-gates.md](phase-gates.md)'s fix-review checklist where not. **Tell tyr-verdict the cap is two iterations, not three**; a third NO-GO is the user's decision. Where a closing-loop runner and a red/green checker are available, use them — at the same cap.
- [ ] **Data repair is its own artifact**, separate from the code fix, under [data-repair.md](data-repair.md) and hard gate 3: dry run by default, its own backup before any write, before/after counts, idempotent, run in a non-production environment first when one exists, and in production only with explicit confirmation.
- [ ] **Verify, promote, verify.** Pre-production first if it exists, then promote by the repo's convention (confirmed), then verify in production. Each piece of evidence — command, result, commit — goes into the log.

- [ ] **Undo containment in steps**, not all at once — a flag back on for a fraction of traffic, a job resumed on a slice, load ramped back up ([containment-levers.md](containment-levers.md)) — each step confirmed and watched, and each struck from the *Temporary changes* list as it's undone.

**Gate:** the fix and any repair are verified in production, and **the exit criteria stated at declaration hold**. Log `resolved`. Anything left on the *Temporary changes* list is either undone now (confirmed) or becomes a dated follow-up in Phase 4.

## 📚 Phase 4: Learn — within 48 hours

- [ ] **The post-mortem.** Run [post-mortem](../post-mortem/SKILL.md) where installed, handing it the incident log and the git range; otherwise use [postmortem-fallback.md](postmortem-fallback.md). Either way: a timeline from the log and git, quantified impact, contributing factors (plural, never "the root cause"), what went well and where you got lucky. **The record describes; it does not prescribe.**
- [ ] **Then follow through**, as a separate step on top of the record ([follow-through.md](follow-through.md)): every contributing factor becomes a **follow-up with an owner, a date and an action type** (mitigate, prevent or process), or an **explicitly accepted risk with a reason** and who accepted it. Nothing left as "noted." Create the tracker items with [ticket](../ticket/SKILL.md) where installed.
- [ ] **If detection was slow, or a user found it first**, one of those follow-ups is the missing alert or monitoring — added now where the repo owns it, ticketed where it doesn't. **If responders were flooded by alerts**, the noise is a factor too.
- [ ] **Close the incident item** (confirmed), with the cause labels the post-mortem settled on, so restore time is recorded and incidents can be counted by cause. Log `closed` and commit the log.

**Gate:** the record exists, every factor is owned or accepted, and the item is closed.

## 🛑 Stopping rule — when to stop and hand it to a human

- **No containment option works**, or every one is too risky to recommend → stop, say so, and lay out what you know; this needs a person with more access or authority.
- **The commander changes**, or the session is ending with the incident still open → hand off explicitly ([roles.md](roles.md)): the state block brought up to date, the incoming person (or session) confirming they have it, and a `handoff` entry logged. Command isn't passed until it's acknowledged.
- **The fix loop hits its cap** (two iterations, still NO-GO) → stop with the open findings and the options: ship the containment as the long-term state, accept the risk, or take it back to design.
- **Evidence runs out** before the cause is found → keep containment in place, record the open question in the log, and say what evidence would settle it. Don't fix a guess. Before stopping, and only once Phase 1's gate holds, [diagnosis.md](diagnosis.md) can still find it: a reproduction from captured artifacts in a non-production copy, then ranked hypotheses — reading and reproducing only, with application code untouched until Phase 3.

Otherwise, stop when Phase 4's gate holds.

## Subagents — optional

**Phase 2's evidence gathering delegates**: one read-only delegate per source — logs, metrics, the git range, the callers, each impact query. Each returns timestamped, sourced findings and states what it could not determine. **Containment, every production action, and the fix decisions never delegate** — they need the user's confirmation in the main thread. **Dispatch contract:** the prior, the target, the context it cannot infer, the return shape, and *"report conclusions, not file excerpts."*

## Handoff

> Incident `<title>` (`<severity>`) closed. Impact `<who/what, counts>` from `<start>` to `<mitigated>` UTC; resolved `<resolved>` UTC. Contained by `<action>`; fixed by `<commit>`; `<n>` records repaired (`<repair artifact>`). Post-mortem: `<link>` — `<k>` factors, each a follow-up or an accepted risk. Log: `<path>`.
