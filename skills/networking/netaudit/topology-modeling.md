# Topology Modelling — The Shared Network Model

> The network family's equivalent of the ER-modelling standard. Every stage reads or writes the same
> normalized model, `topology.json`. The audit recovers it from evidence, the design writes the target
> one, the diagrams draw it, the proposal compares the two, and the blueprint hands the accepted one to
> the IaC skill. Theory terms are defined in [`theory.md`](../netaudit/theory.md) (§N) and
> [`graph-theory.md`](../netaudit/graph-theory.md) (G-N). The harness (`harness/netgraph.py`) computes graph
> metrics and address/flow checks from this file, so the shape below is a contract, not a suggestion.

## M0. Three views, one model

A network is described at three levels. Each one answers a different question, and mixing them on one
page or in one node is the most common modelling error.

| View | Question it answers | Main elements | Diagram |
|---|---|---|---|
| **Physical (L1/L2)** | What is cabled or bridged to what, and what fails together? | switches, links, LAG members, trunks, VLANs, HA pairs | `physical-topology.drawio` |
| **Logical (L3)** | Which networks exist, how are they addressed, and how does a packet get from one to another? | networks/subnets, routers, gateways, firewalls, peerings, VPNs, route tables | `logical-topology.drawio` |
| **Policy (zones and flows)** | Who is allowed to talk to whom, on what, and what is denied by default? | zones, trust levels, allowed and denied flows, management plane | `segmentation.drawio` |

`topology.json` holds all three: `nodes` and `edges` for the physical and logical graph, `networks`
for addressing, `zones` and `flows` for policy. The graph view used by the metrics is the undirected
multigraph of `nodes` and `edges`. Flows are directed and are analysed separately.

## M1. The schema

```json
{
  "meta": {"name": "contoso-prod", "source_version": "git 3f2a1c0 / 2026-10-20", "rubric": "v1.0",
           "stage": "audit | design | blueprint", "status": "recovered | proposed | accepted"},
  "nodes": [
    {"id": "fw-core-a", "kind": "firewall", "zone": "transit", "site": "scl-dc1",
     "attrs": {"vendor": "fortios", "ha_peer": "fw-core-b", "shared_fate": "fw-core-cluster"},
     "evidence": "configs/fw-core-a.conf:12"}
  ],
  "edges": [
    {"id": "e-fwa-core1", "a": "fw-core-a", "b": "sw-core-1", "kind": "l2-link",
     "redundancy_group": "lag-fw-core-a", "attrs": {"capacity_mbps": 10000},
     "evidence": "configs/sw-core-1.cfg:88"}
  ],
  "networks": [
    {"id": "snet-app", "cidr": "10.20.1.0/24", "parent": "vnet-prod", "purpose": "app tier",
     "evidence": "infra/network.tf:41"}
  ],
  "zones": [
    {"id": "internet", "trust": 0, "purpose": "untrusted"},
    {"id": "dmz", "trust": 1, "purpose": "published services"},
    {"id": "app", "trust": 2, "purpose": "application tier"},
    {"id": "mgmt", "trust": 3, "purpose": "management plane"}
  ],
  "flows": [
    {"id": "nsg-app-100", "from_zone": "dmz", "to_zone": "app", "proto": "tcp", "ports": "443",
     "action": "allow", "priority": 100, "evidence": "infra/nsg.tf:17"}
  ],
  "critical_pairs": [
    {"from": "internet", "to": "snet-app", "why": "customer traffic to the storefront"}
  ]
}
```

### Field rules

| Field | Rule |
|---|---|
| `id` | Stable, semantic, lowercase-kebab (`fw-core-a`, `snet-app`). The same ID is the draw.io cell ID in every diagram. Never renumber between stages: a node that survives a redesign keeps its ID. |
| `nodes[].kind` | One of `internet`, `onprem`, `site`, `router`, `switch`, `firewall`, `gateway` (VPN, ExpressRoute/Direct Connect, NAT, internet gateway), `lb`, `dns`, `dhcp`, `proxy`, `vnet`, `subnet`, `lan`, `cluster`, `namespace`, `host-group`, `private-endpoint`, `service`. Add a kind only when none fits, and say why in `attrs.note`. |
| `nodes[].zone` | A `zones[].id`. Required for every node that holds or forwards traffic. The reserved zone `internet` holds the `internet` node. |
| `edges[].kind` | `l2-link` (cable, LAG member, bridged segment), `l3-adjacency` (a subnet attached to its router or implicit cloud router, a routing-protocol neighbour), `peering` (VNet/VPC peering, IX peering), `vpn` (IPsec/SSL tunnel), `route` (a static or UDR next hop that steers traffic through a node). |
| `edges[].redundancy_group` | Shared by parallel members of one logical link (LAG members, ECMP paths, the two tunnels of an active/active VPN). Parallel edges are what make a link non-bridging (G4). |
| `networks[]` | Every network also appears as a node with the same `id` (kind `vnet`, `subnet` or `lan`). That is how graph reachability applies to address checks (overlap between *reachable* networks, §3). `parent` names the enclosing network (subnet → VNet). |
| `zones[].trust` | An integer: 0 = untrusted (internet), higher = more trusted. The segmentation diagram orders zones by it. |
| `flows[]` | Directed. `proto` is `tcp`, `udp`, `icmp` or `any`. `ports` is `"443"`, `"1024-65535"`, `"22,3389"` or `"*"`. `from_zone`/`to_zone` may be `"*"` (any). `action` is `allow` or `deny`. `priority`: lower is evaluated first (NSG/ACL order). A default-deny is an explicit `deny` flow `* → <zone>` or `<zone> → *` with the lowest precedence, citing where the platform makes it implicit. |
| `critical_pairs[]` | The source/destination pairs whose reachability *is* the service: users → app, app → database, site → internet, on-prem → cloud. The harness computes node and edge connectivity (G5) for each one. A model with no critical pairs cannot be graded on resilience; say so. |
| `evidence` | A `file:line` reference into the evidence set, or `inferred: <reason>` when the element is a modelling inference. Inferred elements never ground a ✅ decidable finding. |
| `attrs.shared_fate` | Groups nodes that fail together despite being separate boxes: an HA pair with one control plane or config sync, two VMs on one host, two tunnels on one gateway. The harness counts a shared-fate group as one node for connectivity. |
| `attrs.managed_ha` | `true` on a node or edge that the platform makes redundant: a VNet/VPC's implicit router (the `vnet` node), a subnet's attachment edge to its VNet, a zone-redundant managed gateway or firewall with the zones in evidence. The harness never reports these as articulation points or bridges, and never cuts them for connectivity. It is a claim, so it needs `file:line` evidence (the SKU or zones setting). It is ignored on `inferred:` elements. Never set it on customer-run devices (NVAs, VMs, on-prem boxes), whatever their HA configuration — those get `shared_fate` instead. |

## M2. Modelling rules

1. **One thing, one node.** A firewall cluster of two units is two nodes plus a `shared_fate` group,
   because their links fail independently while their configuration does not. A VNet and its subnets
   are separate nodes, joined by `l3-adjacency` edges to the VNet's implicit router (model it as the
   VNet node itself). The implicit router and those attachment edges are provider-redundant, so mark them
   `managed_ha` with the VNet/subnet resource as evidence — otherwise every cloud subnet looks like a SPOF.
2. **Model the path the packet takes, not the one the diagram shows.** A UDR that sends `0.0.0.0/0`
   to an NVA puts that NVA on every path out of the subnet. Draw it as a `route` edge, even though no
   cable exists.
3. **Peering is not transitive.** Two spokes peered to one hub do not reach each other through it
   unless the hub routes (an NVA or virtual hub with gateway transit). Do not add a spoke-to-spoke edge
   that the platform does not provide.
4. **Overlays are edges, not networks.** An IPsec tunnel is a `vpn` edge between its two gateways. The
   networks behind it stay where they are.
5. **Management is a zone.** Out-of-band management interfaces, jump hosts and the controllers that
   push configuration get the `mgmt` zone (§14). A management interface in a data zone is itself a
   finding.
6. **Containers.** A Kubernetes cluster is a `cluster` node. Namespaces are `namespace` nodes and
   usually their own zone. `NetworkPolicy` objects become `flows`. A namespace with no policy is an
   implicit allow-all, and must be written as an explicit `allow * → *` flow with
   `inferred: no NetworkPolicy selects this namespace`. Compose networks are `lan` nodes; services
   attached to two networks are the bridges between them.
7. **Unknowns stay unknown.** If the evidence does not show what is on the far side of an interface,
   add an `onprem` or `site` node with `inferred:` evidence rather than guessing devices.

## M3. Reverse-engineering procedure (audit, Step 1)

Read the evidence once per view, then reconcile.

| Evidence | Read for | Becomes |
|---|---|---|
| Terraform `azurerm_virtual_network` / `azurerm_subnet` | `address_space`, `address_prefixes` | `vnet`/`subnet` nodes, `networks[]`, `l3-adjacency` edges |
| `azurerm_virtual_network_peering` | `allow_forwarded_traffic`, `allow_gateway_transit`, `use_remote_gateways` | `peering` edges (one per direction pair; note asymmetric flags) |
| `azurerm_network_security_group` / `_rule`, `azurerm_subnet_network_security_group_association` | priority, direction, access, prefixes, ports | `flows[]`; the association decides which zone the rule protects |
| `azurerm_route_table` / `_route`, association | `address_prefix`, `next_hop_type`, `next_hop_in_ip_address` | `route` edges to the NVA or gateway |
| `azurerm_virtual_network_gateway`, `_connection`, `azurerm_express_route_*` | SKU, active-active, BGP, shared key (redacted) | `gateway` nodes, `vpn` edges, `redundancy_group` for active/active |
| `azurerm_firewall`, `azurerm_lb`, `azurerm_application_gateway`, `azurerm_private_endpoint`, `azurerm_nat_gateway` | SKU, zones, rules | `firewall`/`lb`/`private-endpoint`/`gateway` nodes, `flows[]` |
| AWS `aws_vpc`/`aws_subnet`/`aws_security_group`/`aws_network_acl`/`aws_route_table`/`aws_vpc_peering_connection`/`aws_ec2_transit_gateway`; GCP `google_compute_network`/`_subnetwork`/`_firewall`/`_router` | the same concepts | the same mapping; [`detection-signals.md`](../netaudit/detection-signals.md) has the translation table |
| Bicep/ARM | the same resource types under `Microsoft.Network/*` | the same mapping |
| Cisco IOS/NX-OS `interface`, `ip address`, `switchport`, `channel-group`, `vlan` | addressing, L2 membership, LAGs | nodes, `l2-link` edges, `networks[]` |
| `router ospf` / `router bgp` / `ip route` | areas, neighbours, ASNs, statics | `l3-adjacency`/`route` edges with `attrs.protocol` |
| `ip access-list`, `access-group`, zone-based firewall | rule order, interface binding | `flows[]` |
| Junos `interfaces`, `protocols`, `security policies`, `security zones` | the same | the same |
| FortiOS `config system interface`, `config firewall policy`, `config router` | the same | the same |
| Kubernetes `NetworkPolicy`, `Service`, `Ingress`, CNI config | selectors, ingress/egress rules | `namespace` nodes, `flows[]`, `lb` nodes for Services of type LoadBalancer |
| docker-compose `networks:` | which service joins which network | `lan` nodes, edges from each service to its networks |
| IPAM export / IP plan spreadsheet | prefixes, owners, purpose | `networks[]`; reconcile against configs and report drift (audit-lenses §2) |
| Existing diagrams | claimed topology | a second model to diff against the recovered one, never a source of ✅ facts |

Then reconcile:

- [ ] Every network has a parent or is a top-level allocation. Every subnet is inside its parent (§3).
- [ ] Every node that forwards traffic has a zone. Every zone has at least one node.
- [ ] Every interface address falls inside a declared network. Addresses with no network are dark
  space (audit-lenses §3).
- [ ] Every flow binds to a zone that exists. Rules on unattached NSGs or ACLs not applied to any
  interface are dead policy: record them, but don't give them `flows[]` entries.
- [ ] Ask for, or infer and label, the critical pairs.
- [ ] Record which views the evidence supports. A cloud-only estate has no physical view; say so
  rather than inventing one.

## M4. Drills

**D1 — Hub and spoke, Terraform.** A hub VNet `10.0.0.0/16` holds `AzureFirewallSubnet` and
`GatewaySubnet`. Two spokes, `10.1.0.0/16` and `10.2.0.0/16`, are peered to the hub with
`use_remote_gateways = true`. Each spoke subnet has a route table that sends `0.0.0.0/0` to the
firewall's private IP. *Model:* 3 `vnet` nodes plus their `subnet` nodes, 2 `peering` edges, 1
`firewall` node in the hub, `route` edges from every spoke subnet to the firewall, 1 `gateway` node
with a `vpn` edge to `onprem`. *Findings to look for:* the firewall is an articulation point between
every spoke and on-prem unless it is zone-redundant (G4) — an Azure Firewall with `zones = ["1","2","3"]` in evidence is
`managed_ha`; a single NVA VM is not. Spoke-to-spoke traffic exists only through
the firewall (M2.3).

**D2 — Branch router, IOS.** One router has `Gi0/0` to the ISP, `Gi0/1.10` (`10.10.10.0/24`, users)
and `Gi0/1.99` (`10.10.99.0/24`, management), `ip route 0.0.0.0 0.0.0.0` to the ISP, and
`snmp-server community public RO`. *Model:* a `router` node, 2 `lan` nodes, an `l2-link` to an ISP
`gateway`, an `internet` node. *Findings:* a single uplink means the edge to the ISP is a bridge on the
users → internet critical pair (G4). Management shares the router with users and no ACL restricts it
(§12, §14). The SNMPv2c default community is recorded by the redactor (security.md).

**D3 — Kubernetes namespace with no policy.** Namespace `payments` has Deployments and a Service, and
no `NetworkPolicy`. *Model:* a `namespace` node in zone `payments`, plus an inferred `allow * →
payments` flow. *Finding:* no default-deny for the zone, so any compromised pod in the cluster reaches
payments (segmentation.md).

**D4 — Overlapping spokes.** Two spokes both use `10.1.0.0/16`. They were never peered with each
other, but both are peered to the hub. *Finding:* the overlap is between *reachable* networks (through
the hub), so it is High, not Medium (§3). The hub's routing cannot distinguish them.

**D5 — The diagram disagrees.** The existing Visio shows two internet uplinks. The configs show one
default route and one ISP interface. *Model:* the configs win. Record the diagram's claim as drift
(audit-lenses §2), and make the second uplink a 🔬 needs-data flag in case it exists on a device
outside the evidence set.
