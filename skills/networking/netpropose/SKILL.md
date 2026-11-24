---
name: netpropose
description: Prepare a reviewable recommendation for a computer network using audit evidence, a target network design and topology, and the canonical draw.io topology diagrams — prioritized decisions, cut-over sequencing, risk, validation and rollback. Use when a network audit and/or design needs to become a decision for stakeholders; it never applies changes or writes IaC.
---

# netpropose

Turn evidence and a design into a clear recommendation for decision-makers and implementers. This
skill runs on its own when the user supplies the artifacts. It is also the last stage of the network
family before acceptance.

## When NOT to use

- No audit evidence yet → `netaudit`.
- No target design yet → `netdesign`.
- The topology diagrams are missing → `netdiagram`.
- The proposal is already accepted and the final package is wanted → `netblueprint`.

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
design's `topology.json`: same IDs, same CIDRs, same flows. `scripts/netgraph.py` in this folder
does the mechanical part, read-only:

```bash
python3 <this skill's folder>/scripts/netgraph.py diagrams diagrams/ --topology design/topology.json
python3 <this skill's folder>/scripts/netgraph.py analyze design/topology.json    # target κ per critical pair
python3 <this skill's folder>/scripts/netgraph.py analyze audit/topology.json     # today's, for before → after
```

Quote the connectivity before and after from these runs, not from memory. Without Python, compare
the IDs, CIDRs and flows by hand and say the check was manual. Describe any mismatch and route it back to
[netdesign](../netdesign/SKILL.md) or [netdiagram](../netdiagram/SKILL.md). Do not redraw or silently
repair either artifact.

## Write `proposal.md` — a required step

The deliverable is a file, not a chat message. **Write `proposal.md`** in the structure in
[proposal.md](proposal.md), ending with the acceptance line, to the path the user names or, by
default, next to the inputs: the folder that holds `audit/`, `design/` and `diagrams/`, never inside
them. Then read the file back to confirm it is on disk and complete. The work is not done until it is,
even when you have already drafted the whole proposal in your reply.

Your reply summarizes the recommendation and gives the path to `proposal.md`. The proposal never lives
only in the chat. netblueprint and the change board read it from the file.

## Handoff

For an existing network, the usual sequence is [netaudit](../netaudit/SKILL.md) →
[netdesign](../netdesign/SKILL.md) → [netdiagram](../netdiagram/SKILL.md) → this proposal. For a new
network, start at netdesign. After the user **explicitly accepts** the proposal,
[netblueprint](../netblueprint/SKILL.md) produces the final topology package for the IaC stage.
