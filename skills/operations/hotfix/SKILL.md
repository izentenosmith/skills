---
name: hotfix
description: A fast, still-disciplined lane for an urgent bug in a running system that is NOT an incident — the system is up, nothing is being corrupted or exposed right now. Discovers the repo's own build, test, review and ship conventions, proves the bug with a red test, fixes it at the shared cause, runs one adversarial review pass, and ships with recorded evidence in about an hour of agent time. Use for "hotfix", "urgent fix", "quick fix", "bug in prod but not down", "fix urgente", "arreglo rápido". Not for outages, data corruption, security exposure or anything still getting worse — that is incident-fix.
---

# 🩹 Hotfix

## Where this fits

The [development pipeline](../../development/README.md) is the right way to build a change and the wrong way to fix a wrong number on an invoice page by lunchtime. This lane is the short path between them: **every discipline that catches a bad fix, none of the ceremony that designs a good feature.** It is not a lighter standard — the red test, the shared-cause fix and the review pass are all mandatory. What it drops is the design dialogue, the plan document and the review *loop*.

It leans on six reference docs:

- [discovery.md](discovery.md) — finding the repo's commands, conventions and installed skills, and the `.workflow/env.md` profile that caches them
- [root-cause-note.md](root-cause-note.md) — the three-line note, and the caller sweep
- [diagnosis.md](diagnosis.md) — finding the cause when it isn't in plain sight: a red loop, minimise, ranked hypotheses, one probe at a time
- [review-checklist.md](review-checklist.md) — the review pass when no review skill is installed
- [follow-up.md](follow-up.md) — the item a band-aid owes, with or without a tracker
- [final-checklist.md](final-checklist.md) — the record that closes the lane

**Never push, merge, deploy, publish or create a ticket without the user's confirmation** unless the repo's own instructions authorize that specific action. A confirmation covers one action, not the rest of the lane.

## 🔎 Step 0: Discover the environment

Read [discovery.md](discovery.md) and work it. If `.workflow/env.md` exists and is still current, it *is* step 0 — confirm it in one line and move on. Otherwise produce it: the repo's agent and contributor instructions; build, test, lint and type-check commands **as CI runs them**; the merge convention; whether a pre-production environment exists; a tracker, only from evidence; and installed skills that cover a later step.

Whatever cannot be discovered, ask **once, in a single question**, and offer to save the answers to the repo's agent instructions file. A lane that asks five questions across forty minutes isn't fast.

## 🚦 Step 1: Triage — route out before you start

This lane only works for bugs that can wait an hour. Check, in order, and **stop at the first that holds**:

- **Down, degraded, exposing data, or corrupting data now** → stop. This is an incident: run **[incident-fix](../incident-fix/SKILL.md)**, and hand it whatever you already know.
- **Real design ambiguity** — several reasonable fixes with different trade-offs, or a fix that needs a new boundary → stop. Recommend the repo's design workflow ([architect-deep-dive](../../development/architect-deep-dive/SKILL.md) → [agent-brief](../../development/agent-brief/SKILL.md) where installed), or a short options-and-trade-offs discussion where not.
- **The fix touches persistent data, money, permissions or tenancy** — database writes, migrations, financial or inventory figures, file deletion, an authorization check, an isolation boundary → **stay, in strict mode.** Step 4 becomes blocking. These are the failures a green suite is worst at catching, and a two-line diff is perfectly capable of causing one.

**Also ask whether the fix is a revert.** If one identifiable commit introduced the bug and reverting it loses nothing still wanted, the revert *is* the hotfix — the red test still applies.

Say which way the gate went, and why, in one line.

## 🧭 Step 2: Root cause — in three lines

Write the note in [root-cause-note.md](root-cause-note.md): **symptom · cause · why no existing test caught it.** If you cannot write the cause line from evidence, you have not found it — and a fix for a cause you have guessed is a second bug.

**When the code and the report don't hand you the cause** — it resists a first read, it's intermittent, it's a slowdown, or it appeared somewhere between two known-good states — work [diagnosis.md](diagnosis.md) before writing the cause line: a command that goes red on this bug first, then hypotheses. Its minimised reproduction becomes Step 3's red test.

**Before editing, find every caller of the code you're about to change.** The report names the path somebody hit; the defect lives in shared code with other paths into it. **Fix it in the shared place**, once — not on the reported path only, and not by refactoring beyond what the fix needs. If the sweep turns up a caller that would *break* under the fix, that's the design-ambiguity exit from Step 1.

## 🔴 Step 3: Red, then green

- [ ] **A test that fails because of the bug** — through the highest public seam that reproduces it cheaply, the same seam the repo's existing tests use for that code. Go narrower only when that seam needs infrastructure the repo's tests don't have. Follow the repo's test conventions and vocabulary.
- [ ] **Watch it fail, for the right reason.** A test that fails on an import error or a typo proves nothing about the bug. Where a red/green checker is available (it applies only the new tests to the pre-fix code and runs them), use it; otherwise run the test before writing the fix and keep the output.
- [ ] **The minimal fix to green**, in the shared place, following the repo's conventions. No adjacent cleanup — that's a separate change.
- [ ] **The relevant suite, the linter and the type checker** discovered in Step 0, all green.
- [ ] **No test framework at all?** Write the smallest runnable check that fails without the fix and passes with it — a script, an assertion block, a command with an expected output — **say explicitly that the repo has no tests**, and propose a follow-up for the harness.

## 🔥 Step 4: One adversarial review pass

Scoped to **the diff only**, and **one pass — no loop**. Where [devils-advocate](../../development/devils-advocate/SKILL.md) and [tyr-verdict](../../development/tyr-verdict/SKILL.md) are installed, run them back to back: one teardown, one adjudication, cap one iteration. Where they aren't, work [review-checklist.md](review-checklist.md) yourself, after re-reading the diff as if someone else wrote it.

- **Confirmed blockers get fixed now**, red→green like the original bug.
- **Everything else becomes a follow-up item** ([follow-up.md](follow-up.md)), not a second round.
- **Strict mode** (Step 1): any confirmed blocker *or major* blocks shipping. If it can't be fixed inside the lane, stop and hand the change to the full pipeline with the root-cause note and the findings — that's the lane telling you this was never a hotfix.

## 🧷 Step 5: Owe the proper fix, if this is a band-aid

A band-aid is fine; an unrecorded one is not. If the fix guards a symptom rather than removing the cause — a clamp, a retry, a special case, a disabled path — create the follow-up in [follow-up.md](follow-up.md): the proper fix, why it wasn't done now, a target date. In the tracker if one exists (with confirmation), otherwise in the local log. **Reference it in the commit message** using the repo's convention.

## 🚀 Step 6: Ship by the repo's convention

PR or direct merge, protected branches, required checks — whatever Step 0 found, not what's common. **Confirm before each outward action.**

If a pre-production environment exists, **verify there before promoting**: the automated suite, plus one manual hit of the affected behavior — the request, command or page that showed the bug, now showing the fix. Then promote, and repeat the hit in production when that's reachable. **Record each as evidence**: what was run, what came back, at which commit.

## ✅ Step 7: Close with the checklist

Fill [final-checklist.md](final-checklist.md) and tick every item: root-cause note · red→green test · suite, lint and type check · review pass · follow-up item (if a band-aid) · verification evidence. **Report every skipped item and why** — a skipped step said out loud is a decision; a skipped step left silent is a defect in the record. Save it to `.workflow/hotfix-<slug>.md` and put its summary in the commit or PR body.

## 🛑 Stopping rule — when to leave the lane

The lane's speed is a budget, not a promise. Leave it, saying which exit fired:

- **The cause isn't clear** after the evidence you can reasonably gather — no red loop can be built, or every hypothesis in [diagnosis.md](diagnosis.md) is contradicted — escalate to the user with what you've ruled out, or to incident-fix if it's getting worse.
- **The fix spreads** past one module or across a boundary, or the caller sweep finds callers that need different behavior — that's a design question.
- **Strict mode turned up a blocker** that can't be fixed in the lane — hand it to the full pipeline.

Otherwise, stop when Step 7's checklist is complete. **Do not keep improving the code once the bug is fixed** — the follow-ups hold the rest.

## Subagents — optional

The **caller sweep** in Step 2 and the **convention lookups** in Step 0 delegate well: read-only, bounded, and they flood context with file excerpts. The red→green and the fix stay in the main thread. **Dispatch contract:** the prior, the target (described behaviorally), the context it cannot infer, the return shape, and *"report conclusions, not file excerpts."* Delegates stay read-only.

## Handoff

> Hotfix shipped: `<symptom>` fixed at `<shared cause>`, `<n>` caller(s) covered, red→green by `<test>`. Review: `<confirmed>` fixed, `<k>` follow-up(s). Verified in `<environments>` at `<sha>`. `<skipped items, or "nothing skipped">`. Record: `.workflow/hotfix-<slug>.md`.

If a band-aid shipped, end with the follow-up's id and date. If the lane was exited, name the exit and the skill or person it went to.
