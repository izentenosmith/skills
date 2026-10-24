# Audit Lenses — Cross-Cutting Inspection

> Lenses that span every domain. The domain rubrics grade one concern (addressing, segmentation, …).
> These lenses grade a network or an estate as a whole. Theory terms are defined in
> [`theory.md`](theory.md) and [`graph-theory.md`](graph-theory.md).
>
> **Scope reminder:** the audit judges **static evidence only**. See [Explicitly
> excluded](#explicitly-excluded).

## 1. Dead, duplicate and orphaned networks

- **Dead networks.** VNets, VLANs or sites with no attached workloads, no routes in and no flows. Every
  one of them carries cost (address space, rule surface, confusion) and has zero value. Usage is rarely
  in the evidence: ask, or flag 🔬.
- **Duplicates.** An environment that copies another's address space and policy (a `prod` copied into
  `dr` with the same `10.1.0.0/16`). This is decidable by comparing `networks[]` and `flows[]`.
  Duplicated address space is harmless until the two are connected, and then it is a High overlap (§3).
- **Orphaned policy.** NSGs not associated with any subnet or NIC, ACLs not applied to any interface,
  NetworkPolicies whose selectors match nothing, route tables with no association. They are dead
  policy, and they mislead the next engineer. Record them, but give them no `flows[]` entries
  (topology-modeling M3).

## 2. Drift: documented versus actual

- **IPAM vs configs.** Prefixes in the IP plan that no config uses, and configured prefixes missing
  from the plan. Each one is a single-source-of-truth failure: the next allocation will collide.
- **Diagram vs configs.** The existing diagram claims links, devices or redundancy that the
  configuration does not show (topology-modeling D5). The configuration wins. The claim becomes a 🔬
  flag if it might live outside the evidence set.
- **IaC vs portal.** Resources referenced by ID but not declared (`data` sources, hardcoded resource
  IDs, `ignore_changes` on rules) mean part of the network is managed outside code. That is a ⚠️ proxy
  for click-ops drift.

## 3. Dark space and unmanaged devices

- Interface addresses outside every declared network. Next hops pointing at addresses nobody owns.
  Peers and neighbours with no config in the evidence. Each one is a node the audit cannot see into:
  model it as `inferred:` and flag 🔬.
- Large unused allocations are not defects on their own (growth reserve is good, §3). Unused space
  that nobody documented as reserve is an addressing finding.

## 4. Coupling across networks

- Every peering, VPN, shared firewall, shared DNS zone, shared NAT gateway or transit hub between two
  networks is an edge in the **coupling graph**. Count edges by source → target and by type. netpropose
  derives migration and cut-over order from this list.
- **Shared dependencies.** A node that lies on the critical pairs of several networks — the hub
  firewall, the single ExpressRoute circuit, one DNS forwarder — is an estate-level articulation point
  (G4) even when each network looks redundant on its own. Report these in the synthesis.
- **Transitive trust.** Network A trusts B, and B trusts C, so A is effectively reachable from C unless
  B filters. Follow the coupling graph two hops out from every zone with trust ≥ 2.

## 5. Secrets and sensitive data in evidence

- Configs and IaC commonly carry credentials: `enable secret`, `password 7`, `snmp-server community`,
  IPsec pre-shared keys, Terraform `shared_key`, `admin_password`, kubeconfig tokens. **Never reproduce
  the value.** Record its kind, location and weakness: plaintext, type-7 (reversible), default value,
  or shared across devices.
- A secret committed to a repository is a security finding (security.md) in its own right, whatever
  its strength.

## 6. Growth and evolution

- Networks grow by preferential attachment: new links go to the node that is easiest to connect to,
  usually the existing hub (G10). Look for the signature. One firewall, hub VNet or core switch
  accumulates a large share of all edges (hub concentration) and a high betweenness, and the newest
  connections all go there. That is the network becoming fragile to targeted failure (G9), even
  if every individual change looked reasonable.
- Removal matters too. Decommissioned sites whose routes, rules and peerings remain are the network
  equivalent of dead schemas.

## Explicitly excluded

Not judged, because static evidence cannot show it. Each becomes a 🔬 flag when it matters:

- Utilization, latency, loss, jitter and capacity headroom (§2).
- Whether a route is installed or a rule is ever hit.
- Real failover time and whether failover actually works.
- Wireless coverage and RF conditions.
- Whether a device or network is still in use.
- Patch levels and CVE exposure of device firmware, unless the version string is in the evidence. A
  version string is a ⚠️ proxy, not proof.
