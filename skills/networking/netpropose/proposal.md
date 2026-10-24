# Proposal — From Audit and Design to a Decision

This reference governs the recommendation stage. It consumes an audit and a separately reviewed
design when those artifacts apply. **Do not perform the audit, redesign the network, or redraw the
diagrams here.** The companion stages are [netaudit](../netaudit/SKILL.md),
[netdesign](../netdesign/SKILL.md) and [netdiagram](../netdiagram/SKILL.md). Their outputs remain
independently reviewable. The diagrams must follow [diagram-conventions.md](diagram-conventions.md).
A proposal whose required views are absent, or drawn in another convention, is not complete: identify
the gap and route it back through netdiagram.

## Inputs and limits

**Existing network.** Use the per-domain evaluations, the per-network summary, the estate synthesis
(with its coupling edge list), `scores.json`, `gate.md` and the recovered `topology.json`. For a
redesign, also use `design.md`, the target `topology.json` and the diagrams.

**New network.** Use the requirements, the design and the diagrams.

If a needed artifact is absent, identify the gap and scope the proposal accordingly. Never imply a
missing design or diagram exists.

Treat audit findings and scores as evidence, not a substitute for judgement. Read the cap and the gate
reasons:
- an open Critical caps the score at 2.0, and an open High caps it at 6.0;
- a score of 9.0 or more meets the score threshold, while the gate also requires no open
  Critical/High, κ ≥ 2 for every critical pair, a 🔬 ratio ≤ 10%, and usage other than
  decommissioned/duplicate.

Carry runtime questions forward as open questions.

## Recommendation decisions

For each domain of each in-scope network, record a decision. Use the domain's score band as the
starting posture, then explain any evidence-based override:

| Score band | Starting posture |
|---|---|
| 9.0–10 | Keep |
| 7.0–8.9 | Refactor (targeted changes inside the current pattern) |
| 5.0–6.9 | Rework (change the pattern in this domain: re-segment, re-address a region, replace the routing design) |
| 0–4.9 | Rebuild (a new design for the domain, migrated in) |
| Decommissioned or duplicate network | Consider retirement; state the usage evidence and the confirmation needed |

Any open Critical needs an explicit corrective decision **in the first change window**, even when the
overall score is high. Exposure findings (internet-reachable management, any-any into data) come
before structural work, because a containment rule can usually be applied without redesign. Say so.

Resilience decisions name the critical pair, its current κ and cut set, and the target κ, with the
change that raises it. Addressing decisions that require **renumbering** are the most expensive and
the most dependent. Sequence them explicitly.

## Cut-over and sequencing

Use the design's target `topology.json` as the source of the target. Check that its version is clear
and that every diagram corresponds to it. If they disagree, describe the mismatch and route the
correction to netdesign or netdiagram rather than silently changing the model here.

Order the work:

1. **Containment** of Critical exposure: rule changes, disabling a public endpoint. Small, reversible,
   first.
2. **Foundations that others depend on**: address space reservations, hub and transit, DNS, the
   management zone.
3. **Coupled networks in coupling order.** The estate synthesis's coupling edge list gives the
   dependencies: move or re-address leaf networks before the hubs they depend on are changed, or build
   the new hub in parallel and migrate spokes one at a time.
4. **Resilience upgrades** that raise κ on critical pairs. Add the second path before removing
   anything.
5. **Cleanup**: decommission dead networks, shadowed rules and orphaned policy, last, after
   validation.

Each step in the register names:
- the finding(s) it addresses;
- the change in outline (not IaC);
- the pre-check;
- the validation: which critical pairs to test, what "working" looks like;
- the rollback;
- the blast radius: the zones and critical pairs affected while the step is in flight;
- the change window and owner, if known.

All changes are proposals for review. This skill never applies them.

## Deliverable

A concise `proposal.md` that includes:

1. Executive recommendation, scope, source versions, and target platforms.
2. What is good, what needs attention, and the expected improvement: score, gate conditions,
   critical-pair κ before and after.
3. The prioritized decision register per domain, with evidence.
4. The paths to the target design, the target `topology.json` and every diagram, with a sentence on
   what each view communicates and any known model/diagram discrepancy.
5. The cut-over sequence, with dependencies, risks, validation, rollback and blast radius per step.
6. Open questions, especially unresolved 🔬 flags, and the decision each one blocks.
7. A closing line stating that acceptance is required before
   [netblueprint](../netblueprint/SKILL.md) produces the final topology package.

Do not paste large configs, IaC or diagram XML into the proposal when the artifacts can be linked.
Keep it reviewable, and make every referenced path unambiguous.
