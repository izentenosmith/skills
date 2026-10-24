---
name: netdesign
description: Design a new computer network, or revise an audited one, from requirements, an audit or an existing topology — addressing plan, zones and segmentation, routing, network services and failure domains — using networking theory, graph-theoretic resilience and proven topology patterns. Produces a reviewable design and a target topology.json. Use for network architecture, landing-zone or site design, IP planning and redesign work; it designs only and never writes IaC or touches devices.
---

# netdesign

Design the **logical network** — addressing, zones and flows, routing, services, failure domains —
before choosing products, SKUs or vendor syntax. This skill can run on its own for a new network, or
after [netaudit](../netaudit/SKILL.md) for a redesign. It proposes a design. It does not apply
changes, write IaC or push configuration.

## Choose the mode

| Mode | Input | Output |
|---|---|---|
| New design | Requirements, workload inventory, sites, compliance constraints | Target design and a target `topology.json` |
| Audited redesign | An audit (findings, scores, the recovered `topology.json`) | A corrected design. Every material change is traced to an audit finding or a stated requirement. |
| Design review | An existing design, diagram or topology | Findings and improvement recommendations. Rewrite only when asked. |

If you are revising an existing network without an audit, say so. Proceed with the evidence
available, mark unknowns, and recommend netaudit when a defensible assessment is needed. Never claim
runtime properties (throughput, latency, failover time) from static evidence.

## Method

1. **Read the companion references**: [theory.md](theory.md) and [graph-theory.md](graph-theory.md)
   for the principles, [topology-modeling.md](topology-modeling.md) for the model contract, and
   [design-patterns.md](design-patterns.md) for the patterns and the addressing method.
2. **State requirements, assumptions and open questions.** Cover sites and regions, workloads and
   their tiers, users and partners, compliance zones, growth horizon, availability objectives per
   service, and the target platform(s). Never silently turn an assumption into a constraint.
3. **Name the critical pairs** first. They are the reachabilities that *are* the service, and every
   resilience decision is measured against them (graph-theory G5).
4. **Zones and flows.** Define zones by trust and function, with a trust level for each. Write the
   **flow matrix** (zone × zone → allowed protocol/ports, with the reason), and put default-deny
   everywhere else (theory §11–§12). Give the management plane its own zone.
5. **Addressing plan.** Use the hierarchical, summarizable method in design-patterns.md §3: top-level
   allocation, then region/site, then environment, then tier, with aligned blocks and a documented
   reserve. Leave no overlap with anything connected or planned to be connected, on-prem included.
   Plan IPv6 or state it out of scope.
6. **Topology pattern and routing.** Pick the pattern (hub-and-spoke, virtual WAN, leaf-spine,
   three-tier campus, branch) and explain why. Decide where routing is dynamic and where static, where
   summaries are, how external sessions are filtered, and how symmetric paths through stateful devices
   are guaranteed (theory §5–§7).
7. **Services.** DNS (resolvers, private zones, forwarding), DHCP, egress/NAT, load balancing, private
   endpoints and gateways, each redundant across failure domains or with the risk stated.
8. **Failure domains and resilience.** Make every critical pair reach node connectivity ≥ 2 with
   independent fate. Keep hub concentration and betweenness on critical paths deliberate. When the
   harness is available, run `harness/netgraph.py` on the target `topology.json` and include its
   output (G4–G9).
9. **For an audited redesign**, map each material change to its audit finding ID, and separate
   preserved behaviour from intentional behaviour change.
10. **Validation checklist**: no overlap, every flow justified, every zone default-deny, every
    critical pair κ ≥ 2, management isolated, no secrets in the design, open questions listed.

## Deliverable

A reviewable `design.md` with:
- scope, requirements and assumptions;
- critical pairs;
- zones and the flow matrix;
- the addressing plan table;
- the topology pattern and routing design;
- services;
- failure domains and the graph results;
- audit traceability (for redesigns);
- the validation checklist and open questions.

Also deliver a target **`topology.json`** following [topology-modeling.md](topology-modeling.md),
with `meta.stage = "design"` and `meta.status = "proposed"`. Keep the IDs of surviving elements from
the audit's model. Keep the logical design separate from product and SKU choices, which come last and
are labelled as such.

When diagrams are requested or the workflow continues, hand the design to
[netdiagram](../netdiagram/SKILL.md). A full recommendation that incorporates audit evidence and
diagrams belongs to [netpropose](../netpropose/SKILL.md).
