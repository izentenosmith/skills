# Phase gates

Each phase ends at a gate. **Don't start a phase's work on top of an open gate** — except that containment may begin before Step 0's discovery is finished, when the damage is spreading and an obvious lever is already known. Tick each item, or write why it doesn't apply.

## Step 0 — discovered and classified
- [ ] `.workflow/env.md` current, including the incident levers, observability and data access mode
- [ ] Severity stated with a reason ([severity.md](severity.md)); routed to hotfix instead if it isn't an incident
- [ ] Incident log started, in a durable location, with the `detected` entry

## Phase 1 — contained
- [ ] Evidence that containment would destroy captured (or its loss accepted by the user)
- [ ] Containment options listed, ranked by risk and reversibility, one recommended
- [ ] Each production action proposed, **confirmed**, taken, and its effect verified — all logged
- [ ] Tracker item opened with the incident label (confirmed), or "no tracker" noted
- [ ] Stakeholder update drafted
- [ ] `mitigated` logged — impact stopped, or bounded and accepted by the user
- [ ] Log committed

## Phase 2 — diagnosed
- [ ] Cause stated with evidence; git range widened past the incident window
- [ ] Every caller of the faulty code found
- [ ] Impact: who / what, from when to when, a reproducible query or command, and counts
- [ ] Every number marked known or assumed
- [ ] Log committed

## Phase 3 — fixed
- [ ] Design options decided by the user, if there were real options
- [ ] Red test → fix → review → verdict, at most two loops
- [ ] Data repair as a separate artifact ([data-repair.md](data-repair.md)), if any data was written wrong
- [ ] Verified in pre-production (if it exists) → promoted (confirmed) → verified in production
- [ ] Containment no longer needed is undone (confirmed), or kept with a reason
- [ ] `resolved` logged with the evidence; log committed

## Phase 4 — learned
- [ ] Post-mortem record written, blameless, descriptive
- [ ] Every contributing factor → follow-up (owner, date) or accepted risk (reason, who) ([follow-through.md](follow-through.md))
- [ ] Detection gap → alert or monitoring follow-up, if detection was slow or human
- [ ] Tracker item closed (confirmed); `closed` logged; log committed

---

## The fix-review fallback

When the build-and-review skills aren't installed, Phase 3 works this list instead. It is the same discipline compressed: prove the bug, fix it once at the cause, attack the fix, decide.

1. **Red.** A test through the highest public seam that reproduces the defect, shown failing on the unfixed code.
2. **Green.** The minimal fix at the shared cause — every caller from Phase 2 covered. Full suite, lint and type check green.
3. **Clean.** Re-read the diff for structure that will make the next change dangerous: duplicated logic that will diverge, a long function with several exits, a special case that should have been a rule. Fix what's cheap; record the rest.
4. **Attack.** Assume the fix is wrong. For each: does the red test still pass if the fix is reverted? What about empty, boundary, very large and concurrent inputs? Records written *before* the fix? Error paths, permissions, isolation, backward compatibility? Write down what you attacked and what held.
5. **Decide.** Every proven problem that a user would hit is a blocker: fix it red→green and go back to step 4 — **twice at most**. A third round means the fix or the design is wrong; stop and take it to the user.
