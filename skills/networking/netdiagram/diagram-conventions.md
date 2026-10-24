# Diagram Conventions — The Canonical Network Views

> The network family's equivalent of Barker notation: one convention, enforced across every stage and
> checked by the harness (`harness/networkflow.py`). The model is
> [`topology-modeling.md`](topology-modeling.md). These rules say how to draw it.

## 1. Required files and pages

| File | Page name (exact) | Required when | Shows |
|---|---|---|---|
| `logical-topology.drawio` | `Logical topology (L3)` | always | networks and subnets with CIDRs; routers, gateways, firewalls, LBs, DNS; peerings, tunnels, route steering; internet / on-prem / cloud boundaries |
| `segmentation.drawio` | `Segmentation (zones and flows)` | always | zones ordered by trust; allowed flows; default-deny; management plane |
| `physical-topology.drawio` | `Physical topology (L1/L2)` | on-prem device evidence exists | switches, cabling, LAGs, trunks and VLANs, HA pairs, sites/racks |

Each page carries:
- a **title**: `<network name> — <view> — <stage: as-is / proposed / accepted>`;
- a **legend** box whose label contains the text **`Network diagram conventions`** and explains every
  glyph used on the page;
- a **provenance note**: the source `topology.json` and its `meta.source_version`, the date, and the
  number of inferred elements.

Additional pages (per-region detail, a flow table) are allowed after the required page.

## 2. IDs

- Every node, network, zone and edge drawn gets the **cell ID equal to its `topology.json` ID**.
- Decorative cells (title, legend, provenance, boundary labels) use IDs prefixed `deco-`, so the
  cross-check ignores them.
- IDs never change between the as-is, proposed and accepted diagrams for elements that survive. A
  reader diffs the files by ID.

## 3. Logical topology (L3)

| Element | Glyph |
|---|---|
| Boundary (internet, on-prem site, cloud region, subscription) | Large rounded container, light fill, label top-left. The internet is a cloud shape. |
| VNet / VPC / site LAN | Container, solid border, label `name` + newline + `CIDR` |
| Subnet | Nested container inside its parent, label `name` + newline + `CIDR`. **Every network container's label must contain its CIDR.** |
| Router, gateway, firewall, LB, DNS, NAT | Icon from **one** family per page: `mxgraph.azure*` or `mxgraph.aws4` for cloud, `mxgraph.cisco19` for on-prem. Label = node ID or name. |
| Routing adjacency | Solid line, label = protocol and domain (`OSPF a0`, `BGP 65010↔12076`, `static`) |
| Peering | Solid line with a double-arrow end, label `peering` plus transit flags if set |
| VPN / IPsec | Dashed line, padlock icon or the `vpn` label, with tunnel count when grouped |
| Route steering (UDR next hop) | Dotted arrow from the subnet to the steering node, label = prefix (`0.0.0.0/0`) |
| Redundancy group | The members' lines share a label suffix `[lag-1]` or `[ecmp-1]` |
| Shared fate | A thin dashed rectangle around the members, labelled `shared fate: <group>` |
| Inferred element | Dashed outline, grey label suffix `(inferred)` |

Layout: untrusted on the left (internet), trusted on the right, or top-to-bottom by the same order.
Hubs are central. Keep the critical pairs' endpoints visible on the page.

## 4. Segmentation (zones and flows)

| Element | Glyph |
|---|---|
| Zone | Container with a fill colour by trust (0 red-tinted → 3 green-tinted), label `zone — trust N — purpose` |
| Member networks | Small boxes inside each zone, with CIDRs |
| Allowed flow | Directed arrow, zone to zone, label `proto/ports` (`tcp/443`), one arrow per distinct flow group, its ID equal to the flow ID or `flowgrp-<from>-<to>` |
| Denied flow worth showing | Red arrow with a bar end, label `deny` + reason |
| Default-deny | A text badge inside each zone: `default: deny in` / `deny out`, citing the mechanism (`NSG 4096 DenyAll`, `NetworkPolicy default-deny`) |
| Management plane | Its own zone, drawn apart (bottom band), with access only from the bastion/jump zone |

Every arrow must correspond to `allow` entries in `flows[]`. Any-any flows, if they exist, are drawn
in red so they cannot be missed.

## 5. Physical topology (L1/L2)

| Element | Glyph |
|---|---|
| Site / rack | Container |
| Switch / router / firewall unit | `mxgraph.cisco19` icon, label = hostname |
| Link | Solid line, label = interfaces and speed (`Gi1/0/48 ↔ Te1/1, 10G`) |
| LAG | Parallel lines bracketed, label `Po10 (2×10G)` |
| Trunk | Line label lists allowed VLANs (`trunk 10,20,99`). An "all VLANs" trunk is drawn in red. |
| HA pair | The two units side by side, with a `HA` connector and the shared-fate rectangle when config-synced |
| STP root | A `root VLAN x` badge on the switch |

## 6. Style rules

- One icon family per page. Don't mix the Azure, AWS and Cisco stencils on one page, except
  boundary-crossing gateways on the logical page, which use the family of the side they belong to.
- Never draw an L2 link on the logical page or an L3 adjacency on the physical page.
- Labels readable at 100%: at least 11 pt, no overlap, no clipping.
- No decorative imagery that obscures CIDRs, protocols or flow labels.
- No secrets anywhere: no PSKs, communities or passwords in labels or notes.

## 7. Validation checklist (also enforced by the harness)

- [ ] Required files present, with exact names. Each is uncompressed, well-formed `mxfile`.
- [ ] The required page name is present in each file.
- [ ] A visible legend containing `Network diagram conventions` is on each required page.
- [ ] Every network container label contains a parsable CIDR equal to the model's.
- [ ] Every non-`deco-` cell ID that names a model element exists in `topology.json`.
- [ ] Every critical-pair endpoint is drawn on the logical page.
- [ ] Every segmentation arrow maps to `allow` flows. Every zone has a default-deny badge.
