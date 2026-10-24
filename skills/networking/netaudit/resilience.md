# Resilience — Failure Domains and the Graph

> Criteria for grading how the network survives failure. This is where network science is the main
> lens: [`graph-theory.md`](graph-theory.md) G4–G10 define the metrics, and the harness computes them
> from `topology.json` (`harness/netgraph.py`). [`theory.md`](theory.md) §8–§9 cover STP and fabric
> topologies. Severity follows [`scoring.md`](scoring.md).

## 🟢 Well done

- **Every critical pair has node connectivity ≥ 2** (G5). No single device or link failure separates
  users from the service, the app from its data, or the site from the internet or the cloud.
- **Redundancy is independent.** Redundant members don't share a power feed, an availability zone, a
  chassis, a config-sync control plane or an upstream carrier, unless that shared fate is stated
  (`attrs.shared_fate`).
- **Fabrics are built for equal-cost paths.** Leaf-spine/Clos with ECMP, so the loss of one spine
  costs capacity, not reachability (§9).
- **L2 loops are controlled.** STP or a loop-free design (routed access, MLAG/vPC) with the root bridge
  placed deliberately (§8).
- **Low hub concentration on critical paths.** No single node carries most of the shortest paths
  between critical pairs. Where one does (a hub firewall by design), it is redundant, and its blast
  radius is stated (G6).
- **Robust under targeted failure**, not only random failure. Removing the top few nodes by degree or
  betweenness doesn't fragment the network (G9).
- **Failure domains are documented**: what a zone, site or device loss takes down.

## 🔴 Not well done

### Single point of failure on a critical pair
**What:** An articulation point (device) or bridge (link) whose loss disconnects a critical pair, so
the pair's node or edge connectivity is 1.
**Why:** By Menger's theorem the number of disjoint paths *is* the number of failures the pair
survives (G5). Connectivity 1 means one failure is an outage.
**Detect:** computed by the harness. ✅ when the elements rest on configured evidence; ⚠️ when they
rest on `inferred:` nodes.
**Severity:** High.

### False redundancy through shared fate
**What:** Two devices or links that look redundant but fail together. Examples: an HA pair with one
synchronized config, two tunnels on one gateway, two circuits from one carrier through one building
entry, both NVAs in one availability zone.
**Why:** Contracting the shared-fate group to one node brings back the articulation point (G4). The
redundancy protects only against independent failures.
**Detect:** `shared_fate` groups, matching zone/rack/carrier attributes. ✅ for configured
attributes; physical paths are 🔬.
**Severity:** High on a critical pair; Medium elsewhere.

### Choke-point concentration
**What:** One node with very high normalized betweenness, carrying most shortest paths, even if it is
redundant.
**Why:** Its failure, compromise or misconfiguration has the largest blast radius. It is the target a
targeted failure or attack would pick (G6, G9).
**Detect:** betweenness and hub concentration computed by the harness. ⚠️ proxy, since high
betweenness can be intended. Report it with the design intent.
**Severity:** Medium; High when it is also a SPOF.

### Fragile under targeted removal
**What:** A robustness curve where removing the top 5–10% of nodes by degree or betweenness
collapses the largest component, while random removal of the same number does not.
**Why:** This is the hub-dominated signature (G9). Random hardware failure is survived, but
coordinated failure (a bad config push to the core, an attack on the hubs) is not.
**Detect:** robustness curves from the harness. ⚠️ proxy. On networks under ~20 nodes, report the
specific nodes, not the curve (G12).
**Severity:** Medium.

### Uncontrolled L2 loops
**What:** Redundant L2 links with STP disabled, no loop protection, or no root bridge priority set.
**Why:** A loop in L2 causes broadcast storms and MAC-table instability that take down the whole
domain (§8).
**Detect:** `spanning-tree` stanzas, root priority, BPDU guard on access ports. ✅.
**Severity:** High.

### Redundancy that cannot fail over
**What:** A standby path with no mechanism to use it: a second ISP with no second default route or
tracking, an ExpressRoute with no BGP failover to VPN, an active/passive pair with no health signal.
**Why:** The second path exists in the graph but not in the forwarding behaviour, so connectivity is 1
in practice.
**Detect:** routing or tracking config for the backup path. ✅ for config; actual failover is 🔬.
**Severity:** High on a critical pair.

## Checklist

Criteria graded across in-scope critical pairs (and forwarding nodes for 5–6):

1. Node connectivity ≥ 2.
2. Edge connectivity ≥ 2.
3. Redundant paths have independent fate (shared-fate contraction keeps connectivity ≥ 2).
4. The backup path is wired into forwarding (tracking, routing, health).
5. No forwarding node holds a disproportionate share of shortest paths without stated intent and
   redundancy (graded per node).
6. L2 domains with redundant links have loop control and a deliberate root (graded per L2 domain).
7. Failure domains are documented for the pair.
