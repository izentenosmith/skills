---
name: netdiagram
description: Draws editable draw.io network topology diagrams — logical L3, segmentation (zones, VLANs, firewalls and flows), and physical L1/L2 when on-prem evidence exists — from a network design, an audit's topology.json or other network structure, with stable IDs. Use when the user wants a network drawn or redrawn — "diagram this network", "draw the topology", "show the zones and flows" — or as the step after netdesign or netaudit and before netpropose. It never changes the design or configures anything.
---

# netdiagram

Create clear, editable draw.io diagrams of a network in the convention defined in
[diagram-conventions.md](diagram-conventions.md):

- **Logical topology (L3)**: networks with CIDRs, routers, gateways, firewalls, peerings, tunnels,
  route steering.
- **Segmentation (zones and flows)**: zones ordered by trust, allowed flows as labelled arrows,
  default-deny stated, the management plane separate.
- **Physical topology (L1/L2)**: required only when on-prem device evidence exists. Links, LAGs,
  trunks/VLANs, HA pairs.

This skill can run on its own from a supplied design or topology, or consume the output of
[netdesign](../netdesign/SKILL.md) or [netaudit](../netaudit/SKILL.md). Never mix L2 and L3 semantics
on one page.

## Inputs and evidence

- Prefer a `topology.json` ([topology-modeling.md](topology-modeling.md)). It is the source of truth.
  With only a design document or configs, build the model first, label inferred elements, and say so.
- Preserve source names and IDs. **Each draw.io cell ID equals its node, edge, network or zone ID in
  `topology.json`.** That is what lets the drawing be cross-checked against the model.
- Distinguish facts from inferences. An `inferred:` element is drawn with the inferred style (dashed
  outline) and listed in the provenance note.
- If the input lacks information a view needs, draw the supported facts and annotate the unknowns. Do
  not invent devices, links or redundancy.

## Output and validation

- Save native, editable `.drawio` files named exactly `logical-topology.drawio`,
  `segmentation.drawio` and, when applicable, `physical-topology.drawio`. Use uncompressed,
  well-formed `mxfile` XML, with the page names and visible legend the conventions require.
- Author stable semantic cell IDs and all required geometry. Never deliver a flattened image as a
  substitute for the editable files.
- **Validate before handing off:**
  - each file is well-formed XML with the required page name and legend;
  - every network container's label contains a CIDR that parses;
  - every cell ID that names a model element exists in `topology.json`, and every critical-pair
    endpoint appears on the logical page;
  - every flow arrow on the segmentation page matches an `allow` in `flows[]`, and every zone carries
    its default-deny badge: a `deco-deny-<zone id>` text cell inside the zone, never an arrow.

  The script in this skill's folder checks all but the last, and lists every problem it finds:

  ```bash
  python3 <this skill's folder>/scripts/netgraph.py diagrams <output folder> --topology topology.json
  ```

  It needs only standard-library Python. Fix what it lists and run it again until it prints `ok`. Then
  check the arrows and badges by reading the segmentation page against `flows[]`. Without Python, walk the
  checklist in [diagram-conventions.md](diagram-conventions.md) §7 by hand, and say so.

  If a draw.io renderer or the `drawio-skill` validator is available, inspect the rendered pages for
  overlap, clipping and unreadable labels. Report when visual rendering could not be checked.
- When updating an existing diagram, preserve its layout and styles where practical, and explain any
  semantic ambiguity that affects the drawing.

The diagrams are inputs to [netpropose](../netpropose/SKILL.md) for the recommendation, and to
[netblueprint](../netblueprint/SKILL.md) after acceptance. For specialized draw.io authoring, layout,
or export workflows, use the available draw.io skill or tooling.
