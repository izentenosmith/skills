---
name: netblueprint
description: Produces the final network topology package once a network proposal is explicitly accepted — draw.io topology diagrams, a network-design document that explains them, and the accepted topology.json for IaC. Use when a netpropose proposal has been accepted and the user wants the final network design, the blueprint, or the package to hand to IaC; with no recorded acceptance it stops and asks. It never writes IaC or configures devices; structural changes route back through netdesign.
---

# netblueprint

Produce the **accepted topology package** from an accepted proposal and its design. This is the final
network-workflow stage. Its output is the specification that a separate IaC skill implements. **It
writes no Terraform, Bicep, ARM, Ansible or device configuration, and it never connects to a network,
cloud or device.**

## When NOT to use

- The proposal is not yet accepted → `netpropose`.
- The topology needs a structural change → `netdesign`.
- Only diagrams of a design, with no accepted proposal → `netdiagram`.
- Writing the IaC that implements the topology → `terraform`.

## Required inputs

- An **explicitly accepted** proposal, plus the user's statement of acceptance.
- The design (`design.md`) and the target `topology.json` the proposal refers to.
- The proposal's diagrams (`logical-topology.drawio`, `segmentation.drawio`, and
  `physical-topology.drawio` when applicable).
- The requested output location and any naming conventions.

If the proposal, the design and the diagrams disagree, **stop** and describe the mismatch. If a
decision the package needs is missing (a CIDR, a zone's trust level, a flow's ports, a critical pair),
ask for it, or mark the package incomplete. Never fill a structural gap silently.

`scripts/netgraph.py` in this folder validates the model and cross-checks the diagrams against it. It
needs only standard-library Python and writes nothing, so it is safe to run on the inputs before
acceptance too.

## When acceptance is missing

A proposal marked Proposed, Draft or In review, or one with nothing recording its acceptance, is not
accepted. That holds however complete it is, however close its review date, and whatever the request
implies. Do not draft the package "ready for acceptance", do not mark anything accepted, and do not
edit the proposal's status. **Write no package file and touch no input.** Reply with these six
things, then stop:

1. **Status and source.** The proposal's status as written, its version or date, and where acceptance
   would come from: the board, meeting or approver it names.
2. **The acceptance record you need.** Who accepted it, on what date, which version or revision, and
   whether as written or with changes. `network-design.md` opens with exactly this record, so ask for
   each part.
3. **The exceptions acceptance must cover.** Anything the package would otherwise fail on
   ([blueprint.md](blueprint.md) §4): a critical pair the proposal leaves below κ 2, an open 🔬 flag
   that a decision depends on, a deferred retirement. Name each, with its κ or flag, and say the
   acceptance has to state it explicitly.
4. **Readiness, checked read-only.** Whether the proposal, the design and the diagrams agree: run
   `scripts/netgraph.py diagrams` and `analyze` on the inputs and quote the result. Check the target
   model against the IaC handoff contract ([blueprint.md](blueprint.md) §2) rule by rule, and list
   the elements that break each one: they are the fields acceptance time will have to supply,
   because the IaC skill must never guess. Name any input the package will need that the workspace
   lacks, such as an audit that the traceability table (§9) would cite.
5. **What acceptance unlocks.** The package you will produce: `network-design.md`, `topology.json`
   with `meta.stage = "blueprint"` and `meta.status = "accepted"`, and which `.drawio` views, marked
   accepted, this model needs.
6. **Nothing produced.** Say plainly that nothing was written or changed.

## Produce and iterate

1. **Confirm versions.** The accepted proposal, the design, the target `topology.json` and the
   diagrams must be the same versions. Treat the proposal's decisions and the design's model as
   authoritative.
2. **Finalize `topology.json`.**
   - Set `meta.stage = "blueprint"`, `meta.status = "accepted"`, and add the proposal path and the
     acceptance date.
   - Apply only the decisions the proposal records. Keep every ID stable.
   - Validate it: schema, no overlap, every zone default-deny, every critical pair κ ≥ 2. Run
     `python3 <this skill's folder>/scripts/netgraph.py analyze topology.json` (standard-library
     Python) and put its critical-pair table and findings in `network-design.md` §3. Exit 1 lists
     schema errors: the package is not ready until there are none. Without Python, validate by hand
     and say so.
3. **Finalize the diagrams** in the convention of [diagram-conventions.md](diagram-conventions.md),
   marked `accepted`, with cell IDs equal to the final model's IDs. Reuse the proposal's diagrams
   wherever they already match. Redraw only what the accepted decisions changed, and say what changed.
   Check them with `python3 <this skill's folder>/scripts/netgraph.py diagrams <out>/blueprint
   --topology <out>/blueprint/topology.json` until it prints `ok`.
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
