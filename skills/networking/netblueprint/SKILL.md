---
name: netblueprint
description: After a network proposal is explicitly accepted, produce the final network topology package — the canonical draw.io topology diagrams, a companion network-design document that explains them (addressing plan, zones and flow matrix, routing, services, failure domains), and the accepted topology.json that a separate IaC skill implements. Never writes IaC, never configures devices; structural changes route back through design.
---

# netblueprint

Produce the **accepted topology package** from an accepted proposal and its design. This is the final
network-workflow stage. Its output is the specification that a separate IaC skill implements. **It
writes no Terraform, Bicep, ARM, Ansible or device configuration, and it never connects to a network,
cloud or device.**

## Required inputs

- An **explicitly accepted** proposal, plus the user's statement of acceptance.
- The design (`design.md`) and the target `topology.json` the proposal refers to.
- The proposal's diagrams (`logical-topology.drawio`, `segmentation.drawio`, and
  `physical-topology.drawio` when applicable).
- The requested output location and any naming conventions.

If the proposal, the design and the diagrams disagree, **stop** and describe the mismatch. If a
decision the package needs is missing (a CIDR, a zone's trust level, a flow's ports, a critical pair),
ask for it, or mark the package incomplete. Never fill a structural gap silently.

## Produce and iterate

1. **Confirm versions.** The accepted proposal, the design, the target `topology.json` and the
   diagrams must be the same versions. Treat the proposal's decisions and the design's model as
   authoritative.
2. **Finalize `topology.json`.**
   - Set `meta.stage = "blueprint"`, `meta.status = "accepted"`, and add the proposal path and the
     acceptance date.
   - Apply only the decisions the proposal records. Keep every ID stable.
   - Validate it: schema, no overlap, every zone default-deny, every critical pair κ ≥ 2. With the
     harness, run `harness/netgraph.py analyze` and include the output.
3. **Finalize the diagrams** in the convention of [diagram-conventions.md](diagram-conventions.md),
   marked `accepted`, with cell IDs equal to the final model's IDs. Reuse the proposal's diagrams
   wherever they already match. Redraw only what the accepted decisions changed, and say what changed.
4. **Write `network-design.md`**, the companion that explains the diagrams, from the template in
   [blueprint.md](blueprint.md). It is written for the engineers who will build and operate the network
   and for the IaC skill that will implement it: every table matches `topology.json`, and every
   diagram is explained view by view.
5. **Check internal consistency.**
   - Every network in the document and the diagrams exists in `topology.json` with the same CIDR.
   - Every flow-matrix row maps to `flows[]`.
   - Every critical pair is listed with its κ and cut set.
   - No secret appears anywhere.

   State anything that could not be verified.
6. **Treat feedback as iteration.** If it changes networks, zones, flows, routing, services or
   redundancy (anything structural), route it through [netdesign](../netdesign/SKILL.md), regenerate
   the diagrams with [netdiagram](../netdiagram/SKILL.md), and revise the proposal with
   [netpropose](../netpropose/SKILL.md). The revised proposal must be accepted before its blueprint is
   produced. For wording, layout or naming-only changes that leave the model unchanged, update the
   package and state that the model is unchanged.

## Output

Return the paths to `network-design.md`, `topology.json` and each `.drawio` file, plus a short
inventory of the package. Identify assumptions, unverified items, and any iteration that needs renewed
acceptance. State plainly that nothing has been built or changed, and that implementation belongs to
the IaC skill.
