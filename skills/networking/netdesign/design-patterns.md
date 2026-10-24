# Design Patterns — Topologies, Addressing, Routing, Failure Domains

> The network family's physical-design standard: proven patterns and the method for applying them.
> It is Azure-first, because that is the most common target, with AWS/GCP and on-prem equivalents
> named. Theory is in [`theory.md`](theory.md) (§N) and
> [`graph-theory.md`](graph-theory.md) (G-N). The model contract is in
> [`topology-modeling.md`](topology-modeling.md).

## 1. Realize the requirements, don't decorate them

- Start from **critical pairs** and **zones**, not from products. A firewall SKU is a detail. "App
  reaches database on 5432 only, from the app zone only, with two independent paths" is the design.
- Each pattern below trades something. Name the trade in the design, so the reviewer can disagree with
  the trade rather than with the drawing.
- Prefer the platform's native construct over a hand-built equivalent when it meets the requirement.
  It is managed, patched and zone-redundant by default: Azure Firewall over a single NVA VM, a NAT
  Gateway over SNAT on VMs.

## 2. Topology patterns

| Pattern | Use when | Trade-off | Graph signature |
|---|---|---|---|
| **Hub-and-spoke** (Azure hub VNet + spokes; AWS Transit Gateway; GCP hub VPC) | Several workloads share inspection, egress and hybrid connectivity | The hub is a designed condensate (G10). All resilience moves into it, so it must be zone-redundant and κ ≥ 2 to every spoke. Spoke-to-spoke traffic goes through the hub. | Star around a redundant hub. Low clustering, negative assortativity (G7). |
| **Virtual WAN / managed hub** | Many branches or regions, and you want provider-managed transit | Less control over routing detail. Fewer moving parts to operate. | Mesh of hubs, stars below |
| **Leaf-spine (Clos)** | Data center or private-cloud fabric with heavy east-west traffic | More switches and links. In exchange there are no STP-blocked links, ECMP everywhere, and graceful degradation (§9). | Complete bipartite between tiers. Every leaf pair has κ = number of spines. |
| **Three-tier campus** (access / distribution / core) | Large on-prem campus with user access | STP domains must be kept small. Routed access shrinks them (§8). | Tree with redundant uplinks. Check bridges at access. |
| **Branch** (dual-WAN router or SD-WAN edge) | Remote sites | A single CPE is an articulation point. Dual CPE or an LTE backup with tracking fixes it. | Leaf on a bridge unless dual-homed |
| **Flat** | Labs, very small sites only | No segmentation and one blast radius (§11) | One component, one zone. Avoid for production. |

## 3. The addressing method

1. **Reserve one top-level private block per organization** (e.g. `10.0.0.0/8`), excluding anything
   already used on-prem, by partners, or by acquired companies. Write the exclusions down.
2. **Split by region or site**, with aligned blocks of equal size and room for at least double the
   current count (e.g. one `/12` or `/14` per region).
3. **Split by environment** within the region (prod, non-prod, shared/hub, DR). DR gets **its own**
   space, never a copy of prod's, so that failover peering is possible (audit-lenses §1).
4. **Split by tier or function** within the environment (edge, app, data, management, gateway
   subnets). Size them for the workload plus at least 50% headroom. Cloud-reserved addresses (Azure 5
   per subnet; AWS 5) and platform subnet minimums (`GatewaySubnet` /27, `AzureFirewallSubnet` /26,
   AKS node and pod ranges) set the floors.
5. **Every level summarizes into one prefix at the level above** (§3). Check: the covering set of each
   environment is one prefix.
6. **Document the reserve** as reserve, in the IPAM or the design table.
7. **Kubernetes.** Pod and service CIDRs come out of the plan, even when overlay networking means they
   are not routed today. "Not routed today" is how overlaps are born.
8. **IPv6.** A `/48` per site or region, a `/64` per subnet, no NAT66. Dual stack where the platform
   supports it.

Every allocation carries `id`, `cidr`, `parent` and `purpose` in `networks[]`.

## 4. Segmentation design

- **Zones by trust:**
  - `internet` (0)
  - `edge`/`dmz` (1)
  - `app` tiers (2)
  - `data` (3)
  - `mgmt` (3, separate)
  - `partner` (1–2)
  - `shared-services` (2)

  Adjust per estate, but every zone gets a trust level and a purpose.
- **Default-deny at every zone boundary.** The NSG/SG/NetworkPolicy deny is explicit, and the platform
  default is cited where it is implicit.
- **Flow matrix.** Every allowed zone pair lists protocol/ports and the reason. Prefer
  application-identity sources (ASGs, service tags, Kubernetes label selectors) over CIDRs, so rules
  follow workloads.
- **East-west inside a zone** is denied by default where tiers share a subnet (microsegmentation).
- **Egress** leaves through a controlled point with an allow-list, or at least a logging firewall.
- **Management** is reached only through a bastion or jump zone. There are no management ports
  published to the internet, ever (segmentation.md).
- **Inspection placement.** Every inter-zone flow that must be inspected crosses the firewall in
  **both** directions. Pair the route tables so return paths are symmetric (§12, routing.md).

## 5. Routing design

- **Statics at stubs, a protocol where topology changes** (§5).
- **OSPF:** area 0 as the backbone, summaries at ABRs, authentication on every adjacency, passive on
  host-facing interfaces (§6).
- **BGP** at administrative edges: on-prem ↔ cloud (ExpressRoute/Direct Connect/VPN), internet edge,
  SD-WAN. Prefix filters in both directions, max-prefix limits, and announce only your own aggregates
  (§6).
- **Cloud route tables.**
  - `0.0.0.0/0` → the firewall for spokes that must inspect egress.
  - Matching UDRs for the hub's view of each spoke, so traffic is symmetric.
  - Gateway route propagation disabled where it would bypass inspection.
- **Peering is not transitive.** Spoke-to-spoke reachability is designed explicitly, through the hub
  firewall or a virtual hub, never assumed (topology-modeling M2.3).
- **Hybrid failover.** ExpressRoute primary with VPN backup. Use BGP attributes (local preference /
  AS-path) so the backup is used only when the primary is down, and state how it is tested.

## 6. Failure domains and redundancy

- Every critical pair has **node connectivity ≥ 2 with independent fate** (G5):
  - two devices in different zones or racks;
  - two circuits from different carriers, or at least through different entries;
  - two tunnels to two gateways;
  - zone-redundant SKUs for gateways, firewalls, NAT and load balancers.
- **Model shared fate explicitly**: a config-synced HA pair, a single region, a single carrier. Then
  decide whether each is accepted risk.
- **Hubs are allowed. Unexamined hubs are not.** For every node with high betweenness (G6), state its
  redundancy, its blast radius, and what targeted removal of it does (G9).
- **L2 domains stay small.** Routed access, MLAG/vPC instead of STP-blocked redundancy where possible,
  and deliberate root placement where STP remains (§8).
- **Region-level DR** has its own address space, pre-provisioned connectivity, and a documented
  cut-over.

## 7. Services

| Service | Pattern |
|---|---|
| DNS | Two resolvers per site or hub (Azure DNS Private Resolver, Route 53 Resolver, Cloud DNS). Private zones linked to every consuming network. Conditional forwarding to and from on-prem. |
| Private endpoints | One private endpoint per PaaS dependency in the consuming region. Its `privatelink` zone linked centrally. Public network access disabled. |
| Egress / NAT | NAT Gateway or firewall SNAT with a stable set of public IPs sized for SNAT ports. No per-VM public IPs. |
| Load balancing | Zone-redundant. Health probes that test the application. Backends in at least two failure domains. |
| Hybrid gateways | Active/active VPN, two ExpressRoute circuits or one circuit plus VPN, BGP everywhere. |
| Remote access | Bastion or ZTNA for administrators, never public RDP/SSH. User VPN with full tunnel, or posture-checked split tunnel. |

## 8. Security baseline

- Management protocols encrypted and authenticated only (SSH, HTTPS, SNMPv3 authPriv, NETCONF/SSH),
  with centralized AAA (§14).
- Tunnels: IKEv2, AES-GCM, SHA-2, DH ≥ 14 or ECDH, PFS, certificates where feasible (§13).
- Flow logs and device syslog to a central workspace. NTP everywhere. IDS/IPS or threat intelligence at
  the internet edge (§12).
- No secrets in the design or the model. Reference the secret store by name.

## 9. Modeling checklist

- [ ] Requirements, assumptions, open questions stated.
- [ ] Critical pairs listed, with why.
- [ ] Zones with trust levels; flow matrix; default-deny everywhere.
- [ ] Addressing plan: hierarchical, aligned, summarizable, reserve documented, no overlap with
  anything connected or planned to be.
- [ ] Pattern chosen, with its trade-off stated.
- [ ] Routing: protocol choices, summaries, external filters, symmetric inspection paths.
- [ ] Services redundant across failure domains.
- [ ] Every critical pair κ ≥ 2 after shared-fate contraction. Graph results attached.
- [ ] Target `topology.json` valid, with IDs stable against the audit's model.
- [ ] Audit findings traced (redesigns).
