---
name: netpropose
description: Prepare a reviewable recommendation for a computer network using audit evidence, a target network design and topology, and the canonical draw.io topology diagrams — prioritized decisions, cut-over sequencing, risk, validation and rollback. Use when a network audit and/or design needs to become a decision for stakeholders; it never applies changes or writes IaC.
---

# netpropose

Turn evidence and a design into a clear recommendation for decision-makers and implementers. This
skill can be used on its own when the user supplies the artifacts, or as the final stage of the
network workflow harness before acceptance.

## Inputs

Use what is available:
- the audit: evaluations, summary, `scores.json`, `gate.md`, the recovered `topology.json`;
- the design (`design.md` and the target `topology.json`);
- the diagrams (`logical-topology.drawio`, `segmentation.drawio`, and `physical-topology.drawio` when
  applicable);
- requirements, constraints and change windows.

For an existing network, cite the audit's finding IDs and scores. If an audit or design is missing,
name the gap and limit conclusions accordingly. Never fabricate findings or imply that a diagram was
produced. For a new network, the requirements and the design are the evidence base.

## Prepare the proposal

Read [proposal.md](proposal.md) for the decision rules and output structure, and
[design-patterns.md](design-patterns.md) for the patterns the design draws on. Cover:

- the recommendation and its rationale: what is already good, what needs attention, and the expected
  improvement in score, gate conditions and critical-pair connectivity;
- a prioritized decision register per domain (addressing, segmentation, routing, services,
  resilience, security), with each decision for an existing network tied to an audit finding;
- the target design, `topology.json` and diagram paths, with what each view communicates;
- the **cut-over plan**: ordering derived from the coupling edge list and dependencies, change
  windows, pre-checks, validation per step, rollback per step, and blast radius per step;
- open questions, especially unresolved 🔬 flags, and the decision each one blocks.

Keep facts, inferences and decisions distinct. A proposal is not authorization: never push
configuration, apply IaC or touch a device as part of this skill.

Confirm that the diagrams follow [diagram-conventions.md](diagram-conventions.md) and match the
design's `topology.json`: same IDs, same CIDRs, same flows. Describe any mismatch and route it back to
[netdesign](../netdesign/SKILL.md) or [netdiagram](../netdiagram/SKILL.md). Do not redraw or silently
repair either artifact.

## Handoff

For an existing network, the usual sequence is [netaudit](../netaudit/SKILL.md) →
[netdesign](../netdesign/SKILL.md) → [netdiagram](../netdiagram/SKILL.md) → this proposal. For a new
network, start at netdesign. After the user **explicitly accepts** the proposal,
[netblueprint](../netblueprint/SKILL.md) produces the final topology package for the IaC stage.
