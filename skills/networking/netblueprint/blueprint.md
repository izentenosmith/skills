# Blueprint — The Accepted Topology Package

> What netblueprint hands over: the final diagrams, the companion design document that explains them,
> and the accepted `topology.json`. The model contract is
> [`topology-modeling.md`](topology-modeling.md). The drawing rules are
> [`diagram-conventions.md`](diagram-conventions.md). Theory references point into
> [`theory.md`](theory.md) and [`graph-theory.md`](graph-theory.md).

## 1. Package layout

```text
<out>/blueprint/
  network-design.md           the companion document (template below)
  topology.json               meta.stage = "blueprint", meta.status = "accepted"
  logical-topology.drawio     page "Logical topology (L3)", marked accepted
  segmentation.drawio         page "Segmentation (zones and flows)", marked accepted
  physical-topology.drawio    page "Physical topology (L1/L2)", only when on-prem scope exists
```

The three artifact types say the same thing three ways. `topology.json` is authoritative. The
diagrams draw it, and the document explains it. A disagreement between them is a defect in the
package, not a judgement call for the reader.

## 2. The handoff contract for the IaC skill

The IaC skill reads `topology.json` and `network-design.md`, and nothing else from this family. To be
implementable, the package guarantees:

- **Every network** has `id`, `cidr`, `parent`, `purpose`, and a platform hint in
  `attrs.platform`: `azure`, `aws`, `gcp`, `onprem` or `k8s`.
- **Every node** has `kind`, `zone`, `site`, and the decided product class in `attrs.product`, when
  the design chose one (`azure-firewall-premium`, `vpn-gateway-vpngw2az`, `fortigate-ha`), with
  `attrs.zones` (availability zones) where relevant.
- **Every edge** has its `kind`, and `attrs` that carry what implementation needs: protocol and ASNs
  for adjacencies, transit flags for peerings, crypto profile name for VPNs, prefix and next hop for
  routes.
- **Every flow** is implementable as written: zones resolvable to networks, `proto`, `ports`,
  `action`, `priority`, and a description in `attrs.reason`.
- **Every zone** has a `trust` level and an explicit default-deny flow.
- **Secrets are referenced, never included.** `attrs.secret_ref` names the vault entry for PSKs and
  passwords.
- **Nothing is implicit.** If the IaC skill would have to guess, the package is incomplete. List the
  gap in `network-design.md` §10.

## 3. `network-design.md` template

```markdown
# <Network> — Network design (accepted)
> Proposal: <path> — accepted <date> by <who/as stated>. Design: <path>. Model: topology.json
> (<source_version>). Diagrams: logical-topology.drawio, segmentation.drawio[, physical-topology.drawio].

## 1. Purpose and scope
What this network is for, which sites/regions/subscriptions it covers, what is out of scope.

## 2. Reading the diagrams
One paragraph per diagram: what the view shows, how to read its glyphs (point to the legend), and
the three things a reader should notice first.

## 3. Critical pairs and failure domains
| Pair | Why it matters | Node κ | Edge κ | Cut set before → after | Shared fate accepted |
|------|----------------|-------:|-------:|------------------------|----------------------|
Graph results from netgraph: articulation points (none expected on critical pairs), top betweenness
nodes with their redundancy, robustness under targeted vs random removal (graph-theory G4–G9).

## 4. Addressing plan
| Network | CIDR | Parent | Purpose | Platform | Reserve |
|---------|------|--------|---------|----------|---------|
Summary prefixes per region/environment; IPv6 plan or exclusion; exclusions reserved for on-prem/partners.

## 5. Zones and flow matrix
| Zone | Trust | Purpose | Member networks | Default |
|------|------:|---------|-----------------|---------|
| From → To | Proto/ports | Reason | Flow IDs |
|-----------|-------------|--------|----------|
Management plane access path.

## 6. Routing
Protocols and where, ASNs, areas, summaries, external filters, route tables/UDRs and why, symmetric
inspection paths, hybrid failover behaviour.

## 7. Services
DNS (resolvers, zones, forwarding), DHCP, egress/NAT (public IPs, SNAT sizing), load balancers
(probes, zones), private endpoints, gateways and circuits.

## 8. Security baseline
Management protocols and AAA, tunnel crypto profiles (by name), logging and flow logs, NTP, IDS/IPS
placement. Secret references by vault name only.

## 9. Traceability
| Decision | Proposal register row | Audit finding(s) | Theory |
|----------|----------------------|------------------|--------|

## 10. Assumptions, open questions, and implementation notes for IaC
What the IaC skill must not guess; unresolved 🔬 flags and the decision each affects; ordering
constraints from the proposal's cut-over plan.
```

## 4. Consistency checks before handing over

- [ ] `topology.json` validates, and netgraph reports no Critical/High finding and κ ≥ 2 for every
  critical pair. Any accepted exception is listed in §3 with its acceptance.
- [ ] Every network, zone, flow and node in the document exists in `topology.json` with identical
  values.
- [ ] Every diagram passes the [diagram-conventions.md](diagram-conventions.md) checklist, and its
  cell IDs match the model.
- [ ] No secret value anywhere in the package.
- [ ] §10 lists every remaining gap. An empty §10 is a claim; make it only when it is true.
