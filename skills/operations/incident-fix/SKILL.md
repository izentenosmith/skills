---
name: incident-fix
description: Respond to a production incident end to end — contain first, then diagnose and size the impact, fix it through a capped review loop with any data repair as its own audited artifact, and close with a blameless post-mortem whose every contributing factor becomes a follow-up or an accepted risk. For a system down or degraded, data corrupted or at risk, wrong financial or business figures, a security exposure, or a hotfix that turned out to have a systemic cause. Discovers rollback levers, observability and the repo's conventions at runtime; every production-affecting action waits for explicit confirmation. Use for "incident", "outage", "prod down", "data corruption", "rollback", "post-mortem", "incidente", "prod caído", "caída", "datos corruptos", and when hotfix escalates.
---

# 🚨 Incident Fix

## Where this fits

An incident is a bug with a clock running. **Containment comes first and never waits for a diagnosis** — a ranked, reversible action that stops the damage now beats a correct fix in two hours. Then the slower, careful work: evidence, impact, a fix that gets the full review, a repair for whatever data the bug touched, and a record the next incident can learn from.

[hotfix](../hotfix/SKILL.md) routes here when the system is down, data is being corrupted or exposed, or a "quick fix" turned out to have a systemic cause. **The opposite route exists too:** if Step 0 shows nothing is degraded and nothing is getting worse, say so and hand it to hotfix.

Reference docs, all in this folder:

- [severity.md](severity.md) — what qualifies as an incident, and how severe
- [discovery.md](discovery.md) — the repo's conventions, plus rollback levers, observability and data access
- [diagnosis.md](diagnosis.md) — when Phase 2's evidence runs out: a reproduction off production, minimise, ranked hypotheses, one probe at a time
- [incident-log.md](incident-log.md) — the durable, UTC-stamped log every phase writes to
- [data-repair.md](data-repair.md) — the checklist for repairing what the bug wrote
- [follow-through.md](follow-through.md) — turning contributing factors into follow-ups or accepted risks
- [postmortem-fallback.md](postmortem-fallback.md) — the record, when the post-mortem skill isn't installed
- [phase-gates.md](phase-gates.md) — the exit condition of each phase, and the fix-review fallback

## The rules that hold in every phase

1. **Every production-affecting action needs explicit confirmation, every time** — rollback, scale-down, disabling a job, a flag or config flip, rotating a secret, a deploy, a publish, a data write. A broad "go ahead" earlier does not cover the next action. Propose it, say what it changes and how it's undone, and wait.
2. **Read-only first.** Diagnosis reads logs, metrics, history and data; it never writes to production to learn something.
3. **Log as you go**, in [incident-log.md](incident-log.md)'s format, with **timestamps from the system clock** (`date -u`, or the incident log tool where available) — never written from memory or estimated by the model. Commit the log at every phase gate: an incident record that lives only in an uncommitted worktree is one cleanup away from gone.
4. **Known vs. assumed, always marked.** Under pressure a plausible guess hardens into fact within the hour.

## 🔎 Step 0: Discover, and confirm it's an incident

Work [discovery.md](discovery.md) — reuse `.workflow/env.md` if it's current. Beyond the repo's conventions, find the **rollback levers** (previous deployable version, flags and config, scaling and scheduled-job controls, revertable commits, secret rotation), the **observability** reachable from here (CLIs, connected tools, dashboards the repo references — if none, ask the user for logs or screenshots), and the **data access mode** (read-only by default).

Then classify with [severity.md](severity.md), say the severity and why in one line, and **start the incident log** — detection time and source first.

## 🧯 Phase 1: Contain — minutes, no new logic

- [ ] **Capture what containment would destroy.** A rollback, restart or scale-down can wipe the logs, state and in-flight data diagnosis needs. Take them first when it's quick; when it isn't, say what will be lost and let the user weigh it. Redact secrets and personal data from anything saved.
- [ ] **List the containment options** found in Step 0, ranked by **risk** and **reversibility**: what each stops, what it costs users, how long to undo. Prefer switching something *off* (flag, job, traffic) over shipping something new. A security exposure adds **revoke and rotate** to the top of the list.
- [ ] **Recommend one, get confirmation, act, verify the effect** — is the error rate down, the job stopped, the exposure closed? Log the action and its result. If it didn't work, log that too and take the next option.
- [ ] **Open the incident item** in the tracker if one exists, with the label the team uses for incident metrics — after confirmation. No tracker: the log is the record.
- [ ] **Draft the stakeholder update** — what's affected, what's been done, when the next update comes. The user sends it.

**Gate:** user impact has stopped, or is bounded and the user has accepted that. Log `mitigated`. Containment that holds is the goal of this phase — not a fix.

## 🔬 Phase 2: Diagnose and size the impact

- [ ] **Root cause from evidence** — logs, metrics, read-only queries, and the git history of the affected code (the triggering change often merged days earlier: widen the range). Find **every caller** of the faulty code — the impact is the union of their paths, not just the one in the alert.- [ ] **Impact assessment**: which users, records or documents; **from when to when**; with a **reproducible query or command** and its counts. Wrong data is the worst case and the easiest to under-count, because it doesn't announce itself.
- [ ] **Known vs. assumed** for every number. "~2,300 orders (query in log at 15:02); whether refunds were affected is assumed not — no refund path calls this code" is an assessment. "Some orders" is not.

**Gate:** a stated cause with its evidence, and an impact with a reproducible count, both logged.

## 🛠️ Phase 3: Fix — through review, at most two loops

- [ ] **Design, only if there are real options.** Use [architect-deep-dive](../../development/architect-deep-dive/SKILL.md) where installed; otherwise lay out the options with trade-offs and a recommendation, and let the user pick.
- [ ] **Build it the full way**: test-first ([tdd](../../development/tdd/SKILL.md)), [refactor-review](../../development/refactor-review/SKILL.md), [devils-advocate](../../development/devils-advocate/SKILL.md), [tyr-verdict](../../development/tyr-verdict/SKILL.md) — delegating to each where installed, and working [phase-gates.md](phase-gates.md)'s fix-review checklist where not. **Tell tyr-verdict the cap is two iterations, not three**; a third NO-GO is the user's decision. Where a closing-loop runner and a red/green checker are available, use them — at the same cap.
- [ ] **Data repair is its own artifact**, separate from the code fix, under [data-repair.md](data-repair.md): backup first, dry-run mode, before/after counts, idempotent, run in a non-production environment first when one exists, and in production only with explicit confirmation.
- [ ] **Verify, promote, verify.** Pre-production first if it exists, then promote by the repo's convention (confirmed), then verify in production. Each piece of evidence — command, result, commit — goes into the log.

**Gate:** the fix and any repair are verified in production. Log `resolved`. Undo the containment that's no longer needed — confirmed, like any other production action — and log that too.

## 📚 Phase 4: Learn — within 48 hours

- [ ] **The post-mortem.** Run [post-mortem](../post-mortem/SKILL.md) where installed, handing it the incident log and the git range; otherwise use [postmortem-fallback.md](postmortem-fallback.md). Either way: a timeline from the log and git, quantified impact, contributing factors (plural, never "the root cause"), what went well and where you got lucky. **The record describes; it does not prescribe.**
- [ ] **Then follow through**, as a separate step on top of the record ([follow-through.md](follow-through.md)): every contributing factor becomes a **follow-up with an owner and a date**, or an **explicitly accepted risk with a reason** and who accepted it. Nothing left as "noted."
- [ ] **If detection was slow, or a user found it first**, one of those follow-ups is the missing alert or monitoring — added now where the repo owns it, ticketed where it doesn't.
- [ ] **Close the incident item** (confirmed), so restore time is recorded. Log `closed` and commit the log.

**Gate:** the record exists, every factor is owned or accepted, and the item is closed.

## 🛑 Stopping rule — when to stop and hand it to a human

- **No containment option works**, or every one is too risky to recommend → stop, say so, and lay out what you know; this needs a person with more access or authority.
- **The fix loop hits its cap** (two iterations, still NO-GO) → stop with the open findings and the options: ship the containment as the long-term state, accept the risk, or take it back to design.
- **Evidence runs out** before the cause is found → keep containment in place, record the open question in the log, and say what evidence would settle it. Don't fix a guess. Before stopping, and only once Phase 1's gate holds, [diagnosis.md](diagnosis.md) can still find it: a reproduction from captured artifacts in a non-production copy, then ranked hypotheses — reading and reproducing only, with application code untouched until Phase 3.

Otherwise, stop when Phase 4's gate holds.

## Subagents — optional

**Phase 2's evidence gathering delegates**: one read-only delegate per source — logs, metrics, the git range, the callers, each impact query. Each returns timestamped, sourced findings and states what it could not determine. **Containment, every production action, and the fix decisions never delegate** — they need the user's confirmation in the main thread. **Dispatch contract:** the prior, the target, the context it cannot infer, the return shape, and *"report conclusions, not file excerpts."*

## Handoff

> Incident `<title>` (`<severity>`) closed. Impact `<who/what, counts>` from `<start>` to `<mitigated>` UTC; resolved `<resolved>` UTC. Contained by `<action>`; fixed by `<commit>`; `<n>` records repaired (`<repair artifact>`). Post-mortem: `<link>` — `<k>` factors, each a follow-up or an accepted risk. Log: `<path>`.
